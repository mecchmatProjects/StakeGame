from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Synthesize Azteck Plinko paytables and probabilities from fixed constraints")
    parser.add_argument("--root", default="math-sdk/games/azteck_plinko_final", help="Package root path")
    parser.add_argument("--target-rtp", type=float, default=None, help="Override target RTP")
    parser.add_argument("--payout-scale", type=float, default=100.0, help="Scale used by lookup generator")
    return parser.parse_args()


def write_csv(path: Path, headers: list[str], rows: list[list[object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerows(rows)


def binomial_probs(rows: int) -> list[float]:
    return [math.comb(rows, k) / (2.0 ** rows) for k in range(rows + 1)]


def distance_scores(rows: int) -> list[float]:
    center = rows / 2.0
    out: list[float] = []
    for i in range(rows + 1):
        d = abs(i - center)
        norm = (d / center) if center > 0 else 1.0
        out.append(norm)
    return out


def expected_from_beta(max_win: float, probs: list[float], scores: list[float], beta: float) -> float:
    eps = 1e-12
    return sum(p * (max_win * ((s + eps) ** beta)) for p, s in zip(probs, scores))


def solve_beta(max_win: float, probs: list[float], scores: list[float], target_mean: float) -> float:
    lo = 0.0
    hi = 400.0
    # f(beta) decreases with beta
    for _ in range(120):
        mid = (lo + hi) / 2.0
        mean = expected_from_beta(max_win, probs, scores, mid)
        if mean > target_mean:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def synthesize_multipliers(max_win: float, probs: list[float], rows: int, target_mean: float) -> list[float]:
    scores = distance_scores(rows)
    beta = solve_beta(max_win, probs, scores, target_mean)
    eps = 1e-12
    vals = [max_win * ((s + eps) ** beta) for s in scores]

    # Enforce exact edge max and non-negative center.
    vals[0] = max_win
    vals[-1] = max_win
    vals = [max(0.0, min(max_win, v)) for v in vals]

    # Small correction to match target mean exactly by nudging one non-edge bucket.
    current_mean = sum(p * v for p, v in zip(probs, vals))
    delta = target_mean - current_mean
    if abs(delta) > 1e-12:
        # Choose the highest-probability non-edge bucket with headroom.
        candidate_idx = None
        best_prob = -1.0
        for i, p in enumerate(probs):
            if i in (0, len(probs) - 1):
                continue
            if p > best_prob:
                best_prob = p
                candidate_idx = i
        if candidate_idx is not None and probs[candidate_idx] > 0:
            vals[candidate_idx] += delta / probs[candidate_idx]
            vals[candidate_idx] = max(0.0, min(max_win, vals[candidate_idx]))

    return [round(v, 6) for v in vals]


def infer_normal_max(difficulty: str, rows: int, known: dict) -> float:
    # Prefer explicit row mapping when available.
    expert_rows = known["feature_modes"]["normal"].get("expert_max_win_by_rows", {})
    if difficulty == "Expert" and str(rows) in expert_rows:
        return float(expert_rows[str(rows)])

    # Use documented row-range interpolation for non-expert difficulties.
    # Low: 5.6..16, Medium: 13..110, High: 29..1000 (rows 8..16)
    ranges = {
        "Low": (5.6, 16.0),
        "Medium": (13.0, 110.0),
        "High": (29.0, 1000.0),
    }
    if difficulty in ranges:
        lo, hi = ranges[difficulty]
        t = (rows - 8) / 8.0
        return round(lo + (hi - lo) * t, 6)

    # Fallback to global max if present.
    global_max = known["feature_modes"]["normal"].get("max_win_by_difficulty", {})
    return float(global_max.get(difficulty, 100.0))


def infer_buy100_max(difficulty: str, rows: int, known: dict) -> float:
    expert_rows = known["feature_modes"]["100balls"].get("expert_max_win_by_rows", {})
    if difficulty == "Expert" and str(rows) in expert_rows:
        return float(expert_rows[str(rows)])

    global_max = known["feature_modes"]["100balls"].get("max_win_by_difficulty", {})
    return float(global_max.get(difficulty, 1000.0))


def mode_name(mode_type: str, difficulty: str, rows: int) -> str:
    prefix = "buy100" if mode_type == "100balls" else "normal"
    return f"{prefix}_{difficulty.lower()}_{rows}"


def main() -> int:
    args = parse_args()
    root = Path(args.root).resolve()
    inputs = root / "inputs"
    publish = root / "artifacts" / "publish_files"

    constraints_path = inputs / "azteck_plinko_known_constraints.json"
    if not constraints_path.exists():
        raise FileNotFoundError(constraints_path)

    known = json.loads(constraints_path.read_text(encoding="utf-8"))
    target_rtp = float(args.target_rtp) if args.target_rtp is not None else float(known.get("target_rtp", 0.9605))

    difficulties = known["difficulty_levels"]
    rows_supported = [int(x) for x in known["rows_supported"]]

    normal_cost = float(known["feature_modes"]["normal"].get("cost_multiplier", 1.0))
    buy_cost = float(known["feature_modes"]["100balls"].get("cost_multiplier", 99.0))

    normal_rows: list[list[object]] = []
    buy_rows: list[list[object]] = []
    prob_rows: list[list[object]] = []
    modes: list[dict] = []

    for difficulty in difficulties:
        for rows in rows_supported:
            probs = binomial_probs(rows)

            # Normal mode synthesis.
            n_max = infer_normal_max(difficulty, rows, known)
            n_target_mean = target_rtp * normal_cost
            n_mults = synthesize_multipliers(n_max, probs, rows, n_target_mean)
            n_name = mode_name("normal", difficulty, rows)

            for idx, (m, p) in enumerate(zip(n_mults, probs)):
                normal_rows.append([difficulty, rows, idx, m, "x", "model_synthesized", "binomial p=0.5, calibrated to RTP"])
                prob_rows.append(["normal", difficulty, rows, idx, m, round(p, 12), "model_synthesized", "binomial p=0.5"])
            normal_rows.append([difficulty, rows, "MAX", n_max, "x", "model_synthesized", "derived max"])
            prob_rows.append(["normal", difficulty, rows, "MAX", n_max, "", "model_synthesized", "derived max marker"])

            modes.append(
                {
                    "name": n_name,
                    "mode_type": "normal",
                    "difficulty": difficulty,
                    "rows": rows,
                    "cost": normal_cost,
                    "rtp": target_rtp,
                    "max_win": n_max,
                    "weights": f"lookUpTable_{n_name}_0.csv",
                    "events": f"books_{n_name}.jsonl.zst",
                    "status": "model-synthesized",
                }
            )

            # 100 balls mode synthesis as direct static distribution calibrated to RTP at cost 99x.
            b_max = infer_buy100_max(difficulty, rows, known)
            b_target_mean = target_rtp * buy_cost
            b_mults = synthesize_multipliers(b_max, probs, rows, b_target_mean)
            b_name = mode_name("100balls", difficulty, rows)

            for idx, (m, p) in enumerate(zip(b_mults, probs)):
                buy_rows.append(
                    [
                        difficulty,
                        rows,
                        idx,
                        m,
                        "x",
                        "sum_100_independent",
                        int(buy_cost),
                        "model_synthesized",
                        "binomial p=0.5, calibrated to RTP",
                    ]
                )
                prob_rows.append(["100balls", difficulty, rows, idx, m, round(p, 12), "model_synthesized", "binomial p=0.5"])
            buy_rows.append(
                [
                    difficulty,
                    rows,
                    "MAX",
                    b_max,
                    "x",
                    "sum_100_independent",
                    int(buy_cost),
                    "model_synthesized",
                    "derived max",
                ]
            )
            prob_rows.append(["100balls", difficulty, rows, "MAX", b_max, "", "model_synthesized", "derived max marker"])

            modes.append(
                {
                    "name": b_name,
                    "mode_type": "100balls",
                    "difficulty": difficulty,
                    "rows": rows,
                    "cost": buy_cost,
                    "rtp": target_rtp,
                    "max_win": b_max,
                    "weights": f"lookUpTable_{b_name}_0.csv",
                    "events": f"books_{b_name}.jsonl.zst",
                    "status": "model-synthesized",
                }
            )

    write_csv(
        inputs / "azteck_plinko_paytables_normal.csv",
        ["difficulty", "rows", "bucket_index", "multiplier", "payout_unit", "source", "notes"],
        normal_rows,
    )
    write_csv(
        inputs / "azteck_plinko_paytables_100balls.csv",
        [
            "difficulty",
            "rows",
            "bucket_index",
            "multiplier",
            "payout_unit",
            "aggregation_rule",
            "cost_multiplier",
            "source",
            "notes",
        ],
        buy_rows,
    )
    write_csv(
        inputs / "azteck_plinko_probability_tables.csv",
        ["mode_type", "difficulty", "rows", "bucket_index", "multiplier", "probability", "source", "notes"],
        prob_rows,
    )

    index_payload = {
        "game_id": known.get("game_id", "azteck_plinko"),
        "version": "0.0.3-model-synthesized",
        "target_rtp": target_rtp,
        "modes": modes,
        "notes": [
            "Model-synthesized paytables and probabilities from fixed constraints",
            "Bucket probabilities use binomial(n=rows, p=0.5)",
            "Multipliers are calibrated per mode to target RTP and max-win constraints",
        ],
    }
    publish.mkdir(parents=True, exist_ok=True)
    (publish / "index.json").write_text(json.dumps(index_payload, indent=2), encoding="utf-8")

    print(f"Wrote synthesized index: {publish / 'index.json'}")
    print(f"Wrote rows: normal={len(normal_rows)}, buy100={len(buy_rows)}, probs={len(prob_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
