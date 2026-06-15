---
agent: ask
model: GPT-5.4
description: Refresh an existing Treasure Dice package after a math, lookup, or documentation change and bring workbook, validation, and docs back into sync.
---

Use the workflow in [TREASURE_DICE_WORKFLOW_PLAYBOOK.md](../../TREASURE_DICE_WORKFLOW_PLAYBOOK.md).

Task:
Apply a focused change to the existing Treasure Dice package and fully refresh all dependent artifacts without widening scope.

Inputs to collect or confirm:
- exact file or behavior to change
- whether lookup weights or package publish files changed
- whether docs-only refresh is acceptable or full revalidation is required
- target RTP and tolerance for the refresh pass

Required refresh sequence:
1. Find the narrowest owning file for the requested change.
2. Apply the change.
3. If lookup or publish files changed:
   - rebalance lookup weights if needed
   - refresh validation outputs
   - recheck package hashes
   - rebuild `TreasureDiceFull.xlsx`
4. If only workbook or docs changed:
   - rebuild the workbook if any calculated table changed
   - refresh tutorial/README statements that reference package status
5. Validate the exact affected slice first, then run the full package pass against `math-sdk/games/treasure_dice_final`.
6. Remove any new scratch files created during the refresh.

Final response requirements:
- identify the root change applied
- list dependent artifacts refreshed
- report workbook open/validation result
- report final package validation result
- mention any stale files removed during the refresh
