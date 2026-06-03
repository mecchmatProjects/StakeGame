"""Phase 5 validation runner for Treasure Dice Math SDK package artifacts."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from math import sqrt
from pathlib import Path
from typing import Dict, List, Tuple

import zstandard as zstd


ROOT = Path(__file__).resolve().parent
SDK_GAME_DIR = ROOT / "math-sdk" / "games" / "treasure_dice"
PUBLISH_DIR = SDK_GAME_DIR / "library" / "publish_files"
CONFIG_DIR = SDK_GAME_DIR / "library" / "configs"
MAPPING_PATH = ROOT / "treasure_dice_phase3_mapping_spec.json"

SMALL_BETS = [0.01, 0.02, 0.05]


@dataclass
class ModeValidation:
    mode_id: str
    cost: float
    rounds: int
    theoretical_rtp: float
    simulated_rtp: float
    rtp_drift: float
    theoretical_std: float
    simulated_std: float
    std_error: float
    drift_sigma: float
    configured_max_win: float
    mapped_max_win: float
    observed_max_win: float
    weight_sum: int
    book_length: int
    weight_check_pass: bool
    lookup_check_pass: bool
    max_win_check_pass: bool
    replay_check_pass: bool


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def read_lookup_rows(mode_id: str) -> List[Tuple[int, int, float]]:
    """Read publish lookup rows as (id, weight, payout_multiplier)."""
    path = PUBLISH_DIR / f"lookUpTable_{mode_id}_0.csv"
    rows: List[Tuple[int, int, float]] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        for row in reader:
            sim_id = int(row[0])
            weight = int(row[1])
            payout_multiplier = int(row[2]) / 100.0
            rows.append((sim_id, weight, payout_multiplier))
    return rows


def read_books(mode_id: str) -> List[dict]:
    """Read compressed books JSONL for one mode."""
    path = PUBLISH_DIR / f"books_{mode_id}.jsonl.zst"
    dctx = zstd.ZstdDecompressor()
    with path.open("rb") as handle:
        text = dctx.stream_reader(handle).read().decode("utf-8")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def normalize_book_multiplier(raw_value: float, configured_max_win: float) -> float:
    """Normalize book payout multiplier to match lookup multiplier units.

    Some SDK paths store payoutMultiplier in cent-scaled units.
    """
    if raw_value > configured_max_win * 5:
        return raw_value / 100.0
    return raw_value


def theoretical_distribution(mapping: dict, mode_id: str) -> Tuple[float, List[Tuple[float, float]]]:
    """Return (cost, [(probability, payout_multiplier)])."""
    for mode in mapping["regular_modes"]:
        if mode["mode_id"] == mode_id:
            outcomes = [(float(item["probability"]), float(item["payout_multiplier"])) for item in mode["outcomes"]]
            return float(mode["cost_multiplier"]), outcomes

    bonus = mapping["bonus_mode"]
    if bonus["mode_id"] != mode_id:
        raise KeyError(f"Mode not found in mapping: {mode_id}")
    outcomes = [
        (float(item["probability"]), float(item["payout_multiplier_vs_base_bet"]))
        for item in bonus["outcomes"]
    ]
    return float(bonus["cost_multiplier"]), outcomes


def distribution_moments(outcomes: List[Tuple[float, float]]) -> Tuple[float, float]:
    mean = sum(prob * payout for prob, payout in outcomes)
    variance = sum(prob * ((payout - mean) ** 2) for prob, payout in outcomes)
    return mean, sqrt(variance)


def summarize_lookup(lookup_rows: List[Tuple[int, int, float]]) -> Tuple[int, float, float]:
    total_weight = sum(weight for _, weight, _ in lookup_rows)
    if total_weight <= 0:
        return 0, 0.0, 0.0

    mean = sum(weight * payout for _, weight, payout in lookup_rows) / total_weight
    variance = sum(weight * ((payout - mean) ** 2) for _, weight, payout in lookup_rows) / total_weight
    return total_weight, mean, sqrt(variance)


def check_lookup_matches_books(
    lookup_rows: List[Tuple[int, int, float]],
    books: List[dict],
    configured_max_win: float,
) -> bool:
    books_by_id: Dict[int, float] = {}
    for record in books:
        raw = float(record["payoutMultiplier"])
        books_by_id[int(record["id"])] = normalize_book_multiplier(raw, configured_max_win)

    for sim_id, _, payout in lookup_rows:
        if sim_id not in books_by_id:
            return False
        if abs(books_by_id[sim_id] - payout) > 1e-9:
            return False
    return True


def check_replay_determinism(books: List[dict]) -> bool:
    seq_by_outcome: Dict[str, set] = {}
    payout_by_outcome: Dict[str, set] = {}

    for record in books:
        outcome_id = None
        settlement_payout = None
        sequence: List[str] = []

        for event in record.get("events", []):
            event_type = event.get("type")
            if event_type == "round_settlement":
                outcome_id = event.get("outcomeId")
                settlement_payout = float(event.get("payoutMultiplier", 0.0))

        if outcome_id is None:
            return False

        for event in record.get("events", []):
            if event.get("outcomeId") == outcome_id and event.get("type") != "round_settlement":
                sequence.append(str(event.get("type")))

        seq_by_outcome.setdefault(outcome_id, set()).add(tuple(sequence))
        payout_by_outcome.setdefault(outcome_id, set()).add(settlement_payout)

    for outcome_id in seq_by_outcome:
        if len(seq_by_outcome[outcome_id]) != 1:
            return False
        if len(payout_by_outcome.get(outcome_id, set())) != 1:
            return False

    return True


def rounding_effective_rtp_regular(win_prob: float, multiplier: float, bet: float) -> float:
    rounded_payout = round(bet * multiplier + 1e-12, 2)
    return (win_prob * rounded_payout) / bet


def rounding_effective_rtp_bonus(outcomes: List[Tuple[float, float]], bet: float, cost_mult: float) -> float:
    expected_rounded = sum(prob * round(bet * payout + 1e-12, 2) for prob, payout in outcomes)
    return expected_rounded / (bet * cost_mult)


def main() -> int:
    mapping = load_json(MAPPING_PATH)
    be_config = load_json(CONFIG_DIR / "config.json")

    modes = [item["name"] for item in be_config["bookShelfConfig"]]
    by_mode_config = {item["name"]: item for item in be_config["bookShelfConfig"]}

    mode_results: List[ModeValidation] = []

    for mode_id in modes:
        cost, theo_outcomes = theoretical_distribution(mapping, mode_id)
        theo_mean, theo_std = distribution_moments(theo_outcomes)
        theoretical_rtp = theo_mean / cost

        lookup_rows = read_lookup_rows(mode_id)
        books = read_books(mode_id)
        weight_sum, sim_mean, sim_std = summarize_lookup(lookup_rows)

        simulated_rtp = sim_mean / cost if cost > 0 else 0.0
        rounds = len(books)
        std_error = (theo_std / cost) / sqrt(max(weight_sum, 1))
        rtp_drift = simulated_rtp - theoretical_rtp
        drift_sigma = (rtp_drift / std_error) if std_error > 0 else 0.0

        mapped_max = max(payout for _, payout in theo_outcomes)
        observed_max = max((record.get("payoutMultiplier", 0.0) for record in books), default=0.0)
        configured_max = float(by_mode_config[mode_id]["maxWin"])

        weight_check_pass = weight_sum == rounds and weight_sum > 0
        lookup_check_pass = check_lookup_matches_books(lookup_rows, books, configured_max)
        replay_check_pass = check_replay_determinism(books)
        normalized_observed_max = normalize_book_multiplier(observed_max, configured_max)
        max_win_check_pass = normalized_observed_max <= configured_max + 1e-9 and abs(mapped_max - configured_max) < 1e-9

        mode_results.append(
            ModeValidation(
                mode_id=mode_id,
                cost=cost,
                rounds=rounds,
                theoretical_rtp=theoretical_rtp,
                simulated_rtp=simulated_rtp,
                rtp_drift=rtp_drift,
                theoretical_std=theo_std,
                simulated_std=sim_std,
                std_error=std_error,
                drift_sigma=drift_sigma,
                configured_max_win=configured_max,
                mapped_max_win=mapped_max,
                observed_max_win=normalized_observed_max,
                weight_sum=weight_sum,
                book_length=rounds,
                weight_check_pass=weight_check_pass,
                lookup_check_pass=lookup_check_pass,
                max_win_check_pass=max_win_check_pass,
                replay_check_pass=replay_check_pass,
            )
        )

    regular_rounding = []
    for mode in mapping["regular_modes"]:
        win_outcome = next(item for item in mode["outcomes"] if item["payout_multiplier"] > 0)
        p = float(win_outcome["probability"])
        m = float(win_outcome["payout_multiplier"])
        for bet in SMALL_BETS:
            eff = rounding_effective_rtp_regular(p, m, bet)
            regular_rounding.append(
                {
                    "mode_id": mode["mode_id"],
                    "bet": bet,
                    "effective_rtp": eff,
                    "drift_vs_target": eff - 0.96,
                }
            )

    bonus_cost = float(mapping["bonus_mode"]["cost_multiplier"])
    bonus_outcomes = [
        (float(item["probability"]), float(item["payout_multiplier_vs_base_bet"]))
        for item in mapping["bonus_mode"]["outcomes"]
    ]
    bonus_rounding = []
    for bet in SMALL_BETS:
        eff = rounding_effective_rtp_bonus(bonus_outcomes, bet, bonus_cost)
        bonus_rounding.append(
            {
                "mode_id": mapping["bonus_mode"]["mode_id"],
                "bet": bet,
                "effective_rtp": eff,
                "drift_vs_target": eff - 0.96,
            }
        )

    summary = {
        "phase": 5,
        "date": "2026-06-03",
        "package_path": str(SDK_GAME_DIR),
        "modes": [item.__dict__ for item in mode_results],
        "checks": {
            "all_weight_checks_pass": all(item.weight_check_pass for item in mode_results),
            "all_lookup_checks_pass": all(item.lookup_check_pass for item in mode_results),
            "all_max_win_checks_pass": all(item.max_win_check_pass for item in mode_results),
            "all_replay_checks_pass": all(item.replay_check_pass for item in mode_results),
        },
        "rounding": {
            "regular_modes": regular_rounding,
            "bonus_mode": bonus_rounding,
        },
        "notes": [
            "Simulated RTP values are based on current package-generation simulation counts in run.py.",
            "Short runs are expected to deviate from 0.96, especially for high-volatility low-hit modes.",
        ],
    }

    out_path = ROOT / "treasure_dice_phase5_validation_summary.json"
    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
