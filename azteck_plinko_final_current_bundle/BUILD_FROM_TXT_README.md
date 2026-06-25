# Build Azteck Artifacts From TXT

Use `build_azteck_artifacts_from_txt.py` on another computer to rebuild Azteck Plinko artifacts from TXT game inputs.

## Required files

At minimum, provide a multiplier TXT in the same structure as `AzreckPlinko_multipliers.txt`:

```text
Rows    Difficulty    The value of the multipliers
16      Expert        100k - 2.2k - 260 - ... - 100k
...
```

The script expects all four difficulties (`Low`, `Medium`, `High`, `Expert`) and rows `8..16`, with `rows + 1` multipliers per row.

Optional TXT files:
- `bets.txt` - parsed only when `--bet-source txt` is used.
- rules/description TXT/RTF/DOCX files can be kept in the same folder for audit traceability, but the build uses the multiplier TXT as the controlling math input.

## Run examples

From the `Stakes` workspace root:

```powershell
.\.venv\Scripts\python.exe build_azteck_artifacts_from_txt.py --txt-dir . --multipliers "AzreckPlinko_multipliers.txt" --variant current
```

Build the 25,000x cap fallback package too:

```powershell
.\.venv\Scripts\python.exe build_azteck_artifacts_from_txt.py --txt-dir . --multipliers "AzreckPlinko_multipliers.txt" --variant 2500
```

Build current, 2500, and biased-binomial variants:

```powershell
.\.venv\Scripts\python.exe build_azteck_artifacts_from_txt.py --txt-dir . --multipliers "AzreckPlinko_multipliers.txt" --variant all
```

Dry-run without modifying artifacts:

```powershell
.\.venv\Scripts\python.exe build_azteck_artifacts_from_txt.py --txt-dir . --multipliers "AzreckPlinko_multipliers.txt" --variant current --dry-run
```

Use bet values from a TXT file instead of the default official `0.01..500` ladder:

```powershell
.\.venv\Scripts\python.exe build_azteck_artifacts_from_txt.py --txt-dir . --multipliers "AzreckPlinko_multipliers.txt" --bets bets.txt --bet-source txt --max-bet 500
```

## What it produces

For `current`:
- `math-sdk/games/azteck_plinko_final/artifacts/publish_files/`
- `math-sdk/games/azteck_plinko_final/azteck_plinko_final_publish/`
- `math-sdk/games/azteck_plinko_final/azteck_plinko_final_publish.zip`
- `math-sdk/games/azteck_plinko_final/artifacts.zip`
- `math-sdk/games/azteck_plinko_final_publish.zip`
- `math-sdk/games/azteck_plinko_final/AzteckPlinkoFull_audit_formulas.xlsx`

For `2500`:
- `math-sdk/games/azteck_plinko_final/azteck_plinko_final_publish2500/`
- `math-sdk/games/azteck_plinko_final/azteck_plinko_final_publish2500.zip`
- `Plinko2500.xlsx`

For `biased`:
- outputs controlled by `rebuild_azteck_biased_binomial_package.py`.

## Dependencies

Run inside a Python environment that has the same dependencies as this workspace, notably:
- `numpy`
- `zstandard`
- `openpyxl`

The script calls the existing generator/validator scripts, so keep these files in the workspace root:
- `rebuild_azteck_final_symmetric.py`
- `gen_sdk_config.py`
- `sync_publish_destinations.py`
- `build_static_game_full_xlsx.py`
- `check_static_package_readiness.py`
- `check_excel_artifact_consistency.py`
- `rebuild_publish2500_peak_fix.py` for `--variant 2500`
- `rebuild_azteck_biased_binomial_package.py` for `--variant biased` or `all`
