# Treasure Dice Phase 1 Math Report

## Document Status

- Phase: 1 - Regular Routes Validation
- Review purpose: Formal math review
- Date: 2026-06-03
- Analyst: GitHub Copilot (GPT-5.4), preliminary implementation for mathematician review
- Source brief: [Game_Description.md](f:/Gaming/Stakes/Game_Description.md)
- Working worksheet: [Treasure_Dice_Mathematician_Handoff.md](f:/Gaming/Stakes/Treasure_Dice_Mathematician_Handoff.md)

## Scope

This report covers only the seven regular route modes.

Included:

- route multiplier confirmation
- theoretical RTP confirmation
- regular-route paytable confirmation at base bet 1
- variance and standard deviation confirmation
- provisional small-bet fiat-cent rounding analysis
- Gate 1 recommendation

Not included:

- Bonus Buy design
- deterministic event mapping
- Stake Engine Math SDK package generation
- simulation validation

## Summary Verdict

The seven regular routes are mathematically correct before payout rounding. The published route multipliers, theoretical RTP values, and volatility values all reconcile exactly with the formulas in the game brief.

Phase 1 Gate 1 should be treated as `Conditional`, not fully passed, because provisional fiat-cent rounding introduces material RTP drift for several route modes at 0.01 and 0.02 bet levels, and a minor drift for one mode at 0.05. The theoretical model is approved. The low-denomination settlement policy is not yet approved.

## Governing Formulas

For each regular route with win probability $p$ and target RTP $r = 0.96$:

$$
M = \frac{r}{p}
$$

$$
\mathrm{Expected\ payout} = p \times M = 0.96
$$

$$
\mathrm{Var}(X) = p \times M^2 - r^2 = r^2 \times \left(\frac{1}{p} - 1\right)
$$

where $M$ is the total payout multiplier and $X$ is the payout multiplier random variable taking values $M$ on win and $0$ on loss.

## Route Math Confirmation

| Mode ID | Win Chance p | Published Multiplier | Recomputed Multiplier | Theoretical RTP | Status |
| --- | --- | --- | --- | --- | --- |
| safe_shore | 0.80 | 1.20 | 1.20 | 0.9600 | Confirmed |
| hidden_bay | 0.60 | 1.60 | 1.60 | 0.9600 | Confirmed |
| coral_reef | 0.40 | 2.40 | 2.40 | 0.9600 | Confirmed |
| storm_route | 0.25 | 3.84 | 3.84 | 0.9600 | Confirmed |
| skull_island | 0.10 | 9.60 | 9.60 | 0.9600 | Confirmed |
| kraken_waters | 0.05 | 19.20 | 19.20 | 0.9600 | Confirmed |
| lost_treasure | 0.01 | 96.00 | 96.00 | 0.9600 | Confirmed |

## Paytable Confirmation at Base Bet 1

| Mode ID | Multiplier | Win Payout | Net Profit on Win | Status |
| --- | --- | --- | --- | --- |
| safe_shore | 1.20x | 1.20 | 0.20 | Confirmed |
| hidden_bay | 1.60x | 1.60 | 0.60 | Confirmed |
| coral_reef | 2.40x | 2.40 | 1.40 | Confirmed |
| storm_route | 3.84x | 3.84 | 2.84 | Confirmed |
| skull_island | 9.60x | 9.60 | 8.60 | Confirmed |
| kraken_waters | 19.20x | 19.20 | 18.20 | Confirmed |
| lost_treasure | 96.00x | 96.00 | 95.00 | Confirmed |

## Volatility Confirmation

| Mode ID | Variance Published | Variance Recomputed | Std Dev Published | Std Dev Recomputed | Status |
| --- | --- | --- | --- | --- | --- |
| safe_shore | 0.2304 | 0.2304 | 0.4800 | 0.4800 | Confirmed |
| hidden_bay | 0.6144 | 0.6144 | 0.7838 | 0.7838 | Confirmed |
| coral_reef | 1.3824 | 1.3824 | 1.1758 | 1.1758 | Confirmed |
| storm_route | 2.7648 | 2.7648 | 1.6628 | 1.6628 | Confirmed |
| skull_island | 8.2944 | 8.2944 | 2.8800 | 2.8800 | Confirmed |
| kraken_waters | 17.5104 | 17.5104 | 4.1845 | 4.1845 | Confirmed |
| lost_treasure | 91.2384 | 91.2384 | 9.5519 | 9.5519 | Confirmed |

## Precision And Rounding Assumptions Used In This Review

- Theoretical validation kept at 4 decimal places.
- Published route multipliers kept at 2 decimal places, matching the brief.
- Provisional fiat review assumes settlement rounding to the nearest 0.01, midpoint away from zero.
- Crypto-like currency rounding is not resolved in Phase 1.

## Small-Bet Rounding Review

### Detailed Results

