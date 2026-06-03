# Treasure Dice Phase 3 Event Mapping Report

## Document Status

- Phase: 3 - Deterministic Event Mapping
- Review purpose: Formal event-mapping and replay-determinism review
- Date: 2026-06-03
- Analyst: GitHub Copilot (GPT-5.3-Codex), preliminary implementation for mathematician review
- Source brief: [Game_Description.md](Game_Description.md)
- Upstream math approvals: [Treasure_Dice_Phase_1_Math_Report.md](Treasure_Dice_Phase_1_Math_Report.md), [Treasure_Dice_Phase_2_Bonus_Report.md](Treasure_Dice_Phase_2_Bonus_Report.md)

## Scope

This report locks deterministic mapping between approved mathematical outcomes and presentation events.

Included:

- regular route event-family mapping
- Bonus Buy candidate A event-family mapping
- replay determinism constraints
- presentation-only variant constraints
- packaging handoff references

Not included:

- SDK package generation
- simulation/reconciliation runs
- final frontend naming sign-off

## Summary Verdict

Phase 3 mapping is mathematically deterministic and replay-safe under the defined rules:

1. Settlement is fixed before presentation starts.
2. Each outcome ID maps to exactly one ordered event sequence.
3. Presentation variants alter only visual flavor, not probabilities or payouts.

Gate 3 status is `Conditional` pending final event-name sign-off with frontend/integration stakeholders.

## Deterministic Mapping Model

For each mode, the round result is selected from a static weighted outcome set.

Determinism constraints:

1. `mode_id + outcome_id` uniquely determine payout and event sequence.
2. No runtime user interaction changes payout after outcome selection.
3. Replay uses stored `outcome_id` and must reproduce the exact same event order.

## Regular Route Event Families

Required route event families from the brief are used:

- `route_win`
- `route_lose_storm`
- `route_lose_reef`
- `route_lose_skull`
- `route_lose_kraken`
- `route_near_miss`

Each regular mode has exactly 6 outcome families:

1. win family (pays route multiplier)
2. five loss families (all pay 0)

Loss-family split within each mode is fixed and mode-independent:

- storm: 40% of loss bucket
- reef: 25% of loss bucket
- skull: 20% of loss bucket
- kraken: 10% of loss bucket
- near miss: 5% of loss bucket

This split preserves route win chance because:

$$
p(\text{win}) = p
$$

$$
\sum_{f \in \text{loss families}} p(f) = 1-p
$$

with loss-family probabilities derived by:

$$
p(f) = (1-p) \times s_f
$$

where $s_f$ is the fixed family share.

### Route Mapping Table (Family Level)

| Outcome Class | Payout Multiplier | Event Sequence | Settlement Affected | Notes |
| --- | --- | --- | --- | --- |
| win | route-specific multiplier | `route_reveal -> route_win -> route_complete` | Yes | Main winning path |
| lose_storm | 0x | `route_reveal -> route_lose_storm -> route_complete` | No | Presentation-only loss flavor |
| lose_reef | 0x | `route_reveal -> route_lose_reef -> route_complete` | No | Presentation-only loss flavor |
| lose_skull | 0x | `route_reveal -> route_lose_skull -> route_complete` | No | Presentation-only loss flavor |
| lose_kraken | 0x | `route_reveal -> route_lose_kraken -> route_complete` | No | Presentation-only loss flavor |
| near_miss | 0x | `route_reveal -> route_near_miss -> route_complete` | No | Must remain a losing outcome |

## Bonus Event Families (Candidate A)

Working bonus candidate: `A` (recommended in Phase 2).

Bonus required families from the brief are used:

- `bonus_step`
- `bonus_complete`

Each bonus outcome has a fixed total event count from Phase 2. Sequence rule:

1. first events are `bonus_step`
2. final event is `bonus_complete`
3. payout is fixed before first step

### Bonus Mapping Table

| Outcome ID | Probability | Payout Multiplier vs B | Event Count | Deterministic Sequence |
| --- | --- | --- | --- | --- |
| A1 | 0.18 | 0x | 3 | `bonus_step -> bonus_step -> bonus_complete` |
| A2 | 0.22 | 50x | 3 | `bonus_step -> bonus_step -> bonus_complete` |
| A3 | 0.22 | 90x | 4 | `bonus_step -> bonus_step -> bonus_step -> bonus_complete` |
| A4 | 0.18 | 120x | 4 | `bonus_step -> bonus_step -> bonus_step -> bonus_complete` |
| A5 | 0.12 | 180x | 5 | `bonus_step -> bonus_step -> bonus_step -> bonus_step -> bonus_complete` |
| A6 | 0.08 | 275x | 6 | `bonus_step -> bonus_step -> bonus_step -> bonus_step -> bonus_step -> bonus_complete` |

## Replay Determinism Note

Replay key requirement:

- Same `mode_id` and same stored `outcome_id` must produce identical payout and identical ordered events.

Replay data contract for each settled round:

1. mode_id
2. outcome_id
3. payout multiplier
4. ordered event list

No RNG or frontend choice is evaluated during replay.

## Presentation-Only Constraint Note

The following elements are presentation-only and must not alter settlement:

1. loss flavor (`storm`, `reef`, `skull`, `kraken`)
2. near-miss visuals
3. chest-selection animation path after outcome lock
4. dice animation

Any future visual variant must be attached to an existing outcome family and must keep that family's payout and probability unchanged.

## Handoff Pack Contents

Phase 3 handoff pack artifacts:

1. this report: [Treasure_Dice_Phase_3_Event_Mapping_Report.md](Treasure_Dice_Phase_3_Event_Mapping_Report.md)
2. machine-readable mapping spec: [treasure_dice_phase3_mapping_spec.json](treasure_dice_phase3_mapping_spec.json)
3. updated master worksheet with Phase 3 execution record: [Treasure_Dice_Mathematician_Handoff.md](Treasure_Dice_Mathematician_Handoff.md)

## Gate 3 Decision

- Gate 3 status: `Conditional`
- Outcome determinism: `Pass`
- Replay constraints: `Pass`
- Presentation-only protection: `Pass`
- Final event naming alignment: `Pending`

## Recommended Next Step

Proceed to Phase 4 SDK packaging using the mapping spec as source of truth for deterministic outcome-to-event encoding.