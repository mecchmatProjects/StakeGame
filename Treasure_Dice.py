from __future__ import annotations

import json
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple


ROOT = Path(__file__).resolve().parent
MAPPING_PATH = ROOT / "treasure_dice_phase3_mapping_spec.json"
LOG_PATH = ROOT / "log.txt"


def _load_mapping(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Mapping file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _build_mode_data(mapping: dict) -> Dict[str, dict]:
    mode_data: Dict[str, dict] = {}

    for mode in mapping["regular_modes"]:
        mode_id = mode["mode_id"]
        outcomes = []
        for item in mode["outcomes"]:
            outcomes.append(
                {
                    "outcome_id": item["outcome_id"],
                    "probability": float(item["probability"]),
                    "payout_multiplier": float(item["payout_multiplier"]),
                    "event_sequence": list(item["event_sequence"]),
                    "presentation_only": bool(item["presentation_only"]),
                }
            )
        _validate_distribution(mode_id, outcomes)
        mode_data[mode_id] = {
            "mode_id": mode_id,
            "cost_multiplier": float(mode["cost_multiplier"]),
            "outcomes": outcomes,
        }

    bonus = mapping["bonus_mode"]
    bonus_outcomes = []
    for item in bonus["outcomes"]:
        bonus_outcomes.append(
            {
                "outcome_id": item["outcome_id"],
                "probability": float(item["probability"]),
                "payout_multiplier": float(item["payout_multiplier_vs_base_bet"]),
                "event_sequence": list(item["event_sequence"]),
                "presentation_only": bool(item["presentation_only"]),
            }
        )
    _validate_distribution(bonus["mode_id"], bonus_outcomes)
    mode_data[bonus["mode_id"]] = {
        "mode_id": bonus["mode_id"],
        "cost_multiplier": float(bonus["cost_multiplier"]),
        "outcomes": bonus_outcomes,
    }

    return mode_data


def _validate_distribution(mode_id: str, outcomes: Sequence[dict]) -> None:
    total = sum(float(item["probability"]) for item in outcomes)
    if abs(total - 1.0) > 1e-8:
        raise ValueError(f"Probability sum for mode {mode_id} is {total}, expected 1.0")


def _build_cumulative(outcomes: Sequence[dict]) -> List[Tuple[float, dict]]:
    cumulative: List[Tuple[float, dict]] = []
    running = 0.0
    for item in outcomes:
        running += float(item["probability"])
        cumulative.append((running, item))
    return cumulative


def _pick_outcome(rng: random.Random, cumulative: Sequence[Tuple[float, dict]]) -> Tuple[dict, float]:
    draw = rng.random()
    for threshold, outcome in cumulative:
        if draw <= threshold:
            return outcome, draw
    return cumulative[-1][1], draw


@dataclass
class Totals:
    wager: float = 0.0
    payout: float = 0.0

    @property
    def net(self) -> float:
        return self.payout - self.wager

    @property
    def rtp(self) -> float:
        if self.wager <= 0:
            return 0.0
        return self.payout / self.wager


def _prompt_int(prompt: str, minimum: int = 1) -> int:
    while True:
        value = input(prompt).strip()
        try:
            parsed = int(value)
            if parsed < minimum:
                print(f"Enter an integer >= {minimum}.")
                continue
            return parsed
        except ValueError:
            print("Enter a valid integer.")


def _prompt_float(prompt: str, minimum: float = 0.0) -> float:
    while True:
        value = input(prompt).strip()
        try:
            parsed = float(value)
            if parsed < minimum:
                print(f"Enter a number >= {minimum}.")
                continue
            return parsed
        except ValueError:
            print("Enter a valid number.")


def _prompt_optional_int(prompt: str) -> Optional[int]:
    value = input(prompt).strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        print("Invalid seed, using system randomness.")
        return None


def _choose_mode_interactively(available_modes: Sequence[str]) -> str:
    while True:
        print("Available modes:")
        for idx, mode in enumerate(available_modes, start=1):
            print(f"  {idx}. {mode}")
        raw = input("Select mode by number or mode_id: ").strip()
        if raw in available_modes:
            return raw
        try:
            idx = int(raw)
            if 1 <= idx <= len(available_modes):
                return available_modes[idx - 1]
        except ValueError:
            pass
        print("Invalid mode selection. Try again.")


def _write_log_header(
    log_path: Path,
    config: dict,
) -> None:
    with log_path.open("w", encoding="utf-8") as handle:
        handle.write("# Treasure Dice Full Simulation Log\n")
        handle.write(json.dumps(config, sort_keys=True) + "\n")


def _append_log_line(log_path: Path, payload: dict) -> None:
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=True, sort_keys=True) + "\n")


