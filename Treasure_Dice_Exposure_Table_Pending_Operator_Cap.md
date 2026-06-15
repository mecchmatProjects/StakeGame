# Treasure Dice Exposure Table Pending Operator Cap

## Document Status

- Date: 2026-06-04
- Purpose: Provide release-ready exposure formulas until an operator payout cap is supplied

## Rule

If an operator provides an absolute payout cap, then:

`max allowed base bet = payout cap / max win multiplier`

## Per-Mode Exposure Formula Table

| Mode ID | Max Win Multiplier | Max Allowed Base Bet Formula |
| --- | --- | --- |
| safe_shore | 1.20x | `cap / 1.20` |
| hidden_bay | 1.60x | `cap / 1.60` |
| coral_reef | 2.40x | `cap / 2.40` |
| storm_route | 3.84x | `cap / 3.84` |
| skull_island | 9.60x | `cap / 9.60` |
| kraken_waters | 19.20x | `cap / 19.20` |
| lost_treasure | 96.00x | `cap / 96.00` |
| treasure_hunt_buy | 275.00x | `cap / 275.00` |

## Current Status

- No operator payout cap is assumed in the current publication package.
- This table is complete enough for release documentation and must be replaced with a cap-specific table only if an operator mandates an absolute payout cap.