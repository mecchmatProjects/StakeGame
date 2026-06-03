# Treasure Dice Phase 5 Volatility Report

## Document Status

- Phase: 5 - Validation and Reporting
- Date: 2026-06-03
- Analyst: GitHub Copilot (GPT-5.3-Codex)
- Source summary: [treasure_dice_phase5_validation_summary.json](treasure_dice_phase5_validation_summary.json)

## Scope

This report reconciles theoretical and simulated standard deviation (payout-multiplier space) for all eight modes.

## Volatility Comparison

| Mode | Theoretical Std Dev | Simulated Std Dev | Delta |
| --- | ---: | ---: | ---: |
| safe_shore | 0.4800 | 0.4650 | -0.0150 |
| hidden_bay | 0.7838 | 0.7738 | -0.0101 |
| coral_reef | 1.1758 | 1.1821 | +0.0064 |
| storm_route | 1.6628 | 1.7088 | +0.0460 |
| skull_island | 2.8800 | 3.0037 | +0.1237 |
| kraken_waters | 4.1845 | 4.4879 | +0.3033 |
| lost_treasure | 9.5519 | 9.0663 | -0.4856 |
| treasure_hunt_buy | 75.1399 | 75.5730 | +0.4331 |

## Interpretation

- Lower-volatility route modes (`safe_shore`, `hidden_bay`, `coral_reef`) align tightly between theory and simulation.
- Higher-volatility modes and bonus mode show broader spread, expected with current run lengths.
- No structural mismatch between mapped payout ladders and generated lookup distributions was detected.

## Verdict

- Volatility consistency status: Pass (Phase 5 validation scope)
- Recommended follow-up: include higher simulation volume in final statistical sign-off pack
