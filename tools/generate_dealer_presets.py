#!/usr/bin/env python
"""Generate DriveDogs Economy's legacy-truck dealer presets from vanilla truck defs.

Recent game versions dropped the legacy truck lines (DAF XF105, Scania R 2009, Volvo FH16 2009,
...) from the dealers: their parts still ship in def.scs and owned trucks keep working, but a
dealer only offers a model it has a preset for (def/vehicle/truck_dealer{,_uk}/<brand>/*.sii).
This writes presets for the eleven legacy lines back, EU and UK (right-hand drive).

Every preset is built only from vanilla 1.61 parts:
  - chassis / cabin / engine / transmission (and optionally interior, headlight, paint) come from
    the hand-authored PRESETS table below;
  - the remaining accessories are the game's own `defaults[]` of the chosen chassis and cabin;
  - any `require[]` slot of the line's data.sii still empty is filled from its `fallback[]`, then
    the first suitable file in that accessory folder;
  - wheels are the data.sii fallback wheels, one set per axle group (steerable axles take front
    wheels, the rest rear wheels; each extra axle in a group sits at offset 2, as vanilla does).
The UK preset is the EU one with the right-hand-drive interior.

The run fails - writing nothing - on any data_path that does not resolve, a part whose
suitable_for/conflict_with rules the configuration breaks, an unfilled required slot, an interior
on the wrong side, or an output path vanilla already uses. New-truck prices for these lines come
from tools/generate_truck_prices.py (ADR-0002); every line here must be priced there too.

Usage:
    python tools/generate_dealer_presets.py --vanilla-def-dir <def.scs def/> --vanilla-def-dir <dlc def/> ...
"""
import argparse
import re
from pathlib import Path

from generate_truck_prices import LINES as PRICED_LINES

