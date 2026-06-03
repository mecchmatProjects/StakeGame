---
name: instant-win-static-math
description: 'Model instant-win and static-outcome casino games for Stake Engine: fixed-probability route games, discrete outcome tables, buy bonus distributions, RTP analysis, volatility, rounding checks, and max exposure calculations. Use when the game is defined by explicit outcome probabilities or weighted outcomes rather than reel strips.'
argument-hint: 'Path to rules or game description, for example: Game_Description.md'
user-invocable: true
disable-model-invocation: false
---

# Instant-Win Static Math

## What This Skill Produces

Given a rules description for an instant-win or static-outcome game, this skill produces:

1. A normalized mode table with costs, win chances, payout multipliers, and target RTP values.
2. Mathematical analysis for each mode, including expected value, variance, volatility, hit rate, and max win.
3. One or more candidate discrete-outcome distributions for buy-bonus or feature modes when those distributions are not fully defined.
4. Rounding and exposure analysis for small denominations and platform payout-cap calculations.
5. Deterministic validation notes that can be handed to Stake Engine packaging or implementation work.

## When To Use

Use this skill when the user asks to:

- Formalize an instant-win or route-selection game.
- Build RTP tables for fixed-probability or weighted-outcome modes.
- Analyze game options, risk ladders, or alternative mode choices.
- Design or compare Bonus Buy distributions.
- Calculate hit rate, zero rate, profit rate, median, P95, P99, or max win.
- Check rounding drift for small bets and payout precision rules.
- Prepare a math brief before building Stake Engine artifacts.

Typical trigger phrases:

- instant win math model
- route game RTP
- fixed probability payout analysis
- discrete outcome paytable
- Bonus Buy distribution design
- volatility analysis
- payout rounding analysis
- max exposure table

Do not use this skill for:

- Reel-strip balancing or symbol-frequency slot analysis.
- Frontend implementation or animation design.
- Writing the final Math SDK package files themselves.

## Supported Rule Patterns

Handle instant-win or static-outcome variants such as:

- Binary win/lose modes with fixed win probability.
- Route-selection or risk-ladder mode sets.
- Discrete weighted-outcome tables.
- Buy-bonus modes with independent outcome distributions.
- Multi-event outcomes whose full value is determined before presentation starts.
- Presentation variants that do not change settlement.
- Games where replay-safe event mapping is required but outcome math is independent of visuals.

## Inputs

Collect or confirm these inputs before modeling:

1. Rules source path.
2. Mode list and naming.
3. Cost or cost-multiplier for each mode.
4. Known probabilities, weights, or target RTP values.
5. Payout definition: total payout, net profit, multiplier base, and currency unit.
6. Any constraints on volatility, max win, hit rate, or zero rate.
7. Any payout-cap or exposure constraint supplied by the platform.
8. Small-denomination bet levels that must be checked.

## Procedure

### Step 1: Normalize Modes And Units

1. Extract the rules and list every playable mode.
2. Normalize costs, payouts, and multipliers to one base stake definition.
3. Separate settlement logic from presentation-only events.
4. Record any missing quantities or contradictory statements.

Completion check:

- Every mode has a clear stake definition.
- Every payout is expressed in one normalized unit.
- Presentation-only elements are explicitly marked as non-mathematical.

### Step 2: Build Theoretical Math

1. For each fixed-probability mode, compute the payout multiplier implied by the target RTP.
2. For each discrete-outcome mode, compute expected payout from weighted outcomes.
3. Compute hit rate, zero rate, profit rate, expected payout, and expected platform revenue.
4. Compute variance, standard deviation, and useful tail summaries when requested.

Useful forms:

$$
M = \frac{r}{p}
$$

$$
\mathrm{RTP} = \sum_i w_i x_i
$$

where $r$ is target RTP, $p$ is win probability, $w_i$ are normalized outcome probabilities, and $x_i$ are payout multipliers.

Completion check:

- Each mode has a falsifiable RTP equation.
- Assumptions are explicit and tied to named modes.

### Step 3: Analyze Options And Candidate Tables

1. If the game includes a risk ladder or multiple routes, compare the options by hit rate, multiplier, and volatility.
2. If a bonus distribution is under-specified, create 1-2 candidate tables.
3. For each candidate, report RTP, hit frequency, zero-payout probability, below-cost probability, profit probability, median, P95, P99, variance, and max win.
4. Recommend one candidate and explain the tradeoff in volatility and exposure terms.

Completion check:

- The user can compare mode options on more than RTP alone.
- Any undefined buy-bonus mode is narrowed to concrete candidate tables.

### Step 4: Rounding And Exposure Checks

1. Define payout precision assumptions.
2. Check actual RTP after rounding for required small bet levels.
3. If a platform payout cap exists, compute max allowed base bet per mode.
4. Flag cases where rounding or cap constraints materially change the published math.

Completion check:

- Small-bet rounding drift is quantified.
- Exposure formulas are ready for publication or operator review.

### Step 5: Prepare Packaging Hand-off

1. Produce a clean mode table for packaging.
2. Produce deterministic event-mapping requirements if presentation variants exist.
3. List every unresolved external dependency separately.
4. Hand off approved mode math to the Stake Engine packaging workflow.

Completion check:

- The output can be consumed directly by the Stake Engine static package skill.

## Decision Logic And Branching

- If the game is primarily driven by reel mechanics, stop and use slot-casino-modeling instead.
- If a bonus mode is undefined, produce candidate distributions instead of inventing one silently.
- If the platform payout cap is unknown, provide the formula and mark exposure as pending input.
- If presentation choices appear to alter value, require that the outcome be pre-determined before presentation or that all choices be mathematically equivalent.

## Output Contract

Preferred outputs:

- A normalized mode table.
- A mode-by-mode RTP and volatility summary.
- A bonus candidate comparison table when applicable.
- Rounding and exposure notes.
- A hand-off summary for packaging.

## Quality Bar

A run is complete only if:

1. Every playable mode has an explicit RTP definition.
2. Mode comparisons preserve relevant analysis such as option design, RTP, volatility, and tail risk.
3. Rounding effects are checked where required.
4. Any undefined bonus distribution is converted into concrete candidates with clear tradeoffs.
5. The result is reusable for packaging without re-deriving the math.
