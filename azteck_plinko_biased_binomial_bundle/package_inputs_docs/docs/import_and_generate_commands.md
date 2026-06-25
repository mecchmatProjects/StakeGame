# Import and Generate Commands

## Canonical Workflow

Use the synthesis-first path for the current Azteck package.

1. Synthesize mode distributions from fixed constraints:

python synthesize_azteck_distributions.py --root math-sdk/games/azteck_plinko_final --target-rtp 0.9605

2. Generate published lookup and deterministic book artifacts:

python generate_provisional_lookups.py --root math-sdk/games/azteck_plinko_final --strict

3. Validate the package:

python validate_static_package.py --root math-sdk/games/azteck_plinko_final --target-rtp 0.9605 --rtp-tol 0.01 --title "Azteck Plinko"

4. Build the audit workbook:

python build_static_game_full_xlsx.py --root math-sdk/games/azteck_plinko_final --output math-sdk/games/azteck_plinko_final/AzteckPlinkoFull_audit_formulas.xlsx --name AzteckPlinkoFull --target-rtp 0.9605 --rtp-tol 0.01

5. Check package readiness:

python check_static_package_readiness.py --root math-sdk/games/azteck_plinko_final

6. Report coverage quality:

python report_azteck_mode_coverage.py --root math-sdk/games/azteck_plinko_final

## Notes

- The current package is model-synthesized from documented RTP and max-win constraints.
- Legacy manual import helpers were used during exploration only and are no longer part of the canonical package workflow.
