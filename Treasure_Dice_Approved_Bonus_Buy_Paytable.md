# Treasure Dice Approved Bonus Buy Paytable And Treasure Hunt Description

## Document Status

- Date: 2026-06-04
- Approved mode: `treasure_hunt_buy`
- Source approval basis: [Treasure_Dice_Phase_2_Bonus_Report.md](Treasure_Dice_Phase_2_Bonus_Report.md)

## Approved Bonus Model

- Approved candidate: `A`
- Cost: `100 x` base bet
- RTP: `96.00%`
- Max win: `275x` base bet
- Presentation model: deterministic multi-step treasure hunt using `bonus_step ... bonus_complete`

## Approved Paytable

| Outcome ID | Weight | Probability | Total Payout Multiplier vs B | Total Payout vs Cost | Event Count |
| --- | --- | --- | --- | --- | --- |
| A1 | 18 | 0.18 | 0x | 0.00x cost | 3 |
| A2 | 22 | 0.22 | 50x | 0.50x cost | 3 |
| A3 | 22 | 0.22 | 90x | 0.90x cost | 4 |
| A4 | 18 | 0.18 | 120x | 1.20x cost | 4 |
| A5 | 12 | 0.12 | 180x | 1.80x cost | 5 |
| A6 | 8 | 0.08 | 275x | 2.75x cost | 6 |

## Approved Summary Metrics

| Metric | Value |
| --- | --- |
| RTP | 96.00% |
| Hit Rate | 82.00% |
| Zero Rate | 18.00% |
| Below-Cost Rate | 44.00% |
| Profit Rate | 38.00% |
| Median | 90x B |
| P95 | 275x B |
| P99 | 275x B |
| Variance | 5646.0000 |
| Standard deviation | 75.1399 |

## Treasure Hunt Description

The approved Treasure Hunt bonus is a pre-resolved static-outcome feature. The full payout value is fixed before presentation begins. Presentation then reveals the path through a deterministic sequence of `bonus_step` events followed by `bonus_complete`. No visual chest choice changes the mathematical value after outcome selection.