# line -> (unit code, presets). Each preset: chassis, cabin, engine, transmission, paint job, then
# optional overrides {'interior', 'head_light'} (defaults: the cabin's own defaults) and
# 'base_color' (r, g, b) for an unlocked (custom colour) paint job. One entry,
# one mid-range, one flagship tractor per line plus a multi-axle, where the line offers them.
PRESETS = {
    'daf.xf': ('xf105', [
        ('4x2', 'space_cab', 'mx300', '12_speed', 'color1', {}),
        ('4x2', 'space_cab_plus', 'mx340', '12_speed_ret', 'color3', {}),
        ('4x2', 'super_space_cab', 'mx375', 'zf_16as2631to', 'color5', {'interior': 'exclusive', 'head_light': 'xenon'}),
        ('6x2', 'super_space_cab', 'mx375', '12_speed_ret', 'color2', {}),
    ]),
    'iveco.stralis': ('stralis', [
        ('4x2', 'active_time', 'cursor8_330hp', '12_speed', 'color1', {}),
        ('4x2', 'active_time_higher', 'cursor10_450hp', '12_speed_ret', 'color3', {}),
        ('4x2', 'active_space_higher', 'cursor13_560hp', 'zf_16as2631to', 'color5', {'interior': 'exclusive', 'head_light': 'xenon'}),
        ('6x2a', 'active_time_higher', 'cursor13_500hp', '12_speed_ret', 'color2', {}),
    ]),
    'iveco.hiway': ('hiway', [
        ('4x2', 'hiway_cab', 'cursor11_460hp', '12_speed_r', 'color1', {}),
        ('4x2', 'hiway_cab', 'cursor13_560hp', 'zf_16as2631to', 'color3', {'head_light': 'xenon'}),
        ('6x2a', 'hiway_cab', 'cursor13_500hp', '12_speed_r', 'color2', {}),
    ]),
    'man.tgx': ('tgx5', [
        ('4x2', 'xl_cab', 'd2066_294', '12_speed', 'color1', {}),
        ('4x2', 'xlx_cab', 'd2676_397', '12_speed_ret', 'color3', {}),
        ('4x2', 'xxl_cab', 'd2868_500', 'zf_16as2631to', 'color5', {'interior': 'exclusive', 'head_light': 'xenon'}),
        ('6x2_4', 'xxl_cab', 'd2676_397', '12_speed_ret', 'color2', {}),
    ]),
    'mercedes.actros': ('mp3', [
        ('4x2c', 'cabin_l_lw', '1841ls', '12_speed', 'color1', {}),
        ('4x2c', 'cabin_l', '1846ls', '12_speed_ret', 'color3', {}),
        ('4x2a', 'megaspace', '1860ls', 'g280_16_r', 'color5', {'interior': 'exclusive', 'head_light': 'xenon'}),
        ('6x2_4a', 'megaspace', '1851ls', '12_speed_ret', 'color2', {}),
    ]),
    # The Renault legacy lines have a single stock colour; the rest use the custom (color0) and
    # custom metallic (color0m) paint jobs with a base_color.
    'renault.magnum': ('magnum', [
        ('4x2', 'solo', 'dxi13_440', '12_speed_ret', 'color1', {}),
        ('4x2', 'solo', 'dxi13_520', 'zf_16as2631to', 'color0m', {'head_light': 'xenon', 'base_color': (0.05, 0.12, 0.35)}),
        ('6x2_4', 'solo', 'dxi13_480', '12_speed_ret', 'color0', {'base_color': (0.70, 0.04, 0.03)}),
    ]),
    'renault.premium': ('premium', [
        ('4x2', 'normal', 'dxi11_380', '12_speed', 'color1', {}),
        ('4x2', 'higher', 'dxi11_430', '12_speed_ret', 'color0', {'base_color': (0.83, 0.83, 0.83)}),
        ('4x2', 'higher', 'dxi11_460', '12_speed_ret', 'color0m', {'interior': 'expensive', 'head_light': 'xenon', 'base_color': (0.02, 0.02, 0.02)}),
        ('6x2_4', 'higher', 'dxi11_460', '12_speed_ret', 'color0', {'base_color': (0.95, 0.60, 0.02)}),
    ]),
    'scania.r': ('r2009', [
        ('4x2', 'normal', 'dc13_400', '12_speed', 'color1', {}),
        ('4x2', 'highline', 'dc13_480', 'grso925_r', 'color3', {}),
        ('4x2', 'topline', 'dc16_620', 'grso925_r', 'color5', {'interior': 'exclusive', 'head_light': 'xenon'}),
        ('8x4', 'tl_8x4', 'dc16_560', 'grso925_r', 'color2', {}),
    ]),
    'scania.streamline': ('strmline', [
        ('4x2', 'highline', 'dc13_450', '12_speed_ret', 'color1', {}),
        ('4x2', 'topline', 'dc13_490', 'grso925_r', 'color3', {}),
        ('4x2', 'topline', 'dc16_730', 'grso925_r', 'color5', {'interior': 'topline_v8', 'head_light': 'xenon'}),
        ('6x2_midlift', 'topline', 'dc16_580', 'grso925_r', 'color2', {'interior': 'topline_exp'}),
    ]),
    'volvo.fh16': ('fh2009', [
        ('4x2', 'l2h1', 'd13c420', '12_speed', 'color1', {}),
        ('4x2', 'l2h2', 'd13c500', 'ato3512f_r_aso', 'color3', {}),
        ('4x2', 'l2h3', 'd16g700', 'ato3512f_r_aso', 'color5', {'interior': 'exclusive', 'head_light': 'xenon'}),
        ('6x2', 'l2h3', 'd13c540', 'ato3512f_r_aso', 'color2', {}),
    ]),
    'volvo.fh16_2012': ('fh2012', [
        ('4x2', 'l2h1', 'd13c460', '12_speed', 'color1', {}),
        ('4x2', 'l2h2', 'd13k460', 'ato3512f_r_aso', 'color3', {}),
        ('4x2', 'l2h3', 'd16g750', 'ato3512f_r_aso', 'color5', {'interior': 'exclusive', 'head_light': 'xenon'}),
        ('8x4', 'l2h3_8x4', 'd16g600', 'ato3512f_r_aso', 'color2', {}),
    ]),
}

WHEEL_PARTS = ('tire', 'disc', 'hub', 'nuts')
DEALERS = {'truck_dealer': False, 'truck_dealer_uk': True}  # folder -> right-hand drive
UNIT_TOKEN_RE = re.compile(r'^[a-z0-9_]{1,12}$')


class Defs:
    """Read-only view over every --vanilla-def-dir, addressed by game path (/def/...)."""

    def __init__(self, def_dirs):
        self.def_dirs = def_dirs
        self.cache = {}

    def find(self, game_path):
        rel = game_path.removeprefix('/def/')
        for d in self.def_dirs:
            if (d / rel).is_file():
                return d / rel
        return None

    def read(self, game_path):
        if game_path not in self.cache:
            path = self.find(game_path)
            if path is None:
                raise LookupError(f'{game_path} does not exist in any --vanilla-def-dir')
            self.cache[game_path] = path.read_text(encoding='utf-8', errors='replace')
        return self.cache[game_path]

    def unit(self, game_path):
        m = re.search(r'^\s*accessory_\w+\s*:\s*([\w.]+)', self.read(game_path), re.MULTILINE)
        if not m:
            raise LookupError(f'{game_path}: no accessory unit found')
        return m.group(1)

    def values(self, game_path, key):
        return re.findall(rf'^\s*{key}\[\]\s*:\s*"?([^"\n]+?)"?\s*$', self.read(game_path), re.MULTILINE)

    def listdir(self, game_path):
        rel = game_path.removeprefix('/def/')
        names = set()
        for d in self.def_dirs:
            if (d / rel).is_dir():
                names.update(p.name for p in (d / rel).glob('*.sii'))
        return sorted(names)


