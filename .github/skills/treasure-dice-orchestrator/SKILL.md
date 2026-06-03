---
name: treasure-dice-orchestrator
description: 'Orchestrate the Treasure Dice math package from Game_Description.md: analyze the seven route options and the treasure_hunt_buy mode, keep release-specific exclusions, route RTP and volatility work to the instant-win-static-math skill, and route Math SDK artifact generation to the stake-engine-static-package skill.'
argument-hint: 'Path to Treasure Dice rules, for example: Game_Description.md'
user-invocable: true
disable-model-invocation: false
---

# Treasure Dice Orchestrator

## What This Skill Produces

Given `Game_Description.md`, this skill produces a Treasure Dice-specific execution plan that:

1. Confirms the seven regular route requirements and their RTP targets.
2. Routes regular-mode math, bonus-design math, and rounding/exposure analysis to `instant-win-static-math`.
3. Routes Stake Engine publication packaging to `stake-engine-static-package`.
4. Tracks Treasure Dice-specific deliverables, exclusions, and acceptance criteria until the package is complete.

## When To Use

Use this skill when the user asks to:

- Build the Treasure Dice math package.
- Turn `Game_Description.md` into an implementation workflow.
- Analyze Treasure Dice routes, RTP values, or Bonus Buy candidates.
- Prepare Treasure Dice for Stake Engine and Carrot RGS publication.

Typical trigger phrases:

- Treasure Dice math package
- Treasure Dice RTP analysis
- Treasure Dice Bonus Buy
- Treasure Dice Stake Engine package
- route game package from Game_Description.md

## Treasure Dice Scope

This skill is Treasure Dice-specific. It owns:

- The seven regular routes and their names.
- The `treasure_hunt_buy` Bonus Buy mode.
- The release exclusions in the game brief.
- Treasure Dice-specific presentation-event naming and acceptance-criteria tracking.

It does not re-derive generic math or generic SDK workflows when the reusable skills already cover them.

## Required Workflow

### Step 1: Read And Normalize The Game Brief

1. Read `Game_Description.md`.
2. Extract the regular route set, target RTP, Bonus Buy cost, and acceptance criteria.
3. Record unresolved external inputs, especially payout-cap data and final bonus volatility targets.

Completion check:

- Every deliverable in the brief is mapped to either math work, packaging work, or an external dependency.

### Step 2: Route Reusable Math Work

Use `instant-win-static-math` for:

- regular route multiplier confirmation
- volatility and variance analysis
- analysis of the route options and their RTP ladders
- `treasure_hunt_buy` candidate outcome distributions
- hit rate, zero rate, profit rate, median, P95, P99, and max win
- rounding drift at small bet levels
- max exposure formulas and payout-cap calculations

Completion check:

- Treasure Dice-specific reporting preserves the relevant option analysis, RTP values, and volatility outputs from the reusable math skill.

### Step 3: Route Packaging Work

Use `stake-engine-static-package` for:

- GameConfig and BetMode mapping for the eight published modes
- deterministic event mapping for route wins, route losses, near misses, and bonus events
- books, lookup tables, config outputs, index metadata, and compressed publish files
- replay-safe package validation for Carrot RGS publication

Completion check:

- Every package artifact named in the brief is owned by the packaging workflow.

### Step 4: Apply Treasure Dice Release Constraints

Keep these rules specific to Treasure Dice:

- No custom route slider in the release.
- No organic bonus trigger from regular routes in the release.
- Dice animation and map visuals do not affect settlement.
- Near miss is presentation-only and must not change RTP or weights.
- No assumed platform payout cap unless the operator provides one.

Completion check:

- The execution plan does not drift into out-of-scope features.

### Step 5: Track Deliverables Against Acceptance Criteria

Track these Treasure Dice deliverables through completion:

- approved regular-route paytable
- approved Bonus Buy candidate and recommendation
- `index.json`
- `lookUpTable.csv`
- compressed gameplay outcome files
- max-win metadata
- simulation report
- volatility report
- rounding rules
- exposure table when payout cap is provided
- replay-safe presentation-event mapping

Completion check:

- Sections 13-17 of `Game_Description.md` are fully covered.

## Decision Logic And Branching

- If a task is generic instant-win math, route to `instant-win-static-math`.
- If a task is generic Stake Engine packaging, route to `stake-engine-static-package`.
- If a task changes Treasure Dice release scope, keep it in this orchestrator and mark the scope decision explicitly.
- If Bonus Buy remains under-specified, require candidate distributions rather than inventing a final table silently.

## Quality Bar

A run is complete only if:

1. Treasure Dice-specific constraints remain isolated here.
2. Reusable math analysis is preserved rather than duplicated.
3. Reusable packaging guidance is used for SDK outputs.
4. Every deliverable in `Game_Description.md` is assigned, tracked, and checked.
5. The resulting workflow is reusable for future Treasure Dice iterations without contaminating the generic skills.
