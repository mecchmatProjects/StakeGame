---
agent: ask
model: GPT-5.4
description: Refresh an existing Azteck Plinko package after a math, lookup, or documentation change and bring workbook, validation, and docs back into sync.
---

Use the workflow in [STATIC_INSTANT_WIN_WORKFLOW_PLAYBOOK.md](../../STATIC_INSTANT_WIN_WORKFLOW_PLAYBOOK.md).

Task:
Apply a focused change to the existing Azteck Plinko package and refresh dependent artifacts without widening scope.

Inputs to collect or confirm:
- exact file or behavior to change
- whether lookup weights or publish files changed
- whether docs-only refresh is acceptable or full revalidation is required
- target RTP and tolerance for this refresh pass

Required refresh sequence:
1. Find the narrowest owning file for the requested change.
2. Apply the change.
3. If lookup or publish files changed:
   - rebalance lookup weights if needed
   - refresh validation outputs
   - recheck package hashes
   - rebuild workbook
4. If only workbook or docs changed:
   - rebuild workbook if any calculated table changed
   - refresh tutorial or README statements that reference package status
5. Validate the affected slice first, then run full package validation against math-sdk/games/azteck_plinko_final.
6. Remove any new scratch files created during the refresh.

Final response requirements:
- identify root change applied
- list dependent artifacts refreshed
- report workbook generation and validation result
- report final package validation result
- mention stale files removed during refresh
