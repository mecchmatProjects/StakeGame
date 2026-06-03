---
name: slot-casino-modeling
description: 'Create a full slot-game analysis package from a rules description: extract mechanics, generate Excel RTP parameter tables, and produce scripts for exact and Monte Carlo validation using Stake Engine software. Use for slot-type casino games, reel games, paylines, ways games, scatters, wilds, free spins, multipliers, cascades, and common RTP balancing variants. Do not use for instant-win static-outcome route games or fixed-probability buy-bonus packages; use the instant-win-static-math and stake-engine-static-package skills for those.'
argument-hint: 'Path to rules, for example: rules.txt or rules.pdf'
user-invocable: true
disable-model-invocation: false
---

# Slot Casino Modeling

## What This Skill Produces

Given a rules description (PDF or text file) that defines a specific slot-type game, this skill produces:

1. Json files with normalized rule parameters and mechanics for Stake Engine
2. An Excel workbook with configurable parameters and sheets for multiple RTP targets.
3. A Python script for deterministic or semi-analytic calculation checks.
4. A Python Monte Carlo simulation script for empirical validation.

## When To Use

Use this skill when the user asks to:

- Explain or formalize slot game math.
- Convert game rules into a provable model.
- Build RTP tables across parameter sets.
- Validate slot math with exact and simulation methods.
- Document game logic for audit, implementation, or balancing.

Typical trigger phrases:

- slot math model
- RTP calculation
- reel strip probability
- free spins EV
- wild scatter bonus analysis
- Monte Carlo slot validation
- produce Excel from rules

Do not use this skill for:

- Instant-win route selection games.
- Fixed-probability two-outcome or discrete-outcome games.
- Standalone Bonus Buy outcome design without reel mechanics.
- Stake Engine static-outcome packaging tasks centered on `books`, `lookup tables`, `index.json`, or replay-safe event mapping.

## Supported Rule Patterns

Handle common slot variants and combinations of:

- Fixed paylines. (first-class)
- Ways-to-win (for example 243 ways, 1024 ways). (first-class)
- Cascades or avalanches. (first-class)
- Hold-and-spin and respin feature loops. (first-class)
- Progressive jackpot mechanics. (first-class)
- Left-to-right, all-ways, and mixed directional evaluation.
- Wilds (substitute, sticky, expanding, multiplier wild).
- Scatters and bonus triggers.
- Free spins with retrigger.
- Multipliers (line-level, spin-level, feature-level).
- Collect symbols or meter-based features.
- Progressive feature states modeled as finite states.

This skill assumes the payout logic is primarily driven by reels, symbol layouts, paylines, ways, cascades, or stateful slot features. If the rules are better expressed as explicit outcome probabilities and payout multipliers rather than reel mechanics, stop and route to the instant-win/static-outcome skill set instead.

## Inputs

Collect or confirm these inputs before modeling:

1. Rules source PDF path.
2. Reel/window layout and symbol set.
3. Paytable and payout units (bet, line bet, coin).
4. Win-combination rules.
5. Feature triggers and feature logic.
6. Target RTP list (for example 92, 94, 96).
7. Any fixed constraints (hit rate, volatility bands, max win cap).

Default RTP targets when not provided:

- 85
- 87
- 90
- 92
- 94
- 96

## Procedure

### Step 1: Parse And Normalize Rules

1. Extract the rule text.
2. Build a normalized rule schema with named fields as required by Stake Engine, for example:
   - base game
   - symbol catalog
   - paytable
   - reel behavior
   - feature definitions
   - payout composition
3. Identify ambiguities, missing values, and contradictions.
4. Resolve units and normalize all payouts to a single base (for example per total bet).

Completion check:

- Every payout event in rules maps to a normalized formula input.
- No unresolved ambiguity remains for core payout logic.

### Step 2: Build Mathematical Model

1. Define random variables for reels, symbols, and feature states.
2. Define event sets for each payout type.
3. Compute base-game EV and variance components.
4. Model feature EV using either:
   - closed-form conditional expectation, or
   - Markov/state transition equations.
5. Aggregate to total RTP:

$$
\mathrm{RTP}_{total}=\mathrm{RTP}_{base}+\mathrm{RTP}_{features}
$$

6. Add volatility metrics when requested:
   - hit frequency
   - payout distribution moments
   - tail metrics

Completion check:

- The model includes explicit formulas for all payout sources.
- Assumptions are listed and testable.

