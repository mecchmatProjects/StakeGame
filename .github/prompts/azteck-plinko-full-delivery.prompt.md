---
agent: ask
model: GPT-5.4
description: Build or rebuild the full Azteck Plinko static package, validation docs, and workbook from the active brief with minimal drift between math and publish artifacts.
---

Use the workflow in [STATIC_INSTANT_WIN_WORKFLOW_PLAYBOOK.md](../../STATIC_INSTANT_WIN_WORKFLOW_PLAYBOOK.md).

Task:
Build the full Azteck Plinko delivery package from the current brief and existing repo scripts with the least drift between math, package outputs, workbook, and documentation.

Inputs to collect or confirm:
- path to the active game brief
- whether this is a fresh build or rebuild
- target RTP and tolerance (default target is 96.05 percent unless overridden)
- full paytable coverage for all modes (difficulty x rows, plus 100 Balls)
- rounding policy for small bets and currency handling
- operator payout-cap input availability
- replay-state requirements for deterministic reconstruction

Required workflow:
1. Read the brief and extract all published modes, costs, RTP targets, exclusions, and deliverables.
2. Treat math-sdk/games/azteck_plinko_final as the only final delivery target.
3. Build or verify package artifacts with existing repo scripts when possible.
4. If lookup weights change, rebalance first, then refresh validation outputs, then rebuild workbook and documentation.
5. Reconcile final package against brief:
   - mode list and costs
   - normal-mode and 100 Balls metrics
   - RTP tolerance pass state
   - max-win constraints
   - hash integrity
6. Remove scratch duplicates and obsolete generated logs or samples from the workspace root when complete.

Mandatory outputs:
- clean final package folder
- current validation JSON and markdown
- current Excel audit workbook
- artifact tutorial and delivery docs aligned with package
- explicit missing-input list if source brief remains under-specified

Final response requirements:
- list files updated
- list assumptions required
- report RTP tolerance result by mode group
- report hash and workbook validation status
- list outdated files removed
- list remaining external dependencies, especially payout-cap and missing paytable data
