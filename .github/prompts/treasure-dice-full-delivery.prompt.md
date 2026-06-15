---
agent: ask
model: GPT-5.4
description: Build or rebuild the full Treasure Dice static package, workbook, and delivery docs from Game_Description.md using the repo playbook.
---

Use the workflow in [TREASURE_DICE_WORKFLOW_PLAYBOOK.md](../../TREASURE_DICE_WORKFLOW_PLAYBOOK.md).

Task:
Build the full Treasure Dice delivery package from the current brief and existing repo scripts with the least drift between math, package outputs, workbook, and documentation.

Inputs to collect or confirm:
- path to the active game brief
- whether the task is a fresh build or a rebuild of an existing package
- target RTP and tolerance
- whether bonus-buy outcomes are already approved or still candidate-based
- whether operator payout-cap input is available

Required workflow:
1. Read the brief and extract all published modes, costs, RTP targets, exclusions, and deliverables.
2. Treat `math-sdk/games/treasure_dice_final` as the only final delivery target.
3. Update or verify package artifacts with the existing repo scripts instead of inventing new generation paths.
4. If lookup weights change, rebalance first, then refresh validation outputs, then rebuild the workbook and documentation.
5. Reconcile the final package against the brief:
   - mode list
   - costs
   - regular-route hit rates
   - bonus-buy metrics
   - validation pass state
   - hash integrity
6. Remove scratch duplicates and obsolete generated logs/sample outputs from the workspace root when the delivery is complete.

Mandatory outputs:
- clean final package folder
- current validation JSON and markdown
- current Excel audit workbook
- artifact tutorial / delivery docs aligned with the package

Final response requirements:
- state which files were updated
- state whether any assumptions were required
- state whether all modes pass RTP tolerance
- state whether hashes and workbook validation passed
- state which files were removed as outdated
- call out any remaining external dependency, especially payout-cap input
