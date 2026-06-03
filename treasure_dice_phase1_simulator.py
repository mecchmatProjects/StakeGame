"""Simulate Treasure Dice Phase 1 regular-route rounds.

This script models only the seven regular routes defined in the game brief.
It excludes Bonus Buy and any Phase 2+ features.
"""

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
import random
from typing import Dict, List


RTP_TARGET = 0.96
DEFAULT_BET = 1.0
DEFAULT_LOG_FILE = "treasure_dice_phase1_simulator.log"
DEFAULT_REPORT_FILE = "treasure_dice_phase1_report.json"


@dataclass(frozen=True)
class RouteMode:
    """Represents a regular Treasure Dice route.

    Attributes:
        mode_id: Internal route identifier.
        ui_name: Display name.
        cost: Cost multiplier for the round.
        win_chance: Probability of a winning outcome.
        payout_multiplier: Total payout multiplier on win.
    """

    mode_id: str
    ui_name: str
    cost: float
    win_chance: float
    payout_multiplier: float

    @property
    def theoretical_rtp(self) -> float:
        """Returns the theoretical RTP for the route."""
        return self.win_chance * self.payout_multiplier

    @property
    def variance(self) -> float:
        """Returns the payout-multiplier variance for the route."""
        return (RTP_TARGET * RTP_TARGET) * ((1 / self.win_chance) - 1)

    @property
    def standard_deviation(self) -> float:
        """Returns the payout-multiplier standard deviation for the route."""
        return self.variance ** 0.5


@dataclass
class RoundRecord:
    """Stores the outcome of a single simulated round.

    Attributes:
        round_number: Sequential round number.
        mode_id: Route identifier used for the round.
        ui_name: Display name for the route.
        bet_amount: Stake amount for the round.
        win_chance: Probability of winning the route.
        payout_multiplier: Total payout multiplier on win.
        roll: Random draw in [0, 1).
        won: Whether the round was a win.
        payout: Settled payout amount.
        net_profit: Payout minus stake.
        cumulative_wager: Total amount wagered up to and including the round.
        cumulative_payout: Total amount paid up to and including the round.
        cumulative_rtp: Running RTP after the round.
    """

    round_number: int
    mode_id: str
    ui_name: str
    bet_amount: float
    win_chance: float
    payout_multiplier: float
    roll: float
    won: bool
    payout: float
    net_profit: float
    cumulative_wager: float
    cumulative_payout: float
    cumulative_rtp: float


ROUTES: List[RouteMode] = [
    RouteMode("safe_shore", "Safe Shore", 1.0, 0.80, 1.20),
    RouteMode("hidden_bay", "Hidden Bay", 1.0, 0.60, 1.60),
    RouteMode("coral_reef", "Coral Reef", 1.0, 0.40, 2.40),
    RouteMode("storm_route", "Storm Route", 1.0, 0.25, 3.84),
    RouteMode("skull_island", "Skull Island", 1.0, 0.10, 9.60),
    RouteMode("kraken_waters", "Kraken Waters", 1.0, 0.05, 19.20),
    RouteMode("lost_treasure", "Lost Treasure", 1.0, 0.01, 96.00),
]

ROUTE_LOOKUP: Dict[str, RouteMode] = {route.mode_id: route for route in ROUTES}