def truck(line, *parts):
    return '/def/vehicle/truck/' + '/'.join((line,) + parts)


def resolve_fallback(defs, line, entry):
    """A data.sii fallback 'slot|file' entry -> game path."""
    slot, file = entry.split('|', 1)
    candidates = [truck(line, 'accessory', file)] if slot == 'accessory' else [
        truck(line, slot, file), truck(line, 'accessory', slot, file), f'/def/vehicle/{slot}/{file}']
    for c in candidates:
        if defs.find(c):
            return c
    raise LookupError(f'{line}: fallback {entry!r} does not resolve')


def uk_interior(defs, line, interior):
    base = interior.removesuffix('.sii')
    for name in (f'{base}_uk', base.replace('_', '_uk_', 1)):
        path = truck(line, 'interior', f'{name}.sii')
        if defs.find(path):
            return path
    raise LookupError(f'{line}: no right-hand-drive interior for {interior}')


def wheel_sets(defs, line, chassis):
    """[(slot, offset, game path)] - one set per axle group, per vanilla's multi-axle presets."""
    powered = defs.values(chassis, 'powered_axle')
    if not powered:
        raise LookupError(f'{chassis}: no powered_axle[] to count axles from')
    steer = defs.values(chassis, 'steerable_axle') or ['true'] + ['false'] * (len(powered) - 1)
    fallback = dict(e.split('|', 1) for e in defs.values(truck(line, 'data.sii'), 'fallback'))
    sets, seen = [], {'f': 0, 'r': 0}
    for s in steer:
        side = 'f' if s == 'true' else 'r'
        n = seen[side]
        seen[side] += 1
        for part in WHEEL_PARTS:
            slot = f'{side}_{part}'
            sets.append((f'{side}{part}{n + 1 if n else ""}', 2 * n, f'/def/vehicle/{slot}/{fallback[slot]}'))
    return sets


def build(defs, line, preset, rhd):
    """One preset -> (entries, errors). entries: [(unit kind, slot, extra lines, game path)]."""
    chassis, cabin, engine, trans, paint, opts = preset
    p = {
        'data': truck(line, 'data.sii'),
        'chassis': truck(line, 'chassis', f'{chassis}.sii'),
        'cabin': truck(line, 'cabin', f'{cabin}.sii'),
        'engine': truck(line, 'engine', f'{engine}.sii'),
        'transmission': truck(line, 'transmission', f'{trans}.sii'),
        'paint_job': truck(line, 'paint_job', f'{paint}.sii'),
    }
    for path in p.values():
        defs.read(path)

    addons = {}  # accessory folder (slot) -> game path
    for source in (p['chassis'], p['cabin']):
        for d in defs.values(source, 'defaults'):
            kind = d.split('/')[5]
            if kind in ('interior', 'head_light') and kind not in p:
                p[kind] = d
            elif kind == 'accessory':
                addons.setdefault(d.split('/')[6], d)
    def suitable(path, units):
        s, c = defs.values(path, 'suitable_for'), defs.values(path, 'conflict_with')
        return (not s or set(s) & units) and not set(c) & units

    for kind in ('interior', 'head_light'):
        if kind in opts:
            p[kind] = truck(line, kind, f'{opts[kind]}.sii')
        if kind not in p:
            # cabin names no default: data.sii fallback, else the first left-hand-drive part
            # that suits the chosen chassis and cabin
            fb = [resolve_fallback(defs, line, e) for e in defs.values(p['data'], 'fallback')
                  if e.split('|', 1)[0] == kind]
            options = fb + [truck(line, kind, f) for f in defs.listdir(truck(line, kind))
                            if not f.removesuffix('.sii').endswith('_uk') and '_uk_' not in f]
            units = {defs.unit(p['chassis']), defs.unit(p['cabin'])}
            p[kind] = next((o for o in options if suitable(o, units)), None)
            if p[kind] is None:
                raise LookupError(f'{line} {chassis}/{cabin}: no suitable {kind}')
    if rhd:
        p['interior'] = uk_interior(defs, line, p['interior'].rsplit('/', 1)[1])

    selected = {defs.unit(v) for k, v in p.items() if k != 'data'}
    errors = []

    for slot in defs.values(p['data'], 'require'):
        if slot in addons:
            continue
        fb = [e for e in defs.values(p['data'], 'fallback') if e.split('|', 1)[1].startswith(f'{slot}/')
              or e.split('|', 1)[0] == slot]
        options = [resolve_fallback(defs, line, e) for e in fb]
        options += [truck(line, 'accessory', slot, f) for f in defs.listdir(truck(line, 'accessory', slot))]
        pick = next((o for o in options if suitable(o, selected)), None)
        if pick is None:
            errors.append(f'required slot {slot!r} has no suitable part')
        else:
            addons[slot] = pick

    units = selected | {defs.unit(v) for v in addons.values()}
    for path in list(p.values())[1:] + list(addons.values()):
        if not suitable(path, units):
            errors.append(f'{path} is not suitable for this configuration')
    locked = re.search(r'^\s*base_color_locked:\s*true', defs.read(p['paint_job']), re.MULTILINE)
    if 'base_color' in opts and locked:
        errors.append(f'{p["paint_job"]} has a locked colour - base_color would be ignored')
    lht = bool(re.search(r'^\s*left_hand_traffic:\s*true', defs.read(p['interior']), re.MULTILINE))
    if lht != rhd:
        errors.append(f'{p["interior"]} is {"right" if lht else "left"}-hand drive')

    entries = [('vehicle_accessory', k, [], p[k])
               for k in ('data', 'chassis', 'cabin', 'interior', 'engine', 'transmission', 'head_light')]
    color = [f'base_color: ({", ".join(f"{c:.4f}" for c in opts["base_color"])})'] if 'base_color' in opts else []
    entries.append(('vehicle_paint_job_accessory', 'paint_job', color, p['paint_job']))
    entries += [('vehicle_wheel_accessory', slot, [f'offset: {off}'], path)
                for slot, off, path in wheel_sets(defs, line, p['chassis'])]
    entries += [('vehicle_addon_accessory', slot, [], path) for slot, path in sorted(addons.items())]
    for _, _, _, path in entries:
        if not defs.find(path):
            errors.append(f'{path} does not exist')
    return entries, errors


