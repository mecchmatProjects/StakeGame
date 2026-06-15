# Treasure Dice Phase 5 Replay and Audit Report

## Document Status

- Phase: 5 - Validation and Reporting
- Date: 2026-06-03
- Analyst: GitHub Copilot (GPT-5.3-Codex)
- Source summary: [treasure_dice_phase5_validation_summary.json](treasure_dice_phase5_validation_summary.json)

## Scope

This report covers:

- weight integrity checks
- lookup-to-books consistency checks
- max-win checks
- replay determinism checks
- package-level small-bet rounding checks

## Global Audit Results

| Check | Result |
| --- | --- |
| All weight checks pass | Yes |
| All lookup checks pass | Yes |
| All max-win checks pass | Yes |
| All replay checks pass | Yes |

## Replay Determinism Note

Determinism check criteria:

1. each `outcomeId` maps to one unique ordered event sequence
2. each `outcomeId` maps to one payout value
3. lookup payout values align with corresponding book records by simulation id

Result:

- Replay determinism check passed for all 8 modes.

## Max-Win Audit Note

For each mode, observed maximum payout in books was checked against:

1. configured max win in [math-sdk/games/treasure_dice/library/configs/config.json](math-sdk/games/treasure_dice/library/configs/config.json)
2. mapped max win from [treasure_dice_phase3_mapping_spec.json](treasure_dice_phase3_mapping_spec.json)

Result:

- All modes passed max-win bound checks.

## Lookup and Weight Audit Note

- Weight totals matched book lengths in every mode.
- Lookup payout multipliers matched published book payout multipliers by simulation id.

Result:

- Lookup and weight audits passed.

## Package Rounding Note

### Regular Routes (0.01, 0.02, 0.05)

Final publication policy uses Stake Engine six-decimal settlement precision rather than provisional fiat-cent rounding.

Under the final policy:

- All regular-route payouts at 0.01, 0.02, and 0.05 are exactly representable.
- No settlement-rounding RTP drift remains for any published regular mode.

### Bonus Buy (`treasure_hunt_buy`)

At tested small bet levels (0.01, 0.02, 0.05), expected bonus RTP remains exactly 0.96 under the final settlement policy for the selected Candidate A distribution.

## Verdict

- Replay and package audit status: Pass
- Rounding policy status: Pass under final publication policy defined in [Treasure_Dice_Phase_6_Precision_Rounding_And_Frontend_Contract.md](Treasure_Dice_Phase_6_Precision_Rounding_And_Frontend_Contract.md)
