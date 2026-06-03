# Treasure Dice Mathematician Handoff

## Purpose

This document turns the Treasure Dice math plan into an execution handoff for the mathematician/programmer role defined in [Instructions.txt](Instructions.txt). It breaks the work into executable phases, defines explicit outputs for each phase, and provides fill-in templates for Phase 1 and Phase 2.

Primary source brief: [Game_Description.md](Game_Description.md)

## Scope

In scope:

- Seven regular route modes.
- One Bonus Buy mode: `treasure_hunt_buy`.
- Theoretical math validation.
- Bonus distribution design.
- Rounding and exposure analysis.
- Deterministic event mapping.
- Stake Engine Math SDK package generation.
- Simulation and replay validation.
- Publication-ready deliverables.

Out of scope for this release:

- Custom route slider.
- Organic bonus trigger from regular routes.
- Frontend-driven settlement logic.
- Any visual choice that changes mathematical value.

## Execution Summary

| Phase | Name | Primary Goal | Primary Output | Gate |
| --- | --- | --- | --- | --- |
| 1 | Regular Routes Validation | Confirm route math and small-bet rounding | Approved regular route math pack | Gate 1 |
| 2 | Bonus Buy Design | Produce and select candidate bonus distributions | Approved Bonus Buy recommendation | Gate 2 |
| 3 | Deterministic Event Mapping | Lock replay-safe outcome-to-event mapping | Approved math specification handoff | Gate 3 |
| 4 | Stake Engine SDK Packaging | Build the eight-mode static outcome package | SDK package artifacts | Gate 4 |
| 5 | Validation And Reporting | Reconcile theoretical, simulated, and replay behavior | Simulation and validation report | Gate 5 |
| 6 | Publication Readiness | Assemble final delivery pack | Final delivery manifest | Gate 6 |

## Phase 1: Regular Routes Validation

### Objective

Confirm that the seven regular routes are mathematically correct, internally consistent, and ready for publication before rounding adjustments.

### Inputs

- [Game_Description.md](Game_Description.md)
- RTP target: 96.00%
- Route win chances from section 2.1
- Small denominations to test: 0.01, 0.02, 0.05

### Tasks

| ID | Task | Method | Output |
| --- | --- | --- | --- |
| P1-01 | Extract route definitions | Copy the seven route IDs, UI names, costs, win chances, and target multipliers from the brief | Normalized route table |
| P1-02 | Recompute route multipliers | Verify $M = r / p$ with $r = 0.96$ for each route | Multiplier confirmation table |
| P1-03 | Confirm theoretical RTP | Verify expected payout $p \times M = 0.96$ for each route | RTP confirmation table |
| P1-04 | Confirm net profit values | Recompute win payout and net profit at $B = 1$ | Paytable confirmation table |
| P1-05 | Confirm volatility values | Recompute variance and standard deviation for each route | Volatility report section |
| P1-06 | Define precision assumptions | Set internal precision for probabilities, multipliers, and payouts | Precision note |
| P1-07 | Run small-bet rounding checks | Test 0.01, 0.02, and 0.05 bet levels under chosen rounding assumptions | Rounding drift table |
| P1-08 | Define route max-win metadata | Confirm max win multiplier per route equals route multiplier unless changed later | Route max-win table |
| P1-09 | Prepare packaging handoff | Convert approved route math into a clean mode table for SDK packaging | Route handoff table |

### Required Outputs

- Approved regular-route mode table.
- Verified route paytable at base bet 1.
- Verified variance and standard deviation table.
- Precision and rounding assumptions.
- Rounding drift results for 0.01, 0.02, and 0.05 bet levels.
- Route max-win metadata.
- Phase 1 approval note.

### Gate 1 Criteria

Gate 1 passes only if all of the following are true:

- All seven regular routes remain at 96.00% theoretical RTP before rounding.
- The route multipliers match the published values or any deviations are explicitly resolved.
- The volatility table is confirmed.
- Small-bet rounding impact is documented.
- The route math can be handed off without unresolved contradictions.

## Phase 2: Bonus Buy Design

### Objective

Produce 1-2 mathematically valid candidate distributions for `treasure_hunt_buy`, compare them, and recommend one for packaging.

### Inputs

- [Game_Description.md](Game_Description.md)
- Bonus Buy cost: 100 x base bet
- Bonus RTP target: 96.00%
- Any available product guidance on volatility appetite or max exposure
- Any available operator payout-cap constraint

