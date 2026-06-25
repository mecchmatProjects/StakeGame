# Azteck Plinko Rounding Policy

Status: defined for the current model-synthesized package.

## Settlement Basis

- Published lookup tables store `payout_raw = payoutMultiplier * 100`.
- Audit and validation tooling converts `payout_raw / 100` back to the published payout multiplier.
- The current package treats the lookup multiplier as the settlement source of truth.

## Rounding Rules

1. Calculation precision inside the package
- multiplier values are retained as decimal values from the synthesized model
- lookup files store `payout_raw` using the package scale `100.0`
- no per-bucket probability rounding is used in theoretical math beyond CSV export precision

2. Settlement rounding stage
- round only the final round payout
- do not round intermediate path calculations
- do not round per-ball results independently in `100balls` mode

3. Rounding method
- recommended policy: round half up to the currency precision used by the operator wallet
- if the operator enforces a different wallet rule, rerun validation with that rule before release sign-off

4. Currency precision
- default assumption for audit: 2 decimal places
- operator-specific currencies with different precision must be validated separately

## 100 Balls Feature

- `100balls` mode is settled as a true round of 100 independent single-ball draws
- each ball is drawn from the same `P(k)` as the matching `normal` mode (same difficulty/rows)
- the round multiplier is derived from the 100-ball outcome set and scaled for the buy feature contract: `round(sum(ball_payout_raw)/100) * 99`
- buy feature contract cost is `99x` current bet; the package enforces Stake Engine multiplier cap (`<= 25,000x`) at artifact synthesis time
- RTP is calibrated on the generated lookup/book outcomes to preserve the package target (`96.05%`) under the `99x` buy-cost contract
- there is no incremental per-ball wallet rounding; the total win is rounded once at final settlement only

## RTP Validation Policy

- theoretical package target RTP: `96.05%`
- package validation tolerance: `+/- 0.01`
- rounding validation must preserve the per-mode RTP within the same tolerance band

## Test Bets Used For Audit

Minimum verification points:
- `0.01`
- `0.02`
- `0.05`

Recommended extension before production release:
- operator minimum bet
- operator maximum bet
- any currencies with non-standard decimal precision

## Current Conclusion

The current Azteck Plinko package is mathematically validated against lookup multipliers and RTP tolerance under final-round-only rounding assumptions. Any change to wallet precision or rounding stage requires revalidation.
