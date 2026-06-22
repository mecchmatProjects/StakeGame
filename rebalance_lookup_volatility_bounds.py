from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Rebalance lookup weights to keep normalized std within bounds")
    p.add_argument("--root", default="math-sdk/games/azteck_plinko_final", help="Package root")
    p.add_argument("--target-rtp", type=float, default=0.9605, help="Target RTP")
    p.add_argument("--std-min", type=float, default=0.6, help="Minimum normalized std")
    p.add_argument("--std-max", type=float, default=50.0, help="Maximum normalized std")
    p.add_argument("--payout-scale", type=float, default=100.0, help="Lookup payout scale")
    return p.parse_args()


def read_lookup(path: Path) -> list[tuple[int, int, int]]:
    rows: list[tuple[int, int, int]] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        for r in csv.reader(f):
            if len(r) < 3:
                continue
            rows.append((int(float(r[0])), int(float(r[1])), int(float(r[2]))))
    return rows


def write_lookup(path: Path, rows: list[tuple[int, int, int]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        for sid, wt, raw in rows:
            w.writerow([sid, wt, raw])


def stats_from_weights(raws_scaled: list[float], weights: list[int], cost: float) -> tuple[float, float]:
    total = float(sum(weights))
    if total <= 0:
        return 0.0, 0.0
    probs = [w / total for w in weights]
    mean = sum(p * x for p, x in zip(probs, raws_scaled))
    var = sum(p * ((x - mean) ** 2) for p, x in zip(probs, raws_scaled))
    std_norm = (math.sqrt(var) / cost) if cost > 0 else 0.0
    rtp = (mean / cost) if cost > 0 else 0.0
    return rtp, std_norm


def normalize_to_total(values: list[float], total: int) -> list[int]:
    s = sum(values)
    if s <= 0:
        raise ValueError("Cannot normalize non-positive values")
    raw = [v * total / s for v in values]
    flo = [int(math.floor(x)) for x in raw]
    rem = total - sum(flo)
    fracs = sorted(((raw[i] - flo[i], i) for i in range(len(raw))), reverse=True)
    for _, i in fracs[:rem]:
        flo[i] += 1
    return flo


def solve_probs_with_moments(
    x: list[float],
    p0: list[float],
    mean_target: float,
    want_std: float,
    increase_std: bool,
) -> list[float]:
    eps = 1e-18
    logp0 = [math.log(max(p, eps)) for p in p0]

    def probs_for(a: float, b: float) -> list[float]:
        z = [logp0[i] + a * x[i] + b * (x[i] ** 2) for i in range(len(x))]
        mz = max(z)
        e = [math.exp(v - mz) for v in z]
        s = sum(e)
        return [v / s for v in e]

    def mean_for(a: float, b: float) -> float:
        p = probs_for(a, b)
        return sum(pi * xi for pi, xi in zip(p, x))

    def solve_a_for_b(b: float) -> list[float]:
        lo, hi = -1.0, 1.0
        m_lo = mean_for(lo, b)
        m_hi = mean_for(hi, b)
        g = 0
        while m_lo > mean_target and g < 50:
            lo *= 2.0
            m_lo = mean_for(lo, b)
            g += 1
        g = 0
        while m_hi < mean_target and g < 50:
            hi *= 2.0
            m_hi = mean_for(hi, b)
            g += 1
        if not (m_lo <= mean_target <= m_hi):
            return probs_for(0.0, b)
        for _ in range(120):
            mid = (lo + hi) / 2.0
            m_mid = mean_for(mid, b)
            if m_mid < mean_target:
                lo = mid
            else:
                hi = mid
        return probs_for((lo + hi) / 2.0, b)

    def std_of_probs(p: list[float]) -> float:
        m = sum(pi * xi for pi, xi in zip(p, x))
        v = sum(pi * ((xi - m) ** 2) for pi, xi in zip(p, x))
        return math.sqrt(v)

    p_base = solve_a_for_b(0.0)
    s_base = std_of_probs(p_base)

    if increase_std and s_base >= want_std:
        return p_base
    if (not increase_std) and s_base <= want_std:
        return p_base

    if increase_std:
        lo, hi = 0.0, 1.0
        p_hi = solve_a_for_b(hi)
        s_hi = std_of_probs(p_hi)
        guard = 0
        while s_hi < want_std and guard < 40:
            hi *= 2.0
            p_hi = solve_a_for_b(hi)
            s_hi = std_of_probs(p_hi)
            guard += 1
    else:
        hi, lo = 0.0, -1.0
        p_lo = solve_a_for_b(lo)
        s_lo = std_of_probs(p_lo)
        guard = 0
        while s_lo > want_std and guard < 40:
            lo *= 2.0
            p_lo = solve_a_for_b(lo)
            s_lo = std_of_probs(p_lo)
            guard += 1

    for _ in range(100):
        mid = (lo + hi) / 2.0
        p_mid = solve_a_for_b(mid)
        s_mid = std_of_probs(p_mid)
        if increase_std:
            if s_mid < want_std:
                lo = mid
            else:
                hi = mid
        else:
            if s_mid > want_std:
                hi = mid
            else:
                lo = mid

    return solve_a_for_b((lo + hi) / 2.0)


def main() -> int:
    args = parse_args()
    root = Path(args.root).resolve()
    publish = root / "artifacts" / "publish_files"
    index = json.loads((publish / "index.json").read_text(encoding="utf-8"))

    mode_results: list[dict] = []

    for mode in index.get("modes", []):
        if not isinstance(mode, dict):
            continue
        name = mode.get("name")
        lookup = mode.get("weights")
        if not isinstance(name, str) or not isinstance(lookup, str):
            continue

        path = publish / lookup
        rows = read_lookup(path)
        if not rows:
            continue

        cost = float(mode.get("cost", 1.0))
        x = [raw / args.payout_scale for _, _, raw in rows]
        w = [wt for _, wt, _ in rows]
        total = sum(w)
        p0 = [wi / total for wi in w]

        rtp_before, std_before = stats_from_weights(x, w, cost)
        target_mean = args.target_rtp * cost

        needs_up = std_before < args.std_min
        needs_down = std_before > args.std_max

        updated = False
        if needs_up or needs_down:
            desired_std = (args.std_min + 0.01) * cost if needs_up else (args.std_max - 0.2) * cost
            p_cont = solve_probs_with_moments(
                x=x,
                p0=p0,
                mean_target=target_mean,
                want_std=desired_std,
                increase_std=needs_up,
            )

            totals_to_try = [total, total * 2, total * 5, total * 10]
            if needs_down:
                totals_to_try.extend([total * 20, total * 50])

            best_rows = rows
            best_score = 1e18

            for t in totals_to_try:
                w_new = normalize_to_total(p_cont, int(t))
                rtp_after, std_after = stats_from_weights(x, w_new, cost)
                bounds_penalty = 0.0
                if std_after < args.std_min:
                    bounds_penalty += (args.std_min - std_after) * 1000
                if std_after > args.std_max:
                    bounds_penalty += (std_after - args.std_max) * 1000
                score = bounds_penalty + abs(rtp_after - args.target_rtp)
                if score < best_score:
                    best_score = score
                    best_rows = [(rows[i][0], int(w_new[i]), rows[i][2]) for i in range(len(rows))]
                if bounds_penalty == 0 and abs(rtp_after - args.target_rtp) <= 0.0005:
                    break

            rows = best_rows
            updated = True

        rtp_after, std_after = stats_from_weights(x, [wt for _, wt, _ in rows], cost)
        if updated:
            write_lookup(path, rows)

        mode_results.append(
            {
                "name": name,
                "lookup": lookup,
                "rtp_before": rtp_before,
                "std_before": std_before,
                "rtp_after": rtp_after,
                "std_after": std_after,
                "weight_sum_after": sum(wt for _, wt, _ in rows),
                "updated": updated,
                "in_range_after": (args.std_min <= std_after <= args.std_max),
            }
        )

    out = {
        "std_min": args.std_min,
        "std_max": args.std_max,
        "target_rtp": args.target_rtp,
        "updated_modes": sum(1 for r in mode_results if r["updated"]),
        "out_of_range_after": [r for r in mode_results if not r["in_range_after"]],
        "min_std_after": min((r["std_after"] for r in mode_results), default=None),
        "max_std_after": max((r["std_after"] for r in mode_results), default=None),
        "modes": mode_results,
    }

    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