### Tasks

| ID | Task | Method | Output |
| --- | --- | --- | --- |
| P2-01 | Normalize bonus mode definition | Confirm cost, target RTP, and settlement basis | Bonus mode definition note |
| P2-02 | Choose candidate structure A | Define one candidate outcome family and event count model | Candidate A table |
| P2-03 | Choose candidate structure B | Define a second candidate outcome family if needed | Candidate B table |
| P2-04 | Compute candidate RTP | Sum weighted payouts for each candidate | Candidate RTP table |
| P2-05 | Compute candidate frequencies | Calculate hit rate, zero rate, below-cost rate, and profit rate | Frequency metrics table |
| P2-06 | Compute tail statistics | Calculate median, P95, P99, and max win for each candidate | Tail metrics table |
| P2-07 | Compute volatility metrics | Calculate variance and standard deviation | Volatility comparison table |
| P2-08 | Check event-count feasibility | Verify each outcome can map to deterministic presentation events | Event feasibility note |
| P2-09 | Check exposure | If payout cap exists, compute max allowed base bet per candidate | Exposure table or pending note |
| P2-10 | Recommend one candidate | Select the preferred candidate and explain tradeoffs | Bonus recommendation note |

### Required Outputs

- Candidate A distribution table.
- Candidate B distribution table if a second option is produced.
- Bonus metrics comparison table.
- Recommended Bonus Buy distribution.
- Bonus max-win multiplier.
- Exposure note or formula, depending on payout-cap availability.
- Phase 2 approval note.

### Gate 2 Criteria

Gate 2 passes only if all of the following are true:

- At least one candidate achieves 96.00% RTP.
- The selected candidate has explicit hit rate, zero rate, below-cost rate, profit rate, median, P95, P99, variance, and max win.
- The selected candidate can be mapped to deterministic presentation events.
- Exposure is either quantified or explicitly marked pending operator input.
- The selected candidate is suitable for SDK packaging.

## Phase 3: Deterministic Event Mapping

### Objective

Lock the replay-safe mapping between mathematical outcomes and presentation events.

### Tasks

| ID | Task | Method | Output |
| --- | --- | --- | --- |
| P3-01 | Define route event families | Map wins, losses, near misses, and loss variants | Route event map |
| P3-02 | Define bonus event families | Map multi-step bonus outcomes to `bonus_step` and `bonus_complete` flow | Bonus event map |
| P3-03 | Verify replay determinism | Ensure one mathematical outcome always yields one event sequence | Replay determinism note |
| P3-04 | Mark presentation-only variants | Confirm near miss and loss flavors do not alter value | Presentation constraint note |
| P3-05 | Prepare package handoff | Bundle event mapping with approved math tables | Phase 3 handoff pack |

### Required Outputs

- Route event mapping table.
- Bonus event mapping table.
- Replay-determinism note.
- Approved math specification handoff pack.

## Phase 4: Stake Engine SDK Packaging

### Objective

Generate the Treasure Dice static-outcome package in the Math SDK.

### Tasks

| ID | Task | Method | Output |
| --- | --- | --- | --- |
| P4-01 | Create game package structure | Create or adapt the Treasure Dice game folder in Math SDK | Game package folder |
| P4-02 | Define GameConfig | Set game identifiers, RTP, win caps, and mode metadata | GameConfig implementation |
| P4-03 | Define BetModes | Create seven route modes plus one bonus mode | BetMode definitions |
| P4-04 | Define Distributions | Encode win, loss, near miss, and bonus outcome families | Distribution definitions |
| P4-05 | Implement deterministic run logic | Ensure simulation id resolves to deterministic outcome/event flow | Deterministic game logic |
| P4-06 | Generate books | Run create_books for all published modes | Books outputs |
| P4-07 | Generate configs | Run generate_configs and produce package metadata | Config artifacts |
| P4-08 | Check package artifact set | Verify books, lookup tables, index metadata, compressed outputs, and publish files exist | Package completeness report |

### Required Outputs

- SDK game package implementation.
- Eight-mode books output.
- Lookup tables.
- `index.json` and related config outputs.
- Compressed publish artifacts.
- Phase 4 package completeness report.

## Phase 5: Validation And Reporting

### Objective

Prove that the generated package matches the approved math and behaves deterministically in replay.

### Tasks

