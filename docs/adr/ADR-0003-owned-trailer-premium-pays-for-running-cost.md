# ADR-0003: The owned-trailer premium pays for a running cost

**Date:** 2026-09-26
**Status:** accepted
**Deciders:** DevilDogTG (v1.2.1-v1.2.2)

## Context
v1.0.0 raised `cargo_market_revenue_coef_per_km` from vanilla 1.0 to 1.4 against Freight Market's
0.9, so owning the trailer paid 1.56x a company trailer (vanilla 1.11x). In playtest a single reefer
on the Cargo Market paid several times what the same trip paid without the mod.

An owned trailer maps to the same `trailer_def` as the company trailer of that size
(`trailer_owned/scs.box/configurations/single_3/curtain.sii` -> `trailer_def.scs.box.single_3.curtain`),
so for the same cargo the unit count is identical and the coefficient is the only market-specific
lever. Bigger owned trailers (doubles, B-doubles, HCT) pay more because they load more units, the
same as company doubles in vanilla; no per-chain coefficient exists.

The premium also paid for nothing ongoing: owned trailers only wore their tyres (vanilla
`trailer_body_wear` / `trailer_chassis_wear` are 0), and every trailer got the same percentage
whether it cost 25k (single_3 curtainsider) or 80k (single_3 reefer).

## Options Considered

### Option A: Add running cost only
- **Pros:** Gives the premium a reason; repair bills follow trailer price.
- **Cons:** Left at 1.4, the gross premium is still the largest in the economy.

### Option B: Lower the coefficient only (1.0-1.1)
- **Pros:** Simplest.
- **Cons:** Still a flat bonus with no cost behind it, identical for cheap and expensive trailers.

### Option C: Coefficient 1.2 plus owned-trailer running wear
- **Pros:** A visible premium (1.33x gross) that is partly spent on a real, price-proportional cost,
  leaving a modest net margin.
- **Cons:** Wear rate is not documented engine behaviour; it had to be calibrated in playtest.

## Decision
Option C. `cargo_market_revenue_coef_per_km: 1.2` (v1.2.1) and `trailer_body_wear` /
`trailer_chassis_wear: 1e-5` per km, about 1% per 1000 km, fixable at service (v1.2.2). The rate was
deliberately conservative because the per-km pay figures available disagreed by ~5x. Playtest
confirmed Cargo Market stays noticeably more profitable than Freight Market net of the wear
without being overpriced; that is the locked target for this version.

The general principle: every pay difference must be backed by a cost, risk or skill the player
carries, and sized to it.

## Consequences
**Easier:** Owned-trailer profitability now scales with what the trailer cost; future tuning can move
either lever (premium or wear) with a stated reason.
**Harder:** Balancing Cargo Market pay now spans two files (`economy_data.sii` and
`damage_data.sii`); change them together.
**Follow-up (deferred):** the flat `fixed_revenue` per job, vanilla cargo rates left untouched by
Cargo Variety, and bonus stacking (hazmat premium, ADR skill, urgency, level bonus) should be audited
against the same principle.
