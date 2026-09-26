#!/usr/bin/env python
"""Generate DriveDogs Economy's cargo-variety overrides from vanilla def/cargo/*.sui.

Rates are balanced per trailer load, not per unit: a job pays unit_reward_per_km x units loaded,
and units-per-trailer varies wildly between cargo types (a pickup "unit" is 62 kg, so a car
transporter carries 100 of them). Comparing unit_reward_per_km directly across cargo types is
meaningless - v1.1.0 did exactly that and inflated these categories 2.6x-8x per load.

Only writes files for cargo types an actual rule touches - everything else stays unshipped so
vanilla's rate keeps applying untouched.

Usage:
    python tools/generate_cargo_variety.py --vanilla-def-dir <path to extracted def.scs's def/>
"""
import argparse
import re
import statistics
from pathlib import Path

# Target per-load revenue per category, as a multiple of vanilla's all-cargo median load. Ranked
# by real ADR danger (explosives > toxic/infectious > corrosive > gases > flammable solids). Vanilla
# already pays every one of these a small premium per load (1.06x-1.28x); this widens it modestly.
# ADR class 3 (flammable liquids) is left out on purpose: vanilla already pays it 1.59x.
HAZMAT_TARGETS = {'1': 1.50, '6': 1.40, '8': 1.35, '2': 1.30, '4': 1.20}

# Vehicle-as-cargo carriers: vanilla pays these 1.11x per load - a small bump for specialized
# freight. Livestock is left out on purpose: vanilla already pays it 1.36x.
VEHICLE_CARRIER_FILES = {
    'car_balt1', 'car_balt2', 'car_d', 'car_f', 'car_gr', 'car_ibe', 'car_it', 'caravans', 'cars_fr',
    'mondeos', 'pickup_gr', 'vans_fd', 'vans_id', 'vans_vt', 'volvo_cars', 'horse_tr',
    'daf_tr', 'scania_tr', 'volvo_tr',
}
VEHICLE_CARRIER_TARGET = 1.25

# No single cargo may pay more per load than this multiple of the median (just above vanilla's
# own best-paying cargo, ~1.9x), and none may pay less than vanilla.
LOAD_CAP = 2.0

# High-value general cargo vanilla doesn't already flag: comp_process, med_equip and volvo_cars
# already carry valuable: true (see def/skill_data.sii's Valuable Cargo skill - its revenue bonus
# is already wired up in vanilla, so this is purely a skill-eligibility flag, not a rate change).
VALUABLE_FLAG_ONLY_FILES = {'electronics', 'caviar', 'truck_batt', 'truck_batt_c'}

NAME_RE = re.compile(r'^cargo_data:\s*cargo\.(\S+)', re.MULTILINE)
RATE_RE = re.compile(r'(\tunit_reward_per_km:\s*)([\d.]+)')
BODY_RE = re.compile(r'body_types\[\]:\s*(\S+)')
VALUABLE_LINE_RE = re.compile(r'^\tvaluable:\s*true\s*$', re.MULTILINE)


def field(text, key, default=None):
    m = re.search(rf'^\s*{key}:\s*([^\s#]+)', text, re.MULTILINE)
    return m.group(1) if m else default


def load_trailers(def_dir: Path):
    """Generic trailer_defs plus per-cargo ones (def/cargo/<id>/*.sii, owner = that cargo id)."""
    paths = [(p, None) for p in (def_dir / 'vehicle' / 'trailer_defs').glob('*.sii')]
    paths += [(p, p.parent.name) for p in (def_dir / 'cargo').glob('*/*.sii')]
    trailers = []
    for path, owner in paths:
        text = path.read_text(encoding='utf-8-sig')
        body, volume = field(text, 'body_type'), field(text, 'volume')
        if not body or not volume:
            continue
        payload = (float(field(text, 'gross_trailer_weight_limit', 0)) - float(field(text, 'chassis_mass', 0))
                   - float(field(text, 'body_mass', 0)))
        trailers.append({'owner': owner, 'body': body, 'volume': float(volume), 'payload': payload,
                         'chain': field(text, 'chain_type', 'single')})
    return trailers


def units_per_load(entry, cargo_id, trailers):
    """Median units a single trailer carries: limited by trailer volume, then by payload mass."""
    fits = [t for t in trailers if t['body'] in entry['bodies'] and t['owner'] in (None, cargo_id)]
    fits = [t for t in fits if t['chain'] == 'single'] or fits
    counts = []
    for t in fits:
        units = t['volume'] / entry['volume']
        if entry['mass'] > 0 and t['payload'] > 0:
            units = min(units, t['payload'] / entry['mass'])
        counts.append(int(units))
    return statistics.median(counts)