| ID | Task | Method | Output |
| --- | --- | --- | --- |
| P5-01 | Run theoretical RTP checks | Reconcile final package data with approved math tables | RTP reconciliation note |
| P5-02 | Run simulated RTP checks | Simulate sufficient rounds for all eight modes | Simulation summary |
| P5-03 | Run weight checks | Confirm weight totals and outcome reachability | Weight audit |
| P5-04 | Run lookup checks | Confirm lookup values match books payout multipliers | Lookup audit |
| P5-05 | Run max-win checks | Confirm max win metadata is correct and not exceeded | Max-win audit |
| P5-06 | Run replay checks | Confirm same stored outcome yields same event sequence | Replay validation note |
| P5-07 | Run rounding checks on package outputs | Confirm small-bet behavior after packaging | Package rounding note |
| P5-08 | Build final reports | Prepare simulation report and volatility report | Final validation reports |

### Required Outputs

- Simulation report.
- Volatility report.
- Replay validation note.
- Lookup and weight audit notes.
- Final validation summary.

## Phase 6: Publication Readiness

### Objective

Assemble the final delivery pack and close the release checklist.

### Tasks

| ID | Task | Method | Output |
| --- | --- | --- | --- |
| P6-01 | Assemble final math report | Consolidate route math, bonus recommendation, rounding, and constraints | Final math report |
| P6-02 | Assemble final artifact manifest | List every delivered package file and report | Delivery manifest |
| P6-03 | Assemble risk assessment | Record residual risks and open assumptions | Risk assessment |
| P6-04 | Check acceptance criteria | Reconcile sections 13, 16, and 17 of the brief | Acceptance checklist |
| P6-05 | Mark release status | Declare ready, conditional, or blocked | Publication status note |

### Required Outputs

- Final math report.
- Delivery manifest.
- Risk assessment.
- Acceptance checklist.
- Publication status note.

## Dependencies And External Inputs

| Item | Needed By | Status |
| --- | --- | --- |
| Platform payout cap | Phase 2, Phase 5, Phase 6 | Pending unless operator provides it |
| Bonus volatility appetite | Phase 2 | Pending unless product confirms it |
| Final event naming approval | Phase 3 | Pending coordination |
| Python 3.12+ Math SDK environment | Phase 4 onward | Required |
| Rust/Cargo for optimization, if used | Phase 4 onward | Optional |

## Phase 1 Execution Record

### Phase 1 Header

- Date: 2026-06-03
- Analyst: GitHub Copilot (GPT-5.4), preliminary Phase 1 implementation
- Source file version: Game_Description.md, status `Draft for Mathematician Validation`, version `Full release game model, not MVP`
- RTP target: 96.00%
- Precision assumption: theoretical math kept to at least 4 decimal places for validation; published route multipliers kept to 2 decimal places as specified in the brief
- Currency rounding rule: provisional fiat check uses rounding to nearest 0.01 settlement unit, midpoint away from zero; crypto-like currency rounding remains open

### Route Confirmation Table

| Mode ID | Win Chance p | Published Multiplier | Recomputed Multiplier r/p | Match Y/N | Theoretical RTP | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| safe_shore | 0.80 | 1.20 | 1.20 | Y | 0.9600 | Exact match |
| hidden_bay | 0.60 | 1.60 | 1.60 | Y | 0.9600 | Exact match |
| coral_reef | 0.40 | 2.40 | 2.40 | Y | 0.9600 | Exact match |
| storm_route | 0.25 | 3.84 | 3.84 | Y | 0.9600 | Exact match |
| skull_island | 0.10 | 9.60 | 9.60 | Y | 0.9600 | Exact match |
| kraken_waters | 0.05 | 19.20 | 19.20 | Y | 0.9600 | Exact match |
| lost_treasure | 0.01 | 96.00 | 96.00 | Y | 0.9600 | Exact match |

### Volatility Confirmation Table

| Mode ID | Variance Published | Variance Recomputed | Std Dev Published | Std Dev Recomputed | Match Y/N | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| safe_shore | 0.2304 | 0.2304 | 0.4800 | 0.4800 | Y | Exact match |
| hidden_bay | 0.6144 | 0.6144 | 0.7838 | 0.7838 | Y | Exact match |
| coral_reef | 1.3824 | 1.3824 | 1.1758 | 1.1758 | Y | Exact match |
| storm_route | 2.7648 | 2.7648 | 1.6628 | 1.6628 | Y | Exact match |
| skull_island | 8.2944 | 8.2944 | 2.8800 | 2.8800 | Y | Exact match |
| kraken_waters | 17.5104 | 17.5104 | 4.1845 | 4.1845 | Y | Exact match |
| lost_treasure | 91.2384 | 91.2384 | 9.5519 | 9.5519 | Y | Exact match |

