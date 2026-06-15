```markdown
# Status: Draft for Mathematician Validation

**Game Type:** Instant win / route selection game with Bonus Buy mode

**Platform:** Stake Engine / Carrot RGS

**Math Publication:** Stake Engine Math SDK static outcome package

**Target RTP for each available mode:** 96.00%

**House Edge:** 4.00%

**Version:** Full release game model, not MVP

**Official Requirements:**
[[https://stake-engine.com/docs/math]](https://stake-engine.com/docs/math)

---

## 1. Document Purpose

To verify, supplement, and formalize the mathematical model of Treasure Dice for a production release via Stake Engine.

The game has seven regular routes and one Bonus Buy mode. Each available mode is published as a separate static mode in the Stake Engine math package. All possible outcomes are pre-generated using the Stake Engine Math SDK and consumed by Carrot RGS.

The map, ship, dice, storm, reefs, Kraken, chests, and near misses are presentation layer elements. They must not affect payout, outcome weight, or RTP.

---

## 2. Game Modes in Release

### 2.1 Regular Routes

The player chooses one of seven predefined routes with fixed win chance and total payout multiplier. Each route is a separate mode with cost / cost multiplier = 1.

| Mode ID          | UI Name         | Cost | Win Chance | Total Payout Multiplier | RTP   |
| ---------------- | --------------- | ---- | ---------- | ----------------------- | ----- |
| safe_shore       | Safe Shore      | 1    | 80.00%     | 1.20x                   | 96.00% |
| hidden_bay       | Hidden Bay      | 1    | 60.00%     | 1.60x                   | 96.00% |
| coral_reef       | Coral Reef      | 1    | 40.00%     | 2.40x                   | 96.00% |
| storm_route      | Storm Route     | 1    | 25.00%     | 3.84x                   | 96.00% |
| skull_island     | Skull Island    | 1    | 10.00%     | 9.60x                   | 96.00% |
| kraken_waters    | Kraken Waters   | 1    | 5.00%      | 19.20x                  | 96.00% |
| lost_treasure    | Lost Treasure   | 1    | 1.00%      | 96.00x                  | 96.00% |

### 2.2 Bonus Buy — Treasure Hunt

Bonus Buy is published as a separate mode:

- Mode ID: `treasure_hunt_buy`
- Cost / cost multiplier: 100
- Target RTP: 96.00%
- Separate static outcome set
- Final bonus paytable, hit rate, volatility, and max win multiplier to be defined by mathematician.

Recommended presentation model: several sequential chest openings or journey steps. Final payout may consist of the sum of multiple events, but the math package must unambiguously determine the entire round outcome before presentation starts.

Organic bonus trigger from regular routes is **not** included in the release. If added later, the RTP budget of regular modes must be recalculated and the math package reissued.

### 2.3 Custom Route Slider

**Custom Route slider is excluded from the production release.**

Stake Engine flow uses pre‑published static modes. A runtime slider with many possible chances would require a disproportionately large number of configs and outcome sets, or non‑standard integration. For the release, we keep the seven fixed routes.

---

## 3. General Parameters

Target RTP for each mode: `r = 0.96`

House edge for each mode: `1 − r = 0.04 = 4.00%`

Number of regular modes: 7

Number of Bonus Buy modes: 1

Bonus Buy cost: `C = 100 × B`

Bet levels, currency, min bet, and max bet should not be hardcoded into the math model as single dollar values. They are set by platform configuration. For verification, small denominations $0.01, $0.02, and $0.05 must be considered, as Stake Engine recommends supporting them in new releases.

Do not fix an absolute payout cap of $100,000 as part of the math model without platform configuration confirmation. Instead, the mathematician must define the max win multiplier for each mode. If the platform provides an absolute payout cap, calculate permissible bet levels for each mode separately.

---

## 4. Definitions

- **Base bet (B)** – base stake of a regular route or base unit for calculating Bonus Buy cost.
- **Win chance (p)** – probability of winning a regular route, decimal from 0 to 1.
- **Target RTP (r)** – expected return to player fraction; `r = 0.96`.
- **House edge** – `1 − r = 0.04 = 4.00%`.
- **Multiplier (M)** – total payout multiplier, including return of the stake.
- **Payout** – amount credited to the player as a result of the outcome.
- **Net profit** – payout minus the cost of the corresponding stake.
- **Bonus Buy cost (C)** – cost to launch bonus mode; `C = 100 × B`.
- **Bonus payout (P_bonus)** – sum of all payouts within one purchased bonus.
- **Max win multiplier** – highest total payout of a given mode in multiples of base bet.
- **Outcome weight** – weight of an outcome in the static math package.
- **Presentation event** – data for frontend animation that does not change settlement.

---

## 5. Mathematics of Regular Routes

For a route with win probability `p`:

`M = r / p`

Win payout = `B × M`

Lose payout = `0`

Net profit on win = `B × M − B`

Expected payout = `p × B × M = B × r`

Expected platform revenue = `B × (1 − r) = B × 0.04`

The basic formula is correct. All seven regular multipliers have exact values with two decimal places, so they do not create additional RTP drift due to multiplier rounding.

---

## 6. Preliminary Paytable for Regular Routes (B = $1)

| Mode ID          | Win Chance | Multiplier | Payout ($) | Net Profit ($) |
| ---------------- | ---------- | ---------- | ---------- | -------------- |
| safe_shore       | 80.00%     | 1.20x      | 1.20       | 0.20           |
| hidden_bay       | 60.00%     | 1.60x      | 1.60       | 0.60           |
| coral_reef       | 40.00%     | 2.40x      | 2.40       | 1.40           |
| storm_route      | 25.00%     | 3.84x      | 3.84       | 2.84           |
| skull_island     | 10.00%     | 9.60x      | 9.60       | 8.60           |
| kraken_waters    | 5.00%      | 19.20x     | 19.20      | 18.20          |
| lost_treasure    | 1.00%      | 96.00x     | 96.00      | 95.00          |

---

## 7. Preliminary Volatility for Regular Routes

For a regular route, payout multiplier `X` takes value `M` with probability `p` and `0` with probability `1-p`.

`E[X] = r = 0.96`

`Var(X) = p × M² − r² = r² × (1/p − 1)`

| Mode ID          | Hit Rate | Multiplier | Variance (payout multiplier) | Standard deviation |
| ---------------- | -------- | ---------- | ---------------------------- | ------------------ |
| safe_shore       | 80.00%   | 1.20x      | 0.2304                       | 0.4800             |
| hidden_bay       | 60.00%   | 1.60x      | 0.6144                       | 0.7838             |
| coral_reef       | 40.00%   | 2.40x      | 1.3824                       | 1.1758             |
| storm_route      | 25.00%   | 3.84x      | 2.7648                       | 1.6628             |
| skull_island     | 10.00%   | 9.60x      | 8.2944                       | 2.8800             |
| kraken_waters    | 5.00%    | 19.20x     | 17.5104                      | 4.1845             |
| lost_treasure    | 1.00%    | 96.00x     | 91.2384                      | 9.5519             |

The mathematician must confirm these calculations in the final report and provide an accepted description of the volatility profile for each mode.

---

## 8. Stake Engine Outcome Model

Production settlement is **not** implemented via a custom frontend or backend RNG threshold. The frontend does not generate the RNG result nor decide whether the player wins or loses.

For each mode, the mathematician prepares a static set of all possible outcomes and their weights using the Stake Engine Math SDK. Carrot RGS uses the published math package and returns an authoritative round event to the frontend.

For a regular route, minimally required:

- win outcome with correct payout multiplier
- lose outcome
- if needed, several lose presentation variants whose total weight equals the lose probability
- if needed, a near miss presentation variant within losing outcomes.

Presentation variants must not change the total win probability, payout, or RTP.

---

## 9. Bonus Buy Mode — Treasure Hunt

### 9.1 Basic Model

Bonus Buy is a separate stake and a separate mode. It does not overlay a regular route nor modify the payout of an already completed regular round.

`C = 100 × B`

`RTP_bonus = E[P_bonus] / C = 0.96`

`E[P_bonus] = 0.96 × C = 96 × B`

Expected platform revenue per purchased bonus = `0.04 × C = 4 × B`

Example for `B = $1.00`:
- Bonus Buy cost = $100.00
- Expected bonus payout = $96.00
- Expected platform revenue = $4.00

### 9.2 Requirements for Bonus Paytable

The mathematician must propose 1–2 variants of the Treasure Hunt paytable and recommend one of them.

For each variant, specify:

- list of outcomes
- weight of each outcome
- total payout multiplier of each outcome relative to B
- RTP
- hit frequency
- probability of zero payout
- probability of payout below Bonus Buy cost
- probability of profit
- median payout
- P95 and P99 payout
- variance / volatility profile
- max win multiplier
- number of presentation events in each outcome

Avoid interactive decisions that change mathematical value. If the player visually chooses a chest, all available choices must have identical mathematical value, or the result must be determined by the published outcome before interaction.

### 9.3 Combined RTP

If each regular route and Bonus Buy mode has RTP 96.00%, the combined RTP of the game is also 96.00% regardless of the distribution of stakes between modes.

Let:

`W_regular` = total amount staked on regular routes  
`W_bonus` = total amount spent on Bonus Buy

Expected total payout = `0.96 × W_regular + 0.96 × W_bonus`

Combined RTP = `Expected total payout / (W_regular + W_bonus) = 0.96`

Expected platform revenue = `0.04 × (W_regular + W_bonus)`

---

## 10. Max Win Multiplier and Platform Exposure

For each mode, the mathematician must define the max win multiplier and include it in the Stake Engine index metadata.

For regular routes, the preliminary max win multiplier equals the route’s regular multiplier. The highest value among regular routes: 96.00x for `lost_treasure`.

For `treasure_hunt_buy`, the max win multiplier is determined by the bonus paytable.

If the operator / ACP configuration sets an absolute payout cap, prepare a separate exposure table:

`max allowed base bet = absolute payout cap / max win multiplier of the mode`

Winnings must not be truncated after settlement. Available bet levels must be limited before the round starts according to platform configuration.

---

## 11. Precision, Payout Rounding, and Currencies

The mathematician must determine:

1. Internal precision for probabilities, weights, multipliers, and payouts.
2. Currency rounding rules for fiat and crypto‑like currencies.
3. Minimum payout unit.
4. Actual RTP after currency rounding for small bet levels $0.01, $0.02, and $0.05.
5. Impact of rounding on Bonus Buy outcomes.
6. Rules for displaying multipliers in the UI.
7. Alignment of UI multipliers with actual settlement.

---

## 12. Presentation Events and Near Miss

The dice in the game is a thematic animation, not a physical d6 and not a source of randomness.

The seven locations are **not** mapped to the six faces of a die. The player chooses a location before the round starts, and the chosen location determines the Stake Engine mode. After the play request, RGS selects a static outcome within that mode. The die does **not** choose the location and does **not** settle the outcome.

Near miss is allowed only as a presentation variant of a losing outcome. It must not change weights, win chance, payout, or RTP. In replay, the same presentation event must be shown.

The mathematician must provide the frontend team with a list of presentation events and their mapping to outcomes, including at least:

- `route_win`
- `route_lose_storm`
- `route_lose_reef`
- `route_lose_skull`
- `route_lose_kraken`
- `route_near_miss`
- `bonus_step`
- `bonus_complete`

Final event names can be changed together with the programmer, but the mapping must be unambiguous and deterministic for replay.

---

## 13. Stake Engine Math Publication Package

The mathematician must prepare a package using the Stake Engine Math SDK for all eight modes.

Current assembled delivery package for this specification:

- `math-sdk/games/treasure_dice/final_delivery_package/`
- package manifest: `math-sdk/games/treasure_dice/final_delivery_package/README.md`

Expected artifacts:

- configs for seven regular routes with cost = 1
	- `math-sdk/games/treasure_dice/final_delivery_package/artifacts/configs/config_fe_treasure_dice.json`
- config for `treasure_hunt_buy` with cost = 100
	- `math-sdk/games/treasure_dice/final_delivery_package/artifacts/configs/config_fe_treasure_dice.json`
- `index.json`
	- `math-sdk/games/treasure_dice/final_delivery_package/artifacts/publish_files/index.json`
- `lookUpTable.csv`
	- `math-sdk/games/treasure_dice/final_delivery_package/artifacts/publish_files/lookUpTable_safe_shore_0.csv`
	- `math-sdk/games/treasure_dice/final_delivery_package/artifacts/publish_files/lookUpTable_hidden_bay_0.csv`
	- `math-sdk/games/treasure_dice/final_delivery_package/artifacts/publish_files/lookUpTable_coral_reef_0.csv`
	- `math-sdk/games/treasure_dice/final_delivery_package/artifacts/publish_files/lookUpTable_storm_route_0.csv`
	- `math-sdk/games/treasure_dice/final_delivery_package/artifacts/publish_files/lookUpTable_skull_island_0.csv`
	- `math-sdk/games/treasure_dice/final_delivery_package/artifacts/publish_files/lookUpTable_kraken_waters_0.csv`
	- `math-sdk/games/treasure_dice/final_delivery_package/artifacts/publish_files/lookUpTable_lost_treasure_0.csv`
	- `math-sdk/games/treasure_dice/final_delivery_package/artifacts/publish_files/lookUpTable_treasure_hunt_buy_0.csv`
- compressed gameplay outcome files in the format generated by the SDK
	- `math-sdk/games/treasure_dice/final_delivery_package/artifacts/publish_files/books_safe_shore.jsonl.zst`
	- `math-sdk/games/treasure_dice/final_delivery_package/artifacts/publish_files/books_hidden_bay.jsonl.zst`
	- `math-sdk/games/treasure_dice/final_delivery_package/artifacts/publish_files/books_coral_reef.jsonl.zst`
	- `math-sdk/games/treasure_dice/final_delivery_package/artifacts/publish_files/books_storm_route.jsonl.zst`
	- `math-sdk/games/treasure_dice/final_delivery_package/artifacts/publish_files/books_skull_island.jsonl.zst`
	- `math-sdk/games/treasure_dice/final_delivery_package/artifacts/publish_files/books_kraken_waters.jsonl.zst`
	- `math-sdk/games/treasure_dice/final_delivery_package/artifacts/publish_files/books_lost_treasure.jsonl.zst`
	- `math-sdk/games/treasure_dice/final_delivery_package/artifacts/publish_files/books_treasure_hunt_buy.jsonl.zst`
- mapping / library files expected by RGS
	- `math-sdk/games/treasure_dice/final_delivery_package/artifacts/mapping/treasure_dice_phase3_mapping_spec.json`
	- `math-sdk/games/treasure_dice/final_delivery_package/artifacts/configs/event_config_safe_shore.json`
	- `math-sdk/games/treasure_dice/final_delivery_package/artifacts/configs/event_config_hidden_bay.json`
	- `math-sdk/games/treasure_dice/final_delivery_package/artifacts/configs/event_config_coral_reef.json`
	- `math-sdk/games/treasure_dice/final_delivery_package/artifacts/configs/event_config_storm_route.json`
	- `math-sdk/games/treasure_dice/final_delivery_package/artifacts/configs/event_config_skull_island.json`
	- `math-sdk/games/treasure_dice/final_delivery_package/artifacts/configs/event_config_kraken_waters.json`
	- `math-sdk/games/treasure_dice/final_delivery_package/artifacts/configs/event_config_lost_treasure.json`
	- `math-sdk/games/treasure_dice/final_delivery_package/artifacts/configs/event_config_treasure_hunt_buy.json`
- max win metadata
	- `math-sdk/games/treasure_dice/final_delivery_package/artifacts/configs/config_fe_treasure_dice.json`
- confirmed RTP for each mode
	- `math-sdk/games/treasure_dice/final_delivery_package/docs/treasure_dice_phase5_validation_summary.json`
	- `math-sdk/games/treasure_dice/final_delivery_package/docs/Treasure_Dice_Phase_5_Final_Validation_Summary.md`
- simulation report
	- `math-sdk/games/treasure_dice/final_delivery_package/docs/Treasure_Dice_Phase_5_Simulation_Report.md`

Final file names and package structure must conform to the current version of the Stake Engine Math SDK at generation time.

---

## 14. Validation and Tests for the Math

For each mode, the following are required:

- theoretical RTP check
- simulated RTP check
- weight check
- max win multiplier check
- check for invalid or unreachable outcomes
- index metadata check
- lookup table check
- payout rounding check on small bet levels
- replay‑friendly deterministic presentation mapping

For Bonus Buy, additionally:

- cost = 100 check
- RTP 96.00% check
- check of all multi‑event outcomes
- probability distribution report
- max exposure report

**Separate backend threshold test vectors are not required** because no custom backend game service is being developed. Instead, test vectors for static outcomes, weights, lookup, and frontend presentation mapping are needed.

---

## 15. Questions to be Closed by the Mathematician

1. Confirm theoretical RTP 96.00% and house edge 4.00% for each regular mode.
2. Confirm weights and static outcome mapping for each regular mode.
3. Prepare final Bonus Buy paytable with RTP 96.00%.
4. Determine Bonus Buy hit rate, volatility profile, and max win multiplier.
5. Confirm precision and payout rounding rules.
6. Calculate actual RTP after currency rounding for small bet levels.
7. Prepare exposure table after receiving platform payout cap (if provided).
8. Prepare simulation report for all eight modes.
9. Prepare Stake Engine Math SDK publication package.
10. Prepare presentation event mapping for frontend and replay.
11. Confirm that dice animation, near miss, and visual bonus choices do not affect settlement.

---

## 16. Expected Deliverables from the Mathematician

1. Final math report with model version.
	- `math-sdk/games/treasure_dice/final_delivery_package/docs/Treasure_Dice_Final_Math_Report.md`
2. Stake Engine Math SDK package for eight modes.
	- `math-sdk/games/treasure_dice/final_delivery_package/artifacts/`
3. Approved regular routes paytable.
	- `math-sdk/games/treasure_dice/final_delivery_package/docs/Treasure_Dice_Approved_Regular_Routes_Paytable.md`
4. Approved Bonus Buy paytable and description of Treasure Hunt.
	- `math-sdk/games/treasure_dice/final_delivery_package/docs/Treasure_Dice_Approved_Bonus_Buy_Paytable.md`
5. `index.json`, `lookUpTable.csv`, and compressed gameplay outcome files.
	- `math-sdk/games/treasure_dice/final_delivery_package/artifacts/publish_files/`
6. Max win multiplier for each mode.
	- `math-sdk/games/treasure_dice/final_delivery_package/artifacts/configs/config_fe_treasure_dice.json`
7. Simulation report.
	- `math-sdk/games/treasure_dice/final_delivery_package/docs/Treasure_Dice_Phase_5_Simulation_Report.md`
8. Volatility / variance report.
	- `math-sdk/games/treasure_dice/final_delivery_package/docs/Treasure_Dice_Phase_5_Volatility_Report.md`
9. Precision and rounding rules.
	- `math-sdk/games/treasure_dice/final_delivery_package/docs/Treasure_Dice_Phase_6_Precision_Rounding_And_Frontend_Contract.md`
10. Exposure table after receiving platform cap (if required).
	- `math-sdk/games/treasure_dice/final_delivery_package/docs/Treasure_Dice_Exposure_Table_Pending_Operator_Cap.md`
11. Presentation event mapping for frontend and replay.
	- `math-sdk/games/treasure_dice/final_delivery_package/docs/Treasure_Dice_Phase_3_Event_Mapping_Report.md`
	- `math-sdk/games/treasure_dice/final_delivery_package/artifacts/mapping/treasure_dice_phase3_mapping_spec.json`
12. Brief risk assessment.
	- `math-sdk/games/treasure_dice/final_delivery_package/docs/Treasure_Dice_Phase_6_Risk_Assessment.md`

---

## 17. Acceptance Criteria for the Math Specification

1. All seven regular routes published as separate static modes with cost = 1.
2. Bonus Buy published as a separate `treasure_hunt_buy` mode with cost = 100.
3. Theoretical RTP of each available mode equals 96.00% before currency rounding.
4. Combined RTP remains 96.00% regardless of the proportion of Bonus Buy stakes.
5. Impact of currency rounding described and verified on small bet levels.
6. Max win multiplier fixed for each mode.
7. If a platform cap is set, no available bet level exceeds the allowed exposure.
8. Winnings are **not** truncated after settlement.
9. Visual elements do not affect outcomes, weights, or RTP.
10. All modes are covered by simulations with stated number of rounds and acceptable deviation between theoretical and simulated RTP.
11. Static files generated by the current Stake Engine Math SDK and ready for RGS publication.

---

## 18. Preliminary Assessment of Concept Adequacy

**Regular Routes** are mathematically consistent: the formula is transparent, the seven routes provide a clear risk gradation, and the multipliers are computed without rounding error.

**Bonus Buy** is reasonably designed as a separate mode with cost 100× base bet, its own paytable, and RTP 96.00%. This does not change the combined house edge as long as bonus outcomes are generated and validated separately.

**Custom Route slider** is not recommended for a production release on Stake Engine. Eight fixed modes create a clean, verifiable model for RGS, social testing, replay, and approval.

```