def load_vanilla(def_dir: Path):
    trailers = load_trailers(def_dir)
    cargo = {}
    for path in (def_dir / 'cargo').glob('*.sui'):
        text = path.read_text(encoding='utf-8-sig')
        m = NAME_RE.search(text)
        if not m:
            continue
        file_id = m.group(1)
        entry = {
            'text': text,
            'adr': field(text, 'adr_class'),
            'rate': float(RATE_RE.search(text).group(2)),
            'volume': float(field(text, 'volume', 1)),
            'mass': float(field(text, 'mass', 0)),
            'bodies': BODY_RE.findall(text),
        }
        entry['units'] = units_per_load(entry, file_id, trailers)
        entry['load'] = entry['rate'] * entry['units']
        cargo[file_id] = entry
    return cargo


def scale_group(cargo, file_ids, target, median_load):
    """Scale a group so its median load hits target x median_load, clamped to [vanilla, cap]."""
    scale = target * median_load / statistics.median(cargo[f]['load'] for f in file_ids)
    new_rates = {}
    for file_id in file_ids:
        entry = cargo[file_id]
        cap_rate = LOAD_CAP * median_load / entry['units']
        rate = round(min(entry['rate'] * scale, cap_rate), 3)
        if rate > entry['rate']:
            new_rates[file_id] = rate
    return new_rates


def build_new_rates(cargo):
    median_load = statistics.median(c['load'] for c in cargo.values())
    new_rates = {}
    for cls, target in HAZMAT_TARGETS.items():
        members = [f for f, c in cargo.items() if c['adr'] == cls]
        new_rates.update(scale_group(cargo, members, target, median_load))
    new_rates.update(scale_group(cargo, VEHICLE_CARRIER_FILES, VEHICLE_CARRIER_TARGET, median_load))
    return new_rates, median_load


def render(file_id, entry, new_rate, rule_comment):
    text = entry['text']
    if new_rate != entry['rate']:
        text = RATE_RE.sub(lambda m: f'{m.group(1)}{new_rate}', text, count=1)
        text = re.sub(
            r'(\n)(\tunit_reward_per_km:)',
            lambda m: f'{m.group(1)}\t# DDE: {rule_comment}\n{m.group(2)}',
            text, count=1,
        )
    if file_id in VALUABLE_FLAG_ONLY_FILES and not VALUABLE_LINE_RE.search(text):
        text = text.replace(
            '{\n',
            '{\n\t# DDE: flagged valuable - eligible for vanilla\'s existing Valuable Cargo skill '
            'revenue bonus (no base-rate change)\n\tvaluable: true\n',
            1,
        )
    return text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--vanilla-def-dir', required=True, type=Path)
    ap.add_argument('--out-dir', default=Path(__file__).resolve().parent.parent / 'src' / 'def' / 'cargo', type=Path)
    args = ap.parse_args()

    cargo = load_vanilla(args.vanilla_def_dir)
    new_rates, median_load = build_new_rates(cargo)

    touched = set(new_rates) | VALUABLE_FLAG_ONLY_FILES
    args.out_dir.mkdir(parents=True, exist_ok=True)

    for file_id in sorted(touched):
        entry = cargo[file_id]
        new_rate = new_rates.get(file_id, entry['rate'])
        new_load = new_rate * entry['units']
        per_load = f"{entry['load']:.1f} -> {new_load:.1f} EUR/km per load ({new_load / median_load:.2f}x median)"
        if file_id in VEHICLE_CARRIER_FILES:
            rule_comment = f"vanilla {entry['rate']} - vehicle-as-cargo carrier premium, {per_load}"
        elif entry['adr'] in HAZMAT_TARGETS:
            rule_comment = f"vanilla {entry['rate']} - ADR class {entry['adr']} hazmat premium, {per_load}"
        else:
            rule_comment = ''
        out_text = render(file_id, entry, new_rate, rule_comment)
        (args.out_dir / f'{file_id}.sui').write_text(out_text, encoding='utf-8', newline='\n')

    stale = sorted(p.stem for p in args.out_dir.glob('*.sui') if p.stem not in touched)
    print(f'Wrote {len(touched)} cargo files to {args.out_dir} (vanilla median load {median_load:.1f} EUR/km)')
    if stale:
        print(f'No longer touched by any rule - delete these to fall back to vanilla: {", ".join(stale)}')


if __name__ == '__main__':
    main()