def run() -> int:
    print("Treasure Dice Interactive Simulator")
    print("----------------------------------")

    mapping = _load_mapping(MAPPING_PATH)
    mode_data = _build_mode_data(mapping)
    mode_ids = list(mode_data.keys())

    rounds = _prompt_int("How many rounds should be simulated? ", minimum=1)
    base_bet = _prompt_float("Base bet amount (example 1.0): ", minimum=0.0000001)
    starting_balance = _prompt_float("Starting balance (example 1000.0): ", minimum=0.0)
    seed = _prompt_optional_int("RNG seed (optional, press Enter to skip): ")

    print("Mode selection policy:")
    print("  1. single (one mode for all rounds)")
    print("  2. cycle (iterate through all modes)")
    print("  3. random (random mode each round)")
    print("  4. manual (you choose each round)")

    policy_map = {
        "1": "single",
        "2": "cycle",
        "3": "random",
        "4": "manual",
        "single": "single",
        "cycle": "cycle",
        "random": "random",
        "manual": "manual",
    }

    policy = ""
    while policy not in policy_map:
        policy = input("Choose policy [1/2/3/4]: ").strip().lower()
    policy = policy_map[policy]

    fixed_mode = None
    if policy == "single":
        fixed_mode = _choose_mode_interactively(mode_ids)

    rng = random.Random(seed)
    totals = Totals()
    current_balance = starting_balance

    config = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "rounds": rounds,
        "base_bet": base_bet,
        "starting_balance": starting_balance,
        "seed": seed,
        "policy": policy,
        "fixed_mode": fixed_mode,
        "mapping_spec": mapping.get("spec_id", "unknown"),
    }
    _write_log_header(LOG_PATH, config)

    cumulative_by_mode: Dict[str, Dict[str, float]] = {
        mode: {"rounds": 0.0, "wager": 0.0, "payout": 0.0} for mode in mode_ids
    }

    for round_index in range(rounds):
        if policy == "single":
            mode_id = fixed_mode
        elif policy == "cycle":
            mode_id = mode_ids[round_index % len(mode_ids)]
        elif policy == "random":
            mode_id = rng.choice(mode_ids)
        else:
            print(f"\nRound {round_index + 1}/{rounds}")
            mode_id = _choose_mode_interactively(mode_ids)

        assert mode_id is not None
        mode = mode_data[mode_id]
        cost_multiplier = float(mode["cost_multiplier"])
        round_wager = base_bet * cost_multiplier

        cumulative = _build_cumulative(mode["outcomes"])
        outcome, draw = _pick_outcome(rng, cumulative)

        payout_multiplier = float(outcome["payout_multiplier"])
        round_payout = base_bet * payout_multiplier
        net = round_payout - round_wager

        totals.wager += round_wager
        totals.payout += round_payout
        current_balance += net

        cumulative_by_mode[mode_id]["rounds"] += 1.0
        cumulative_by_mode[mode_id]["wager"] += round_wager
        cumulative_by_mode[mode_id]["payout"] += round_payout

        event_states = [
            {
                "index": i,
                "type": event_type,
                "mode_id": mode_id,
                "outcome_id": outcome["outcome_id"],
            }
            for i, event_type in enumerate(outcome["event_sequence"])
        ]

        round_state = {
            "type": "round_state",
            "round_number": round_index + 1,
            "mode_id": mode_id,
            "cost_multiplier": cost_multiplier,
            "base_bet": base_bet,
            "round_wager": round_wager,
            "rng_draw": draw,
            "selected_outcome": {
                "outcome_id": outcome["outcome_id"],
                "probability": float(outcome["probability"]),
                "payout_multiplier": payout_multiplier,
                "presentation_only": bool(outcome["presentation_only"]),
            },
            "event_sequence": list(outcome["event_sequence"]),
            "event_states": event_states,
            "round_payout": round_payout,
            "round_net": net,
            "cumulative_wager": totals.wager,
            "cumulative_payout": totals.payout,
            "cumulative_net": totals.net,
            "cumulative_rtp": totals.rtp,
            "balance_after_round": current_balance,
        }
        _append_log_line(LOG_PATH, round_state)

        print(
            "Round {r}: mode={m}, outcome={o}, wager={w:.4f}, payout={p:.4f}, net={n:.4f}, rtp={rtp:.6f}".format(
                r=round_index + 1,
                m=mode_id,
                o=outcome["outcome_id"],
                w=round_wager,
                p=round_payout,
                n=net,
                rtp=totals.rtp,
            )
        )

    per_mode_summary = {}
    for mode_id in mode_ids:
        rounds_mode = cumulative_by_mode[mode_id]["rounds"]
        wager_mode = cumulative_by_mode[mode_id]["wager"]
        payout_mode = cumulative_by_mode[mode_id]["payout"]
        per_mode_summary[mode_id] = {
            "rounds": int(rounds_mode),
            "wager": wager_mode,
            "payout": payout_mode,
            "net": payout_mode - wager_mode,
            "rtp": (payout_mode / wager_mode) if wager_mode > 0 else 0.0,
        }

    final_summary = {
        "type": "final_summary",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "rounds": rounds,
        "base_bet": base_bet,
        "starting_balance": starting_balance,
        "ending_balance": current_balance,
        "total_wager": totals.wager,
        "total_payout": totals.payout,
        "total_net": totals.net,
        "total_rtp": totals.rtp,
        "policy": policy,
        "fixed_mode": fixed_mode,
        "per_mode_summary": per_mode_summary,
    }
    _append_log_line(LOG_PATH, final_summary)

    print("\nSimulation complete.")
    print(f"Rounds: {rounds}")
    print(f"Total wager: {totals.wager:.4f}")
    print(f"Total payout: {totals.payout:.4f}")
    print(f"Total net: {totals.net:.4f}")
    print(f"Total RTP: {totals.rtp:.6f}")
    print(f"Ending balance: {current_balance:.4f}")
    print(f"Log written to: {LOG_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