### Small-Bet Rounding Matrix

| Bet Level | Mode ID | Raw Win Payout | Rounded Win Payout | Effective RTP | RTP Drift vs 96.00% | Acceptable Y/N | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0.01 | safe_shore | 0.0120 | 0.01 | 0.8000 | -0.1600 | N | Material under-return under fiat-cent rounding |
| 0.01 | hidden_bay | 0.0160 | 0.02 | 1.2000 | 0.2400 | N | Material over-return under fiat-cent rounding |
| 0.01 | coral_reef | 0.0240 | 0.02 | 0.8000 | -0.1600 | N | Material under-return under fiat-cent rounding |
| 0.01 | storm_route | 0.0384 | 0.04 | 1.0000 | 0.0400 | N | Small but still outside target |
| 0.01 | skull_island | 0.0960 | 0.10 | 1.0000 | 0.0400 | N | Small but still outside target |
| 0.01 | kraken_waters | 0.1920 | 0.19 | 0.9500 | -0.0100 | N | Slight under-return |
| 0.01 | lost_treasure | 0.9600 | 0.96 | 0.9600 | 0.0000 | Y | Exact after rounding |
| 0.02 | safe_shore | 0.0240 | 0.02 | 0.8000 | -0.1600 | N | Material under-return under fiat-cent rounding |
| 0.02 | hidden_bay | 0.0320 | 0.03 | 0.9000 | -0.0600 | N | Material under-return |
| 0.02 | coral_reef | 0.0480 | 0.05 | 1.0000 | 0.0400 | N | Small but still outside target |
| 0.02 | storm_route | 0.0768 | 0.08 | 1.0000 | 0.0400 | N | Small but still outside target |
| 0.02 | skull_island | 0.1920 | 0.19 | 0.9500 | -0.0100 | N | Slight under-return |
| 0.02 | kraken_waters | 0.3840 | 0.38 | 0.9500 | -0.0100 | N | Slight under-return |
| 0.02 | lost_treasure | 1.9200 | 1.92 | 0.9600 | 0.0000 | Y | Exact after rounding |
| 0.05 | safe_shore | 0.0600 | 0.06 | 0.9600 | 0.0000 | Y | Exact after rounding |
| 0.05 | hidden_bay | 0.0800 | 0.08 | 0.9600 | 0.0000 | Y | Exact after rounding |
| 0.05 | coral_reef | 0.1200 | 0.12 | 0.9600 | 0.0000 | Y | Exact after rounding |
| 0.05 | storm_route | 0.1920 | 0.19 | 0.9500 | -0.0100 | N | Slight under-return |
| 0.05 | skull_island | 0.4800 | 0.48 | 0.9600 | 0.0000 | Y | Exact after rounding |
| 0.05 | kraken_waters | 0.9600 | 0.96 | 0.9600 | 0.0000 | Y | Exact after rounding |
| 0.05 | lost_treasure | 4.8000 | 4.80 | 0.9600 | 0.0000 | Y | Exact after rounding |

### Phase 1 Route Packaging Handoff Table

| Mode ID | Cost | Win Outcome Required | Lose Outcome Required | Preliminary Max Win Multiplier | Phase 1 Status | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| safe_shore | 1 | Yes | Yes | 1.20x | Approved mathematically | Loss presentation variants remain packaging detail |
| hidden_bay | 1 | Yes | Yes | 1.60x | Approved mathematically | Loss presentation variants remain packaging detail |
| coral_reef | 1 | Yes | Yes | 2.40x | Approved mathematically | Loss presentation variants remain packaging detail |
| storm_route | 1 | Yes | Yes | 3.84x | Approved mathematically | Loss presentation variants remain packaging detail |
| skull_island | 1 | Yes | Yes | 9.60x | Approved mathematically | Loss presentation variants remain packaging detail |
| kraken_waters | 1 | Yes | Yes | 19.20x | Approved mathematically | Loss presentation variants remain packaging detail |
| lost_treasure | 1 | Yes | Yes | 96.00x | Approved mathematically | Loss presentation variants remain packaging detail |

