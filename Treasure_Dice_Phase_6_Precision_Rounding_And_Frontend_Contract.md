# Treasure Dice Phase 6 Precision, Rounding, and Frontend Contract

## Document Status

- Phase: 6 - Publication Readiness
- Date: 2026-06-04
- Analyst: GitHub Copilot (GPT-5.4)
- Purpose: Final closure of Game_Description sections 11 and 12 for Treasure Dice publication

## Governing Engine Rule

Stake Engine settlement uses integer monetary values with six decimal places of precision.

Source evidence:

- [math-sdk/docs/rgs_docs/RGS.md](math-sdk/docs/rgs_docs/RGS.md)

This supersedes the earlier provisional fiat-cent review assumption used in Phase 1 for sensitivity analysis. Currency formatting belongs to the display layer and does not alter gameplay logic or settlement.

## Final Section 11 Policy

### 1. Internal Precision

- Probabilities and normalized outcome weights are validated to an absolute tolerance of `1e-8`.
- Regular-route payout multipliers are fixed exactly as published in the brief: `1.20`, `1.60`, `2.40`, `3.84`, `9.60`, `19.20`, `96.00`.
- Bonus payout multipliers for the approved Candidate A package are fixed as exact whole-number multiples of base bet: `0`, `50`, `90`, `120`, `180`, `275`.
- Settlement amounts are represented in Stake Engine money units with six decimal places of precision.

### 2. Currency Rounding Rules

- Settlement rule for all supported currencies: compute payout using Stake Engine six-decimal money precision, with no pre-settlement cent rounding.
- Display rule for fiat and crypto-like currencies: apply currency formatting only after authoritative settlement is determined.
- Display formatting must never be used to recalculate or alter payout.

### 3. Minimum Payout Unit

- Minimum settlement unit: `0.000001` of the displayed currency amount.
- Example: `1.000000` is represented by integer amount `1000000` in Stake Engine.

### 4. Actual RTP After Currency Rounding For Required Small Bet Levels

Under the final Stake Engine settlement rule, all tested Treasure Dice payouts are exactly representable for base bets `0.01`, `0.02`, and `0.05`. Therefore the effective RTP remains exactly `0.96` for all eight published modes.

| Mode ID | RTP at 0.01 | RTP at 0.02 | RTP at 0.05 | Status |
| --- | --- | --- | --- | --- |
| safe_shore | 0.9600 | 0.9600 | 0.9600 | Exact |
| hidden_bay | 0.9600 | 0.9600 | 0.9600 | Exact |
| coral_reef | 0.9600 | 0.9600 | 0.9600 | Exact |
| storm_route | 0.9600 | 0.9600 | 0.9600 | Exact |
| skull_island | 0.9600 | 0.9600 | 0.9600 | Exact |
| kraken_waters | 0.9600 | 0.9600 | 0.9600 | Exact |
| lost_treasure | 0.9600 | 0.9600 | 0.9600 | Exact |
| treasure_hunt_buy | 0.9600 | 0.9600 | 0.9600 | Exact |

### 5. Impact Of Rounding On Bonus Buy Outcomes

- No RTP drift is introduced by settlement rounding for the approved Bonus Buy package at the tested bet levels.
- Candidate A payouts remain exactly representable under six-decimal settlement precision.

### 6. Final Multiplier Display Wording

- UI field label: `Win Multiplier`
- UI value source: authoritative `round_settlement.payoutMultiplier`
- Regular-route formatting rule: always display exactly two decimal places with `x` suffix.
- Bonus-mode formatting rule: display whole-number multipliers without trailing decimal zeroes when the value is integral; otherwise display up to two decimal places with `x` suffix.
- Currency amount formatting is separate from multiplier formatting and must use the already-settled payout amount.

Approved route display strings:

| Mode ID | Display String |
| --- | --- |
| safe_shore | `1.20x` |
| hidden_bay | `1.60x` |
| coral_reef | `2.40x` |
| storm_route | `3.84x` |
| skull_island | `9.60x` |
| kraken_waters | `19.20x` |
| lost_treasure | `96.00x` |

Approved bonus outcome display strings:

| Outcome ID | Display String |
| --- | --- |
| A1 | `0x` |
| A2 | `50x` |
| A3 | `90x` |
| A4 | `120x` |
| A5 | `180x` |
| A6 | `275x` |

### 7. Alignment Of UI Multipliers With Actual Settlement

- The UI must derive multiplier text from the same `payoutMultiplier` value that is recorded in books, lookup validation, and `round_settlement` events.
- The UI must not infer multiplier text from rounded currency amounts.
- Because all published regular-route multipliers use two decimals and all published bonus multipliers are integral, the approved display strings are lossless relative to settlement.

## Final Section 12 Event Contract

The final frontend event names are confirmed as follows:

- `round_start`
- `route_reveal`
- `route_win`
- `route_lose_storm`
- `route_lose_reef`
- `route_lose_skull`
- `route_lose_kraken`
- `route_near_miss`
- `route_complete`
- `bonus_step`
- `bonus_complete`
- `round_settlement`

Event contract rules:

- `route_near_miss` remains a losing presentation variant only.
- Dice animation and chest presentation are visual only and never determine settlement.
- Replay must reproduce the same ordered event sequence from stored outcome data.
- Final event names above are locked for this publication package.

## Closure Decision

- Section 11 status: Present
- Section 12 naming status: Present
- Publication impact: no math-package regeneration is required for payout logic, but the publication bundle must be refreshed so the final policy and contract documents replace the previous conditional status.