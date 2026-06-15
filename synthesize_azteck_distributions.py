from __future__ import annotations

import argparse
import csv
import json
import math
import re
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Synthesize full Azteck Plinko multipliers and probabilities to satisfy target RTP"
    )
    parser.add_argument(
        "--root",
        default="math-sdk/games/azteck_plinko_final",
        help="Package root path",
    )
    parser.add_argument(
        "--target-rtp",
        type=float,
        default=None,
        help="Override target RTP. Defaults to known constraints target.",
    )
    parser.add_argument(
        "--multiplier-file",
        default="AzreckPlinko_multipliers.txt",
        help="Path to authoritative normal-mode multipliers table",
    )
    return parser.parse_args()


def mode_from_name(mode_name: str) -> tuple[str, str, int]:
    parts = mode_name.split("_")
    if len(parts) < 3:
        return ("", "", 0)
    prefix = parts[0].lower()
    difficulty = parts[1].capitalize()
    rows = int(parts[2])
    mode_type = "100balls" if prefix == "buy100" else "normal"
    return (mode_type, difficulty, rows)


def shape_for(difficulty: str, mode_type: str) -> float:
    base = {
        "Low": 1.15,
        "Medium": 1.45,
        "High": 1.9,
        "Expert": 2.5,
    }.get(difficulty, 1.5)
    if mode_type == "100balls":
        return base + 0.35
    return base


def parse_multiplier_token(token: str) -> float:
    t = token.strip().lower().replace(",", "")
    if not t:
        raise ValueError("empty multiplier token")
    if t.endswith("k"):
        return float(t[:-1]) * 1000.0
    return float(t)


def parse_authoritative_multipliers(path: Path) -> dict[tuple[str, int], list[float]]:
    if not path.exists():
        raise FileNotFoundError(f"Multiplier file not found: {path}")

    table: dict[tuple[str, int], list[float]] = {}
    pattern = re.compile(r"^\s*(\d+)\s+([A-Za-z]+)\s+(.+?)\s*$")

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.lower().startswith("rows"):
            continue

        match = pattern.match(line)
        if not match:
            continue

        rows = int(match.group(1))
        difficulty = match.group(2).capitalize()
        payload = match.group(3)

        parts = [p.strip() for p in payload.split("-") if p.strip()]
        values = [parse_multiplier_token(p) for p in parts]
        expected = rows + 1
        if len(values) != expected:
            raise ValueError(
                f"Multiplier count mismatch for {difficulty} rows={rows}: got {len(values)}, expected {expected}"
            )

        table[(difficulty, rows)] = values

    expected_keys = {(d, r) for d in ("Low", "Medium", "High", "Expert") for r in range(8, 17)}
    missing = sorted(expected_keys - set(table.keys()))
    if missing:
        raise ValueError(f"Multiplier table missing entries: {missing}")

    return table


def derive_100balls_multipliers(normal: list[float], cost_multiplier: float = 99.0, cap: float = 100000.0) -> list[float]:
    return [round(min(cap, m * cost_multiplier), 6) for m in normal]


def build_multiplier_ladder(max_win: float, rows: int, shape: float) -> list[float]:
    n = max(rows, 2)
    ladder: list[float] = []
    for idx in range(n + 1):
        t = idx / n
        value = max_win * (t ** shape)
        if idx == 0:
            value = 0.0
        if idx == n:
            value = max_win
        ladder.append(round(value, 6))

    # Ensure non-decreasing and unique-ish progression for numeric stability.
    for i in range(1, len(ladder)):
        if ladder[i] < ladder[i - 1]:
            ladder[i] = ladder[i - 1]
    return ladder


def softmax_probs_for_target(multipliers: list[float], target_mean: float) -> list[float]:
    if not multipliers:
        return []

    max_m = max(multipliers)
    if max_m <= 0:
        return [1.0] + [0.0] * (len(multipliers) - 1)

    x = [m / max_m for m in multipliers]

    def probs(lam: float) -> list[float]:
        # numerically stable softmax over -lam*x
        vals = [-lam * v for v in x]
        mx = max(vals)
        exps = [math.exp(v - mx) for v in vals]
        s = sum(exps)
        return [e / s for e in exps]

    def expected(lam: float) -> float:
        p = probs(lam)
        return sum(pi * mi for pi, mi in zip(p, multipliers))

    lo, hi = 0.0, 1.0
    e_lo = expected(lo)
    e_hi = expected(hi)

    # expected decreases as lambda increases. Expand hi until target is bracketed.
    while e_hi > target_mean and hi < 1e12:
        hi *= 2.0
        e_hi = expected(hi)

    if target_mean >= e_lo:
        return probs(lo)
    if target_mean <= e_hi:
        return probs(hi)

    for _ in range(120):
        mid = (lo + hi) / 2.0
        e_mid = expected(mid)
        if e_mid > target_mean:
            lo = mid
        else:
            hi = mid

    return probs((lo + hi) / 2.0)


def solve_probs_with_reachable_max(multipliers: list[float], target_mean: float, min_max_prob: float) -> list[float]:
    if not multipliers:
        return []
    if len(multipliers) == 1:
        return [1.0]

    max_multiplier = multipliers[-1]
    reserved = min_max_prob * max_multiplier
    if reserved >= target_mean:
        tail = [0.0] * (len(multipliers) - 1) + [1.0]
        return tail

    remaining_prob = 1.0 - min_max_prob
    remaining_target = (target_mean - reserved) / remaining_prob
    base_probs = softmax_probs_for_target(multipliers[:-1], remaining_target)
    return [p * remaining_prob for p in base_probs] + [min_max_prob]