### Step 3: Generate Documentation tutorial 

Create a text file containing:
Insruction of what has to be done to produce Stake Engine artifacts for Game modelling.

Completion check:

- Equations compile and symbols are consistently defined.
- A reviewer can reproduce all final RTP formulas.

### Step 4: Generate Excel RTP Workbook

Create an Excel workbook with sheets:

1. Input Parameters.
2. Paytable.
3. Reel/Weight Configuration.
4. Feature Parameters.
5. RTP Scenarios (one block per target RTP).
6. Sensitivity Analysis.
7. Validation Summary.

For each RTP target:

1. Solve or tune designated parameters.
2. Recompute RTP decomposition.
3. Record constraints and pass/fail checks.

Completion check:

- Each RTP target has a reproducible parameter set.
- All formulas are linked from input sheets, not hard-coded in result cells.

### Step 5: Generate Deterministic Check Script

Create a Python script that:

1. Loads normalized parameters.
2. Computes theoretical EV/RTP components.
3. Outputs a structured report matching LaTeX and Excel totals.
4. Includes unit checks for probabilities and payout scaling.

Minimum checks:

- Probability mass sanity (sum to 1 where required).
- Non-negative event probabilities.
- Consistency between per-line and per-bet representations.

Completion check:

- Script reproduces documented RTP values within strict tolerance.

### Step 6: Generate Monte Carlo Validation Script

Create a Python script that:

1. Simulates spins with full rule logic.
2. Supports a deterministic seed.
3. Runs enough trials for confidence intervals.
4. Reports empirical RTP and confidence bounds.

Suggested output:

- empirical RTP
- 95 percent confidence interval
- per-feature trigger frequency
- key distribution percentiles

Completion check:

- Theoretical RTP lies inside the simulation confidence interval for sufficient sample size.

### Step 7: Cross-Artifact Reconciliation

1. Compare LaTeX totals, Excel totals, deterministic Python totals, and Monte Carlo estimate.
2. Flag mismatch above threshold (default: 1e-4 absolute for deterministic sources).
3. Produce a final reconciliation note.

Completion check:

- All deterministic artifacts align within tolerance.
- Simulation deviation is statistically explained.

## Decision Logic And Branching

- If the game has no memory/stateful feature, prefer closed-form EV first.
- If the game includes retriggers, persistent multipliers, or meters, use state-based model.
- If reel strips are unavailable but symbol frequencies are available, use weighted approximation and label it as approximation.
- If RTP targets conflict with constraints, produce nearest feasible parameter sets and mark infeasible targets explicitly.

## Output Contract

Fixed output folder layout:

- output/latex/game_model.tex
- output/excel/game_rtp_parameters.xlsx
- output/python/verify_rtp.py
- output/python/game_pyomo_model.py
- output/python/search_game_tables.py
- output/python/monte_carlo_check.py
- output/reports/reconciliation_report.md

Do not rename these by default. Instead of "game" pattern U can use the name of the game if it is provided by the user.  

Artifact names:

- game_model.tex
- game_rtp_parameters.xlsx
- verify_rtp.py
- game_pyomo_model.py
- search_game_tables.py
- monte_carlo_check.py
- reconciliation_report.md

## Quality Bar

A run is complete only if:

1. Every rule mechanic is represented in equations and code.
2. All assumptions are explicit.
3. Deterministic outputs agree across LaTeX, Excel, and Python.
4. Monte Carlo results statistically support deterministic RTP.
5. Produced files are readable, versionable, and reproducible.

## Repo Workflow

For this repository, prefer the compact-RAG workflow documented in `SLOT_MODELING_RAG_PLAYBOOK.md`.

Required repo-first process:

1. Extract the PDF once into `output/catalog/`.
2. Build `output/catalog/<game>_rag_packet.md` as the reusable normalized source of truth.
3. Generate TeX and deterministic Python from that packet first.
4. Generate the Excel workbook and Monte Carlo script second.
5. Reconcile all artifacts in a final consistency pass.

If a reusable invocation is needed, use `.github/prompts/slot-model-package.prompt.md` as the repo prompt template.

## Prompt Examples

- Build a slot model package from rules.pdf with RTP targets 92, 94, and 96.
- From this game PDF, produce LaTeX derivation, Excel parameter tables, verify_rtp.py, and monte_carlo_check.py.
- Analyze this cascading reels game and include feature-state Markov modeling plus Monte Carlo validation.
