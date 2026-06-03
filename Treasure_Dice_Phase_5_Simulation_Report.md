# Treasure Dice Phase 5 Simulation Report

## Document Status

- Phase: 5 - Validation and Reporting
- Date: 2026-06-03
- Analyst: GitHub Copilot (GPT-5.3-Codex)
- Source package: [math-sdk/games/treasure_dice](math-sdk/games/treasure_dice)
- Source summary: [treasure_dice_phase5_validation_summary.json](treasure_dice_phase5_validation_summary.json)

## Scope

This report covers simulated-versus-theoretical RTP reconciliation for all eight published modes.

## RTP Reconciliation Summary

| Mode | Rounds | Theoretical RTP | Simulated RTP | Drift | Drift Sigma |
| --- | ---: | ---: | ---: | ---: | ---: |
| safe_shore | 2000 | 0.9600 | 0.9792 | +0.0192 | +1.79 |
| hidden_bay | 1000 | 0.9600 | 1.0032 | +0.0432 | +1.74 |
| coral_reef | 1000 | 0.9600 | 0.9936 | +0.0336 | +0.90 |
| storm_route | 1000 | 0.9600 | 1.0445 | +0.0845 | +1.61 |
| skull_island | 1000 | 0.9600 | 1.0560 | +0.0960 | +1.05 |
| kraken_waters | 1000 | 0.9600 | 1.1136 | +0.1536 | +1.16 |
| lost_treasure | 2000 | 0.9600 | 0.8640 | -0.0960 | -0.45 |
| treasure_hunt_buy | 1000 | 0.9600 | 0.9341 | -0.0259 | -1.09 |

## Interpretation

- All modes are directionally consistent with theoretical expectations for short package-generation run sizes.
- No mode exceeds an absolute drift of 2 sigma in this run.
- High-volatility and low-hit modes (`kraken_waters`, `lost_treasure`) show larger raw drift as expected at low simulation volumes.

## Simulation Notes

- Simulation counts are controlled by [math-sdk/games/treasure_dice/run.py](math-sdk/games/treasure_dice/run.py).
- This run is suitable for package validation and smoke-level reconciliation.
- Larger-run convergence testing remains recommended for release sign-off statistics.

## Verdict

- Simulation report status: Pass (for Phase 5 package validation scope)
- Release-statistics confidence level: Conditional pending larger-run convergence campaign
