#!/usr/bin/env python
"""Generate DriveDogs Economy's new-truck dealer price overrides from vanilla truck defs.

Vanilla prices trucks by part size only, never by model generation: a 2009 Volvo FH16 and a 2024
FH share an identical cheapest configuration (62,260), and Scania R 2009 / R 2016 / S 2016 sit
within 0.6% of each other. This prices each truck line by the real-world generation it represents.

One multiplier per truck line, applied to every big-four part (chassis, cabin, engine,
transmission) of that line - so vanilla's within-line spread survives (a bigger engine still costs
proportionally more than a smaller one). Everything else (headlights, accessories, paint,
interiors) stays vanilla. Anchored so the oldest lines sit at ~vanilla and every newer generation
costs more: the game never gets cheaper, only the relative value of each line changes.

Used-truck listings are priced from these same part prices minus wear, so the multiplier carries
straight through to the used market too.

Vanilla truck defs live in more than one archive - def.scs holds the 17 legacy lines, each newer
line ships in its own free truck DLC (dlc_daf_2021.scs, dlc_volvo_fh_2024.scs, ...). Pass the
extracted def/ directory of every one of them.

Usage:
    python tools/generate_truck_prices.py --vanilla-def-dir <def.scs def/> --vanilla-def-dir <dlc def/> ...
"""
import argparse
import re
from pathlib import Path

PARTS = ('chassis', 'cabin', 'engine', 'transmission')

# Generation tier base multipliers. G0 = 1990s designs, G1 = 2002-2009 legacy, G2 = 2012-2014
# previous generation, G3 = 2016-2022 current, G4 = 2024. Battery-electric lines are flat 2.30 -
# real BEV tractors cost roughly 2-3x a diesel; 2.30 keeps them ~1.7x a current diesel here.
TIER_BASE = {'G0': 1.00, 'G1': 1.05, 'G2': 1.20, 'G3': 1.35, 'G4': 1.50, 'E': 2.30}

# Brand positioning on top of the tier (premium brands up, value brands down). Not applied to 'E'.
BRAND_OFFSET = {'scania': 0.04, 'volvo': 0.04, 'mercedes': 0.02, 'man': 0.0, 'daf': 0.0,
                'renault': -0.05, 'iveco': -0.06}

# line -> (tier, model offset, real-world design era). Within each brand the result only ever rises
# with generation.
LINES = {
    'renault.magnum':      ('G0', 0.0, '1990, last facelift 2008'),
    'renault.premium':     ('G0', 0.0, '1996, facelift 2006'),
    'iveco.stralis':       ('G1', 0.0, '2002, AS 2007'),
    'daf.xf':              ('G1', 0.0, '2005 XF105'),
    'man.tgx':             ('G1', 0.0, '2007'),
    'mercedes.actros':     ('G1', 0.0, '2008 MP3'),
    'scania.r':            ('G1', 0.0, '2009 R gen 3'),
    'volvo.fh16':          ('G1', 0.0, '2009 FH gen 3'),
    'iveco.hiway':         ('G2', 0.0, '2012'),
    'renault.t':           ('G2', 0.0, '2013'),
    'scania.streamline':   ('G2', -0.06, '2013 facelift of the 2009 R platform'),
    'daf.xf_euro6':        ('G2', 0.0, '2013 XF106'),
    'man.tgx_euro6':       ('G2', 0.0, '2012, facelift 2017'),
    'mercedes.actros2014': ('G2', 0.0, '2011/2014 MP4'),
    'volvo.fh16_2012':     ('G2', 0.0, '2012 FH gen 4'),
    'iveco.sway':          ('G3', 0.0, '2019'),
    'daf.xd':              ('G3', -0.05, '2022 distribution range'),
    'daf.2021':            ('G3', 0.0, '2021 XF/XG/XG+'),
    'man.tgx_2020':        ('G3', 0.0, '2020'),
    'scania.r_2016':       ('G3', 0.0, '2016 NTG'),
    'volvo.fh_2021':       ('G3', 0.0, '2020 FH gen 5'),
    'scania.s_2016':       ('G3', 0.05, '2016 NTG flagship over R'),
    'volvo.fh_2024':       ('G4', 0.0, '2024'),
    'daf.xf_electric':     ('E', 0.0, 'battery-electric'),
    'renault.etech_t':     ('E', 0.0, 'battery-electric 2023'),
    'scania.s_2024e':      ('E', 0.0, 'battery-electric 2024'),
}

PRICE_RE = re.compile(r'^(\tprice:\s*)(\d+)[ \t]*$', re.MULTILINE)


def multiplier(line):
    tier, model_offset, _ = LINES[line]
    brand = 0.0 if tier == 'E' else BRAND_OFFSET[line.split('.')[0]]
    return round(TIER_BASE[tier] + brand + model_offset, 2)


def load_vanilla(def_dirs):
    """Every big-four part file of every known line, keyed by its path under def/."""
    parts = {}
    for def_dir in def_dirs:
        for path in (def_dir / 'vehicle' / 'truck').glob('*/*/*.sii'):
            line, part = path.parent.parent.name, path.parent.name
            if part not in PARTS:
                continue
            if line not in LINES:
                raise SystemExit(f'Unknown truck line {line!r} in {def_dir} - add it to LINES first')
            rel = path.relative_to(def_dir)
            if rel in parts:
                raise SystemExit(f'{rel} found in more than one --vanilla-def-dir')
            parts[rel] = path.read_text(encoding='utf-8')
    missing = sorted(set(LINES) - {rel.parts[2] for rel in parts})
    if missing:
        raise SystemExit(f'No vanilla files found for: {", ".join(missing)} - pass every truck DLC def/ dir')
    return parts


def render(text, line):
    matches = PRICE_RE.findall(text)
    if len(matches) != 1:
        raise ValueError(f'expected exactly one price line, found {len(matches)}')
    vanilla = int(matches[0][1])
    mult = multiplier(line)
    new = int(round(vanilla * mult, -1))
    tier, _, era = LINES[line]
    comment = f'\t# DDE: vanilla {vanilla} - {tier} ({era}) x{mult:.2f}\n'
    return PRICE_RE.sub(lambda m: f'{comment}{m.group(1)}{new}', text, count=1), vanilla, new


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--vanilla-def-dir', required=True, action='append', type=Path)
    ap.add_argument('--out-dir', default=Path(__file__).resolve().parent.parent / 'src' / 'def', type=Path)
    args = ap.parse_args()

    parts = load_vanilla(args.vanilla_def_dir)
    written = set()
    for rel, text in sorted(parts.items()):
        try:
            out_text, _, _ = render(text, rel.parts[2])
        except ValueError as e:
            raise SystemExit(f'{rel}: {e}')
        out = args.out_dir / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(out_text, encoding='utf-8', newline='\n')
        written.add(out)

    truck_root = args.out_dir / 'vehicle' / 'truck'
    stale = sorted(str(p.relative_to(args.out_dir)) for p in truck_root.glob('*/*/*.sii') if p not in written)
    print(f'Wrote {len(written)} truck part files across {len(LINES)} lines to {truck_root}')
    if stale:
        print(f'No longer generated - delete these to fall back to vanilla: {", ".join(stale)}')


if __name__ == '__main__':
    main()
