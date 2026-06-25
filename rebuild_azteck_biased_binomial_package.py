"""Biased-binomial Azteck Plinko package builder.

Model
-----
Each mode is a biased Plinko: a ball falls through ``N`` rows and steps RIGHT with
per-mode probability ``p_i`` (LEFT with ``1 - p_i``). The landing bucket is
``X ~ Binomial(N, p_i)``. Multipliers follow a monotone geometric ladder

    M(k) = a * r**k ,   k = 0 .. N ,   with the jackpot  M(N) = W (= max_win).

With this ladder the binomial theorem gives closed forms

    RTP        = a / cost * (1 - p + p*r)**N
    E[m**2]    = a**2     * (1 - p + p*r**2)**N

Imposing the two hard constraints (max_win and RTP = 96.05%) fixes

    a  = W / r**N
    p  = (c1*r - 1) / (r - 1) ,   c1 = (R / W)**(1/N) ,   R = TARGET_RTP * cost

which leaves the ladder steepness ``r`` as the single free knob. STD increases
monotonically in ``r``; we bisect ``r`` so that STD lands inside [0.6, 60].

The resulting (asymmetric) biased binomial pmf is encoded as integer lookup
weights at high precision, exactly like the existing static lookup tables.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import shutil
from pathlib import Path

import zstandard as zstd

SRC = Path("math-sdk/games/azteck_plinko_final")
DEST = Path("math-sdk/games/azteck_plinko_biased_binomial")
DEST_PUBLISH = Path("math-sdk/games/azteck_plinko_biased_binomial_publish")

VERSION = "0.0.7-biased-binomial"
PAYOUT_SCALE = 100          # payout_raw = round(multiplier * 100)
WEIGHT_SCALE = 10**9        # integer lookup weight = round(pmf * WEIGHT_SCALE)
TARGET_RTP = 0.9605
STD_LO, STD_HI = 0.6, 60.0
MAX_PROB_GE_5000 = 0.0099

# Desired STD per difficulty (clamped into the feasible band per mode).
DESIRED_STD = {"low": 1.5, "medium": 6.0, "high": 20.0, "expert": 45.0}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# --------------------------------------------------------------------------- #
# Closed-form biased-binomial / geometric-ladder solver
# --------------------------------------------------------------------------- #
def _p_of_r(r: float, c1: float) -> float:
    return (c1 * r - 1.0) / (r - 1.0)


def _std_of_r(r: float, N: int, W: float, cost: float, c1: float) -> float:
    """Exact (pre-rounding) STD of the net multiplier m/cost for steepness r."""
    p = _p_of_r(r, c1)
    e_m2 = (W ** 2) * (((1.0 - p) + p * r * r) / (r * r)) ** N
    var = e_m2 / (cost ** 2) - TARGET_RTP ** 2
    return math.sqrt(max(0.0, var))


def _rows_for_r(N: int, W: float, cost: float, c1: float, r: float) -> tuple[float, float, list[tuple[int, int, int]]]:
    p = _p_of_r(r, c1)
    a = W / r ** N
    return p, a, build_rows(N, W, p, r, a, cost)


def _prob_ge_threshold(rows: list[tuple[int, int, int]], threshold_raw: int) -> float:
    total_weight = float(sum(weight for _, weight, _ in rows))
    if total_weight <= 0:
        return 0.0
    return sum(weight for _, weight, payout_raw in rows if payout_raw >= threshold_raw) / total_weight


def _prob_ge_threshold_exact(N: int, p: float, a: float, r: float, threshold_raw: int) -> float:
    total = 0.0
    for k in range(N + 1):
        payout_raw = int(round(a * (r ** k) * PAYOUT_SCALE))
        if payout_raw >= threshold_raw:
            total += math.comb(N, k) * (p ** k) * ((1.0 - p) ** (N - k))
    return total


def solve_mode(N: int, W: float, cost: float, difficulty: str) -> tuple[float, float, float, float]:
    """Return (p, r, a, target_std) for one mode."""
    R = TARGET_RTP * cost
    c1 = (R / W) ** (1.0 / N)            # < 1 since R < W
    r_min = 1.0 / c1                     # p -> 0+ as r -> r_min+

    # Limiting STD as r -> infinity (jackpot carries all RTP).
    std_max = math.sqrt(max(0.0, TARGET_RTP * W / cost - TARGET_RTP ** 2))
    target = DESIRED_STD[difficulty]
    target = min(target, 0.95 * std_max, STD_HI)
    target = max(target, STD_LO)

    # Bisect r in (r_min, r_hi) so that STD(r) == target (STD increasing in r).
    lo = r_min * (1.0 + 1e-9)
    hi = r_min * 2.0
    while _std_of_r(hi, N, W, cost, c1) < target and hi < 1e9:
        hi *= 2.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if _std_of_r(mid, N, W, cost, c1) < target:
            lo = mid
        else:
            hi = mid
    r = 0.5 * (lo + hi)
    p = _p_of_r(r, c1)
    a = W / r ** N

    if _prob_ge_threshold_exact(N, p, a, r, 5000 * PAYOUT_SCALE) > MAX_PROB_GE_5000:
        hi = r
        lo = r_min * (1.0 + 1e-9)
        lo_p = _p_of_r(lo, c1)
        lo_a = W / lo ** N
        if _prob_ge_threshold_exact(N, lo_p, lo_a, lo, 5000 * PAYOUT_SCALE) > MAX_PROB_GE_5000:
            raise ValueError(f"Unable to satisfy 5K probability cap for N={N}, W={W}, cost={cost}")

        for _ in range(120):
            mid = 0.5 * (lo + hi)
            mid_p = _p_of_r(mid, c1)
            mid_a = W / mid ** N
            if _prob_ge_threshold_exact(N, mid_p, mid_a, mid, 5000 * PAYOUT_SCALE) > MAX_PROB_GE_5000:
                hi = mid
            else:
                lo = mid

        r = 0.5 * (lo + hi)
        p = _p_of_r(r, c1)
        a = W / r ** N

    return p, r, a, target


def build_rows(N: int, W: float, p: float, r: float, a: float, cost: float) -> list[tuple[int, int, int]]:
    """Build (sim_id, integer_weight, payout_raw) rows and correct RTP rounding drift."""
    # Biased-binomial pmf -> integer weights.
    pmf = [math.comb(N, k) * (p ** k) * ((1.0 - p) ** (N - k)) for k in range(N + 1)]
    weights = [max(0, int(round(w * WEIGHT_SCALE))) for w in pmf]

    payouts = [int(round(a * (r ** k) * PAYOUT_SCALE)) for k in range(N + 1)]
    payouts[N] = int(round(W * PAYOUT_SCALE))      # guarantee exact max_win

    # Correct RTP rounding drift by nudging ONE high-precision weight (1e9 granularity),
    # which leaves payouts, max_win, monotonicity and STD essentially untouched.
    # Solve target = (S + d*p_j) / ((T + d) * SCALE_C) for integer d, where
    # S = sum(w*payout), T = sum(w), SCALE_C = TARGET_RTP*cost*PAYOUT_SCALE handled below.
    K = TARGET_RTP * cost * PAYOUT_SCALE
    # pick a bucket whose payout is far from K (stable denominator) with weight headroom.
    j = max((k for k in range(N + 1) if weights[k] > 0),
            key=lambda k: abs(K - payouts[k]), default=int(max(range(N + 1), key=lambda k: payouts[k])))
    S = sum(w * pay for w, pay in zip(weights, payouts))
    T = sum(weights)
    denom = K - payouts[j]
    if abs(denom) > 1e-9:
        d = int(round((S - K * T) / denom))
        weights[j] = max(0, weights[j] + d)

    return [(k, weights[k], payouts[k]) for k in range(N + 1)]


def write_lookup(path: Path, rows: list[tuple[int, int, int]]) -> bytes:
    payload = "\n".join(f"{sid},{w},{p}" for sid, w, p in rows) + "\n"
    data = payload.encode("utf-8")
    path.write_bytes(data)
    return data


def write_books(path: Path, mode_name: str, mode_type: str, difficulty: str,
                n_rows: int, p_right: float, rows: list[tuple[int, int, int]]) -> bytes:
    lines = []
    for sid, weight, payout_raw in rows:
        obj = {
            "id": sid,
            "mode": mode_name,
            "modeType": mode_type,
            "difficulty": difficulty,
            "rows": n_rows,
            "pRight": round(p_right, 8),
            "weight": int(weight),
            "outcomeBucketId": int(sid),
            "payoutMultiplier": int(payout_raw),
            "criteria": "biased_binomial_static_outcome",
            "events": [{"type": "payout", "amount": int(payout_raw), "currency": "credit", "id": 1}],
        }
        lines.append(json.dumps(obj, separators=(",", ":"), ensure_ascii=False))
    data = zstd.ZstdCompressor(level=19).compress(("\n".join(lines) + "\n").encode("utf-8"))
    path.write_bytes(data)
    return data


def mode_metrics(rows: list[tuple[int, int, int]], cost: float) -> tuple[float, float, float]:
    total_weight = float(sum(w for _, w, _ in rows))
    mults = [p / PAYOUT_SCALE for _, _, p in rows]
    probs = [w / total_weight for _, w, _ in rows]
    rtp = sum(pr * m for pr, m in zip(probs, mults)) / cost
    e_x2 = sum(pr * (m / cost) ** 2 for pr, m in zip(probs, mults))
    std = math.sqrt(max(0.0, e_x2 - rtp ** 2))
    return rtp, std, max(mults)


def rebuild() -> None:
    if DEST.exists():
        shutil.rmtree(DEST)
    shutil.copytree(SRC, DEST)

    publish_dir = DEST / "artifacts" / "publish_files"
    config_dir = DEST / "artifacts" / "configs"
    for child in publish_dir.iterdir():
        if child.is_file():
            child.unlink()

    src_index = json.loads((SRC / "artifacts" / "publish_files" / "index.json").read_text(encoding="utf-8"))

    index_modes: list[dict] = []
    bookshelf: list[dict] = []
    fe_modes: list[dict] = []

    force_bytes = b"{}\n"
    (publish_dir / "force.json").write_bytes(force_bytes)
    force_sha = sha256_bytes(force_bytes)

    report: list[tuple[str, float, float, float, float]] = []

    for mode in src_index["modes"]:
        name = mode["name"]
        mode_type = mode["mode_type"]
        difficulty = mode["difficulty"]
        N = int(mode["rows"])
        cost = float(mode["cost"])
        W = float(mode["max_win"])
        diff_key = difficulty.lower()

        p, r, a, target_std = solve_mode(N, W, cost, diff_key)
        rows = build_rows(N, W, p, r, a, cost)

        lookup_file = f"lookUpTable_{name}_0.csv"
        books_file = f"books_{name}.jsonl.zst"
        force_record_file = f"force_record_{name}.json"

        lookup_bytes = write_lookup(publish_dir / lookup_file, rows)
        books_bytes = write_books(publish_dir / books_file, name, mode_type, difficulty, N, p, rows)
        force_record_bytes = b"[]\n"
        (publish_dir / force_record_file).write_bytes(force_record_bytes)

        rtp, std, max_win = mode_metrics(rows, cost)
        report.append((name, p, rtp, std, max_win))

        index_modes.append({
            "name": name, "mode_type": mode_type, "difficulty": difficulty, "rows": N,
            "cost": cost, "p_right": round(p, 8), "rtp": round(rtp, 6),
            "std": round(std, 6), "max_win": round(max_win, 4),
            "weights": lookup_file, "events": books_file, "status": "biased-binomial",
        })
        bookshelf.append({
            "name": name, "tables": [{"file": lookup_file, "sha256": sha256_bytes(lookup_bytes)}],
            "cost": cost, "rtp": round(rtp, 6), "std": round(std, 6), "bookLength": 1_000_000,
            "feature": True, "autoEndRoundDisabled": False, "buyBonus": mode_type == "100balls",
            "maxWin": round(max_win, 4),
            "booksFile": {"file": books_file, "sha256": sha256_bytes(books_bytes)},
            "forceFile": {"file": force_record_file, "sha256": sha256_bytes(force_record_bytes)},
        })
        fe_modes.append({"name": name, "cost": cost, "maxWin": round(max_win, 4)})

    index_payload = {
        "game_id": "azteck_plinko_biased_binomial", "version": VERSION,
        "target_rtp": TARGET_RTP, "std_band": [STD_LO, STD_HI], "modes": index_modes,
    }
    index_bytes = json.dumps(index_payload, indent=2).encode("utf-8")
    (publish_dir / "index.json").write_bytes(index_bytes)

    cfg_template = json.loads((SRC / "artifacts" / "configs" / "config.json").read_text(encoding="utf-8"))
    fe_template = json.loads((SRC / "artifacts" / "configs" / "fe_config.json").read_text(encoding="utf-8"))

    fe_template["gameId"] = "azteck_plinko_biased_binomial"
    fe_template["version"] = VERSION
    fe_template["modes"] = fe_modes
    fe_bytes = json.dumps(fe_template, indent=4).encode("utf-8")
    (config_dir / "fe_config.json").write_bytes(fe_bytes)

    cfg_template["workingName"] = "azteck_plinko_biased_binomial"
    cfg_template["gameID"] = "azteck_plinko_biased_binomial"
    cfg_template["bookShelfConfig"] = bookshelf
    cfg_template["frontendConfig"] = {"file": "fe_config.json", "sha256": sha256_bytes(fe_bytes)}
    cfg_template["standardForceFile"] = {"file": "force.json", "sha256": force_sha}
    cfg_bytes = json.dumps(cfg_template, indent=4).encode("utf-8")
    (config_dir / "config.json").write_bytes(cfg_bytes)
    (DEST / "config.json").write_bytes(cfg_bytes)
    (DEST / "fe_config.json").write_bytes(fe_bytes)

    if DEST_PUBLISH.exists():
        shutil.rmtree(DEST_PUBLISH)
    DEST_PUBLISH.mkdir(parents=True, exist_ok=True)
    for item in publish_dir.iterdir():
        shutil.copy2(item, DEST_PUBLISH / item.name)
    shutil.copy2(config_dir / "config.json", DEST_PUBLISH / "config.json")
    shutil.copy2(config_dir / "fe_config.json", DEST_PUBLISH / "fe_config.json")

    rtps = [m["rtp"] for m in index_modes]
    stds = [m["std"] for m in index_modes]
    out_rtp = [m["name"] for m in index_modes if abs(m["rtp"] - TARGET_RTP) > 0.01]
    out_std = [m["name"] for m in index_modes if not (STD_LO <= m["std"] <= STD_HI)]
    print(f"Generated package:  {DEST}")
    print(f"Publish folder:     {DEST_PUBLISH}")
    print(f"Modes:              {len(index_modes)}")
    print(f"RTP range:          {min(rtps):.6f}..{max(rtps):.6f}  (out-of-tol: {len(out_rtp)})")
    print(f"STD range:          {min(stds):.4f}..{max(stds):.4f}  (out-of-band: {len(out_std)})")
    print(f"p_right range:      {min(m['p_right'] for m in index_modes):.4f}.."
          f"{max(m['p_right'] for m in index_modes):.4f}")
    if out_rtp:
        print("  RTP out:", out_rtp)
    if out_std:
        print("  STD out:", out_std)


if __name__ == "__main__":
    rebuild()
