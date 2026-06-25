# Azteck Plinko Final Package

This folder is the clean final delivery target for Azteck Plinko static-outcome artifacts.

## Package Layout

- artifacts/configs: SDK and RGS configuration outputs
- artifacts/publish_files: index metadata, lookup tables, and compatibility-named book payloads
- artifacts/mapping: deterministic replay and presentation mapping specs
- docs: math reports and validation summaries
- inputs: canonical source tables required before final build

## Build Status

Current status: validated model-synthesized math package.

The current package contains:
- complete paytables for all 72 published modes under `inputs/`
- probability tables calibrated to the documented RTP target of `96.05%`
- published lookup tables and deterministic book payloads under `artifacts/publish_files/`
- validation outputs confirming RTP tolerance, weight integrity, and max-win reachability
- an Excel audit workbook with formula-driven RTP and probability checks

Book payload note:
- `books_<mode>.jsonl.zst` files are zstd-compressed binary payloads with JSONL content, matching expected Stake Engine publish file format.

## Current Validation State

- RTP tolerance: Pass
- Weight integrity: Pass
- Max-win reachability: Pass
- Inputs readiness: Pass

## Remaining Non-Math Follow-Up

The package is math-complete, but these surfaces remain implementation-policy items rather than final engine-native outputs:
- operator-specific currency rounding policy confirmation
- final frontend event enrichment on top of deterministic replay fields
- final Stake Engine generated config surfaces if a later integration step requires engine-native output files