def resolve_max_win(mode: dict, constraints: dict, mode_type: str, difficulty: str, rows: int) -> float:
    current = mode.get("max_win")
    if isinstance(current, (int, float)):
        return float(current)

    branch = constraints["feature_modes"]["100balls" if mode_type == "100balls" else "normal"]

    if difficulty == "Expert":
        by_rows = branch.get("expert_max_win_by_rows", {})
        if str(rows) in by_rows:
            return float(by_rows[str(rows)])

    by_diff = branch.get("max_win_by_difficulty", {})
    if difficulty in by_diff:
        return float(by_diff[difficulty])

    raise ValueError(f"Cannot resolve max win for {mode_type} {difficulty} rows={rows}")


def write_csv(path: Path, headers: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow({h: row.get(h, "") for h in headers})


def main() -> int:
    args = parse_args()
    root = Path(args.root).resolve()
    inputs = root / "inputs"
    publish = root / "artifacts" / "publish_files"

    constraints_path = inputs / "azteck_plinko_known_constraints.json"
    index_path = publish / "index.json"
    multiplier_file = Path(args.multiplier_file).resolve()

    constraints = json.loads(constraints_path.read_text(encoding="utf-8"))
    index = json.loads(index_path.read_text(encoding="utf-8"))
    authoritative = parse_authoritative_multipliers(multiplier_file)

    target_rtp = float(args.target_rtp) if args.target_rtp is not None else float(constraints["target_rtp"])

    modes = index.get("modes", [])

    prob_rows: list[dict] = []
    pay_normal: list[dict] = []
    pay_buy: list[dict] = []

    mode_summaries: list[dict] = []

    for mode in modes:
        if not isinstance(mode, dict):
            continue

        mode_name = mode.get("name")
        if not isinstance(mode_name, str):
            continue

        mode_type, difficulty, rows = mode_from_name(mode_name)
        if not mode_type:
            continue

        cost = float(mode.get("cost", 1.0))
        key = (difficulty, rows)
        if key not in authoritative:
            raise ValueError(f"Missing authoritative multipliers for {difficulty} rows={rows}")

        base_multipliers = authoritative[key]
        if mode_type == "normal":
            multipliers = [round(v, 6) for v in base_multipliers]
        else:
            multipliers = derive_100balls_multipliers(base_multipliers, cost_multiplier=99.0, cap=100000.0)

        max_win = float(max(multipliers)) if multipliers else resolve_max_win(mode, constraints, mode_type, difficulty, rows)
        mode["max_win"] = max_win

        target_mean = target_rtp * cost
        probs = solve_probs_with_reachable_max(multipliers, target_mean, min_max_prob=1e-6)

        rtp_check = (sum(p * m for p, m in zip(probs, multipliers)) / cost) if cost > 0 else 0.0

        for bucket_index, (m, p) in enumerate(zip(multipliers, probs)):
            prob_rows.append(
                {
                    "mode_type": mode_type,
                    "difficulty": difficulty,
                    "rows": str(rows),
                    "bucket_index": str(bucket_index),
                    "multiplier": f"{m:.6f}",
                    "probability": f"{p:.18e}",
                    "source": "authoritative_multiplier_table+rtp_solver",
                    "notes": f"mode={mode_name}",
                }
            )

            if mode_type == "normal":
                pay_normal.append(
                    {
                        "difficulty": difficulty,
                        "rows": str(rows),
                        "bucket_index": str(bucket_index),
                        "multiplier": f"{m:.6f}",
                        "payout_unit": "x",
                        "source": "authoritative_multiplier_table",
                        "notes": f"mode={mode_name}",
                    }
                )
            else:
                pay_buy.append(
                    {
                        "difficulty": difficulty,
                        "rows": str(rows),
                        "bucket_index": str(bucket_index),
                        "multiplier": f"{m:.6f}",
                        "payout_unit": "x",
                        "aggregation_rule": "sum_100_independent",
                        "cost_multiplier": "99",
                        "source": "derived_from_authoritative_normal_x99_capped",
                        "notes": f"mode={mode_name}",
                    }
                )

        mode_summaries.append(
            {
                "mode": mode_name,
                "cost": cost,
                "max_win": max_win,
                "rows": rows,
                "target_rtp": target_rtp,
                "computed_rtp": rtp_check,
                "rtp_drift": rtp_check - target_rtp,
            }
        )

    index["target_rtp"] = target_rtp
    index["version"] = "0.0.4-authoritative-multipliers"
    index["notes"] = [
        "Normal-mode multipliers sourced from AzreckPlinko_multipliers.txt.",
        "100balls multipliers derived as min(100000, normal_multiplier*99).",
        "Probabilities solved per mode to satisfy target RTP.",
    ]

    index_path.write_text(json.dumps(index, indent=2), encoding="utf-8")

    write_csv(
        inputs / "azteck_plinko_probability_tables.csv",
        ["mode_type", "difficulty", "rows", "bucket_index", "multiplier", "probability", "source", "notes"],
        prob_rows,
    )
    write_csv(
        inputs / "azteck_plinko_paytables_normal.csv",
        ["difficulty", "rows", "bucket_index", "multiplier", "payout_unit", "source", "notes"],
        pay_normal,
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
        pay_buy,
    )

    docs = root / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    summary_path = docs / "calculated_distribution_summary.json"
    summary_path.write_text(json.dumps(mode_summaries, indent=2), encoding="utf-8")

    print(f"Updated {index_path}")
    print(f"Updated {inputs / 'azteck_plinko_probability_tables.csv'}")
    print(f"Updated {inputs / 'azteck_plinko_paytables_normal.csv'}")
    print(f"Updated {inputs / 'azteck_plinko_paytables_100balls.csv'}")
    print(f"Wrote {summary_path}")
    print(f"Multiplier source: {multiplier_file}")
    print(f"Modes synthesized: {len(mode_summaries)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
