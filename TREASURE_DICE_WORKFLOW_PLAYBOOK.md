# Treasure Dice Workflow Playbook

## Purpose

Use this playbook for future Treasure Dice-style instant-win deliveries that must produce:
- Stake Engine static package artifacts
- mathematician-facing documentation
- validation outputs
- the Excel audit workbook
- a clean final delivery folder with no stale scratch files

This playbook assumes the game brief lives in [Game_Description.md](Game_Description.md) and the clean delivery target is [math-sdk/games/treasure_dice_final](math-sdk/games/treasure_dice_final).

## Authoritative Inputs

Use these as the source of truth before touching any generated artifact:
- [Game_Description.md](Game_Description.md)
- [Pirates Treasure Dice Math.docx](Pirates%20Treasure%20Dice%20Math.docx)
- [Treasure_Dice_Mathematician_Artifacts_Package.docx](Treasure_Dice_Mathematician_Artifacts_Package.docx)
- Existing reusable skill: [.github/skills/treasure-dice-orchestrator/SKILL.md](.github/skills/treasure-dice-orchestrator/SKILL.md)

## Authoritative Outputs

The final publishable package is the single delivery authority:
- [math-sdk/games/treasure_dice_final](math-sdk/games/treasure_dice_final)

Inside that package, treat these as release outputs:
- [math-sdk/games/treasure_dice_final/artifacts/publish_files/index.json](math-sdk/games/treasure_dice_final/artifacts/publish_files/index.json)
- lookup CSVs and compressed books under `artifacts/publish_files/`
- [math-sdk/games/treasure_dice_final/artifacts/configs/config.json](math-sdk/games/treasure_dice_final/artifacts/configs/config.json)
- [math-sdk/games/treasure_dice_final/docs/treasure_dice_phase5_validation_summary.json](math-sdk/games/treasure_dice_final/docs/treasure_dice_phase5_validation_summary.json)
- [math-sdk/games/treasure_dice_final/TreasureDiceFull.xlsx](math-sdk/games/treasure_dice_final/TreasureDiceFull.xlsx)
- [math-sdk/games/treasure_dice_final/ARTIFACT_TUTORIAL.md](math-sdk/games/treasure_dice_final/ARTIFACT_TUTORIAL.md)

## Recommended Execution Plan

### 1. Normalize Requirements First

Extract and lock these before editing code or artifacts:
- published modes and costs
- target RTP and tolerance
- regular-route hit rates and multipliers
- bonus-buy cost and required metrics
- release exclusions
- documentation/delivery checklist

If any item is ambiguous, record the missing assumption explicitly instead of filling it in silently.

### 2. Update Math And Package Inputs

Use the existing scripts and package surfaces instead of creating new ad hoc paths:
- simulation and verification: [simulator.py](simulator.py)
- weight rebalance: [rebalance_lookup_rtp.py](rebalance_lookup_rtp.py)
- validation refresh: [refresh_final_phase5_outputs.py](refresh_final_phase5_outputs.py)
- workbook build: [build_treasure_dice_full_xlsx.py](build_treasure_dice_full_xlsx.py)

### 3. Rebalance Before Documentation Refresh

If lookup tables change:
1. rebalance package weights
2. refresh validation JSON/markdown
3. verify hashes in `config.json`
4. rebuild the Excel workbook
5. refresh any package tutorial or README statements that mention pass/fail status

### 4. Validate Narrowly, Then Validate End-To-End

Run narrow checks first:
- workbook generation succeeds
- package opens and hashes match
- per-mode RTP meets tolerance
- bonus and route metrics reconcile with docs

Then run the full package audit against the clean final folder.

### 5. Keep Generated Outputs In One Clean Place

Write final delivery artifacts only to:
- [math-sdk/games/treasure_dice_final](f:/Gaming/Stakes/math-sdk/games/treasure_dice_final)

Avoid leaving duplicate final workbooks or alternate publish copies in the root folder.

## Cleanup Policy

Delete these after the final package passes validation:
- scratch workbooks created for testing
- root-level duplicate final workbooks
- `__pycache__`
- generated `*.log` files
- `*_sample*` JSON/log outputs used only for dry runs

Retain these even if they are phase-specific:
- accepted phase reports
- scripts that reproduce package generation or validation
- root source docs used as the brief or handoff basis

## Future Task Modes

Use one of these two modes for future requests:
- full delivery mode: build or rebuild the entire Treasure Dice package from the brief to the clean final folder
- refresh mode: apply a focused change to an existing package, then rebalance, revalidate, and rebuild workbook/docs

## Done Criteria

A task is not complete until all of these are true:
- final package exists only in the clean final folder
- package hashes are current
- all published modes pass RTP tolerance
- workbook opens in Excel and uses formula-driven audit cells where calculations are shown
- package docs reflect the current validated package state
- no root-level scratch duplicates remain
