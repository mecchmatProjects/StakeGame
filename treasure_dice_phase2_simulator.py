"""Simulate Treasure Dice Phase 2 Bonus Buy candidate rounds.

This script models only the Treasure Hunt Bonus Buy candidates defined in the
Phase 2 bonus report. It excludes regular routes and all later-phase SDK work.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
from dataclasses import asdict, dataclass
from math import fsum
from pathlib import Path
import random
from typing import Dict, List, Sequence


DEFAULT_BASE_BET = 1.0
DEFAULT_COST_MULTIPLIER = 100.0
DEFAULT_LOG_FILE = "treasure_dice_phase2_simulator.log"
DEFAULT_REPORT_FILE = "treasure_dice_phase2_report.json"


@dataclass(frozen=True)
class BonusOutcome:
    """Represents a single weighted bonus outcome.

    Attributes:
        outcome_id: Outcome identifier.
        weight: Integer-style publication weight.
        probability: Normalized probability of the outcome.
        payout_multiplier: Total payout in multiples of base bet.
        event_count: Number of presentation events in the outcome path.
        notes: Short descriptive note.
    """

    outcome_id: str
    weight: int
    probability: float
    payout_multiplier: float
    event_count: int
    notes: str

    def payout_vs_cost(self, cost_multiplier: float) -> float:
        """Returns payout as a multiple of bonus cost.

        Args:
            cost_multiplier: Bonus cost in multiples of base bet.

        Returns:
            Payout divided by bonus cost.
        """
        return self.payout_multiplier / cost_multiplier


@dataclass(frozen=True)
class CandidateDefinition:
    """Represents one Bonus Buy candidate.

    Attributes:
        candidate_id: Candidate identifier.
        outcomes: Weighted outcome list.
        recommended: Whether the candidate is the current preferred option.
        summary_note: Qualitative summary.
    """

    candidate_id: str
    outcomes: Sequence[BonusOutcome]
    recommended: bool
    summary_note: str

    @property
    def theoretical_rtp(self) -> float:
        """Returns theoretical RTP in multiples of bonus cost."""
        expected_payout = fsum(
            outcome.probability * outcome.payout_multiplier for outcome in self.outcomes
        )
        return expected_payout / DEFAULT_COST_MULTIPLIER

    @property
    def expected_payout_multiplier(self) -> float:
        """Returns expected payout in multiples of base bet."""
        return fsum(outcome.probability * outcome.payout_multiplier for outcome in self.outcomes)

    @property
    def hit_rate(self) -> float:
        """Returns the probability of any non-zero payout."""
        return fsum(outcome.probability for outcome in self.outcomes if outcome.payout_multiplier > 0)

    @property
    def zero_rate(self) -> float:
        """Returns the probability of zero payout."""
        return fsum(outcome.probability for outcome in self.outcomes if outcome.payout_multiplier == 0)

    @property
    def below_cost_rate(self) -> float:
        """Returns the probability of a non-zero payout below bonus cost."""
        return fsum(
            outcome.probability
            for outcome in self.outcomes
            if 0 < outcome.payout_multiplier < DEFAULT_COST_MULTIPLIER
        )

    @property
    def profit_rate(self) -> float:
        """Returns the probability of profit above bonus cost."""
        return fsum(
            outcome.probability
            for outcome in self.outcomes
            if outcome.payout_multiplier > DEFAULT_COST_MULTIPLIER
        )

    @property
    def break_even_rate(self) -> float:
        """Returns the probability of exact break-even."""
        return fsum(
            outcome.probability
            for outcome in self.outcomes
            if outcome.payout_multiplier == DEFAULT_COST_MULTIPLIER
        )

    @property
    def variance(self) -> float:
        """Returns payout-multiplier variance in multiples of base bet."""
        second_moment = fsum(
            outcome.probability * (outcome.payout_multiplier ** 2) for outcome in self.outcomes
        )
        mean = self.expected_payout_multiplier
        return second_moment - (mean ** 2)

    @property
    def standard_deviation(self) -> float:
        """Returns payout-multiplier standard deviation in multiples of base bet."""
        return self.variance ** 0.5

    @property
    def median(self) -> float:
        """Returns the 50th percentile payout multiplier."""
        return self.quantile(0.50)

    @property
    def p95(self) -> float:
        """Returns the 95th percentile payout multiplier."""
        return self.quantile(0.95)

    @property
    def p99(self) -> float:
        """Returns the 99th percentile payout multiplier."""
        return self.quantile(0.99)

    @property
    def max_win_multiplier(self) -> float:
        """Returns the highest payout multiplier in the candidate."""
        return max(outcome.payout_multiplier for outcome in self.outcomes)

    def quantile(self, quantile_value: float) -> float:
        """Returns a payout quantile from the ordered discrete distribution.

        Args:
            quantile_value: Quantile in [0, 1].

        Returns:
            Payout multiplier at the requested quantile.
        """
        cumulative = 0.0
        for outcome in sorted(self.outcomes, key=lambda item: item.payout_multiplier):
            cumulative += outcome.probability
            if cumulative >= quantile_value - 1e-12:
                return outcome.payout_multiplier
        return sorted(self.outcomes, key=lambda item: item.payout_multiplier)[-1].payout_multiplier


@dataclass
class BonusRoundRecord:
    """Stores the outcome of a single simulated bonus round.

    Attributes:
        round_number: Sequential round number.
        candidate_id: Candidate identifier.
        base_bet: Base bet amount.
        cost_multiplier: Bonus cost in multiples of base bet.
        bonus_cost: Total cost of the bonus round.
        draw: Random weighted draw in [0, 1).
        outcome_id: Selected outcome identifier.
        outcome_probability: Probability of selected outcome.
        payout_multiplier: Total payout in multiples of base bet.
        payout: Settled payout amount.
        payout_vs_cost: Payout divided by bonus cost.
        net_profit: Payout minus bonus cost.
        event_count: Number of presentation events.
        event_sequence: Deterministic presentation sequence for the outcome.
        cumulative_wager: Total bonus cost spent up to and including this round.
        cumulative_payout: Total payout up to and including this round.
        cumulative_rtp: Running RTP after the round.
    """

    round_number: int
    candidate_id: str
    base_bet: float
    cost_multiplier: float
    bonus_cost: float
    draw: float
    outcome_id: str
    outcome_probability: float
    payout_multiplier: float
    payout: float
    payout_vs_cost: float
    net_profit: float
    event_count: int
    event_sequence: List[str]
    cumulative_wager: float
    cumulative_payout: float
    cumulative_rtp: float


CANDIDATES: Dict[str, CandidateDefinition] = {
    "A": CandidateDefinition(
        candidate_id="A",
        recommended=True,
        summary_note="Recommended candidate with lower volatility and tighter exposure.",
        outcomes=(
            BonusOutcome("A1", 18, 0.18, 0.0, 3, "Full miss, short reveal path."),
            BonusOutcome("A2", 22, 0.22, 50.0, 3, "Low chest recovery outcome."),
            BonusOutcome("A3", 22, 0.22, 90.0, 4, "Near break-even path."),
            BonusOutcome("A4", 18, 0.18, 120.0, 4, "First profitable tier."),
            BonusOutcome("A5", 12, 0.12, 180.0, 5, "Mid-tier profitable path."),
            BonusOutcome("A6", 8, 0.08, 275.0, 6, "Top tier for Candidate A."),
        ),
    ),
    "B": CandidateDefinition(
        candidate_id="B",
        recommended=False,
        summary_note="Higher-volatility alternative with a wider tail and larger max win.",
        outcomes=(
            BonusOutcome("B1", 46, 0.46, 0.0, 3, "Full miss, highest zero rate."),
            BonusOutcome("B2", 18, 0.18, 60.0, 3, "Low-value recovery."),
            BonusOutcome("B3", 10, 0.10, 100.0, 4, "Break-even outcome."),
            BonusOutcome("B4", 12, 0.12, 180.0, 5, "Mid-tier profitable path."),
            BonusOutcome("B5", 9, 0.09, 320.0, 6, "High-tier profitable path."),
            BonusOutcome("B6", 5, 0.05, 496.0, 7, "Top tier for Candidate B."),
        ),
    ),
}


def parse_args() -> argparse.Namespace:
    """Parses command-line arguments.

    Returns:
        Parsed CLI namespace.
    """
    parser = argparse.ArgumentParser(
        description="Simulate Treasure Dice Phase 2 Bonus Buy candidate rounds."
    )
    parser.add_argument("--rounds", type=int, default=10, help="Number of bonus rounds to simulate.")
    parser.add_argument(
        "--base-bet",
        type=float,
        default=DEFAULT_BASE_BET,
        help="Base bet amount used to price the bonus round.",
    )
    parser.add_argument(
        "--mode",
        choices=("single", "compare"),
        default="single",
        help="Run a single candidate simulation or compare both candidates in one report.",
    )
    parser.add_argument(
        "--candidate",
        choices=tuple(CANDIDATES.keys()),
        default="A",
        help="Bonus candidate to simulate when --mode=single.",
    )
    parser.add_argument("--seed", type=int, default=12345, help="Deterministic RNG seed.")
    parser.add_argument(
        "--report-file",
        type=Path,
        default=Path(DEFAULT_REPORT_FILE),
        help="Path to write JSON report output.",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        default=Path(DEFAULT_LOG_FILE),
        help="Path to write log output.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        help="Logger level.",
    )
    parser.add_argument(
        "--record-mode",
        choices=("full", "summary"),
        default="full",
        help="full stores round-by-round records in JSON; summary omits detailed round records.",
    )
    parser.add_argument(
        "--csv-prefix",
        type=Path,
        default=None,
        help="Optional CSV output prefix. Example: reports/phase2 creates phase2_summary.csv.",
    )
    return parser.parse_args()


def configure_logger(log_file: Path, log_level: str) -> logging.Logger:
    """Configures a logger for console and file output.

    Args:
        log_file: Path to the log file.
        log_level: Logging level name.

    Returns:
        Configured logger instance.
    """
    logger = logging.getLogger("treasure_dice_phase2")
    logger.setLevel(getattr(logging, log_level.upper()))
    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    logger.propagate = False
    return logger


def choose_outcome(candidate: CandidateDefinition, draw: float) -> BonusOutcome:
    """Chooses a weighted outcome from the candidate distribution.

    Args:
        candidate: Candidate definition.
        draw: Random draw in [0, 1).

    Returns:
        Selected bonus outcome.
    """
    cumulative = 0.0
    for outcome in candidate.outcomes:
        cumulative += outcome.probability
        if draw < cumulative:
            return outcome
    return candidate.outcomes[-1]


def build_event_sequence(event_count: int) -> List[str]:
    """Builds a deterministic presentation sequence for an outcome.

    Args:
        event_count: Total event count required for the outcome.

    Returns:
        Ordered event names for the outcome path.
    """
    if event_count <= 1:
        return ["bonus_complete"]
    return ["bonus_step"] * (event_count - 1) + ["bonus_complete"]


def simulate_rounds(args: argparse.Namespace, logger: logging.Logger) -> Dict[str, object]:
    """Simulates the requested number of Phase 2 bonus rounds.

    Args:
        args: Parsed CLI arguments.
        logger: Configured logger.

    Returns:
        JSON-serializable simulation report.
    """
    candidate = CANDIDATES[args.candidate]
    rng = random.Random(args.seed)
    record_mode = args.record_mode
    include_round_records = record_mode == "full"
    records: List[BonusRoundRecord] = []
    cumulative_wager = 0.0
    cumulative_payout = 0.0
    bonus_cost = round(args.base_bet * DEFAULT_COST_MULTIPLIER, 4)

    outcome_counts: Dict[str, int] = {outcome.outcome_id: 0 for outcome in candidate.outcomes}

    for round_index in range(args.rounds):
        draw = rng.random()
        outcome = choose_outcome(candidate, draw)
        payout = round(args.base_bet * outcome.payout_multiplier, 4)
        net_profit = round(payout - bonus_cost, 4)
        cumulative_wager = round(cumulative_wager + bonus_cost, 4)
        cumulative_payout = round(cumulative_payout + payout, 4)
        outcome_counts[outcome.outcome_id] += 1

        record = BonusRoundRecord(
            round_number=round_index + 1,
            candidate_id=candidate.candidate_id,
            base_bet=round(args.base_bet, 4),
            cost_multiplier=DEFAULT_COST_MULTIPLIER,
            bonus_cost=bonus_cost,
            draw=round(draw, 6),
            outcome_id=outcome.outcome_id,
            outcome_probability=outcome.probability,
            payout_multiplier=outcome.payout_multiplier,
            payout=payout,
            payout_vs_cost=round(outcome.payout_vs_cost(DEFAULT_COST_MULTIPLIER), 6),
            net_profit=net_profit,
            event_count=outcome.event_count,
            event_sequence=build_event_sequence(outcome.event_count),
            cumulative_wager=cumulative_wager,
            cumulative_payout=cumulative_payout,
            cumulative_rtp=round(cumulative_payout / cumulative_wager, 6),
        )
        if include_round_records:
            records.append(record)

        if logger.isEnabledFor(logging.INFO):
            logger.info(
                "Round %s | candidate=%s | draw=%.6f | outcome=%s | payout=%.4f | payout_vs_cost=%.4f | net=%.4f | cum_rtp=%.6f",
                record.round_number,
                record.candidate_id,
                record.draw,
                record.outcome_id,
                record.payout,
                record.payout_vs_cost,
                record.net_profit,
                record.cumulative_rtp,
            )

    outcome_summaries: List[Dict[str, object]] = []
    for outcome in candidate.outcomes:
        rounds_hit = outcome_counts[outcome.outcome_id]
        simulated_probability = (rounds_hit / args.rounds) if args.rounds else 0.0
        outcome_summaries.append(
            {
                "outcome_id": outcome.outcome_id,
                "weight": outcome.weight,
                "theoretical_probability": outcome.probability,
                "simulated_probability": round(simulated_probability, 6),
                "payout_multiplier": outcome.payout_multiplier,
                "payout_vs_cost": round(outcome.payout_vs_cost(DEFAULT_COST_MULTIPLIER), 6),
                "event_count": outcome.event_count,
                "notes": outcome.notes,
            }
        )

    report = {
        "phase": 2,
        "feature_scope": "bonus buy candidate simulation only",
        "mode": "single",
        "candidate_id": candidate.candidate_id,
        "recommended_candidate": candidate.recommended,
        "candidate_summary_note": candidate.summary_note,
        "rounds": args.rounds,
        "base_bet": args.base_bet,
        "bonus_cost_multiplier": DEFAULT_COST_MULTIPLIER,
        "bonus_cost": bonus_cost,
        "seed": args.seed,
        "record_mode": record_mode,
        "theoretical_rtp_target": 0.96,
        "theoretical_rtp": round(candidate.theoretical_rtp, 6),
        "expected_payout_multiplier": round(candidate.expected_payout_multiplier, 6),
        "theoretical_hit_rate": round(candidate.hit_rate, 6),
        "theoretical_zero_rate": round(candidate.zero_rate, 6),
        "theoretical_below_cost_rate": round(candidate.below_cost_rate, 6),
        "theoretical_profit_rate": round(candidate.profit_rate, 6),
        "theoretical_break_even_rate": round(candidate.break_even_rate, 6),
        "median_multiplier": candidate.median,
        "p95_multiplier": candidate.p95,
        "p99_multiplier": candidate.p99,
        "variance": round(candidate.variance, 6),
        "standard_deviation": round(candidate.standard_deviation, 6),
        "max_win_multiplier": candidate.max_win_multiplier,
        "total_wager": cumulative_wager,
        "total_payout": cumulative_payout,
        "total_net_profit": round(cumulative_payout - cumulative_wager, 4),
        "simulated_rtp": round(cumulative_payout / cumulative_wager, 6),
        "outcome_summaries": outcome_summaries,
    }
    if include_round_records:
        report["round_records"] = [asdict(record) for record in records]
    else:
        report["round_records_omitted"] = True
    return report


def build_compare_report(
    args: argparse.Namespace,
    logger: logging.Logger,
) -> Dict[str, object]:
    """Builds a side-by-side report for candidates A and B.

    Args:
        args: Parsed CLI arguments.
        logger: Configured logger.

    Returns:
        Combined compare report.
    """
    candidate_a_args = argparse.Namespace(**vars(args))
    candidate_a_args.candidate = "A"

    candidate_b_args = argparse.Namespace(**vars(args))
    candidate_b_args.candidate = "B"
    candidate_b_args.seed = args.seed + 1

    logger.info("Starting compare mode: candidate A (seed=%s)", candidate_a_args.seed)
    report_a = simulate_rounds(candidate_a_args, logger)

    logger.info("Starting compare mode: candidate B (seed=%s)", candidate_b_args.seed)
    report_b = simulate_rounds(candidate_b_args, logger)

    return {
        "phase": 2,
        "feature_scope": "bonus buy candidate comparison",
        "mode": "compare",
        "rounds_per_candidate": args.rounds,
        "base_bet": args.base_bet,
        "bonus_cost_multiplier": DEFAULT_COST_MULTIPLIER,
        "seed": args.seed,
        "seed_policy": {"A": args.seed, "B": args.seed + 1},
        "candidate_reports": {
            "A": report_a,
            "B": report_b,
        },
        "comparison_summary": {
            "recommended_candidate": "A",
            "simulated_rtp": {
                "A": report_a["simulated_rtp"],
                "B": report_b["simulated_rtp"],
            },
            "theoretical_rtp": {
                "A": report_a["theoretical_rtp"],
                "B": report_b["theoretical_rtp"],
            },
            "variance": {
                "A": report_a["variance"],
                "B": report_b["variance"],
            },
            "max_win_multiplier": {
                "A": report_a["max_win_multiplier"],
                "B": report_b["max_win_multiplier"],
            },
            "zero_rate": {
                "A": report_a["theoretical_zero_rate"],
                "B": report_b["theoretical_zero_rate"],
            },
            "profit_rate": {
                "A": report_a["theoretical_profit_rate"],
                "B": report_b["theoretical_profit_rate"],
            },
        },
    }


def write_report(report_file: Path, report: Dict[str, object]) -> None:
    """Writes the simulation report to disk as JSON.

    Args:
        report_file: Output report path.
        report: Simulation report object.
    """
    report_file.write_text(json.dumps(report, indent=2), encoding="utf-8")


def _ensure_parent(path: Path) -> None:
    """Creates a parent directory when needed."""
    if path.parent and str(path.parent) not in ("", "."):
        path.parent.mkdir(parents=True, exist_ok=True)


def _write_single_candidate_csvs(report: Dict[str, object], prefix: Path) -> List[Path]:
    """Writes CSV outputs for a single-candidate report.

    Args:
        report: Single-candidate report object.
        prefix: Output CSV prefix.

    Returns:
        List of written CSV file paths.
    """
    written: List[Path] = []

    summary_path = Path(f"{prefix}_summary.csv")
    _ensure_parent(summary_path)
    summary_fields = [
        "phase",
        "mode",
        "candidate_id",
        "recommended_candidate",
        "rounds",
        "base_bet",
        "bonus_cost_multiplier",
        "bonus_cost",
        "seed",
        "record_mode",
        "theoretical_rtp_target",
        "theoretical_rtp",
        "expected_payout_multiplier",
        "theoretical_hit_rate",
        "theoretical_zero_rate",
        "theoretical_below_cost_rate",
        "theoretical_profit_rate",
        "theoretical_break_even_rate",
        "median_multiplier",
        "p95_multiplier",
        "p99_multiplier",
        "variance",
        "standard_deviation",
        "max_win_multiplier",
        "total_wager",
        "total_payout",
        "total_net_profit",
        "simulated_rtp",
    ]
    with summary_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=summary_fields)
        writer.writeheader()
        writer.writerow({field: report.get(field, "") for field in summary_fields})
    written.append(summary_path)

    outcomes_path = Path(f"{prefix}_outcomes.csv")
    _ensure_parent(outcomes_path)
    outcome_rows = report.get("outcome_summaries", [])
    with outcomes_path.open("w", newline="", encoding="utf-8") as handle:
        if outcome_rows:
            fieldnames = list(outcome_rows[0].keys())
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(outcome_rows)
        else:
            handle.write("\n")
    written.append(outcomes_path)

    if "round_records" in report:
        rounds_path = Path(f"{prefix}_rounds.csv")
        _ensure_parent(rounds_path)
        round_rows = report["round_records"]
        with rounds_path.open("w", newline="", encoding="utf-8") as handle:
            if round_rows:
                fieldnames = list(round_rows[0].keys())
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(round_rows)
            else:
                handle.write("\n")
        written.append(rounds_path)

    return written


def _write_compare_csvs(report: Dict[str, object], prefix: Path) -> List[Path]:
    """Writes CSV outputs for compare-mode reports.

    Args:
        report: Compare-mode report object.
        prefix: Output CSV prefix.

    Returns:
        List of written CSV file paths.
    """
    written: List[Path] = []

    compare_path = Path(f"{prefix}_comparison.csv")
    _ensure_parent(compare_path)
    summary = report.get("comparison_summary", {})
    row = {
        "phase": report.get("phase"),
        "mode": report.get("mode"),
        "rounds_per_candidate": report.get("rounds_per_candidate"),
        "base_bet": report.get("base_bet"),
        "seed_A": report.get("seed_policy", {}).get("A"),
        "seed_B": report.get("seed_policy", {}).get("B"),
        "recommended_candidate": summary.get("recommended_candidate"),
        "simulated_rtp_A": summary.get("simulated_rtp", {}).get("A"),
        "simulated_rtp_B": summary.get("simulated_rtp", {}).get("B"),
        "theoretical_rtp_A": summary.get("theoretical_rtp", {}).get("A"),
        "theoretical_rtp_B": summary.get("theoretical_rtp", {}).get("B"),
        "variance_A": summary.get("variance", {}).get("A"),
        "variance_B": summary.get("variance", {}).get("B"),
        "max_win_multiplier_A": summary.get("max_win_multiplier", {}).get("A"),
        "max_win_multiplier_B": summary.get("max_win_multiplier", {}).get("B"),
        "zero_rate_A": summary.get("zero_rate", {}).get("A"),
        "zero_rate_B": summary.get("zero_rate", {}).get("B"),
        "profit_rate_A": summary.get("profit_rate", {}).get("A"),
        "profit_rate_B": summary.get("profit_rate", {}).get("B"),
    }
    with compare_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(row.keys()))
        writer.writeheader()
        writer.writerow(row)
    written.append(compare_path)

    candidate_reports = report.get("candidate_reports", {})
    for candidate_id, candidate_report in candidate_reports.items():
        child_prefix = Path(f"{prefix}_candidate_{candidate_id}")
        written.extend(_write_single_candidate_csvs(candidate_report, child_prefix))

    return written


def write_csv_exports(report: Dict[str, object], csv_prefix: Path) -> List[Path]:
    """Writes CSV exports for report data.

    Args:
        report: Simulation report object.
        csv_prefix: Prefix used to produce CSV output names.

    Returns:
        List of CSV files written.
    """
    if report.get("mode") == "compare":
        return _write_compare_csvs(report, csv_prefix)
    return _write_single_candidate_csvs(report, csv_prefix)


def main() -> int:
    """Runs the CLI entry point.

    Returns:
        Process exit code.
    """
    args = parse_args()
    if args.rounds <= 0:
        raise ValueError("--rounds must be a positive integer.")
    if args.base_bet <= 0:
        raise ValueError("--base-bet must be greater than zero.")

    logger = configure_logger(args.log_file, args.log_level)
    if args.mode == "compare":
        report = build_compare_report(args, logger)
    else:
        report = simulate_rounds(args, logger)

    write_report(args.report_file, report)
    if args.csv_prefix is not None:
        csv_files = write_csv_exports(report, args.csv_prefix)
        logger.info("Wrote %s CSV files using prefix=%s", len(csv_files), args.csv_prefix)

    if args.mode == "compare":
        summary = report["comparison_summary"]
        logger.info(
            "Completed compare mode | rounds_per_candidate=%s | A_simulated_rtp=%.6f | B_simulated_rtp=%.6f | report=%s",
            args.rounds,
            summary["simulated_rtp"]["A"],
            summary["simulated_rtp"]["B"],
            args.report_file,
        )
    else:
        logger.info(
            "Completed %s bonus rounds | candidate=%s | simulated_rtp=%.6f | report=%s",
            args.rounds,
            args.candidate,
            report["simulated_rtp"],
            args.report_file,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())