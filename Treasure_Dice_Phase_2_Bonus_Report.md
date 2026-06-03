# Treasure Dice Phase 2 Bonus Report

## Document Status

- Phase: 2 - Bonus Buy Design
- Review purpose: Formal bonus-mode math review
- Date: 2026-06-03
- Analyst: GitHub Copilot (GPT-5.4), preliminary implementation for mathematician review
- Source brief: [Game_Description.md](f:/Gaming/Stakes/Game_Description.md)
- Working worksheet: [Treasure_Dice_Mathematician_Handoff.md](f:/Gaming/Stakes/Treasure_Dice_Mathematician_Handoff.md)

## Scope

This report covers only the Bonus Buy mode `treasure_hunt_buy`.

Included:

- candidate outcome distributions
- RTP confirmation
- hit rate, zero rate, below-cost rate, and profit rate
- median, P95, and P99 payout
- variance and volatility comparison
- preliminary max win comparison
- deterministic event feasibility review
- Gate 2 recommendation

Not included:

- regular route re-validation
- final frontend event naming
- Stake Engine Math SDK package generation
- simulation validation

## Summary Verdict

Two provisional Bonus Buy candidates were built and both satisfy the required 96.00% RTP target exactly.

Candidate A is the recommended release candidate. It delivers a materially lower volatility profile, a higher hit rate, a tighter payout tail, and a lower max-win multiplier than Candidate B. Candidate B is mathematically valid but significantly more volatile and exposes the operator to a larger top-end payout profile.

Gate 2 should be treated as `Conditional`, not fully passed, because the operator payout cap and the desired Bonus Buy volatility appetite have not yet been confirmed.

## Governing Model

The Bonus Buy cost is fixed at:

$$
C = 100 \times B
$$

The target expected payout is:

$$
E[P_{bonus}] = 0.96 \times C = 96 \times B
$$

For each candidate distribution:

$$
\mathrm{RTP} = \sum_i p_i x_i
$$

where $p_i$ is the outcome probability and $x_i$ is the total payout multiplier in multiples of base bet $B$.

## Candidate Summary

| Candidate | Outcome Count | RTP | Hit Rate | Zero Rate | Below-Cost Rate | Profit Rate | Median | P95 | P99 | Variance | Max Win | Recommended |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | 6 | 96.00 | 82.00% | 18.00% | 44.00% | 38.00% | 90x B | 275x B | 275x B | 5646.0000 | 275x B | Yes |
| B | 6 | 96.00 | 54.00% | 46.00% | 18.00% | 26.00% | 60x B | 320x B | 496x B | 17836.8000 | 496x B | No |

## Candidate A Distribution

| Outcome ID | Weight | Probability | Total Payout Multiplier vs B | Total Payout vs Cost | Event Count | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| A1 | 18 | 0.18 | 0x B | 0.00x cost | 3 | Full miss, short reveal path |
| A2 | 22 | 0.22 | 50x B | 0.50x cost | 3 | Low chest recovery outcome |
| A3 | 22 | 0.22 | 90x B | 0.90x cost | 4 | Near break-even path |
| A4 | 18 | 0.18 | 120x B | 1.20x cost | 4 | First profitable tier |
| A5 | 12 | 0.12 | 180x B | 1.80x cost | 5 | Mid-tier profitable path |
| A6 | 8 | 0.08 | 275x B | 2.75x cost | 6 | Top tier for Candidate A |

### Candidate A Notes

- Exact expected payout: 96x B
- Median payout: 90x B
- P95 payout: 275x B
- P99 payout: 275x B
- Variance: 5646.0000
- Standard deviation: 75.1399
- Qualitative profile: moderate volatility, frequent non-zero results, softer tail

## Candidate B Distribution

| Outcome ID | Weight | Probability | Total Payout Multiplier vs B | Total Payout vs Cost | Event Count | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| B1 | 46 | 0.46 | 0x B | 0.00x cost | 3 | Full miss, highest zero rate |
| B2 | 18 | 0.18 | 60x B | 0.60x cost | 3 | Low-value recovery |
| B3 | 10 | 0.10 | 100x B | 1.00x cost | 4 | Break-even outcome |
| B4 | 12 | 0.12 | 180x B | 1.80x cost | 5 | Mid-tier profitable path |
| B5 | 9 | 0.09 | 320x B | 3.20x cost | 6 | High-tier profitable path |
| B6 | 5 | 0.05 | 496x B | 4.96x cost | 7 | Top tier for Candidate B |

### Candidate B Notes

- Exact expected payout: 96x B
- Median payout: 60x B
- P95 payout: 320x B
- P99 payout: 496x B
- Variance: 17836.8000
- Standard deviation: 133.5545
- Qualitative profile: high volatility, heavy zero concentration, much wider tail

## Comparative Interpretation

Both candidates are mathematically valid. The choice is not about RTP compliance, but about volatility, player experience, and operator exposure.

Candidate A advantages:

- much lower variance
- higher hit frequency
- lower zero-payout rate
- lower top-end exposure
- smoother event-count ladder that is easy to present as a progressive treasure-hunt reveal

Candidate B advantages:

- larger tail rewards
- stronger top-end aspiration
- more extreme contrast between miss states and premium outcomes

Candidate B disadvantages:

- 46.00% zero-payout rate
- much lower hit rate
- materially higher variance
- significantly larger max win multiplier
- higher exposure pressure if an operator payout cap is later imposed

## Deterministic Event Feasibility

Both candidates are compatible with deterministic pre-resolved presentation.

Candidate A feasibility:

- event count increases with payout tier from 3 to 6 events
- well suited to several chest reveals followed by a completion event
- no outcome requires runtime choice to determine value

Candidate B feasibility:

- also deterministic if the full outcome is selected before presentation starts
- longer top-end path may require more pronounced audiovisual escalation
- still mathematically valid for replay-safe mapping

## Exposure Review

The operator payout cap is not yet available.

Current formulas:

- Candidate A max allowed base bet = payout cap / 275
- Candidate B max allowed base bet = payout cap / 496

Interpretation:

- Candidate A is materially safer under unknown operator constraints.
- Candidate B becomes much more restrictive once a payout cap is introduced.

## Recommendation

Recommended candidate: `A`

Reasoning:

Candidate A is the stronger release candidate because it preserves the required RTP while reducing volatility, tail risk, and operator exposure. It still provides profitable outcomes and a credible treasure-hunt progression, but avoids the heavy miss profile and high-end concentration seen in Candidate B.

## Gate 2 Decision

- Gate 2 status: `Conditional`
- RTP compliance: `Pass`
- Candidate feasibility: `Pass`
- Recommendation readiness: `Pass`
- Exposure closure: `Pending operator payout cap`
- Product preference closure: `Pending volatility direction`

## Formal Review Notes

Open items for mathematician review:

1. Confirm whether the release should prioritize Candidate A’s smoother profile or deliberately target a more volatile bonus.
2. Confirm whether break-even outcomes such as 100x B should be retained, reduced, or removed in the final bonus design.
3. Confirm the operator payout cap so the exposure table can be closed.
4. Confirm whether the final event-count ladder should remain proportional to payout tier.

## Recommended Next Step

Proceed to Phase 3 event mapping using Candidate A as the working assumption, but do not mark Phase 2 as unconditionally approved until payout-cap and volatility-direction inputs are closed.
