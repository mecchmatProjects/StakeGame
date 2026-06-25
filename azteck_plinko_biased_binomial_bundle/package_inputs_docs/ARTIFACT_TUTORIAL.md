# Azteck Plinko Artifact Tutorial

This tutorial explains how artifacts should be populated in azteck_plinko_final.

## Inputs First

Populate files in inputs before package generation:
- azteck_plinko_paytables_normal.csv
- azteck_plinko_paytables_100balls.csv
- azteck_plinko_probability_tables.csv
- azteck_plinko_replay_contract.json
- azteck_plinko_rounding_policy.md

## Expected Generation Outputs

After math and package generation:
- artifacts/publish_files/index.json
- artifacts/publish_files/lookUpTable_<mode>_0.csv
- artifacts/publish_files/books_<mode>.jsonl.zst
- artifacts/configs/config.json and related frontend config files
- docs validation and simulation reports
- workbook generated via build_static_game_full_xlsx.py

Book payload note:
- the current package keeps the `books_<mode>.jsonl.zst` naming convention for compatibility with expected artifact families
- the files themselves contain deterministic line-delimited JSON payloads and are intentionally left uncompressed for audit and replay inspection

## Validation Commands

Example exact RTP pass over all modes:
- python simulator.py --path math-sdk/games/azteck_plinko_final/artifacts/publish_files --all-modes --target-rtp 0.9605 --rtp-tol 0.01

Example 100,000-spin Monte Carlo verification over all modes:
- python simulator_plinko.py --root math-sdk/games/azteck_plinko_final --spins 100000 --target-rtp 0.9605 --rtp-tol 0.01

Example full terminal walkthrough for a few games in one mode:
- python simulator_plinko.py --root math-sdk/games/azteck_plinko_final --mode normal_low_8 --demo --demo-games 10 --seed 2026

Example package summary refresh:
- python validate_static_package.py --root math-sdk/games/azteck_plinko_final --target-rtp 0.9605 --rtp-tol 0.01 --title "Azteck Plinko"

Example workbook generation:
- python build_static_game_full_xlsx.py --root math-sdk/games/azteck_plinko_final --name AzteckPlinkoFull --target-rtp 0.9605 --rtp-tol 0.01

## Workbook Audit Coverage

The Summary sheet now includes explicit audit fields for structural and risk checks:
- Rows Config
- Expected Buckets
- Rows
- Unique Multipliers
- Bucket Structure Pass (checks Rows equals Rows Config + 1)
- Max Win Probability
- Max Exposure

The workbook also includes a dedicated `TestVectors` sheet with deterministic draw points and expected outcomes per mode.