### Phase 1 Decision Log

- Unresolved issues: final fiat and crypto-like payout rounding rules are not closed; fiat-cent rounding causes material RTP drift at 0.01 and 0.02 for several routes and a minor drift for some 0.05 cases.
- Assumptions made: regular-route settlement uses the published total payout multipliers; provisional fiat check rounds win payouts to the nearest 0.01 settlement unit with midpoint away from zero; no platform payout cap is assumed in Phase 1.
- Changes required in published brief: none to the theoretical route math; add an explicit note in the final report that small-bet fiat rounding materially distorts several routes unless sub-cent precision or a different settlement policy is available.
- Packaging handoff ready: No, pending final rounding policy decision for low fiat denominations.
- Gate 1 status: Conditional
- Gate 1 approver: Pending mathematician review
- Gate 1 date: 2026-06-03

## Phase 2 Execution Record

### Phase 2 Header

- Date: 2026-06-03
- Analyst: GitHub Copilot (GPT-5.4), preliminary Phase 2 implementation
- Bonus mode ID: treasure_hunt_buy
- Bonus cost multiple: 100x base bet
- RTP target: 96.00%
- Platform payout cap provided: No
- Bonus volatility target provided: No

### Candidate Summary Table

| Candidate | Outcome Count | RTP | Hit Rate | Zero Rate | Below-Cost Rate | Profit Rate | Median | P95 | P99 | Variance | Max Win | Recommended Y/N |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | 6 | 96.00 | 82.00% | 18.00% | 44.00% | 38.00% | 90x B | 275x B | 275x B | 5646.0000 | 275x B | Y |
| B | 6 | 96.00 | 54.00% | 46.00% | 18.00% | 26.00% | 60x B | 320x B | 496x B | 17836.8000 | 496x B | N |

### Candidate Outcome Table A

| Outcome ID | Weight | Probability | Total Payout Multiplier vs B | Total Payout vs Cost | Event Count | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| A1 | 18 | 0.18 | 0x B | 0.00x cost | 3 | Full miss, short reveal path |
| A2 | 22 | 0.22 | 50x B | 0.50x cost | 3 | Low chest recovery outcome |
| A3 | 22 | 0.22 | 90x B | 0.90x cost | 4 | Near break-even path |
| A4 | 18 | 0.18 | 120x B | 1.20x cost | 4 | First profitable tier |
| A5 | 12 | 0.12 | 180x B | 1.80x cost | 5 | Mid-tier profitable path |
| A6 | 8 | 0.08 | 275x B | 2.75x cost | 6 | Top tier for Candidate A |

### Candidate Outcome Table B

| Outcome ID | Weight | Probability | Total Payout Multiplier vs B | Total Payout vs Cost | Event Count | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| B1 | 46 | 0.46 | 0x B | 0.00x cost | 3 | Full miss, highest zero rate |
| B2 | 18 | 0.18 | 60x B | 0.60x cost | 3 | Low-value recovery |
| B3 | 10 | 0.10 | 100x B | 1.00x cost | 4 | Break-even outcome |
| B4 | 12 | 0.12 | 180x B | 1.80x cost | 5 | Mid-tier profitable path |
| B5 | 9 | 0.09 | 320x B | 3.20x cost | 6 | High-tier profitable path |
| B6 | 5 | 0.05 | 496x B | 4.96x cost | 7 | Top tier for Candidate B |

### Exposure And Event Feasibility Notes

- Platform payout cap: Not provided.
- Max allowed base bet formula: max allowed base bet = absolute payout cap / max win multiplier.
- Candidate A max allowed base bet: Pending operator payout cap. Formula becomes cap / 275.
- Candidate B max allowed base bet: Pending operator payout cap. Formula becomes cap / 496.
- Candidate A deterministic event feasibility: Feasible. Event counts rise monotonically with payout tier and can be resolved before presentation starts.
- Candidate B deterministic event feasibility: Feasible. More volatile path length, but still deterministic if the full payout is fixed before the chest sequence begins.

### Recommendation Note

