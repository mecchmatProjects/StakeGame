from __future__ import annotations

import argparse
import csv
import json
import random
from dataclasses import dataclass
from math import sqrt
from pathlib import Path
from typing import Dict, List, Sequence, Tuple


ROOT = Path(__file__).resolve().parent
MAPPING_PATH = ROOT / "treasure_dice_phase3_mapping_spec.json"
DEFAULT_ROUNDS = 10000
DEFAULT_OUT_CSV = ROOT / "Treasure_Dice_MC_Stats.csv"


@dataclass
class ModeResult:
    mode_id: str
    rounds: int
    base_bet: float
    cost_multiplier: float
    total_wager: float
    total_payout: float
    simulated_rtp: float
    theoretical_rtp: float
    rtp_drift: float
    hit_rate: float
    zero_rate: float
    avg_payout_per_round: float
    avg_net_per_round: float
    std_dev_payout: float


def load_mapping(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Mapping file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def build_mode_definitions(mapping: dict) -> Dict[str, dict]:
    mode_defs: Dict[str, dict] = {}

    for mode in mapping["regular_modes"]:
        outcomes = [
            {
                "outcome_id": item["outcome_id"],
                "probability": float(item["probability"]),
                "payout_multiplier": float(item["payout_multiplier"]),
            }
            for item in mode["outcomes"]
        ]
        validate_distribution(mode["mode_id"], outcomes)
        mode_defs[mode["mode_id"]] = {
            "mode_id": mode["mode_id"],
            "cost_multiplier": float(mode["cost_multiplier"]),
            "outcomes": outcomes,
        }

    bonus = mapping["bonus_mode"]
    bonus_outcomes = [
        {
            "outcome_id": item["outcome_id"],
            "probability": float(item["probability"]),
            "payout_multiplier": float(item["payout_multiplier_vs_base_bet"]),
        }
        for item in bonus["outcomes"]
    ]
    validate_distribution(bonus["mode_id"], bonus_outcomes)
    mode_defs[bonus["mode_id"]] = {
        "mode_id": bonus["mode_id"],
        "cost_multiplier": float(bonus["cost_multiplier"]),
        "outcomes": bonus_outcomes,
    }

    return mode_defs


def validate_distribution(mode_id: str, outcomes: Sequence[dict]) -> None:
    total_prob = sum(item["probability"] for item in outcomes)
    if abs(total_prob - 1.0) > 1e-8:
        raise ValueError(f"Mode {mode_id} probability sum is {total_prob}, expected 1.0")


def theoretical_rtp(mode_def: dict) -> float:
    expected_payout = sum(
        item["probability"] * item["payout_multiplier"] for item in mode_def["outcomes"]
    )
    cost = mode_def["cost_multiplier"]
    return expected_payout / cost


def build_cumulative(outcomes: Sequence[dict]) -> List[Tuple[float, dict]]:
    running = 0.0
    cumulative: List[Tuple[float, dict]] = []
    for item in outcomes:
        running += item["probability"]
        cumulative.append((running, item))
    return cumulative


def draw_outcome(rng: random.Random, cumulative: Sequence[Tuple[float, dict]]) -> dict:
    draw = rng.random()
    for threshold, item in cumulative:
        if draw <= threshold:
            return item
    return cumulative[-1][1]


def run_mode_mc(mode_def: dict, rounds: int, base_bet: float, rng: random.Random) -> ModeResult:
    cost_multiplier = float(mode_def["cost_multiplier"])
    round_wager = base_bet * cost_multiplier
    cumulative = build_cumulative(mode_def["outcomes"])

    total_wager = 0.0
    total_payout = 0.0
    hit_count = 0
    payouts: List[float] = []

    for _ in range(rounds):
        outcome = draw_outcome(rng, cumulative)
        payout = base_bet * float(outcome["payout_multiplier"])

        total_wager += round_wager
        total_payout += payout
        payouts.append(payout)

        if payout > 0.0:
            hit_count += 1

    simulated_rtp = (total_payout / total_wager) if total_wager > 0 else 0.0
    theo_rtp = theoretical_rtp(mode_def)
    mean_payout = total_payout / rounds if rounds > 0 else 0.0
    variance = sum((p - mean_payout) ** 2 for p in payouts) / rounds if rounds > 0 else 0.0
    std_dev = sqrt(variance)

    return ModeResult(
        mode_id=mode_def["mode_id"],
        rounds=rounds,
        base_bet=base_bet,
        cost_multiplier=cost_multiplier,
        total_wager=total_wager,
        total_payout=total_payout,
        simulated_rtp=simulated_rtp,
        theoretical_rtp=theo_rtp,
        rtp_drift=simulated_rtp - theo_rtp,
        hit_rate=hit_count / rounds if rounds > 0 else 0.0,
        zero_rate=1.0 - (hit_count / rounds if rounds > 0 else 0.0),
        avg_payout_per_round=mean_payout,
        avg_net_per_round=(total_payout - total_wager) / rounds if rounds > 0 else 0.0,
        std_dev_payout=std_dev,
    )


def write_csv(results: Sequence[ModeResult], out_path: Path) -> None:
    fieldnames = [
        "mode_id",
        "rounds",
        "base_bet",
        "cost_multiplier",
        "total_wager",
        "total_payout",
        "simulated_rtp",
        "theoretical_rtp",
        "rtp_drift",
        "hit_rate",
        "zero_rate",
        "avg_payout_per_round",
        "avg_net_per_round",
        "std_dev_payout",
    ]

    with out_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in results:
            writer.writerow(
                {
                    "mode_id": row.mode_id,
                    "rounds": row.rounds,
                    "base_bet": f"{row.base_bet:.8f}",
                    "cost_multiplier": f"{row.cost_multiplier:.8f}",
                    "total_wager": f"{row.total_wager:.8f}",
                    "total_payout": f"{row.total_payout:.8f}",
                    "simulated_rtp": f"{row.simulated_rtp:.8f}",
                    "theoretical_rtp": f"{row.theoretical_rtp:.8f}",
                    "rtp_drift": f"{row.rtp_drift:.8f}",
                    "hit_rate": f"{row.hit_rate:.8f}",
                    "zero_rate": f"{row.zero_rate:.8f}",
                    "avg_payout_per_round": f"{row.avg_payout_per_round:.8f}",
                    "avg_net_per_round": f"{row.avg_net_per_round:.8f}",
                    "std_dev_payout": f"{row.std_dev_payout:.8f}",
                }
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Treasure Dice Monte Carlo tests for all modes and export CSV statistics."
    )
    parser.add_argument("--rounds", type=int, default=DEFAULT_ROUNDS, help="Rounds per mode.")
    parser.add_argument("--base-bet", type=float, default=1.0, help="Base bet for simulation.")
    parser.add_argument(
        "--seed",
        type=int,
        default=20260603,
        help="Deterministic RNG seed. Each mode uses an offset from this seed.",
    )
    parser.add_argument(
        "--out-csv",
        type=Path,
        default=DEFAULT_OUT_CSV,
        help="Output CSV path.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.rounds <= 0:
        raise ValueError("--rounds must be > 0")
    if args.base_bet <= 0:
        raise ValueError("--base-bet must be > 0")

    mapping = load_mapping(MAPPING_PATH)
    mode_defs = build_mode_definitions(mapping)

    mode_ids = sorted(mode_defs.keys())
    results: List[ModeResult] = []

    for index, mode_id in enumerate(mode_ids):
        rng = random.Random(args.seed + index)
        result = run_mode_mc(mode_defs[mode_id], args.rounds, args.base_bet, rng)
        results.append(result)

    write_csv(results, args.out_csv)

    print(f"Monte Carlo complete for {len(results)} modes.")
    print(f"Rounds per mode: {args.rounds}")
    print(f"CSV written to: {args.out_csv}")

    for row in results:
        print(
            "{mode}: hit_rate={hit:.6f}, sim_rtp={sim:.6f}, theo_rtp={theo:.6f}, drift={drift:+.6f}".format(
                mode=row.mode_id,
                hit=row.hit_rate,
                sim=row.simulated_rtp,
                theo=row.theoretical_rtp,
                drift=row.rtp_drift,
            )
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
