import argparse
import csv
import json
import math
import os
import shutil
import time
from typing import Dict, List, Tuple


Row = Dict[str, float]


def load_index(index_path: str) -> dict:
    with open(index_path, "r", encoding="utf-8") as f:
        return json.load(f)


def detect_header(first_row: List[str]) -> bool:
    markers = {"id", "simulation_id", "probability", "weight", "payout_multiplier", "multiplier", "payout"}
    return any(col.strip().lower() in markers for col in first_row)


def read_lookup(path: str) -> Tuple[List[Row], Dict[str, str]]:
    """
    Returns rows and metadata:
    metadata keys: has_header (bool), id_key, weight_key, mult_key
    """
    rows: List[Row] = []

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        first = next(reader)
        has_header = detect_header(first)

        if has_header:
            f.seek(0)
            dreader = csv.DictReader(f)
            headers = dreader.fieldnames
            if not headers:
                raise ValueError(f"Header detected but fieldnames missing in {path}")

            id_key = next((h for h in headers if h.lower() in ["simulation_id", "id", "outcome"]), None)
            weight_key = next((h for h in headers if h.lower() in ["probability", "weight", "prob"]), None)
            mult_key = next((h for h in headers if h.lower() in ["payout_multiplier", "multiplier", "payout"]), None)

            if not all([id_key, weight_key, mult_key]):
                raise ValueError(f"Unsupported CSV header format in {path}: {headers}")

            for row in dreader:
                rows.append(
                    {
                        "id": float(row[id_key]),
                        "weight": float(row[weight_key]),
                        "mult": float(row[mult_key]),
                    }
                )

            return rows, {
                "has_header": "1",
                "id_key": id_key,
                "weight_key": weight_key,
                "mult_key": mult_key,
            }

        if len(first) < 3:
            raise ValueError(f"Headerless CSV requires >=3 columns in {path}")

        rows.append({"id": float(first[0]), "weight": float(first[1]), "mult": float(first[2])})
        for row in reader:
            if not row:
                continue
            rows.append({"id": float(row[0]), "weight": float(row[1]), "mult": float(row[2])})

    return rows, {
        "has_header": "0",
        "id_key": "id",
        "weight_key": "weight",
        "mult_key": "mult",
    }