def render(line, preset, entries, unit, rhd):
    chassis, cabin, engine, trans, _, _ = preset
    out = ['SiiNunit', '{',
           f'# DDE: legacy {line} restored to the {"UK " if rhd else ""}dealer - {chassis} / {cabin} / '
           f'{engine} / {trans}.',
           '# Generated by tools/generate_dealer_presets.py from vanilla 1.61 parts - do not edit by hand.',
           f'vehicle: .ddetd.{unit}', '{']
    out += [f'\taccessories[]: .{unit}.{slot}' for _, slot, _, _ in entries]
    out.append('}')
    for kind, slot, extra, path in entries:
        out += ['', f'{kind} : .{unit}.{slot} {{'] + [f'\t{e}' for e in extra] + [f'\tdata_path: "{path}"', '}']
    out.append('}')
    return '\n'.join(out) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--vanilla-def-dir', required=True, action='append', type=Path)
    ap.add_argument('--out-dir', default=Path(__file__).resolve().parent.parent / 'src' / 'def', type=Path)
    args = ap.parse_args()
    defs = Defs(args.vanilla_def_dir)

    files, errors = {}, []
    for line, (code, presets) in PRESETS.items():
        if line not in PRICED_LINES:
            errors.append(f'{line}: not priced by generate_truck_prices.py - add it to LINES there first')
        brand = line.split('.')[0]
        for i, preset in enumerate(presets, 1):
            for dealer, rhd in DEALERS.items():
                unit = f'dd{code}{i}{"u" if rhd else ""}'
                rel = Path('vehicle', dealer, brand, f'dde_{line.replace(".", "_")}_{i}.sii')
                label = f'{rel.as_posix()}'
                try:
                    entries, errs = build(defs, line, preset, rhd)
                except LookupError as e:
                    errors.append(f'{label}: {e}')
                    continue
                errors += [f'{label}: {e}' for e in errs]
                bad = [t for _, slot, _, _ in entries for t in (unit, slot) if not UNIT_TOKEN_RE.match(t)]
                if bad:
                    errors.append(f'{label}: unit name tokens too long or invalid: {sorted(set(bad))}')
                if defs.find('/def/' + rel.as_posix()):
                    errors.append(f'{label}: vanilla already ships this path')
                files[rel] = render(line, preset, entries, unit, rhd)
    if errors:
        raise SystemExit('Nothing written:\n  ' + '\n  '.join(errors))

    for rel, text in files.items():
        out = args.out_dir / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding='utf-8', newline='\n')
    stale = sorted(str(p.relative_to(args.out_dir)) for dealer in DEALERS
                   for p in (args.out_dir / 'vehicle' / dealer).glob('*/dde_*.sii')
                   if p.relative_to(args.out_dir) not in files)
    print(f'Wrote {len(files)} dealer presets ({len(files) // 2} per dealer) for {len(PRESETS)} legacy lines')
    if stale:
        print(f'No longer generated - delete these: {", ".join(stale)}')


if __name__ == '__main__':
    main()