- Recommended candidate: A
- Rationale: Candidate A preserves the 96.00% RTP target while offering materially lower variance, a higher hit rate, a tighter tail, and a more even step-up reward ladder. It is more suitable for a first-release Bonus Buy because it reduces both player whiplash and operator exposure while still producing profitable outcomes and multi-step presentation variety.
- Main volatility tradeoff: Candidate A is meaningfully softer than Candidate B, with variance 5646.0000 versus 17836.8000 and a median of 90x B versus 60x B. Candidate B offers a larger top-end tail but at the cost of a much higher zero rate and more severe payout dispersion.
- Main exposure tradeoff: Candidate A tops out at 275x B, while Candidate B reaches 496x B. Without an operator payout cap, Candidate A is the safer default for release planning.
- Required follow-up before Phase 3: confirm whether product wants a softer, more regular Bonus Buy profile or wants to explicitly pursue a higher-volatility bonus; obtain payout-cap guidance if exposure limits are enforced at the operator level.

### Phase 2 Decision Log

- Unresolved issues: operator payout cap is not yet available; preferred Bonus Buy volatility appetite is not confirmed by product; final event naming remains pending Phase 3 coordination.
- Assumptions made: normalized provisional weights can be scaled without changing probabilities; payout multipliers are measured in multiples of base bet B; break-even is treated separately from profit in Candidate B.
- External inputs still missing: payout cap policy, bonus volatility preference, and final frontend event naming alignment.
- Packaging handoff ready: Yes, conditionally.
- Gate 2 status: Conditional
- Gate 2 approver: Pending mathematician review
- Gate 2 date: 2026-06-03

## Phase 3 Execution Record

### Phase 3 Header

- Date: 2026-06-03
- Analyst: GitHub Copilot (GPT-5.3-Codex), preliminary Phase 3 implementation
- Input regular route set: approved Phase 1 regular-route table
- Input bonus set: Candidate A from Phase 2 recommendation
- Event naming source: section 12 of [Game_Description.md](Game_Description.md)

### Route Event Family Mapping

All regular routes use one win family and five loss families.

- Win family event sequence: `route_reveal -> route_win -> route_complete`
- Loss family event sequences:
	- `route_reveal -> route_lose_storm -> route_complete`
	- `route_reveal -> route_lose_reef -> route_complete`
	- `route_reveal -> route_lose_skull -> route_complete`
	- `route_reveal -> route_lose_kraken -> route_complete`
	- `route_reveal -> route_near_miss -> route_complete`

Loss bucket split (constant across all seven regular modes):

- storm: 40% of losses
- reef: 25% of losses
- skull: 20% of losses
- kraken: 10% of losses
- near miss: 5% of losses

### Bonus Event Family Mapping (Candidate A)

Bonus mode uses only `bonus_step` and `bonus_complete` in deterministic order.

| Bonus Outcome ID | Probability | Payout Multiplier vs B | Event Count | Sequence |
| --- | --- | --- | --- | --- |
| A1 | 0.18 | 0x | 3 | `bonus_step, bonus_step, bonus_complete` |
| A2 | 0.22 | 50x | 3 | `bonus_step, bonus_step, bonus_complete` |
| A3 | 0.22 | 90x | 4 | `bonus_step, bonus_step, bonus_step, bonus_complete` |
| A4 | 0.18 | 120x | 4 | `bonus_step, bonus_step, bonus_step, bonus_complete` |
| A5 | 0.12 | 180x | 5 | `bonus_step, bonus_step, bonus_step, bonus_step, bonus_complete` |
| A6 | 0.08 | 275x | 6 | `bonus_step, bonus_step, bonus_step, bonus_step, bonus_step, bonus_complete` |

### Replay Determinism Validation Note

- Determinism rule applied: one `mode_id + outcome_id` pair maps to one payout and one ordered event sequence.
- Replay rule applied: replay uses stored identifiers and does not evaluate new RNG or user choice.
- Result: deterministic mapping validated at specification level.

### Presentation-Only Constraint Note

- Near miss and loss flavor variants are marked as presentation-only outcomes.
- Presentation-only outcomes always keep payout at 0 and remain within the lose bucket.
- Bonus chest progression can vary visually, but payout and sequence length are fixed by outcome ID before animation begins.

### Phase 3 Handoff Pack

- Phase 3 report: [Treasure_Dice_Phase_3_Event_Mapping_Report.md](Treasure_Dice_Phase_3_Event_Mapping_Report.md)
- Machine-readable mapping: [treasure_dice_phase3_mapping_spec.json](treasure_dice_phase3_mapping_spec.json)
- Upstream approved math references:
	- [Treasure_Dice_Phase_1_Math_Report.md](Treasure_Dice_Phase_1_Math_Report.md)
	- [Treasure_Dice_Phase_2_Bonus_Report.md](Treasure_Dice_Phase_2_Bonus_Report.md)

