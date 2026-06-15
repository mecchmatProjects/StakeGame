# Treasure Dice RTP Rebalance Summary

## Scope
- Package path: math-sdk/games/treasure_dice/library/publish_files
- Target RTP (normalized): 96.00
- Tolerance: +/- 0.01
- Rebalance script: rebalance_lookup_rtp.py
- Verification script: simulator.py

## Execution
- Rebalance applied in write mode with backup suffix: .bak_20260606_130344
- Rebalance report: rebalance_report.json
- Post-write compliance check: all modes pass

## Mode Results

| Mode | Cost | Before RTP (Norm) | After RTP (Norm) | Delta To Target | Pass After | Scale Used | L1 Weight Change | Lookup |
|---|---:|---:|---:|---:|---|---:|---:|---|
| safe_shore | 1.0 | 97.920000 | 96.000000 | 0.000000 | True | 1 | 64 | lookUpTable_safe_shore_0.csv |
| hidden_bay | 1.0 | 100.320000 | 96.000000 | 0.000000 | True | 1 | 54 | lookUpTable_hidden_bay_0.csv |
| coral_reef | 1.0 | 99.360000 | 96.000000 | 0.000000 | True | 1 | 28 | lookUpTable_coral_reef_0.csv |
| storm_route | 1.0 | 104.448000 | 96.000000 | 0.000000 | True | 1 | 44 | lookUpTable_storm_route_0.csv |
| skull_island | 1.0 | 105.600000 | 96.000000 | 0.000000 | True | 1 | 20 | lookUpTable_skull_island_0.csv |
| kraken_waters | 1.0 | 111.360000 | 96.000000 | 0.000000 | True | 1 | 16 | lookUpTable_kraken_waters_0.csv |
| lost_treasure | 1.0 | 86.400000 | 96.000000 | 0.000000 | True | 1 | 4 | lookUpTable_lost_treasure_0.csv |
| treasure_hunt_buy | 100.0 | 93.410000 | 95.995000 | -0.005000 | True | 5 | 4018 | lookUpTable_treasure_hunt_buy_0.csv |

## Outcome
- Compliance result: PASS
- all_modes_pass = True at target 96.00 with tolerance 0.01

## Notes
- treasure_hunt_buy required scale factor 5 to satisfy tight tolerance using integer weights.
- Backup files were created before overwriting lookup tables.

## Repro Commands
```powershell
# 1) Dry-run rebalance (no file changes)
& C:\Users\brpri\AppData\Local\Microsoft\WindowsApps\python3.13.exe f:/Gaming/Stakes/rebalance_lookup_rtp.py --path f:/Gaming/Stakes/math-sdk/games/treasure_dice/library/publish_files --target-rtp 96 --tol 0.01 --max-scale 500

# 2) Apply rebalance in place with backups and JSON report
& C:\Users\brpri\AppData\Local\Microsoft\WindowsApps\python3.13.exe f:/Gaming/Stakes/rebalance_lookup_rtp.py --path f:/Gaming/Stakes/math-sdk/games/treasure_dice/library/publish_files --target-rtp 96 --tol 0.01 --max-scale 500 --write --report-json f:/Gaming/Stakes/rebalance_report.json

# 3) Verify all modes against target/tolerance
& C:\Users\brpri\AppData\Local\Microsoft\WindowsApps\python3.13.exe f:/Gaming/Stakes/simulator.py --path f:/Gaming/Stakes/math-sdk/games/treasure_dice/library/publish_files --all-modes --target-rtp 96 --rtp-tol 0.01
```
