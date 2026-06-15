# Static Instant-Win Workflow Playbook

## Purpose

Use this playbook for static-outcome and instant-win deliveries that must produce:
- Stake Engine static package artifacts
- mathematician-facing documentation
- validation outputs
- an Excel audit workbook
- a clean final delivery folder with no stale scratch files

This playbook is game-agnostic. It is suitable for route games, Plinko-style burst games, and other deterministic static-outcome packages.

## Inputs Checklist

Confirm these before implementation:
- source brief path (for example, DOCX or markdown)
- finalized mode matrix (all playable modes)
- cost model per mode
- target RTP and tolerance policy
- max win and exposure constraints
- rounding policy for small-denomination bets
- replay-state requirements
- operator payout-cap input, if applicable

If any are missing, log them as blocking external dependencies instead of guessing.

## Authoritative Outputs

Treat one clean folder as the only final delivery authority:
- math-sdk/games/<game_id>_final

Expected release output families:
- artifacts/publish_files/index.json
- artifacts/publish_files lookup CSV files
- artifacts/publish_files compressed books files
- artifacts/configs config files
- docs validation and math reports
- final workbook
- artifact tutorial

## Recommended Execution Plan

### 1. Normalize Requirements

Extract and lock:
- mode names and costs
- target RTP per mode
- full multiplier or payout distributions
- feature-mode rules (if any)
- exclusions and non-release items
- acceptance criteria

### 2. Build Math Model

For each mode:
- expected value and RTP equation
- hit rate, zero rate, profit rate
- variance and volatility indicators
- median, P95, P99, max-win probability
- exposure formula

For under-specified features, produce candidate distributions and keep recommendation rationale explicit.

### 3. Package For Stake Engine

Implement deterministic static outcomes in the game package and generate:
- books
- lookup tables
- configs
- index metadata
- compressed publish outputs

Keep replay deterministic for the same stored outcome.

### 4. Validate In Layers

Run narrow checks first:
- lookup and book payout coherence
- per-mode RTP tolerance
- hash and config consistency
- rounding drift at required stake levels

Then run full-package validation and compile docs/workbook.

### 5. Clean Final Delivery

Retain only final deliverables in the final package path. Remove temporary artifacts and root-level scratch outputs from the build run.

## Cleanup Policy

Safe to remove after final pass:
- root-level temporary workbooks
- generated log files used for dry runs
- sample outputs for debugging only
- __pycache__

Keep:
- source brief and source references
- scripts required to reproduce package generation and validation
- accepted validation reports

## Done Criteria

A delivery is complete only if all of these are true:
- final package is consolidated in one clean target folder
- all published modes pass RTP tolerance
- lookup, books, and configs are coherent
- workbook is generated from current package artifacts
- docs reflect current validated state
- unresolved external dependencies are explicitly listed