### Phase 3 Decision Log

- Unresolved issues: final cross-team event naming sign-off is still pending.
- Assumptions made: Candidate A remains selected for initial packaging; loss-family split remains mode-independent.
- Packaging handoff ready: Yes, conditionally.
- Gate 3 status: Conditional
- Gate 3 approver: Pending mathematician and integration review
- Gate 3 date: 2026-06-03

## Phase 4 Execution Record

### Phase 4 Header

- Date: 2026-06-03
- Analyst: GitHub Copilot (GPT-5.3-Codex), preliminary Phase 4 implementation
- Target SDK path: [math-sdk/games/treasure_dice](math-sdk/games/treasure_dice)
- Mapping source wired directly: [treasure_dice_phase3_mapping_spec.json](treasure_dice_phase3_mapping_spec.json)

### Implemented SDK Scaffold

Created Treasure Dice package scaffold files:

- [math-sdk/games/treasure_dice/game_config.py](math-sdk/games/treasure_dice/game_config.py)
- [math-sdk/games/treasure_dice/gamestate.py](math-sdk/games/treasure_dice/gamestate.py)
- [math-sdk/games/treasure_dice/game_events.py](math-sdk/games/treasure_dice/game_events.py)
- [math-sdk/games/treasure_dice/game_calculations.py](math-sdk/games/treasure_dice/game_calculations.py)
- [math-sdk/games/treasure_dice/game_executables.py](math-sdk/games/treasure_dice/game_executables.py)
- [math-sdk/games/treasure_dice/game_override.py](math-sdk/games/treasure_dice/game_override.py)
- [math-sdk/games/treasure_dice/run.py](math-sdk/games/treasure_dice/run.py)
- [math-sdk/games/treasure_dice/readme.txt](math-sdk/games/treasure_dice/readme.txt)

### Wiring Summary

- `game_config.py` now loads and validates probabilities from the Phase 3 mapping JSON.
- Eight bet modes are constructed from the mapping spec:
	- seven regular routes with cost 1
	- one bonus mode `treasure_hunt_buy` with cost 100
- `gamestate.py` selects outcomes deterministically per mode and simulation id.
- Event sequences are emitted directly from mapped `event_sequence` values.
- Bonus mode payout multipliers are interpreted in base-bet units (consistent with Phase 2 model and cost=100 RTP math).

### Execution Validation

- Static diagnostics check for scaffold files: passed.
- Mapping JSON syntax validation: passed.
- `zstandard` dependency installed in active Math SDK Python environment.
- Runtime execution `python games/treasure_dice/run.py` completed and generated package artifacts.

### Phase 4 Artifact Status

- SDK code scaffold: Complete.
- Books/config generation run: Complete.
- Package completeness report: [Treasure_Dice_Phase_4_Package_Completeness_Report.md](Treasure_Dice_Phase_4_Package_Completeness_Report.md)

### Phase 4 Decision Log

- Unresolved issues: none in packaging generation path.
- Assumptions made: Candidate A remains active bonus mapping.
- Packaging handoff ready: Yes.
- Gate 4 status: Pass
- Gate 4 approver: Pending mathematician and programmer sign-off
- Gate 4 date: 2026-06-03

### Immediate Next Action

Proceed to Phase 5 validation and reporting using generated Treasure Dice artifacts.

## Phase 5 Execution Record

### Phase 5 Header

- Date: 2026-06-03
- Analyst: GitHub Copilot (GPT-5.3-Codex)
- Package under validation: [math-sdk/games/treasure_dice](math-sdk/games/treasure_dice)
- Validation runner: [treasure_dice_phase5_validate.py](treasure_dice_phase5_validate.py)
- Validation data output: [treasure_dice_phase5_validation_summary.json](treasure_dice_phase5_validation_summary.json)

### Required Output Artifacts

- Simulation report: [Treasure_Dice_Phase_5_Simulation_Report.md](Treasure_Dice_Phase_5_Simulation_Report.md)
- Volatility report: [Treasure_Dice_Phase_5_Volatility_Report.md](Treasure_Dice_Phase_5_Volatility_Report.md)
- Replay and audit note: [Treasure_Dice_Phase_5_Replay_Audit_Report.md](Treasure_Dice_Phase_5_Replay_Audit_Report.md)
- Final validation summary: [Treasure_Dice_Phase_5_Final_Validation_Summary.md](Treasure_Dice_Phase_5_Final_Validation_Summary.md)

