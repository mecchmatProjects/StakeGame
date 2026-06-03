---
name: stake-engine-static-package
description: 'Build Stake Engine Math SDK packages for static-outcome games: convert approved mode tables and deterministic event mappings into books, lookup tables, config files, index metadata, compressed publish artifacts, and validation outputs for RGS publication. Use for static outcomes, instant-win games, route games, and pre-generated weighted outcome packages.'
argument-hint: 'Path to approved math brief or game description, for example: Game_Description.md'
user-invocable: true
disable-model-invocation: false
---

# Stake Engine Static Package

## What This Skill Produces

Given approved mode math and deterministic event requirements, this skill produces:

1. Guidance for building the game folder and configuration surfaces in the Stake Engine Math SDK.
2. A packaging plan for `GameConfig`, `BetMode`, `Distribution`, and deterministic event generation.
3. The required publication artifacts: books, lookup tables, config files, index metadata, and compressed publish outputs.
4. Validation expectations for replay safety, payout coherence, and package completeness.

## When To Use

Use this skill when the user asks to:

- Convert approved static-outcome math into Stake Engine artifacts.
- Build a Math SDK package for an instant-win or route game.
- Generate books, lookup tables, index.json, or publish files.
- Define deterministic event mapping for replay-safe outcomes.
- Prepare a package for Carrot RGS publication.

Typical trigger phrases:

- Stake Engine static package
- Math SDK package
- generate books and lookup tables
- index json for Stake Engine
- static outcome package
- publish files for RGS
- replay-safe event mapping

Do not use this skill for:

- Deriving RTP or volatility from scratch.
- Balancing reel strips or slot mechanics.
- Frontend implementation details beyond deterministic event contracts.

## Inputs

Collect or confirm these inputs before packaging:

1. Approved mode table with costs, payout multipliers, or weighted outcomes.
2. Event-mapping requirements for replay-safe presentation.
3. Max-win metadata per mode.
4. Any mode-level exclusions or release constraints.
5. SDK runtime requirements and chosen template game.

## Procedure

### Step 1: Choose The Closest SDK Surface

1. Start from `math-sdk/games/template` or the nearest example game.
2. Use `math-sdk/games/0_0_lines/run.py` as a workflow reference when no static-outcome example exists.
3. Anchor implementation decisions to the real SDK abstractions in:
   - `math-sdk/src/config/config.py`
   - `math-sdk/src/config/betmode.py`
   - `math-sdk/src/config/distributions.py`
   - `math-sdk/src/state/run_sims.py`
   - `math-sdk/src/write_data/write_configs.py`

Completion check:

- The package plan points to specific SDK surfaces rather than generic placeholders.

### Step 2: Define Modes And Criteria

1. Configure `GameConfig` with game identifiers, RTP targets, win caps, and mode metadata.
2. Define one `BetMode` per published mode with explicit cost and max-win values.
3. Define `Distribution` criteria that drive static-outcome generation and any presentation subtypes.
4. Keep presentation-only variants from altering the total win probability or payout distribution.

Completion check:

- Each published mode has one explicit SDK representation.
- Criteria quotas and weights are coherent with the approved math.

### Step 3: Define Deterministic Outcome And Event Flow

1. Implement deterministic `run_spin` behavior that produces the approved outcome for each simulation id.
2. Emit replay-safe events whose presentation is fully determined by the chosen outcome.
3. Keep settlement independent of frontend choices.
4. Ensure `payoutMultiplier` values align with lookup-table entries.

Completion check:

- Replay shows the same event path for the same stored outcome.
- Settlement data and presentation data are unambiguous.

### Step 4: Generate SDK Outputs

1. Run `create_books` using the required number of simulations per mode.
2. Run `generate_configs` to produce frontend and backend configuration files.
3. Produce lookup tables, segmented criteria tables, and compressed books where required.
4. Check the publish folder contents for package completeness.

Expected artifact families include:

- books
- compressed gameplay outputs
- lookup tables
- config files
- index metadata
- publish files

Completion check:

- The package contains the artifacts required for RGS publication.

### Step 5: Validate The Package

1. Check theoretical math against the generated lookup values.
2. Check lookup-table coherence with `payoutMultiplier` in books.
3. Check max-win metadata.
4. Check invalid or unreachable outcomes.
5. Check replay-safe event mapping and any small-bet payout behavior that belongs in package validation.

Completion check:

- The package is internally coherent and publication-ready.

## Decision Logic And Branching

- If the math itself is not approved yet, stop and route back to instant-win-static-math.
- If the package requires reel-driven logic, route to slot-casino-modeling instead.
- If an event mapping is not deterministic in replay, treat that as a blocking defect.
- If the SDK README and local repo conventions disagree, use the stricter SDK runtime requirement for SDK execution.

## Output Contract

Preferred outputs:

- A concrete SDK packaging plan.
- The list of required generated artifact families.
- Validation steps tied to books, lookup tables, configs, and publish files.
- A publish-readiness summary.

## Quality Bar

A run is complete only if:

1. Mode metadata, outcome tables, and event mapping agree.
2. The package references real Stake Engine SDK abstractions and artifact names.
3. Replay safety is explicit and testable.
4. Generated outputs match the approved math model.
5. The result is suitable for Carrot RGS publication workflow.
