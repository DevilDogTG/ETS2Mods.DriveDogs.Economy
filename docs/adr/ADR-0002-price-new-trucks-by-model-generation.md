# ADR-0002: Price new trucks by model generation, big four parts only

**Date:** 2026-09-26
**Status:** accepted
**Deciders:** DevilDogTG (v1.2.0)

## Context
Vanilla 1.61 prices a truck only by the size of its parts, never by which generation of truck it
is. The four Volvo lines (FH16 2009, FH16 2012, FH 2021, FH 2024) share an identical cheapest
configuration of 62,260, and Scania R 2009, R 2016 and S 2016 are within 0.6% of each other. A
twenty-year-old design costs the same as its current replacement, so there is no value decision
between an older and a newer model.

The reference mod, Realistic Truck Dealer Prices (Comwil, v1.5.2), reprices the 17 legacy lines by
generation but touches ~5,769 files (every accessory, paint job and headlight) and leaves the nine
newer lines at vanilla price. It also discounts legacy lines heavily (~57-78% of vanilla), which
makes early-game trucks much cheaper.

Truck part defs live in ten archives: `def.scs` (17 legacy lines) and one free DLC archive per
newer line. Every big-four part file has exactly one `price:` line. Headlight files overlap Better
Flares, which every DriveDogs mod runs alongside; Frkn64's physics mod ships full copies of 190
chassis files.

## Options Considered

### Option A: Adopt Comwil's prices
- **Pros:** Already tuned by hand; generation logic is sound.
- **Cons:** Thousands of files and full overlap with Better Flares headlights; nine newest lines
  missing, so a 2024 truck would cost less than a 2016 one; legacy discounts make the game easier.

### Option B: Per-line multiplier over every priced part
- **Pros:** Covers the whole truck including accessories.
- **Cons:** Same headlight overlap as A and thousands of files to regenerate on every patch, for
  parts that make up a small share of a truck's price.

### Option C: Per-line multiplier over chassis, cabin, engine and transmission only
A generator reads every vanilla big-four file and applies one multiplier per line: a generation
tier base (G0 1990s 1.00, G1 2002-2009 1.05, G2 2012-2014 1.20, G3 2016-2022 1.35, G4 2024 1.50,
battery-electric 2.30 flat) plus a brand offset (Scania/Volvo +0.04, Mercedes +0.02, MAN/DAF 0,
Renault -0.05, Iveco -0.06) and a few model offsets (Streamline -0.06, DAF XD -0.05, Scania S
+0.05).
- **Pros:** 640 files, none shared with Better Flares; vanilla's within-line spread survives;
  all 26 lines covered; regenerates cleanly after a game patch.
- **Cons:** Accessories and paint stay at vanilla price; overlaps Frkn64's chassis files.

## Decision
Option C, anchored so the oldest lines sit at about vanilla (0.95-1.09) and each newer generation
costs more (up to 1.54, electric 2.30). A first draft anchored on Comwil's discounts (legacy
~0.72, cheapest new truck 54k -> 36k) was rejected: the goal is to reflect relative value, not to
make the game easier. Cargo pay was already made more meaningful (ADR-0001), so current models
are allowed to cost 30-54% more than vanilla.

## Consequences
**Easier:** Older models become a real value choice; tiers read directly as "x vanilla" and can
be retuned in one table.
**Harder:** Current-generation trucks, and fleet expansion with them, take longer to afford.
Regenerating needs the extracted `def/` of `def.scs` and all nine truck DLC archives.
**Follow-up:** Used listings follow the same curve (they are priced from part prices minus wear)
- confirm in playtest. Frkn64 physics must stay disabled, since its chassis copies carry vanilla
prices. A new SCS truck line needs a `LINES` entry before the generator will run.
