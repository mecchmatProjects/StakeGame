# Treasure Dice Final Math Report

## Document Status

- Model version: `treasure_dice_release_math_v1_2026_06_04`
- Date: 2026-06-04
- Analyst: GitHub Copilot (GPT-5.4)
- Scope: Final production math summary for Treasure Dice release package

## Release Scope

Included in the release:

- seven regular route modes
- one Bonus Buy mode: `treasure_hunt_buy`
- deterministic replay-safe presentation mapping
- Stake Engine static outcome package for all eight modes

Excluded from the release:

- custom route slider
- organic bonus trigger from regular routes
- any frontend choice that changes settlement value

## Final Mode Summary

| Mode ID | Cost | RTP | Max Win | Status |
| --- | --- | --- | --- | --- |
| safe_shore | 1 | 96.00% | 1.20x | Approved |
| hidden_bay | 1 | 96.00% | 1.60x | Approved |
| coral_reef | 1 | 96.00% | 2.40x | Approved |
| storm_route | 1 | 96.00% | 3.84x | Approved |
| skull_island | 1 | 96.00% | 9.60x | Approved |
| kraken_waters | 1 | 96.00% | 19.20x | Approved |
| lost_treasure | 1 | 96.00% | 96.00x | Approved |
| treasure_hunt_buy | 100 | 96.00% | 275.00x | Approved |

## Final Decisions

### Regular Routes

- Route multipliers are approved exactly as published in the brief.
- Theoretical RTP for each regular route is exactly `0.96`.
- Regular-route paytable is finalized in [Treasure_Dice_Approved_Regular_Routes_Paytable.md](Treasure_Dice_Approved_Regular_Routes_Paytable.md).

### Bonus Buy

- Approved bonus design: Candidate A.
- Approved bonus paytable is finalized in [Treasure_Dice_Approved_Bonus_Buy_Paytable.md](Treasure_Dice_Approved_Bonus_Buy_Paytable.md).
- Approved max win multiplier for `treasure_hunt_buy`: `275x` base bet.

### Precision And Rounding

- Governing settlement rule: Stake Engine integer money with six decimal places.
- Minimum settlement unit: `0.000001`.
- Required small-bet validation at `0.01`, `0.02`, and `0.05` is closed with exact RTP retention under the final settlement model.
- Full policy is finalized in [Treasure_Dice_Phase_6_Precision_Rounding_And_Frontend_Contract.md](Treasure_Dice_Phase_6_Precision_Rounding_And_Frontend_Contract.md).

### Presentation And Replay

- Final event names are locked for the publication package.
- Near miss remains a losing presentation-only outcome.
- Replay determinism is closed and approved.
- Mapping is finalized in [Treasure_Dice_Phase_3_Event_Mapping_Report.md](Treasure_Dice_Phase_3_Event_Mapping_Report.md).

## Supporting Reports

- Simulation report: [Treasure_Dice_Phase_5_Simulation_Report.md](Treasure_Dice_Phase_5_Simulation_Report.md)
- Volatility report: [Treasure_Dice_Phase_5_Volatility_Report.md](Treasure_Dice_Phase_5_Volatility_Report.md)
- Validation summary: [Treasure_Dice_Phase_5_Final_Validation_Summary.md](Treasure_Dice_Phase_5_Final_Validation_Summary.md)
- Risk assessment: [Treasure_Dice_Phase_6_Risk_Assessment.md](Treasure_Dice_Phase_6_Risk_Assessment.md)

## Publication Status

- Package status: Ready
- Acceptance status: Pass
- Remaining deployment-specific note: if an operator later imposes an absolute payout cap, publish the cap-specific exposure table before enabling the affected bet envelope.