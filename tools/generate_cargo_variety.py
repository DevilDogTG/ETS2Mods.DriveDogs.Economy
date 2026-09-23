#!/usr/bin/env python
"""Generate DriveDogs Economy's cargo-variety overrides from vanilla def/cargo/*.sui.

Only writes files for cargo types an actual rule touches - everything else stays
unshipped so vanilla's (already mass-correlated) rate keeps applying untouched.

Usage:
    python tools/generate_cargo_variety.py --vanilla-cargo-dir <path to extracted def/cargo>
"""
import argparse
import re
from pathlib import Path

# ADR hazmat classes present in vanilla cargo, target class-average EUR/km ranked by real-world
# danger (explosives > toxic/infectious > corrosive > gases > flammable liquids > flammable solids),
# landing near vanilla's overall cargo average (1.76 EUR/km) rather than far beyond it. Capped so a
# single pre-existing vanilla outlier (e.g. a tanker variant) can't get amplified into an absurd rate.
HAZMAT_TARGETS = {'1': 2.75, '6': 2.45, '8': 2.20, '2': 1.95, '3': 1.75, '4': 1.55}
HAZMAT_CAP = 3.3

# Vehicle-as-cargo carriers: vanilla prices every one of these near-identically low regardless of
# type (cars, vans, pickups, caravans, horse trailers, even trucks-as-cargo), ignoring that hauling
# vehicles is specialized, higher-value freight in practice.
VEHICLE_CARRIER_FILES = {
    'car_balt1', 'car_balt2', 'car_d', 'car_f', 'car_gr', 'car_ibe', 'car_it', 'caravans', 'cars_fr',
    'mondeos', 'pickup_gr', 'vans_fd', 'vans_id', 'vans_vt', 'volvo_cars', 'horse_tr',
    'daf_tr', 'scania_tr', 'volvo_tr',
}
VEHICLE_CARRIER_TARGET = 0.85

# Live animal transport: vanilla prices this like generic freight, ignoring welfare/time-sensitivity
# requirements real livestock haulage carries.
LIVESTOCK_FILES = {'live_cattle', 'live_pigs'}
LIVESTOCK_TARGET = 1.10

# High-value general cargo vanilla doesn't already flag: comp_process, med_equip and volvo_cars
# already carry valuable: true (see def/skill_data.sii's Valuable Cargo skill - its revenue bonus
# is already wired up in vanilla, so this is purely a skill-eligibility flag, not a rate change).
VALUABLE_FLAG_ONLY_FILES = {'electronics', 'caviar', 'truck_batt', 'truck_batt_c'}

NAME_RE = re.compile(r'^cargo_data:\s*cargo\.(\S+)', re.MULTILINE)
ADR_RE = re.compile(r'adr_class:\s*(\S+)')
RATE_RE = re.compile(r'(\tunit_reward_per_km:\s*)([\d.]+)')
VALUABLE_LINE_RE = re.compile(r'^\tvaluable:\s*true\s*$', re.MULTILINE)


def load_vanilla(vanilla_dir: Path):
    cargo = {}
    for path in vanilla_dir.glob('*.sui'):
        text = path.read_text(encoding='utf-8-sig')
        m = NAME_RE.search(text)
        if not m:
            continue
        file_id = m.group(1)
        adr_m = ADR_RE.search(text)
        rate_m = RATE_RE.search(text)
        cargo[file_id] = {
            'text': text,
            'adr': adr_m.group(1) if adr_m else None,
            'rate': float(rate_m.group(2)) if rate_m else None,
        }
    return cargo


def class_average(cargo, cls):
    items = [c['rate'] for c in cargo.values() if c['adr'] == cls]
    return sum(items) / len(items)


def group_average(cargo, file_ids):
    items = [cargo[f]['rate'] for f in file_ids]
    return sum(items) / len(items)


def build_new_rates(cargo):
    new_rates = {}

    class_avgs = {cls: class_average(cargo, cls) for cls in HAZMAT_TARGETS}
    for file_id, entry in cargo.items():
        if entry['adr'] in HAZMAT_TARGETS:
            scale = HAZMAT_TARGETS[entry['adr']] / class_avgs[entry['adr']]
            new_rates[file_id] = min(round(entry['rate'] * scale, 3), HAZMAT_CAP)

    veh_avg = group_average(cargo, VEHICLE_CARRIER_FILES)
    veh_scale = VEHICLE_CARRIER_TARGET / veh_avg
    for file_id in VEHICLE_CARRIER_FILES:
        new_rates[file_id] = round(cargo[file_id]['rate'] * veh_scale, 3)

    live_avg = group_average(cargo, LIVESTOCK_FILES)
    live_scale = LIVESTOCK_TARGET / live_avg
    for file_id in LIVESTOCK_FILES:
        new_rates[file_id] = round(cargo[file_id]['rate'] * live_scale, 3)

    return new_rates


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
    ap.add_argument('--vanilla-cargo-dir', required=True, type=Path)
    ap.add_argument('--out-dir', default=Path(__file__).resolve().parent.parent / 'src' / 'def' / 'cargo', type=Path)
    args = ap.parse_args()

    cargo = load_vanilla(args.vanilla_cargo_dir)
    new_rates = build_new_rates(cargo)

    touched = set(new_rates) | VALUABLE_FLAG_ONLY_FILES
    args.out_dir.mkdir(parents=True, exist_ok=True)

    for file_id in sorted(touched):
        entry = cargo[file_id]
        new_rate = new_rates.get(file_id, entry['rate'])
        if entry['adr'] in HAZMAT_TARGETS:
            rule_comment = f"vanilla {entry['rate']} - ADR class {entry['adr']} hazmat base-rate fix, scaled to class target"
        elif file_id in VEHICLE_CARRIER_FILES:
            rule_comment = f"vanilla {entry['rate']} - vehicle-as-cargo carrier premium (specialized/higher-value freight)"
        elif file_id in LIVESTOCK_FILES:
            rule_comment = f"vanilla {entry['rate']} - livestock transport premium (welfare/time-sensitivity)"
        else:
            rule_comment = ''
        out_text = render(file_id, entry, new_rate, rule_comment)
        (args.out_dir / f'{file_id}.sui').write_text(out_text, encoding='utf-8', newline='\n')

    print(f'Wrote {len(touched)} cargo files to {args.out_dir}')


if __name__ == '__main__':
    main()