### Validation Check Outcomes

- Theoretical RTP reconciliation: Completed for all 8 modes.
- Simulated RTP reconciliation: Completed for all 8 modes from generated package lookup/books.
- Weight audit: Pass for all 8 modes.
- Lookup audit: Pass for all 8 modes.
- Max-win audit: Pass for all 8 modes.
- Replay determinism: Pass for all 8 modes.
- Package-level small-bet rounding review: Completed; regular-route low-denomination drift remains open dependency from Phase 1 policy discussion.

### Phase 5 Decision Log

- Unresolved issues: low-denomination regular-route rounding policy remains open (carry-over from Phase 1).
- Assumptions made: Phase 4 package outputs are the source of truth for this Phase 5 validation run.
- Final validation summary ready: Yes.
- Gate 5 status: Conditional Pass
- Gate 5 approver: Pending mathematician and programmer sign-off
- Gate 5 date: 2026-06-03

## Phase 6 Execution Record

### Phase 6 Header

- Date: 2026-06-03
- Analyst: GitHub Copilot (GPT-5.3-Codex)
- Objective: Assemble publication-readiness artifacts from completed Phases 1-5

### Phase 6 Required Outputs

1. Final delivery manifest: [Treasure_Dice_Phase_6_Delivery_Manifest.md](Treasure_Dice_Phase_6_Delivery_Manifest.md)
2. Risk assessment: [Treasure_Dice_Phase_6_Risk_Assessment.md](Treasure_Dice_Phase_6_Risk_Assessment.md)
3. Acceptance checklist: [Treasure_Dice_Phase_6_Acceptance_Checklist.md](Treasure_Dice_Phase_6_Acceptance_Checklist.md)
4. Publication status note: [Treasure_Dice_Phase_6_Publication_Status_Note.md](Treasure_Dice_Phase_6_Publication_Status_Note.md)

### Phase 6 Completion Summary

- Delivery manifest assembled with specification docs, validators, and SDK package artifacts.
- Risk register assembled with open and closed items, including inherited rounding-policy dependency.
- Acceptance checklist reconciled against section 17 criteria in [Game_Description.md](Game_Description.md).
- Publication status note prepared with conditional-ready recommendation.

### Phase 6 Decision Log

- Unresolved issues: low-denomination regular-route rounding policy decision and optional operator payout-cap input.
- Assumptions made: no additional package regeneration required after Phase 5 validator rerun.
- Final Phase 6 artifact set ready: Yes.
- Gate 6 status: Conditional Ready
- Gate 6 approver: Pending release owner, mathematician, and integration sign-off
- Gate 6 date: 2026-06-03

### Phase 6 Addendum: Full Consistency And Monte Carlo Audit

- Date: 2026-06-03
- Analyst: GitHub Copilot (GPT-5.3-Codex)
- Audit runner: [treasure_dice_full_consistency_mc_audit.py](treasure_dice_full_consistency_mc_audit.py)
- Audit outputs:
	- [Treasure_Dice_Full_Consistency_MC_Audit.md](Treasure_Dice_Full_Consistency_MC_Audit.md)
	- [treasure_dice_full_consistency_mc_audit.json](treasure_dice_full_consistency_mc_audit.json)

Audit scope executed:

1. Cross-artifact structural consistency between mapping, config, and publish index mode sets.
2. Presence and filename consistency for publish books, publish lookups, lookup tables, and force files.
3. Mode-level integrity checks for lookup-to-books matching, replay determinism, max-win alignment, and weight/book length parity.
4. Monte Carlo validation across all 8 modes at 1,000,000 rounds per mode.
5. Required report/document presence and markdown link integrity checks.

Audit result summary:

- Overall full audit pass: Yes.
- All 8 mode consistency checks: Pass.
- Monte Carlo RTP checks within statistical tolerance for all modes: Pass.
- Required artifacts present and markdown links valid: Pass.

Gate impact note:

- This addendum strengthens publication evidence and validates package consistency at high simulation volume.
- Gate 6 status remains Conditional Ready due to previously tracked policy dependencies (low-denomination rounding policy closure and optional payout-cap input), not due to package inconsistency.