def write_lookup(path: str, rows: List[Row], meta: Dict[str, str]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        if meta["has_header"] == "1":
            writer.writerow([meta["id_key"], meta["weight_key"], meta["mult_key"]])

        for r in rows:
            # IDs in these tables are integral; preserve integer formatting.
            out_id = int(round(r["id"]))
            out_weight = int(round(r["weight"]))

            mult = r["mult"]
            if abs(mult - round(mult)) < 1e-12:
                out_mult = str(int(round(mult)))
            else:
                out_mult = f"{mult:.12g}"

            writer.writerow([out_id, out_weight, out_mult])


def weighted_mean(rows: List[Row]) -> float:
    total_w = sum(r["weight"] for r in rows)
    if total_w <= 0:
        raise ValueError("Total weight must be > 0")
    return sum(r["weight"] * r["mult"] for r in rows) / total_w


def normalize_to_total(weights: List[float], total: int) -> List[int]:
    s = sum(weights)
    if s <= 0:
        raise ValueError("Cannot normalize non-positive weights")

    raw = [w * total / s for w in weights]
    flo = [int(math.floor(x)) for x in raw]
    rem = total - sum(flo)

    fracs = sorted(((raw[i] - flo[i], i) for i in range(len(raw))), reverse=True)
    for _, i in fracs[:rem]:
        flo[i] += 1

    return flo


def smooth_reweight_integer(
    rows: List[Row],
    target_raw: float,
    tol_raw: float,
    max_iters: int = 4000,
    total_override: int = 0,
) -> Tuple[List[int], bool]:
    """
    Finds integer weights with same total weight that move mean close to target_raw.
    Strategy:
    1) Exponential tilt around original weights (continuous)
    2) Integer rounding preserving total
    3) Local pairwise single-unit moves to enter tolerance band
    """
    n = len(rows)
    orig_w = [max(float(r["weight"]), 0.0) for r in rows]
    mults = [float(r["mult"]) for r in rows]
    total = int(round(sum(orig_w))) if total_override <= 0 else int(total_override)
    if total <= 0:
        raise ValueError("Total weight must be positive")

    # If already within tolerance after integer normalization, keep original.
    current_mean = weighted_mean(rows)
    if abs(current_mean - target_raw) <= tol_raw:
        return [int(round(w)) for w in orig_w], True

    min_m, max_m = min(mults), max(mults)
    if target_raw < min_m - tol_raw or target_raw > max_m + tol_raw:
        return [int(round(w)) for w in orig_w], False

    logw = [math.log(max(w, 1e-15)) for w in orig_w]

    def mean_for_alpha(alpha: float) -> float:
        vals = [logw[i] + alpha * mults[i] for i in range(n)]
        shift = max(vals)
        expv = [math.exp(v - shift) for v in vals]
        den = sum(expv)
        num = sum(expv[i] * mults[i] for i in range(n))
        return num / den

    # Bracket alpha so that mean(alpha) spans target.
    lo, hi = -1.0, 1.0
    m_lo, m_hi = mean_for_alpha(lo), mean_for_alpha(hi)

    guard = 0
    while m_lo > target_raw and guard < 30:
        lo *= 2.0
        m_lo = mean_for_alpha(lo)
        guard += 1

    guard = 0
    while m_hi < target_raw and guard < 30:
        hi *= 2.0
        m_hi = mean_for_alpha(hi)
        guard += 1

    if not (m_lo <= target_raw <= m_hi):
        # Could not bracket due numeric saturation or impossible target.
        return [int(round(w)) for w in orig_w], False

    for _ in range(80):
        mid = 0.5 * (lo + hi)
        m_mid = mean_for_alpha(mid)
        if m_mid < target_raw:
            lo = mid
        else:
            hi = mid

    alpha = 0.5 * (lo + hi)
    vals = [logw[i] + alpha * mults[i] for i in range(n)]
    shift = max(vals)
    cont = [math.exp(v - shift) for v in vals]

    int_w = normalize_to_total(cont, total)

    def mean_from_int(weights: List[int]) -> float:
        num = sum(weights[i] * mults[i] for i in range(n))
        return num / total

    mean_now = mean_from_int(int_w)
    if abs(mean_now - target_raw) <= tol_raw:
        return int_w, True

    # Local improvement: move one weight unit donor -> receiver.
    # Use only small candidate bands per iteration for speed.
    idx_sorted = sorted(range(n), key=lambda i: mults[i])
    band = min(50, n)

    for _ in range(max_iters):
        diff = target_raw - mean_now
        if abs(diff) <= tol_raw:
            return int_w, True

        if diff > 0:
            donors = [i for i in idx_sorted[:band] if int_w[i] > 0]
            receivers = idx_sorted[-band:]
        else:
            donors = [i for i in idx_sorted[-band:] if int_w[i] > 0]
            receivers = idx_sorted[:band]

        best_pair = None
        best_abs = abs(diff)

        for d in donors:
            md = mults[d]
            for r in receivers:
                if r == d:
                    continue
                gain = (mults[r] - md) / total
                new_diff = diff - gain
                cand_abs = abs(new_diff)
                if cand_abs + 1e-15 < best_abs:
                    best_abs = cand_abs
                    best_pair = (d, r)

        if best_pair is None:
            break

        d, r = best_pair
        int_w[d] -= 1
        int_w[r] += 1
        mean_now += (mults[r] - mults[d]) / total

    return int_w, abs(mean_now - target_raw) <= tol_raw


def rebalance_mode(
    publish_path: str,
    mode: dict,
    target_norm: float,
    tol_norm: float,
    write: bool,
    backup_suffix: str,
    max_iters: int,
    max_scale: int,
) -> dict:
    lookup_file = mode["weights"]
    lookup_path = os.path.join(publish_path, lookup_file)

    rows, meta = read_lookup(lookup_path)
    cost = float(mode.get("cost", 1.0))
    if cost <= 0:
        raise ValueError(f"Mode {mode['name']} has non-positive cost {cost}")

    before_raw = weighted_mean(rows)
    before_norm = before_raw / cost

    target_raw = target_norm * cost
    tol_raw = tol_norm * cost

    orig_total = int(round(sum(r["weight"] for r in rows)))
    if orig_total <= 0:
        raise ValueError(f"Mode {mode['name']} has non-positive total weight")

    int_weights = [int(round(r["weight"])) for r in rows]
    solved = False
    scale_used = 1

    for scale in range(1, max(1, max_scale) + 1):
        cand_weights, cand_solved = smooth_reweight_integer(
            rows,
            target_raw=target_raw,
            tol_raw=tol_raw,
            max_iters=max_iters,
            total_override=orig_total * scale,
        )
        cand_rows = [
            {"id": rows[i]["id"], "weight": float(cand_weights[i]), "mult": rows[i]["mult"]}
            for i in range(len(rows))
        ]
        cand_after_norm = weighted_mean(cand_rows) / cost

        if abs(cand_after_norm - target_norm) <= tol_norm:
            int_weights = cand_weights
            solved = True
            scale_used = scale
            break

        if scale == 1:
            int_weights = cand_weights
            solved = cand_solved
            scale_used = 1

    new_rows: List[Row] = []
    for i, r in enumerate(rows):
        new_rows.append({"id": r["id"], "weight": float(int_weights[i]), "mult": r["mult"]})

    after_raw = weighted_mean(new_rows)
    after_norm = after_raw / cost
    pass_after = abs(after_norm - target_norm) <= tol_norm

    l1_change = int(
        sum(abs(int(round(new_rows[i]["weight"] - rows[i]["weight"]))) for i in range(len(rows)))
    )

    if write:
        backup_path = lookup_path + backup_suffix
        if not os.path.exists(backup_path):
            shutil.copyfile(lookup_path, backup_path)
        write_lookup(lookup_path, new_rows, meta)

    return {
        "mode": mode["name"],
        "lookup": lookup_file,
        "cost": cost,
        "before_norm": before_norm,
        "after_norm": after_norm,
        "target_norm": target_norm,
        "tol_norm": tol_norm,
        "pass_before": abs(before_norm - target_norm) <= tol_norm,
        "pass_after": pass_after,
        "solver_converged": solved,
        "scale_used": scale_used,
        "l1_weight_change": l1_change,
    }


def parse_mode_filter(raw: str) -> set:
    if not raw:
        return set()
    return {m.strip() for m in raw.split(",") if m.strip()}


def main() -> None:
    parser = argparse.ArgumentParser(description="Auto-rebalance lookup table weights to hit target RTP")
    parser.add_argument("--path", required=True, help="Path to publish_files")
    parser.add_argument("--target-rtp", type=float, default=96.0, help="Target normalized RTP")
    parser.add_argument("--tol", type=float, default=0.01, help="Absolute tolerance on normalized RTP")
    parser.add_argument("--modes", default="", help="Comma-separated mode names; default is all modes")
    parser.add_argument("--write", action="store_true", help="Write updated lookup tables in place")
    parser.add_argument("--backup-suffix", default="", help="Backup suffix (default: timestamped .bak)")
    parser.add_argument("--max-iters", type=int, default=4000, help="Max local refinement iterations per mode")
    parser.add_argument(
        "--max-scale",
        type=int,
        default=200,
        help="Max multiplier for total integer weight (helps hit tight RTP tolerances)",
    )
    parser.add_argument("--report-json", default="", help="Optional path to save JSON report")

    args = parser.parse_args()

    publish_path = args.path
    index_path = os.path.join(publish_path, "index.json")
    index = load_index(index_path)

    requested = parse_mode_filter(args.modes)

    suffix = args.backup_suffix
    if not suffix:
        suffix = f".bak_{time.strftime('%Y%m%d_%H%M%S')}"

    report: List[dict] = []

    for mode in index.get("modes", []):
        mode_name = mode.get("name", "")
        if requested and mode_name not in requested:
            continue

        row = rebalance_mode(
            publish_path=publish_path,
            mode=mode,
            target_norm=args.target_rtp,
            tol_norm=args.tol,
            write=args.write,
            backup_suffix=suffix,
            max_iters=args.max_iters,
            max_scale=args.max_scale,
        )
        report.append(row)

    print("mode,before_norm,after_norm,target,tol,pass_before,pass_after,solver_converged,scale_used,l1_weight_change,lookup")
    for r in report:
        print(
            f"{r['mode']},{r['before_norm']:.6f},{r['after_norm']:.6f},{r['target_norm']:.6f},{r['tol_norm']:.6f},"
            f"{r['pass_before']},{r['pass_after']},{r['solver_converged']},{r['scale_used']},{r['l1_weight_change']},{r['lookup']}"
        )

    all_pass = bool(report) and all(r["pass_after"] for r in report)
    print(f"all_modes_pass_after: {all_pass}")
    print(f"write_applied: {args.write}")
    if args.write:
        print(f"backup_suffix: {suffix}")

    if args.report_json:
        with open(args.report_json, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"report_json: {args.report_json}")


if __name__ == "__main__":
    main()
