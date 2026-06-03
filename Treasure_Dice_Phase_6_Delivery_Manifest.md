# Treasure Dice Phase 6 Delivery Manifest

## Document Status

- Phase: 6 - Publication Readiness
- Date: 2026-06-03
- Analyst: GitHub Copilot (GPT-5.3-Codex)
- Scope: Final delivery inventory from completed Phases 1-5

## Core Specifications and Reports

1. [Treasure_Dice_Mathematician_Handoff.md](Treasure_Dice_Mathematician_Handoff.md)
2. [Treasure_Dice_Phase_1_Math_Report.md](Treasure_Dice_Phase_1_Math_Report.md)
3. [Treasure_Dice_Phase_2_Bonus_Report.md](Treasure_Dice_Phase_2_Bonus_Report.md)
4. [Treasure_Dice_Phase_3_Event_Mapping_Report.md](Treasure_Dice_Phase_3_Event_Mapping_Report.md)
5. [Treasure_Dice_Phase_4_Package_Completeness_Report.md](Treasure_Dice_Phase_4_Package_Completeness_Report.md)
6. [Treasure_Dice_Phase_5_Simulation_Report.md](Treasure_Dice_Phase_5_Simulation_Report.md)
7. [Treasure_Dice_Phase_5_Volatility_Report.md](Treasure_Dice_Phase_5_Volatility_Report.md)
8. [Treasure_Dice_Phase_5_Replay_Audit_Report.md](Treasure_Dice_Phase_5_Replay_Audit_Report.md)
9. [Treasure_Dice_Phase_5_Final_Validation_Summary.md](Treasure_Dice_Phase_5_Final_Validation_Summary.md)

## Machine-Readable Math and Validation Assets

1. [treasure_dice_phase3_mapping_spec.json](treasure_dice_phase3_mapping_spec.json)
2. [treasure_dice_phase5_validation_summary.json](treasure_dice_phase5_validation_summary.json)
3. [treasure_dice_phase5_validate.py](treasure_dice_phase5_validate.py)

## Simulator and Math Review Utilities

1. [treasure_dice_phase1_simulator.py](treasure_dice_phase1_simulator.py)
2. [treasure_dice_phase2_simulator.py](treasure_dice_phase2_simulator.py)
3. [Treasure_Dice_Phase_1_Simulator_Manual.txt](Treasure_Dice_Phase_1_Simulator_Manual.txt)
4. [Treasure_Dice_Phase_2_Simulator_Manual.txt](Treasure_Dice_Phase_2_Simulator_Manual.txt)

## Stake Engine Package - Treasure Dice

Package root:

- [math-sdk/games/treasure_dice](math-sdk/games/treasure_dice)

Key game implementation files:

1. [math-sdk/games/treasure_dice/game_config.py](math-sdk/games/treasure_dice/game_config.py)
2. [math-sdk/games/treasure_dice/gamestate.py](math-sdk/games/treasure_dice/gamestate.py)
3. [math-sdk/games/treasure_dice/game_events.py](math-sdk/games/treasure_dice/game_events.py)
4. [math-sdk/games/treasure_dice/game_calculations.py](math-sdk/games/treasure_dice/game_calculations.py)
5. [math-sdk/games/treasure_dice/game_executables.py](math-sdk/games/treasure_dice/game_executables.py)
6. [math-sdk/games/treasure_dice/game_override.py](math-sdk/games/treasure_dice/game_override.py)
7. [math-sdk/games/treasure_dice/run.py](math-sdk/games/treasure_dice/run.py)
8. [math-sdk/games/treasure_dice/readme.txt](math-sdk/games/treasure_dice/readme.txt)

Generated package artifact directories:

1. [math-sdk/games/treasure_dice/library/configs](math-sdk/games/treasure_dice/library/configs)
2. [math-sdk/games/treasure_dice/library/lookup_tables](math-sdk/games/treasure_dice/library/lookup_tables)
3. [math-sdk/games/treasure_dice/library/forces](math-sdk/games/treasure_dice/library/forces)
4. [math-sdk/games/treasure_dice/library/publish_files](math-sdk/games/treasure_dice/library/publish_files)

## Mode Coverage Confirmed

Published modes in package index:

1. safe_shore
2. hidden_bay
3. coral_reef
4. storm_route
5. skull_island
6. kraken_waters
7. lost_treasure
8. treasure_hunt_buy

Evidence: [math-sdk/games/treasure_dice/library/publish_files/index.json](math-sdk/games/treasure_dice/library/publish_files/index.json)

## Manifest Verdict

- Delivery manifest completeness: Pass
- Publication bundle status: Conditionally ready pending final policy closure captured in Phase 6 risk and status notes