| Bet Level | Mode ID | Raw Win Payout | Rounded Win Payout | Effective RTP | Drift vs 96.00% | Review Result |
| --- | --- | --- | --- | --- | --- | --- |
| 0.01 | safe_shore | 0.0120 | 0.01 | 0.8000 | -0.1600 | Not acceptable |
| 0.01 | hidden_bay | 0.0160 | 0.02 | 1.2000 | 0.2400 | Not acceptable |
| 0.01 | coral_reef | 0.0240 | 0.02 | 0.8000 | -0.1600 | Not acceptable |
| 0.01 | storm_route | 0.0384 | 0.04 | 1.0000 | 0.0400 | Not acceptable |
| 0.01 | skull_island | 0.0960 | 0.10 | 1.0000 | 0.0400 | Not acceptable |
| 0.01 | kraken_waters | 0.1920 | 0.19 | 0.9500 | -0.0100 | Not acceptable |
| 0.01 | lost_treasure | 0.9600 | 0.96 | 0.9600 | 0.0000 | Acceptable |
| 0.02 | safe_shore | 0.0240 | 0.02 | 0.8000 | -0.1600 | Not acceptable |
| 0.02 | hidden_bay | 0.0320 | 0.03 | 0.9000 | -0.0600 | Not acceptable |
| 0.02 | coral_reef | 0.0480 | 0.05 | 1.0000 | 0.0400 | Not acceptable |
| 0.02 | storm_route | 0.0768 | 0.08 | 1.0000 | 0.0400 | Not acceptable |
| 0.02 | skull_island | 0.1920 | 0.19 | 0.9500 | -0.0100 | Not acceptable |
| 0.02 | kraken_waters | 0.3840 | 0.38 | 0.9500 | -0.0100 | Not acceptable |
| 0.02 | lost_treasure | 1.9200 | 1.92 | 0.9600 | 0.0000 | Acceptable |
| 0.05 | safe_shore | 0.0600 | 0.06 | 0.9600 | 0.0000 | Acceptable |
| 0.05 | hidden_bay | 0.0800 | 0.08 | 0.9600 | 0.0000 | Acceptable |
| 0.05 | coral_reef | 0.1200 | 0.12 | 0.9600 | 0.0000 | Acceptable |
| 0.05 | storm_route | 0.1920 | 0.19 | 0.9500 | -0.0100 | Not acceptable |
| 0.05 | skull_island | 0.4800 | 0.48 | 0.9600 | 0.0000 | Acceptable |
| 0.05 | kraken_waters | 0.9600 | 0.96 | 0.9600 | 0.0000 | Acceptable |
| 0.05 | lost_treasure | 4.8000 | 4.80 | 0.9600 | 0.0000 | Acceptable |

### Interpretation

The theoretical route design is sound. The issue is not the route math itself, but the interaction between published multipliers and a fiat-cent settlement floor.

Observed impacts:

- At bet level 0.01, only `lost_treasure` remains exact under provisional fiat-cent rounding.
- At bet level 0.02, only `lost_treasure` remains exact under provisional fiat-cent rounding.
- At bet level 0.05, six routes remain exact and `storm_route` drifts slightly to 95.00%.

This means one of the following must happen before final approval:

- the settlement precision must support sub-cent payouts for low denominations,
- a different rounding policy must be confirmed,
- or the allowed low bet levels must be constrained by mode.

## Preliminary Max Win Metadata For Regular Routes

| Mode ID | Preliminary Max Win Multiplier |
| --- | --- |
| safe_shore | 1.20x |
| hidden_bay | 1.60x |
| coral_reef | 2.40x |
| storm_route | 3.84x |
| skull_island | 9.60x |
| kraken_waters | 19.20x |
| lost_treasure | 96.00x |

## Packaging Handoff Status

The regular-route math is ready for packaging in principle, but the payout rounding policy remains a blocking review item for low fiat denominations.

Current packaging handoff status: `Conditionally ready`

Conditions remaining:

- close the fiat rounding rule for 0.01 and 0.02 bet levels,
- decide whether 0.05 is acceptable for `storm_route` under the provisional fiat rule,
- close crypto-like rounding rules separately.

## Gate 1 Decision

- Gate 1 status: `Conditional`
- Theoretical route math: `Pass`
- Volatility confirmation: `Pass`
- Small-bet rounding review: `Conditional / Pending policy decision`

## Formal Review Notes

Open items for mathematician review:

1. Confirm whether the provisional fiat rounding model matches the intended platform behavior.
2. Decide whether low-denomination support requires sub-cent settlement precision or mode restrictions.
3. Confirm whether the final report should state that some low-denomination route/mode combinations are unsupported under fiat-cent rounding.

## Recommended Next Step

Proceed to Phase 2 Bonus Buy design while treating low-denomination rounding policy as an active cross-phase dependency. Do not mark the full regular-route package as unconditionally approved until the settlement precision question is closed.
