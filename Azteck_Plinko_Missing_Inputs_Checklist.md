# Azteck Plinko Missing Inputs Checklist

## Status

This checklist captures blocking external inputs required to produce final math and package artifacts with no assumptions.

## Blocking Items

1. Full Normal Mode paytables
- Scope: all difficulties (Low, Medium, High, Expert) x rows 8-16
- Needed fields: full multiplier buckets, ordering, and payout units
- Current status: missing
- Source owner: product or reference capture

2. Full 100 Balls paytables
- Scope: all difficulties x rows 8-16
- Needed fields: full multiplier buckets and aggregation behavior
- Current status: missing
- Source owner: product or reference capture

3. Bucket probabilities per configuration
- Scope: each difficulty and row count for Normal and 100 Balls
- Needed fields: probability distribution for each multiplier bucket
- Current status: missing
- Source owner: math reference or reverse-engineering agreement

4. 100 Balls settlement model details
- Needed fields:
  - whether 100 outcomes are independent draws
  - exact total-win aggregation rule
  - any feature-level cap logic
  - how 99x feature cost is applied in RTP accounting
- Current status: partially defined, not finalized
- Source owner: product plus math review

5. Rounding rules and currency precision
- Scope: minimum stake edge cases and per-currency behavior
- Needed fields:
  - rounding mode (for example, banker, floor, half-up)
  - rounding stage (bucket, per-ball, per-round final)
  - currency decimal precision policy
- Current status: missing
- Source owner: platform policy owner

6. Replay state contract
- Needed fields:
  - minimum backend state needed for deterministic replay
  - event schema expected by frontend
  - deterministic mapping from stored outcome to animation path
- Current status: missing
- Source owner: backend plus frontend architecture

7. Acceptance tolerances
- Needed fields:
  - exact RTP tolerance per mode in QA and release checks
  - confidence interval policy for simulation sign-off
  - max exposure acceptance threshold
- Current status: missing
- Source owner: math and product sign-off

## Required Screenshot Capture (Reference Backfill)

1. Normal mode screenshots
- all difficulties and rows 8-16
- full visible multiplier buckets for each configuration

2. 100 Balls screenshots
- all difficulties and rows 8-16
- full multiplier buckets and any max-win display

3. Rules or help modal screenshots
- full scroll from top to bottom
- RTP, house edge, bet range, cost and feature text

4. Replay or history screenshots
- low win, zero payout, high win, and max-win cases where possible

## Unblock Criteria

This checklist is resolved when all blocking items have explicit values and are exported to a canonical machine-readable source file set:
- azteck_plinko_paytables_normal.csv
- azteck_plinko_paytables_100balls.csv
- azteck_plinko_probability_tables.csv
- azteck_plinko_replay_contract.json
- azteck_plinko_rounding_policy.md
