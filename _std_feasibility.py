"""Read-only feasibility check: per-mode current STD vs maximum achievable STD
(cost-normalized payout multiplier basis, EV pinned at TARGET_RTP).

Max achievable STD for a fixed payout support {v_i} with mean mu is the two-point
extreme: sqrt((mu - v_min) * (v_max - mu)). If that upper bound < MIN_STD, the mode
cannot satisfy the rule without changing its multiplier table / product model.
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path

PUBLISH = Path("math-sdk/games/azteck_plinko_final/artifacts/publish_files")
PAYOUT_SCALE = 100
TARGET_RTP = 0.9605
MIN_STD = 0.6
MAX_STD = 60.0

index = json.loads((PUBLISH / "index.json").read_text(encoding="utf-8"))
cost_by_mode = {m["name"]: float(m["cost"]) for m in index["modes"]}


def lookup_rows(mode: str):
    f = PUBLISH / f"lookUpTable_{mode}_0.csv"
    rows = []
    with f.open(newline="", encoding="utf-8") as h:
        for r in csv.reader(h):
            if len(r) < 3:
                continue
            rows.append((int(float(r[1])), float(r[2]) / PAYOUT_SCALE))
    return rows


def stats(mode: str):
    cost = cost_by_mode[mode]
    rows = lookup_rows(mode)
    total = sum(w for w, _ in rows)
    vals = [m / cost for _, m in rows]
    mean = math.fsum(w * v for (w, _), v in zip(rows, vals)) / total
    e_x2 = math.fsum(w * v * v for (w, _), v in zip(rows, vals)) / total
    std = math.sqrt(max(0.0, e_x2 - mean * mean))
    vmin, vmax = min(vals), max(vals)
    mu = TARGET_RTP  # E[payout/cost] target
    max_std = math.sqrt(max(0.0, (mu - vmin) * (vmax - mu)))
    return cost, std, max_std, vmin, vmax


rows_out = []
for m in cost_by_mode:
    cost, std, max_std, vmin, vmax = stats(m)
    feasible = max_std >= MIN_STD
    rows_out.append((m, cost, std, max_std, feasible))

print(f"{'mode':28} {'cost':>6} {'cur_std':>9} {'max_std':>9} feasible>=0.6")
infeasible = []
below = []
for m, cost, std, max_std, feasible in rows_out:
    flag = "OK" if feasible else "INFEASIBLE"
    if not feasible:
        infeasible.append(m)
    if std < MIN_STD:
        below.append(m)
    print(f"{m:28} {cost:6.1f} {std:9.4f} {max_std:9.4f} {flag}")

print()
print(f"modes_below_min (cur_std<0.6): {len(below)}")
print(f"modes_infeasible (max_std<0.6): {len(infeasible)}")
print("infeasible:", ", ".join(infeasible) if infeasible else "none")
