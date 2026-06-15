from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed Azteck Plinko index.json mode manifest from known constraints")
    parser.add_argument(
        "--constraints",
        default="math-sdk/games/azteck_plinko_final/inputs/azteck_plinko_known_constraints.json",
        help="Path to known constraints JSON",
    )
    parser.add_argument(
        "--index",
        default="math-sdk/games/azteck_plinko_final/artifacts/publish_files/index.json",
        help="Path to index.json to write",
    )
    return parser.parse_args()


def mode_name(prefix: str, difficulty: str, rows: int) -> str:
    return f"{prefix}_{difficulty.lower()}_{rows}"


def main() -> int:
    args = parse_args()
    constraints_path = Path(args.constraints)
    index_path = Path(args.index)

    constraints = json.loads(constraints_path.read_text(encoding="utf-8"))

    difficulties = constraints["difficulty_levels"]
    rows_values = constraints["rows_supported"]
    target_rtp = float(constraints["target_rtp"])

    normal = constraints["feature_modes"]["normal"]
    buy = constraints["feature_modes"]["100balls"]

    modes: list[dict] = []

    for difficulty in difficulties:
        for rows in rows_values:
            n_name = mode_name("normal", difficulty, rows)
            n_max = None
            if difficulty == "Expert":
                n_max = float(normal["expert_max_win_by_rows"][str(rows)])

            modes.append(
                {
                    "name": n_name,
                    "mode_type": "normal",
                    "difficulty": difficulty,
                    "rows": rows,
                    "cost": float(normal["cost_multiplier"]),
                    "rtp": target_rtp,
                    "max_win": n_max,
                    "weights": f"lookUpTable_{n_name}_0.csv",
                    "events": f"books_{n_name}.jsonl.zst",
                    "status": "pending-paytable",
                }
            )

            b_name = mode_name("buy100", difficulty, rows)
            b_max = None
            if difficulty == "Expert":
                b_max = float(buy["expert_max_win_by_rows"][str(rows)])

            modes.append(
                {
                    "name": b_name,
                    "mode_type": "100balls",
                    "difficulty": difficulty,
                    "rows": rows,
                    "cost": float(buy["cost_multiplier"]),
                    "rtp": target_rtp,
                    "max_win": b_max,
                    "weights": f"lookUpTable_{b_name}_0.csv",
                    "events": f"books_{b_name}.jsonl.zst",
                    "status": "pending-paytable",
                }
            )

    payload = {
        "game_id": constraints["game_id"],
        "version": "0.0.2-seeded-manifest",
        "target_rtp": target_rtp,
        "modes": modes,
        "notes": [
            "Manifest seeded from known constraints",
            "Lookup and book files are placeholders until paytables/probabilities are finalized",
        ],
    }

    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"Seeded index: {index_path}")
    print(f"Total modes: {len(modes)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
