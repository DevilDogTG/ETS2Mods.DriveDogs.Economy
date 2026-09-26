# ADR-0001: Balance cargo pay per trailer load, not per unit

**Date:** 2026-09-26
**Status:** accepted
**Deciders:** DevilDogTG (PR #4, v1.1.1)

## Context
Cargo Variety (v1.1.0) rebalanced hazmat, vehicle-carrier and livestock pay by comparing each
cargo's `unit_reward_per_km` against the others. In-game, car-transporter jobs then paid
~EUR 166/km against ~EUR 20-39/km for ordinary jobs, and ADR class 6 cargo would have paid ~8x an
ordinary load.

A job pays `unit_reward_per_km x units loaded`, and units per trailer vary by two orders of
magnitude between cargo types: a trailer carries `min(trailer volume / cargo volume, trailer
payload / cargo mass)` units, so a car transporter holds 100 pickups at 62 kg each. A low per-unit
rate is usually offset by a high unit count. Measured per load, vanilla already paid all three
categories a small premium (1.06x-1.59x the median load); the "vanilla underpays hazmat" finding
existed only under the per-unit metric.

## Options Considered

### Option A: Revert Cargo Variety to vanilla rates
- **Pros:** Simplest; vanilla's per-load ordering is already sensible.
- **Cons:** Drops the intended danger-ranked hazmat premium entirely.

### Option B: Keep per-unit targets, just lower them
- **Pros:** Small change to the existing generator.
- **Cons:** Still the wrong metric; per-item results stay erratic because unit counts differ
  within each category.

### Option C: Target per-load revenue relative to vanilla's median load
The generator reads vanilla `trailer_defs`, computes median units per single trailer for each cargo,
and scales each category so its median load hits a multiple of vanilla's all-cargo median load.
- **Pros:** Measures what the player is actually paid; targets read directly as "Nx an ordinary
  job"; clamping each cargo between vanilla and 2x median bounds outliers.
- **Cons:** Unit counts are a median across matching trailers, so an approximation; the generator
  now depends on vanilla trailer data too.

## Decision
Option C: category targets are set per trailer load (ADR 1 1.5x, ADR 6 1.4x, ADR 8 1.35x,
ADR 2 1.3x, ADR 4 1.2x, vehicle carriers 1.25x), clamped to [vanilla rate, 2x median load].
ADR 3 and livestock stay vanilla because they already pay a premium. Per-load is the only
comparison that matches in-game pay.

## Consequences
**Easier:** Future rebalances (including a separate add-on cargo-pack mod) can state targets as
multiples of an ordinary job and verify them numerically before playtesting.
**Harder:** Regenerating needs the extracted vanilla `def/` root (cargo and
`vehicle/trailer_defs`), not just `def/cargo`.
**Follow-up:** Any cargo-pack mod that adds new trailers must include those trailer_defs in the
unit-count calculation.
