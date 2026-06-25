"""Validation oracle: per-mode STD on the RAW multiplier basis (X = payoutMultiplier),
std = sqrt(E[X^2] - E[X]^2), checked against [MIN_STD, MAX_STD].

This matches the Stake Engine validator definition (multiplier per base bet, NOT
divided by buy cost). Also reports the max achievable STD (two-point extreme on the
existing payout support at the mode's actual mean) so we know which fixes are feasible.
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path

PUBLISH = Path("math-sdk/games/azteck_plinko_final/artifacts/publish_files")
PAYOUT_SCALE = 100
MIN_STD = 0.6
MAX_STD = 60.0

index = json.loads((PUBLISH / "index.json").read_text(encoding="utf-8"))
modes = [m["name"] for m in index["modes"]]


def rows(mode: str):
    f = PUBLISH / f"lookUpTable_{mode}_0.csv"
    out = []
    with f.open(newline="", encoding="utf-8") as h:
        for r in csv.reader(h):
            if len(r) < 3:
                continue
            out.append((int(float(r[1])), float(r[2]) / PAYOUT_SCALE))
    return out


def analyze(mode: str):
    rs = rows(mode)
    total = sum(w for w, _ in rs)
    mean = math.fsum(w * x for w, x in rs) / total
    e_x2 = math.fsum(w * x * x for w, x in rs) / total
    std = math.sqrt(max(0.0, e_x2 - mean * mean))
    xmin = min(x for _, x in rs)
    xmax = max(x for _, x in rs)
    max_std = math.sqrt(max(0.0, (mean - xmin) * (xmax - mean)))
    return mean, std, max_std


low, high = [], []
print(f"{'mode':28} {'mean':>10} {'std':>10} {'max_std':>10}  status")
for m in modes:
    mean, std, max_std = analyze(m)
    status = "OK"
    if std < MIN_STD:
        status = "TOO_LOW"
        low.append((m, std, max_std))
    elif std > MAX_STD:
        status = "TOO_HIGH"
        high.append((m, std, max_std))
    print(f"{m:28} {mean:10.4f} {std:10.4f} {max_std:10.4f}  {status}")

print()
print(f"violations: {len(low)+len(high)}  (too_low={len(low)}, too_high={len(high)})")
if low:
    print("too_low:", ", ".join(f"{m}({s:.3f},max{ms:.2f})" for m, s, ms in low))
if high:
    print("too_high:", ", ".join(f"{m}({s:.3f})" for m, s, _ in high))
print("ALL_PASS" if not low and not high else "FAIL")
