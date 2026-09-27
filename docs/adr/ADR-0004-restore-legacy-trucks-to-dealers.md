# ADR-0004: Restore legacy trucks to the dealers with generated presets

**Date:** 2026-09-27
**Status:** accepted
**Deciders:** DevilDogTG (v1.3.0)

## Context
Recent game versions removed the eleven legacy truck lines (DAF XF105, Iveco Stralis and Hi-Way,
MAN TGX Euro 5, Mercedes Actros MP3, Renault Magnum and Premium, Scania R 2009 and Streamline,
Volvo FH16 2009 and 2012) from the dealers. Their parts still ship in `def.scs` and owned trucks
keep working, but a dealer only offers a model it has a preset for
(`def/vehicle/truck_dealer{,_uk}/<brand>/*.sii`), and vanilla 1.61 has none for these lines.
ADR-0002 already prices them as the cheap end of the generation curve (~1.00-1.24x vanilla), so
without them that end of the curve can't be bought new.

The reference mod, Restore Old Trucks (Baldy09, Workshop 3097032249, v1.1 "1.57+"), ships 207
dealer presets. Against vanilla 1.61: 101 add the legacy lines (2 point at a rear bumper that no
longer exists), 88 are identical re-ships of vanilla and DLC presets, and 18 replace current
Scania R/S 2016 and Renault T presets with older copies (16 point at a Scania logo file 1.61
renamed, and they drop 1.61 accessories). Its author forbids re-uploading it.

## Options Considered

### Option A: Run Restore Old Trucks alongside this mod
- **Pros:** No work.
- **Cons:** The 18 stale overrides downgrade current Scania 2016 / Renault T dealer trucks; broken
  references; another mod every player has to load and keep in sync.

### Option B: Copy its legacy presets into this mod
- **Pros:** Hand-made configurations, quick.
- **Cons:** Redistributes files the author asked not to be re-uploaded; breaks this repo's rule of
  never adopting a reference mod wholesale; the broken references come with it and nothing
  catches the next rename.

### Option C: Generate presets from vanilla defs
`tools/generate_dealer_presets.py` builds each preset from a short hand-authored table (chassis,
cabin, engine, transmission, paint, optional interior/headlight) plus the game's own `defaults[]`
of the chosen chassis and cabin, the line's `require[]` / `fallback[]`, and fallback wheels per
axle group. The UK preset swaps in the right-hand-drive interior.
- **Pros:** Only vanilla 1.61 parts; fails on any missing file, broken `suitable_for` /
  `conflict_with` rule, empty required slot or wrong-side interior; never uses a vanilla file
  path, so current presets can't be overridden; regenerates after a patch.
- **Cons:** Presets carry the stock default accessories only, no badges or styling extras, so
  they look plainer than vanilla's hand-made ones.

## Decision
Option C, for the 11 legacy lines only, at both EU and UK dealers: 3-4 presets per line (entry,
mid, flagship, and a multi-axle where the line offers one), 42 per dealer. Files are
`dde_<line>_<n>.sii`. Pricing is unchanged: ADR-0002 already covers every one of these lines, and
the generator refuses a line that `generate_truck_prices.py` doesn't price. Restore Old Trucks was
used only as a reference for which configurations make sense.

## Consequences
**Easier:** The cheap end of the generation curve can be bought new, so a new player can pick an
older, cheaper truck. The used market is expected to list legacy trucks too (it appears to draw on
dealer presets; confirm in playtest).
**Harder:** A game patch that renames a legacy part fails the generator until the table is
updated. Restore Old Trucks must stay disabled next to this mod: its stale overrides would win or
lose depending on load order.
**Follow-up:** Playtest the multi-axle presets' wheels (offsets inferred from vanilla's own
multi-axle presets) and check `game.log` for accessory errors.