def parse_args() -> argparse.Namespace:
    """Parses command-line arguments.

    Returns:
        Parsed CLI namespace.
    """
    parser = argparse.ArgumentParser(
        description="Simulate Treasure Dice Phase 1 regular-route rounds."
    )
    parser.add_argument("--rounds", type=int, default=10, help="Number of rounds to simulate.")
    parser.add_argument(
        "--bet",
        type=float,
        default=DEFAULT_BET,
        help="Base bet amount per round.",
    )
    parser.add_argument(
        "--selection-policy",
        choices=("cycle", "random", "single"),
        default="cycle",
        help="How routes are selected across rounds.",
    )
    parser.add_argument(
        "--mode-id",
        choices=tuple(ROUTE_LOOKUP.keys()),
        default="safe_shore",
        help="Route to use when selection policy is single.",
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
    return parser.parse_args()


def configure_logger(log_file: Path, log_level: str) -> logging.Logger:
    """Configures a logger for console and file output.

    Args:
        log_file: Path to the log file.
        log_level: Logging level name.

    Returns:
        Configured logger instance.
    """
    logger = logging.getLogger("treasure_dice_phase1")
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


def choose_route(
    round_index: int,
    selection_policy: str,
    rng: random.Random,
    single_mode_id: str,
) -> RouteMode:
    """Selects the route for a given round.

    Args:
        round_index: Zero-based round index.
        selection_policy: Route selection policy.
        rng: Random number generator.
        single_mode_id: Mode to use for single-mode runs.

    Returns:
        Selected route mode.
    """
    if selection_policy == "single":
        return ROUTE_LOOKUP[single_mode_id]
    if selection_policy == "random":
        return rng.choice(ROUTES)
    return ROUTES[round_index % len(ROUTES)]


def simulate_rounds(args: argparse.Namespace, logger: logging.Logger) -> Dict[str, object]:
    """Simulates the requested number of Phase 1 rounds.

    Args:
        args: Parsed CLI arguments.
        logger: Configured logger.

    Returns:
        JSON-serializable simulation report.
    """
    rng = random.Random(args.seed)
    records: List[RoundRecord] = []
    cumulative_wager = 0.0
    cumulative_payout = 0.0
    wins_by_mode: Dict[str, int] = {route.mode_id: 0 for route in ROUTES}
    rounds_by_mode: Dict[str, int] = {route.mode_id: 0 for route in ROUTES}

    for round_index in range(args.rounds):
        route = choose_route(round_index, args.selection_policy, rng, args.mode_id)
        roll = rng.random()
        won = roll < route.win_chance
        payout = args.bet * route.payout_multiplier if won else 0.0
        net_profit = payout - args.bet
        cumulative_wager += args.bet
        cumulative_payout += payout
        rounds_by_mode[route.mode_id] += 1
        if won:
            wins_by_mode[route.mode_id] += 1

        record = RoundRecord(
            round_number=round_index + 1,
            mode_id=route.mode_id,
            ui_name=route.ui_name,
            bet_amount=round(args.bet, 4),
            win_chance=route.win_chance,
            payout_multiplier=route.payout_multiplier,
            roll=round(roll, 6),
            won=won,
            payout=round(payout, 4),
            net_profit=round(net_profit, 4),
            cumulative_wager=round(cumulative_wager, 4),
            cumulative_payout=round(cumulative_payout, 4),
            cumulative_rtp=round(cumulative_payout / cumulative_wager, 6),
        )
        records.append(record)
        logger.info(
            "Round %s | mode=%s | roll=%.6f | won=%s | payout=%.4f | net=%.4f | cum_rtp=%.6f",
            record.round_number,
            record.mode_id,
            record.roll,
            record.won,
            record.payout,
            record.net_profit,
            record.cumulative_rtp,
        )

    mode_summaries: List[Dict[str, object]] = []
    for route in ROUTES:
        rounds_played = rounds_by_mode[route.mode_id]
        wins = wins_by_mode[route.mode_id]
        simulated_hit_rate = (wins / rounds_played) if rounds_played else 0.0
        mode_summaries.append(
            {
                "mode_id": route.mode_id,
                "ui_name": route.ui_name,
                "rounds_played": rounds_played,
                "wins": wins,
                "simulated_hit_rate": round(simulated_hit_rate, 6),
                "theoretical_hit_rate": route.win_chance,
                "theoretical_rtp": round(route.theoretical_rtp, 6),
                "payout_multiplier": route.payout_multiplier,
                "variance": round(route.variance, 6),
                "standard_deviation": round(route.standard_deviation, 6),
                "preliminary_max_win_multiplier": route.payout_multiplier,
            }
        )

    total_report = {
        "phase": 1,
        "feature_scope": "regular routes only",
        "rounds": args.rounds,
        "bet": args.bet,
        "selection_policy": args.selection_policy,
        "seed": args.seed,
        "theoretical_rtp_target": RTP_TARGET,
        "total_wager": round(cumulative_wager, 4),
        "total_payout": round(cumulative_payout, 4),
        "total_net_profit": round(cumulative_payout - cumulative_wager, 4),
        "simulated_rtp": round(cumulative_payout / cumulative_wager, 6),
        "round_records": [asdict(record) for record in records],
        "mode_summaries": mode_summaries,
    }
    return total_report


def write_report(report_file: Path, report: Dict[str, object]) -> None:
    """Writes the simulation report to disk as JSON.

    Args:
        report_file: Output report path.
        report: Simulation report object.
    """
    report_file.write_text(json.dumps(report, indent=2), encoding="utf-8")


def main() -> int:
    """Runs the CLI entry point.

    Returns:
        Process exit code.
    """
    args = parse_args()
    logger = configure_logger(args.log_file, args.log_level)
    report = simulate_rounds(args, logger)
    write_report(args.report_file, report)
    logger.info(
        "Completed %s rounds | simulated_rtp=%.6f | report=%s",
        args.rounds,
        report["simulated_rtp"],
        args.report_file,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())