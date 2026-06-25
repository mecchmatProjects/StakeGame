# Azteck Plinko Package Status Summary

## Current Status

The current Azteck Plinko package is a validated model-synthesized static package covering all 72 published modes:
- 36 normal modes
- 36 100 Balls modes

## Math Validation

- RTP target: `96.05%`
- RTP tolerance check: Pass
- Weight integrity check: Pass
- Max-win reachability check: Pass
- Inputs readiness: Pass

## Consistency Recheck (Latest)

- Workbook-to-artifacts consistency: Pass
- Mode coverage report: complete=72, partial=0, missing=0
- Simulator all-modes run (100,000 spins each mode): Pass
- Package validation summary refresh: Pass

## Key Artifacts

- Mode and publish index: `artifacts/publish_files/index.json`
- Lookup tables: `artifacts/publish_files/lookUpTable_<mode>_0.csv`
- Deterministic replay payloads: `artifacts/publish_files/books_<mode>.jsonl.zst`
- Validation summary: `docs/validation_summary.json`
- Audit workbook: `AzteckPlinkoFull_audit_formulas.xlsx`

## Important Packaging Note

The current `books_<mode>.jsonl.zst` files are zstd-compressed binary payloads and pass byte-signature validation (`28 b5 2f fd`) expected for Stake Engine publish ingestion.

## Multiplier Source Provenance

- Source file: `AzreckPlinko_multipliers.txt`
- SHA-256: `20bc97ece58633e5dfcfd27f75106430bade9f564aeeeea802dd5a20d7c77070`
- Size (bytes): `3040`
- Applied policy: normal-mode multipliers are sourced directly from the file; 100 Balls multipliers are derived as `min(100000, normal_multiplier * 99)`.

## Remaining Integration Policy Items

These are outside the validated math core and may still need downstream implementation confirmation:
- operator-specific currency precision and wallet rounding policy
- final frontend presentation enrichment on top of deterministic replay fields
- engine-native config generation if later integration requires Stake Engine-specific generated config files
