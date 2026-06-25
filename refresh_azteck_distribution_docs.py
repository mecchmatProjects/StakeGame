"""Refresh docs/volatility_report_per_mode.csv and docs/calculated_distribution_summary.json
from the CURRENT lookup tables (symmetric-design build). Pure analytics refresh; does not
modify any math, lookups, books, or inputs.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

PAYOUT_SCALE = 100  # payout_raw = round(multiplier * 100)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", default="math-sdk/games/azteck_plinko_final")
    return p.parse_args()


def load_lookup(path: Path) -> list[tuple[int, float]]:
    """Return list of (weight, multiplier) from a lookUpTable csv (sim_id,weight,payout_raw)."""
    rows: list[tuple[int, float]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            parts = line.split(",")
            if len(parts) < 3:
                continue
            try:
                weight = int(parts[1])
                payout_raw = int(parts[2])
            except ValueError:
                continue
            rows.append((weight, payout_raw / PAYOUT_SCALE))
    return rows


def mode_stats(rows: list[tuple[int, float]], cost: float) -> dict:
    weight_sum = sum(w for w, _ in rows)
    mean_payout = sum(w * m for w, m in rows) / weight_sum
    var = sum(w * (m - mean_payout) ** 2 for w, m in rows) / weight_sum
    std_payout = math.sqrt(var)
    mults = [m for _, m in rows]
    return {
        "weight_sum": weight_sum,
        "mean_payout": mean_payout,
        "normalized_rtp": mean_payout / cost,
        "std_payout": std_payout,
        "normalized_std": std_payout / cost,
        "min_multiplier": min(mults),
        "max_multiplier": max(mults),
    }


def main() -> None:
    args = parse_args()
    root = Path(args.root)
    pub = root / "artifacts" / "publish_files"
    docs = root / "docs"
    docs.mkdir(parents=True, exist_ok=True)

    index = json.loads((pub / "index.json").read_text(encoding="utf-8"))
    target_rtp = index.get("target_rtp", 0.9605)
    std_rule = index.get("std_rule", {}) if isinstance(index.get("std_rule"), dict) else {}
    base_std = float(index.get("base_std", 0.5))
    std_min = float(std_rule.get("min", 0.6))
    std_max = float(std_rule.get("max", 60.0))

    vol_rows: list[dict] = []
    dist_rows: list[dict] = []

    for mode in index["modes"]:
        name = mode["name"]
        cost = float(mode["cost"])
        rows = load_lookup(pub / mode["weights"])
        st = mode_stats(rows, cost)
        norm_std = st["normalized_std"]
        vol_rows.append(
            {
                "mode": name,
                "cost": cost,
                "weight_sum": st["weight_sum"],
                "mean_payout": round(st["mean_payout"], 7),
                "normalized_rtp": round(st["normalized_rtp"], 7),
                "std_payout": round(st["std_payout"], 8),
                "normalized_std": round(norm_std, 8),
                "base_std": base_std,
                "std_min": std_min,
                "std_max": std_max,
                "min_multiplier": round(st["min_multiplier"], 6),
                "max_multiplier": round(st["max_multiplier"], 6),
                "std_rule_pass": bool(std_min <= norm_std <= std_max),
            }
        )
        dist_rows.append(
            {
                "mode": name,
                "cost": cost,
                "max_win": round(st["max_multiplier"], 6),
                "rows": mode["rows"],
                "target_rtp": target_rtp,
                "computed_rtp": st["normalized_rtp"],
                "rtp_drift": st["normalized_rtp"] - target_rtp,
            }
        )

    vol_path = docs / "volatility_report_per_mode.csv"
    with vol_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(vol_rows[0].keys()))
        writer.writeheader()
        writer.writerows(vol_rows)

    dist_path = docs / "calculated_distribution_summary.json"
    dist_path.write_text(json.dumps(dist_rows, indent=2), encoding="utf-8")

    worst = max(abs(r["rtp_drift"]) for r in dist_rows)
    print(f"Wrote {vol_path}")
    print(f"Wrote {dist_path}")
    print(f"modes={len(dist_rows)} worst_rtp_drift={worst:.3e}")


if __name__ == "__main__":
    main()
