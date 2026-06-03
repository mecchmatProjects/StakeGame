# Treasure Dice Phase 6 Risk Assessment

## Document Status

- Phase: 6 - Publication Readiness
- Date: 2026-06-03
- Analyst: GitHub Copilot (GPT-5.3-Codex)

## Risk Scale

- Severity: High, Medium, Low
- Likelihood: High, Medium, Low

## Active Risks

### R1 - Low-denomination regular-route rounding drift

- Description: Under cent rounding at bet levels 0.01 and 0.02, multiple regular routes materially deviate from 96.00% target RTP.
- Source evidence: [Treasure_Dice_Phase_1_Math_Report.md](Treasure_Dice_Phase_1_Math_Report.md), [Treasure_Dice_Phase_5_Replay_Audit_Report.md](Treasure_Dice_Phase_5_Replay_Audit_Report.md)
- Severity: High
- Likelihood: High
- Impact: Compliance and expected-return mismatch for low fiat stakes.
- Mitigation options:
  1. Support sub-cent settlement precision for affected routes.
  2. Restrict affected low denominations by mode.
  3. Apply explicitly approved alternate rounding policy and revalidate.
- Owner: Math and platform policy owners.
- Status: Open

### R2 - Short-run simulation drift for high-volatility modes

- Description: Current package-validation simulation lengths are suitable for integrity checks but can show notable RTP drift in volatile modes.
- Source evidence: [Treasure_Dice_Phase_5_Simulation_Report.md](Treasure_Dice_Phase_5_Simulation_Report.md)
- Severity: Medium
- Likelihood: Medium
- Impact: Potential misinterpretation of production RTP if short-run metrics are used as final statistical sign-off.
- Mitigation options:
  1. Run larger simulation volume for final statistical confidence.
  2. Use sigma-based interpretation in release notes.
- Owner: Math validation owner.
- Status: Open for final sign-off campaign, acceptable for package integrity gate.

### R3 - Operator payout-cap dependency for exposure closure

- Description: Absolute payout-cap value is not confirmed; exposure table uses formulas only.
- Source evidence: [Treasure_Dice_Phase_2_Bonus_Report.md](Treasure_Dice_Phase_2_Bonus_Report.md)
- Severity: Medium
- Likelihood: Medium
- Impact: Final max-allowed-bet envelope cannot be frozen at operator level.
- Mitigation options:
  1. Obtain operator cap input.
  2. Finalize cap-specific max bet constraints per mode.
- Owner: Product and operator integration owners.
- Status: Open

## Closed or Mitigated Risks

### C1 - Missing zstandard runtime dependency

- Description: Package generation was previously blocked by missing zstandard dependency.
- Mitigation applied: Installed zstandard in active Math SDK Python environment and reran package generation.
- Evidence: successful run output and generated publish/config artifacts.
- Status: Closed

### C2 - Determinism and lookup consistency risk

- Description: Risk that replay event sequences or lookup values diverge from settlement.
- Mitigation applied: Phase 5 replay, lookup, and weight audits across all eight modes.
- Evidence: [treasure_dice_phase5_validation_summary.json](treasure_dice_phase5_validation_summary.json)
- Status: Closed for current package.

## Overall Risk Posture

- Publication posture: Conditional
- Blocking risks: R1 (rounding policy for low fiat denominations)
- Non-blocking but open risks: R2, R3

## Recommended Decision Path

1. Close R1 with an explicit rounding policy decision.
2. Confirm payout-cap policy input for R3.
3. If needed by release governance, run expanded simulation campaign for R2.
