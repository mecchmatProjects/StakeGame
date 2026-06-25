"""In-place rebuild of azteck_plinko_final using the Stake Engine bucket-first model.

Model (per Plinko_updates.txt)
------------------------------
For each mode (difficulty d, rows N):

    outcome k ~ P_d^N(k),      Win = bet * M_d^N(k),
    RTP = sum_k P_d^N(k) * M_d^N(k) / cost = TARGET_RTP.

The multipliers ``M(k)`` are the FIXED authoritative U-shaped tables (kept in true
bucket order 0..N). The probability distribution ``P(k)`` is the design variable and
is chosen SYMMETRIC so that equal-multiplier mirror buckets carry equal mass:

    P(k) proportional to  C(N, k) * exp(theta * |k - N/2|)

This is the physical Plinko binomial prior (C(N,k)) tempered by a single symmetric
knob ``theta``. ``theta`` is solved by bisection so the RTP equation holds exactly.
``E[M]`` is monotone increasing in ``theta`` (more edge mass -> higher payout), and
since the centre multiplier < TARGET_RTP*cost < edge multiplier for every mode, a
unique theta always exists.

The script regenerates, from this single source, every dependent artifact so they all
stay consistent:
  * inputs/azteck_plinko_probability_tables.csv
  * artifacts/publish_files/lookUpTable_<mode>_0.csv
  * artifacts/publish_files/books_<mode>.jsonl.zst
  * artifacts/publish_files/index.json
Config, force files, workbook and docs are refreshed by the existing downstream
scripts (gen_sdk_config.py, build_static_game_full_xlsx.py, validate_static_package.py).
"""

from __future__ import annotations

import csv
import json
import math
import zlib
from pathlib import Path
from typing import Sequence

import numpy as np
import zstandard as zstd

ROOT = Path("math-sdk/games/azteck_plinko_final")
PUBLISH = ROOT / "artifacts" / "publish_files"
INPUTS = ROOT / "inputs"

VERSION = "0.0.6-std-bounded-symmetric-design"
PAYOUT_SCALE = 100
# High resolution so that extreme-multiplier (up to 100000x) jackpot buckets keep
# enough weight precision to hold RTP; a coarse scale rounds the tiny tail weight and
# blows up the RTP of high-max-win expert modes.
WEIGHT_SCALE = 1_000_000_000_000
TARGET_RTP = 0.9605
BASE_STD = 0.6
MIN_STD = 0.6
MAX_STD = 60.0
# Aim slightly above the floor/below the ceiling so downstream integer rounding, symmetry
# enforcement, RTP correction and max-win uplift cannot nudge a mode back out of the band.
STD_FLOOR_TARGET = 0.70
STD_CEIL_TARGET = 58.0
MAX_WIN_MAX_ODDS = 20_000_000.0  # Max advertised max-win odds: <= 1 in 20.00M
MAX_MULTIPLIER = 100_000.0  # Marketing/live cap on payout multiplier (<= 100,000x)
TAIL_THRESHOLD_RAW = 5000 * PAYOUT_SCALE  # 5000x cap reference (informational)

# True 100-ball buy-feature model.
# Product contract: feature costs 99x bet and drops 100 independent balls.
# Settlement is synthesized from those 100 balls and calibrated so package RTP remains target.
N_BALLS = 100
MC_SAMPLES = 100_000
MC_SEED = 20_240_624
BUY100_COST = 99.0
# EV-safe rebalance across all difficulties. Alpha<1 flattens tails while an
# exponential tilt restores the target mean exactly.
REBALANCE_ALPHA_BY_DIFFICULTY: dict[str, float] = {
    "low": 0.92,
    "medium": 0.88,
    "high": 0.82,
    "expert": 0.74,
}
BUY100_REBALANCE_ALPHA_BY_DIFFICULTY: dict[str, float] = {
    "low": 0.88,
    "medium": 0.82,
    "high": 0.74,
    "expert": 0.58,
}
BUY100_WEIGHT_MULTIPLIER = 1_000
# Split high-frequency payout bins into several replay variants to avoid repeated
# identical 100-ball trajectories for the same payout multiplier.
BUY100_MAX_VARIANTS_PER_PAYOUT = 24
BUY100_VARIANT_BUCKET = 8_000


def load_paytables() -> dict[tuple[str, str, int], list[float]]:
    """Return {(mode_type, difficulty_lower, rows): [M0..MN]} in bucket order."""
    collected: dict[tuple[str, str, int], list[tuple[int, float]]] = {}
    for mode_type, file_name in [
        ("normal", "azteck_plinko_paytables_normal.csv"),
        ("100balls", "azteck_plinko_paytables_100balls.csv"),
    ]:
        with (INPUTS / file_name).open("r", encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                bucket_raw = str(row["bucket_index"]).strip()
                if not bucket_raw.lstrip("-").isdigit():
                    continue  # skip any non-integer marker rows
                key = (mode_type, row["difficulty"].strip().lower(), int(row["rows"]))
                collected.setdefault(key, []).append((int(bucket_raw), float(row["multiplier"])))

    ordered: dict[tuple[str, str, int], list[float]] = {}
    for key, rows in collected.items():
        rows.sort(key=lambda x: x[0])
        ordered[key] = [m for _, m in rows]
    return ordered


def symmetric_pmf(multipliers: list[float], theta: float) -> list[float]:
    """Symmetric tempered-binomial pmf for a given theta."""
    n = len(multipliers) - 1
    center = n / 2.0
    log_w = [
        math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1) + theta * abs(k - center)
        for k in range(n + 1)
    ]
    peak = max(log_w)
    weights = [math.exp(lw - peak) for lw in log_w]
    total = math.fsum(weights)
    return [w / total for w in weights]


def _add_symmetric(weights: list[int], indices: list[int], amount: int) -> int:
    """Add `amount` weight spread evenly across `indices`, rounding up to a multiple of
    len(indices) so a mirrored index set stays exactly symmetric. Returns the amount added."""
    if amount <= 0 or not indices:
        return 0
    k = len(indices)
    amount = ((amount + k - 1) // k) * k
    per = amount // k
    for i in indices:
        weights[i] += per
    return amount


def _enforce_max_win_achievability(weights: list[int], payouts: list[int], max_odds: float,
                                   cost: float) -> None:
    """Ensure the advertised max win is realistically obtainable: odds <= max_odds, while
    keeping RTP on target.

    Raising max-payout (edge) weight alone meets the odds cap but inflates RTP, and the
    interior buckets are pinned at weight 1 so the follow-up RTP correction cannot pull it
    back. To stay at target we simultaneously add compensating weight to the minimum-payout
    (centre) buckets. Solving the two requirements together:

        odds:  (T + x + y) <= max_odds * (M + x)
        RTP :  (Q + x*Pmax + y*Pc) / (T + x + y) == Q / T   ->   y = x * (T*Pmax - Q)/(Q - T*Pc)

    where x is the weight added to the max edges and y to the centre. We round both up and
    let the second `_correct_rtp` pass remove the tiny integer residual (centre now carries
    enough weight for that pass to nudge RTP upward to exactly target).
    """
    if max_odds <= 1.0:
        return

    total = sum(weights)
    max_payout = max(payouts)
    min_payout = min(payouts)
    max_idx = [i for i, p in enumerate(payouts) if p == max_payout]
    cur_max = sum(weights[i] for i in max_idx)
    if cur_max <= 0:
        return
    if total <= max_odds * cur_max:
        return  # already achievable

    num = sum(w * p for w, p in zip(weights, payouts))
    center_idx = [i for i, p in enumerate(payouts) if p == min_payout and i not in max_idx]

    # Ratio of centre compensation to edge uplift that holds RTP fixed.
    denom_r = float(num) - float(total) * float(min_payout)
    r = 0.0
    if center_idx and denom_r > 0:
        r = (float(total) * float(max_payout) - float(num)) / denom_r

    denom_x = max_odds - 1.0 - r
    if denom_x <= 0:
        # Compensation would overwhelm the odds budget; fall back to edge-only minimal lift.
        r = 0.0
        denom_x = max_odds - 1.0

    numerator = float(total) - max_odds * float(cur_max)
    if numerator <= 0:
        return
    x_required = int(math.ceil(numerator / denom_x))
    if x_required <= 0:
        return

    x_added = _add_symmetric(weights, max_idx, x_required)
    if r > 0 and center_idx:
        y_required = int(math.ceil(r * x_added))
        _add_symmetric(weights, center_idx, y_required)


def expected_multiplier(multipliers: list[float], theta: float) -> float:
    pmf = symmetric_pmf(multipliers, theta)
    return math.fsum(p * m for p, m in zip(pmf, multipliers))


def solve_theta(multipliers: list[float], target_ev: float) -> float:
    """Bisect theta so expected_multiplier == target_ev (EV increasing in theta)."""
    lo, hi = -200.0, 200.0
    if expected_multiplier(multipliers, lo) >= target_ev:
        return lo
    if expected_multiplier(multipliers, hi) <= target_ev:
        return hi
    for _ in range(300):
        mid = 0.5 * (lo + hi)
        if expected_multiplier(multipliers, mid) < target_ev:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def pmf_stats(multipliers: list[float], cost: float, pmf: list[float]) -> tuple[float, float]:
    values = [m / cost for m in multipliers]
    mean = math.fsum(p * x for p, x in zip(pmf, values))
    e_x2 = math.fsum(p * x * x for p, x in zip(pmf, values))
    return mean, math.sqrt(max(0.0, e_x2 - mean * mean))


def ev_preserving_flatten_pmf(base_pmf: list[float], multipliers: list[float],
                              target_mean: float, alpha: float) -> list[float]:
    """Flatten pmf with exponent ``alpha`` and re-tilt to preserve EV exactly."""
    alpha = float(alpha)
    if alpha >= 0.999999:
        s = math.fsum(base_pmf)
        return [p / s for p in base_pmf]

    prior = [max(p, 1e-300) ** alpha for p in base_pmf]
    s_prior = math.fsum(prior)
    prior = [p / s_prior for p in prior]

    def mean_at(lmb: float) -> float:
        x = [lmb * m for m in multipliers]
        peak = max(x)
        w = [pr * math.exp(xx - peak) for pr, xx in zip(prior, x)]
        s_w = math.fsum(w)
        q = [ww / s_w for ww in w]
        return math.fsum(qq * mm for qq, mm in zip(q, multipliers))

    lo, hi = -60.0, 60.0
    m_lo, m_hi = mean_at(lo), mean_at(hi)
    for _ in range(8):
        if m_lo <= target_mean <= m_hi:
            break
        if target_mean < m_lo:
            hi = lo
            lo *= 2.0
        else:
            lo = hi
            hi *= 2.0
        m_lo, m_hi = mean_at(lo), mean_at(hi)

    if not (m_lo <= target_mean <= m_hi):
        s = math.fsum(base_pmf)
        return [p / s for p in base_pmf]

    for _ in range(120):
        mid = 0.5 * (lo + hi)
        m_mid = mean_at(mid)
        if m_mid < target_mean:
            lo = mid
        else:
            hi = mid

    lmb = 0.5 * (lo + hi)
    x = [lmb * m for m in multipliers]
    peak = max(x)
    w = [pr * math.exp(xx - peak) for pr, xx in zip(prior, x)]
    s_w = math.fsum(w)
    return [ww / s_w for ww in w]


def _max_variance_two_point(multipliers: list[float], cost: float, target_mean: float) -> tuple[list[float], float]:
    """Symmetric, EV-preserving two-point pmf placing mass only on the global minimum-value
    (centre) and maximum-value (edge) buckets. This realises the largest STD attainable on the
    fixed multiplier support at ``target_mean`` and is used as the high-variance end-point for an
    EV-preserving blend that lifts low-variance modes up to the STD floor."""
    values = [m / cost for m in multipliers]
    v_low = min(values)
    v_high = max(values)
    pmf = [0.0 for _ in multipliers]
    if v_high - v_low <= 1e-12 or not (v_low < target_mean < v_high):
        return pmf, 0.0
    low_idx = [i for i, v in enumerate(values) if abs(v - v_low) <= 1e-12]
    high_idx = [i for i, v in enumerate(values) if abs(v - v_high) <= 1e-12]
    prob_high = (target_mean - v_low) / (v_high - v_low)
    prob_low = 1.0 - prob_high
    for i in low_idx:
        pmf[i] += prob_low / len(low_idx)
    for i in high_idx:
        pmf[i] += prob_high / len(high_idx)
    _mean, std = pmf_stats(multipliers, cost, pmf)
    return pmf, std


def std_bounded_pmf(multipliers: list[float], cost: float, base_pmf: list[float]) -> tuple[list[float], str]:
    """Return a symmetric pmf satisfying the normalized STD band when possible.

    The one-parameter tempered binomial is preferred because it is smooth. When its
    RTP-calibrated STD falls outside the package rule, first solve an EV-preserving
    alpha-rebalance (keeps full support across buckets) to land inside
    [MIN_STD, MAX_STD]. Only if no feasible alpha bracket is found do we fallback to
    a symmetric two-point distribution.
    """
    mean, std = pmf_stats(multipliers, cost, base_pmf)
    if MIN_STD <= std <= MAX_STD:
        return base_pmf, f"tempered_binomial; std={std:.8f}; base_std={BASE_STD}; std_rule={MIN_STD}-{MAX_STD}"

    target_ev = TARGET_RTP * cost

    def std_at(alpha: float) -> tuple[list[float], float]:
        q = ev_preserving_flatten_pmf(base_pmf, multipliers, target_ev, alpha)
        _mean, s = pmf_stats(multipliers, cost, q)
        return q, s

    if std < MIN_STD:
        # EV-preserving blend toward the maximum-variance two-point distribution so the mode
        # reaches the STD floor while staying as smooth as possible (small blend weight keeps
        # the bulk of the mass on the original tempered-binomial shape).
        tp_pmf, tp_std = _max_variance_two_point(multipliers, cost, TARGET_RTP)
        if tp_std > std:
            reach = min(STD_FLOOR_TARGET, tp_std)
            denom = tp_std * tp_std - std * std
            t = 0.0 if denom <= 0 else (reach * reach - std * std) / denom
            t = max(0.0, min(1.0, t))
            blended = [(1.0 - t) * b + t * p for b, p in zip(base_pmf, tp_pmf)]
            s_total = math.fsum(blended)
            blended = [x / s_total for x in blended]
            _mean, blended_std = pmf_stats(multipliers, cost, blended)
            return blended, (
                f"std_floor_two_point_blend; base_std={std:.8f}; chosen_std={blended_std:.8f}; "
                f"blend_t={t:.8f}; max_var_std={tp_std:.8f}; std_rule={MIN_STD}-{MAX_STD}"
            )
        # Max-variance support cannot reach the floor: keep the smooth base distribution.
        return base_pmf, (
            f"std_floor_unreachable; base_std={std:.8f}; max_var_std={tp_std:.8f}; "
            f"target_min={MIN_STD}; reason=support_limited"
        )

    if std > MAX_STD:
        hi_a, lo_a = 1.0, 0.7
        lo_q, lo_s = std_at(lo_a)
        for _ in range(14):
            if lo_s <= MAX_STD:
                break
            hi_a = lo_a
            lo_a *= 0.7
            lo_q, lo_s = std_at(lo_a)
        if lo_s <= MAX_STD:
            for _ in range(60):
                mid_a = 0.5 * (lo_a + hi_a)
                mid_q, mid_s = std_at(mid_a)
                if mid_s > MAX_STD:
                    hi_a = mid_a
                else:
                    lo_a, lo_q, lo_s = mid_a, mid_q, mid_s
            return lo_q, (
                f"std_bounded_alpha_rebalance; base_std={std:.8f}; chosen_std={lo_s:.8f}; "
                f"alpha={lo_a:.8f}; std_rule={MIN_STD}-{MAX_STD}"
            )
        return lo_q, (
            f"std_soft_clamp_alpha; base_std={std:.8f}; chosen_std={lo_s:.8f}; "
            f"alpha={lo_a:.8f}; target_max={MAX_STD}; reason=full_support_priority"
        )

    n = len(multipliers) - 1
    target_mean = TARGET_RTP

    groups: list[tuple[int, int, float]] = []
    for left in range(n // 2 + 1):
        right = n - left
        value_left = multipliers[left] / cost
        value_right = multipliers[right] / cost
        value = 0.5 * (value_left + value_right)
        groups.append((left, right, value))

    candidates: list[tuple[float, int, int, float]] = []
    for low_idx, (_, _, low_value) in enumerate(groups):
        if low_value >= target_mean:
            continue
        for high_idx, (_, _, high_value) in enumerate(groups):
            if high_value <= target_mean:
                continue
            variance = (target_mean - low_value) * (high_value - target_mean)
            if variance <= 0:
                continue
            candidate_std = math.sqrt(variance)
            if MIN_STD <= candidate_std <= MAX_STD:
                target = MIN_STD if std < MIN_STD else MAX_STD
                candidates.append((abs(candidate_std - target), low_idx, high_idx, candidate_std))

    if not candidates:
        raise ValueError(
            f"No symmetric two-point pmf can satisfy STD rule for cost={cost}; "
            f"base std={std:.8f}, rule={MIN_STD}-{MAX_STD}"
        )

    _, low_idx, high_idx, chosen_std = min(candidates, key=lambda item: item[0])
    low_left, low_right, low_value = groups[low_idx]
    high_left, high_right, high_value = groups[high_idx]
    prob_high_group = (target_mean - low_value) / (high_value - low_value)
    prob_low_group = 1.0 - prob_high_group

    pmf = [0.0 for _ in multipliers]
    for probability, left, right in [(prob_low_group, low_left, low_right), (prob_high_group, high_left, high_right)]:
        if left == right:
            pmf[left] += probability
        else:
            pmf[left] += probability / 2.0
            pmf[right] += probability / 2.0

    return pmf, (
        f"std_bounded_two_point; base_std={std:.8f}; chosen_std={chosen_std:.8f}; "
        f"std_rule={MIN_STD}-{MAX_STD}; value_pair={low_value:.8f}/{high_value:.8f}"
    )


def build_rows(multipliers: list[float], cost: float, difficulty: str) -> tuple[list[tuple[int, int, int]], float, str]:
    """Return ([(sim_id, weight, payout_raw)], theta, design_note) with a symmetric, RTP-calibrated pmf."""
    n = len(multipliers) - 1
    target_ev = TARGET_RTP * cost
    theta = solve_theta(multipliers, target_ev)
    base_pmf = symmetric_pmf(multipliers, theta)
    alpha = REBALANCE_ALPHA_BY_DIFFICULTY.get(difficulty.lower(), 1.0)
    rebased = ev_preserving_flatten_pmf(base_pmf, multipliers, target_ev, alpha)
    pmf, std_note = std_bounded_pmf(multipliers, cost, rebased)
    design_note = f"rebalance_alpha={alpha:.4f}; {std_note}"

    payouts = [int(round(m * PAYOUT_SCALE)) for m in multipliers]

    # Integer weights; floor at 1 so every bucket (incl. max-win edges) is reachable.
    weights = [max(1, int(round(p * WEIGHT_SCALE))) for p in pmf]

    # Enforce exact mirror symmetry: P(k) == P(N-k) (average to avoid upward bias).
    for k in range(n // 2 + 1):
        mirror = n - k
        shared = max(1, (weights[k] + weights[mirror] + 1) // 2)
        weights[k] = weights[mirror] = shared

    # RTP drift correction: transfer weight between the centre group and a symmetric
    # interior pair, keeping total weight and symmetry fixed and leaving payouts exact.
    _correct_rtp(weights, payouts, n, cost)

    # Regulatory/product requirement: max win must be realistically reachable.
    _enforce_max_win_achievability(weights, payouts, MAX_WIN_MAX_ODDS, cost)

    # Re-center RTP after max-win uplift while preserving max-win bucket weights.
    _correct_rtp(weights, payouts, n, cost)

    rows = [(k + 1, weights[k], payouts[k]) for k in range(n + 1)]
    return rows, theta, design_note


def _center_indices(n: int) -> list[int]:
    return [n // 2] if n % 2 == 0 else [(n - 1) // 2, (n + 1) // 2]


def _correct_rtp(weights: list[int], payouts: list[int], n: int, cost: float) -> None:
    centers = _center_indices(n)
    m_center = payouts[centers[0]]
    m_max = max(payouts)

    # Candidate interior pairs (j, n-j) sorted by largest |M_j - M_center| first
    # (smallest required nudge), excluding the centre and the jackpot edge tail.
    candidates = sorted(
        (
            j for j in range(n + 1)
            if j not in centers and j < n - j and payouts[j] < TAIL_THRESHOLD_RAW and payouts[j] < m_max
        ),
        key=lambda j: abs(payouts[j] - m_center),
        reverse=True,
    )
    if not candidates:
        candidates = [j for j in range(n + 1) if j not in centers and j < n - j and payouts[j] < m_max]
    if not candidates:
        return

    for _ in range(8):
        total_w = sum(weights)
        num = sum(w * p for w, p in zip(weights, payouts))
        target_num = TARGET_RTP * cost * total_w
        residual = target_num - num
        if abs(residual) < 0.5:
            break
        applied = False
        for j in candidates:
            mirror = n - j
            denom = 2.0 * (payouts[j] - m_center)
            if abs(denom) < 1e-9:
                continue
            delta = int(round(residual / denom))
            if delta == 0:
                break
            # Move delta into each of (j, mirror); remove delta from each centre member.
            if min(weights[j], weights[mirror]) + delta < 1:
                continue
            if min(weights[c] for c in centers) - delta < 1:
                continue
            weights[j] += delta
            weights[mirror] += delta
            for c in centers:
                weights[c] -= delta
            applied = True
            break
        if not applied:
            break


def write_lookup(path: Path, rows: Sequence[Sequence[int]]) -> None:
    payload = "\n".join(f"{sid},{weight},{payout}" for sid, weight, payout in rows) + "\n"
    path.write_bytes(payload.encode("utf-8"))


def write_books(path: Path, name: str, mode_type: str, difficulty: str, n_rows: int,
                rows: list[tuple[int, int, int]]) -> None:
    lines = []
    for sid, weight, payout in rows:
        bucket = sid - 1
        obj = {
            "id": sid,
            "mode": name,
            "modeType": mode_type,
            "difficulty": difficulty,
            "rows": n_rows,
            "weight": int(weight),
            "outcomeBucketId": bucket,
            "payoutMultiplier": payout,
            "criteria": "deterministic_static_outcome",
            "events": [
                {"type": "round_init", "mode": name, "modeType": mode_type,
                 "difficulty": difficulty, "rows": n_rows},
                {"type": "trajectory_selected", "outcomeBucketId": bucket},
                {"type": "bucket_landed", "outcomeBucketId": bucket, "payoutMultiplier": payout},
                {"type": "settlement", "totalPayoutMultiplier": payout},
            ],
        }
        lines.append(json.dumps(obj, separators=(",", ":"), ensure_ascii=False))
    text = "\n".join(lines) + "\n"
    path.write_bytes(zstd.ZstdCompressor(level=19).compress(text.encode("utf-8")))


def _calibrated_flatten_probs(base_probs: np.ndarray, multipliers: np.ndarray,
                              target_mean: float, alpha: float) -> np.ndarray:
    """Flatten a pmf with exponent ``alpha`` and re-calibrate EV to ``target_mean``.

    q_i(lambda) proportional to base_i^alpha * exp(lambda * multiplier_i)

    For fixed alpha this is monotone in lambda for the expected multiplier, so
    bisection yields a stable EV-constrained flattened distribution.
    """
    alpha = float(alpha)
    prior = np.power(np.maximum(base_probs, 1e-300), alpha)
    prior = prior / prior.sum()

    # Helper: evaluate mean under tilt lambda with overflow-safe centering.
    def mean_at(lmb: float) -> float:
        x = lmb * multipliers
        x = x - np.max(x)
        w = prior * np.exp(x)
        q = w / w.sum()
        return float(np.dot(q, multipliers))

    lo, hi = -60.0, 60.0
    m_lo = mean_at(lo)
    m_hi = mean_at(hi)

    # Expand bracket if needed.
    for _ in range(8):
        if m_lo <= target_mean <= m_hi:
            break
        if target_mean < m_lo:
            hi = lo
            lo *= 2.0
            m_lo = mean_at(lo)
            m_hi = mean_at(hi)
        else:
            lo = hi
            hi *= 2.0
            m_lo = mean_at(lo)
            m_hi = mean_at(hi)

    if not (m_lo <= target_mean <= m_hi):
        # Fallback: no feasible bracket found; keep original probs.
        return base_probs / base_probs.sum()

    for _ in range(120):
        mid = 0.5 * (lo + hi)
        m_mid = mean_at(mid)
        if m_mid < target_mean:
            lo = mid
        else:
            hi = mid

    lmb = 0.5 * (lo + hi)
    x = lmb * multipliers
    x = x - np.max(x)
    w = prior * np.exp(x)
    q = w / w.sum()
    return q


def _build_balanced_replay_sequence(seed: int, num_buckets: int, difficulty: str, payout: int) -> list[int]:
    """Build a low-peak 100-ball replay sequence without changing settlement payout."""
    rng = np.random.default_rng(seed)
    counts = np.full(num_buckets, N_BALLS // num_buckets, dtype=int)
    remainder = N_BALLS - int(counts.sum())

    # Deterministic but varied remainder placement keeps repeated payouts from sharing
    # the same histogram shape.
    order = rng.permutation(num_buckets)
    counts[order[:remainder]] += 1

    # Add a gentle payout-aware tilt so the sequence still differs across payout tiers.
    if num_buckets >= 3:
        target = min(num_buckets - 1, max(0, int(round((payout / PAYOUT_SCALE) / max(1.0, BUY100_COST / 2.0)))))
        bias_span = 2 if difficulty.lower() == "expert" else 1
        for offset in range(-bias_span, bias_span + 1):
            idx = target + offset
            if 0 <= idx < num_buckets and counts[idx] > 0:
                counts[idx] += 1
                donor = order[(offset + bias_span) % num_buckets]
                if donor != idx and counts[donor] > 1:
                    counts[donor] -= 1

    balls = np.repeat(np.arange(num_buckets, dtype=int), counts)
    rng.shuffle(balls)
    return balls.tolist()

def _balls_for_round_payout(ball_payout: np.ndarray, target_payout: int) -> list[int]:
    """Find a 100-ball replay whose settlement rounds exactly to target_payout."""
    settlement_all_max = round((int(ball_payout.max()) * N_BALLS / N_BALLS) * BUY100_COST)
    if settlement_all_max == target_payout:
        max_bucket = int(np.argmax(ball_payout))
        return [max_bucket] * N_BALLS

    center = int(round(target_payout * N_BALLS / BUY100_COST))
    candidate_sums = [s for s in range(center - 4, center + 5) if round((s / N_BALLS) * BUY100_COST) == target_payout]
    if not candidate_sums:
        raise ValueError(f"No settlement sum rounds to {target_payout}")
    target_sum = candidate_sums[0]
    base, remainder = divmod(target_sum, N_BALLS)
    synthetic = [-(base + 1)] * remainder + [-base] * (N_BALLS - remainder)
    if round((sum(-b for b in synthetic) / N_BALLS) * BUY100_COST) != target_payout:
        raise ValueError(f"Cannot build settlement-consistent balls for payout {target_payout}")
    return synthetic


def build_buy100_rows(normal_rows: list[tuple[int, int, int]], seed: int, difficulty: str):
    """Build buy100 outcomes from 100 independent balls and return replay-diversified rows.

    Returns:
      * lookup_rows: [[sim_id, weight, payout_raw], ...]
      * row_balls: {sim_id: [bucket_0..bucket_99]} replay sequence per lookup row
      * ball_payout: per-bucket single-ball payout_raw
      * design_note: provenance metadata
    """
    weights = np.array([w for _, w, _ in normal_rows], dtype=np.float64)
    probs = weights / weights.sum()

    ball_payout = np.array([p for _, _, p in normal_rows], dtype=np.int64)
    ball_mult = ball_payout.astype(np.float64) / PAYOUT_SCALE

    # Controlled rebalance: for expert buy100, flatten the single-ball pmf and
    # automatically tilt it back to target EV so RTP remains stable.
    alpha_buy = BUY100_REBALANCE_ALPHA_BY_DIFFICULTY.get(difficulty.lower(), 1.0)
    probs = _calibrated_flatten_probs(
        probs,
        ball_mult,
        TARGET_RTP,
        alpha_buy,
    )

    num_buckets = len(probs)

    rng = np.random.default_rng(seed)
    balls = rng.choice(num_buckets, size=(MC_SAMPLES, N_BALLS), p=probs)
    round_sum = ball_payout[balls].sum(axis=1)
    round_payout = np.rint((round_sum / N_BALLS) * BUY100_COST).astype(np.int64)
    round_payout = np.minimum(round_payout, int(MAX_MULTIPLIER * PAYOUT_SCALE))

    uniq, inv, counts = np.unique(round_payout, return_inverse=True, return_counts=True)

    # Build multiple replay variants per payout bucket so repeated outcomes do not replay
    # one fixed 100-ball path every time.
    variants: list[tuple[int, int, list[int]]] = []  # (weight, payout, balls)
    for payout_idx, payout in enumerate(uniq):
        idxs = np.flatnonzero(inv == payout_idx)
        cnt = int(counts[payout_idx])
        n_variants = min(BUY100_MAX_VARIANTS_PER_PAYOUT, max(2 if difficulty.lower() == "expert" else 1, cnt // BUY100_VARIANT_BUCKET + 1))
        n_variants = min(n_variants, len(idxs))

        # Candidate pool for diversity scoring.
        pool_size = min(len(idxs), 8192 if difficulty.lower() == "expert" else 512)
        if pool_size == len(idxs):
            pool = idxs
        else:
            pool = rng.choice(idxs, size=pool_size, replace=False)

        scored: list[tuple[int, float, float, int, int]] = []  # (unique_buckets, entropy, -top_share, span, sample_idx)
        for sample_idx in pool:
            b = balls[sample_idx]
            hist = np.bincount(b, minlength=num_buckets)
            probs_hist = hist[hist > 0].astype(np.float64)
            probs_hist = probs_hist / probs_hist.sum()
            entropy = float(-(probs_hist * np.log2(probs_hist)).sum())
            span = int(b.max() - b.min())
            top_share = float(hist.max() / N_BALLS)
            scored.append((int(np.count_nonzero(hist)), entropy, -top_share, span, int(sample_idx)))
        scored.sort(reverse=True)

        if difficulty.lower() == "expert":
            anti_peak = [s for s in scored if s[0] >= 4 and s[2] <= -0.45]
            if len(anti_peak) >= n_variants:
                scored = anti_peak

        chosen = [s[4] for s in scored[:n_variants]]
        if not chosen:
            chosen = [int(idxs[0])]
        n = len(chosen)
        base = cnt // n
        rem = cnt % n
        for j, sample_idx in enumerate(chosen):
            w = base + (1 if j < rem else 0)
            if w <= 0:
                continue
            variants.append((int(w), int(payout), balls[sample_idx].tolist()))

    variants = [(w * BUY100_WEIGHT_MULTIPLIER, p, b) for w, p, b in variants]

    max_bucket = int(np.argmax(ball_payout))
    max_round_payout = min(int(MAX_MULTIPLIER * PAYOUT_SCALE), int(round(float(ball_payout[max_bucket]) * BUY100_COST)))
    jackpot_weight = max(1, int(math.ceil(sum(w for w, _, _ in variants) / MAX_WIN_MAX_ODDS)))
    variants.append((jackpot_weight, max_round_payout, _balls_for_round_payout(ball_payout, max_round_payout)))

    lookup_rows = [[int(i + 1), int(w), int(p)] for i, (w, p, _) in enumerate(variants)]
    _correct_average_rtp(lookup_rows, TARGET_RTP * BUY100_COST * PAYOUT_SCALE)

    # Replay events must stay numerically consistent with settlement: keep the original
    # sampled 100-ball sequence that produced this payout bucket.
    row_balls = {int(i + 1): list(variants[i][2]) for i in range(len(variants))}
    design_note = (
        f"true_100balls_mc; balls={N_BALLS}; samples={MC_SAMPLES}; outcomes={len(lookup_rows)}; "
        f"buy_cost={BUY100_COST}; flatten_alpha={alpha_buy}; "
        f"variants_per_payout<={BUY100_MAX_VARIANTS_PER_PAYOUT}"
    )
    return lookup_rows, row_balls, ball_payout.tolist(), design_note


def _correct_average_rtp(lookup_rows: list[list[int]], target_raw: float) -> None:
    """Remove Monte-Carlo sampling noise so the weighted-mean payout equals the target exactly.

    Heavy-tailed expert modes can have a raw sample mean off by ~1e-2, which a near-target
    straddle cannot repair (it would need to move more weight than those bins hold). Instead we
    transfer a small integer weight between the most-populous bin (pivot) and the opposite
    payout extreme (max lever), which always reaches the target with only a few tens of units of
    movement. Total weight (sum of counts) is preserved and every touched bin already has a
    representative 100-ball book, so no outcome is left without events."""
    pays = [p for _, _, p in lookup_rows]
    i_max = max(range(len(pays)), key=lambda i: pays[i])
    i_min = min(range(len(pays)), key=lambda i: pays[i])
    for _ in range(500):
        total = sum(w for _, w, _ in lookup_rows)
        num = sum(w * p for _, w, p in lookup_rows)
        gap = target_raw * total - num
        if abs(gap) < 0.5:
            break
        sink = i_max if gap > 0 else i_min
        i_piv = max((i for i in range(len(lookup_rows)) if i != sink),
                    key=lambda i: lookup_rows[i][1])
        lever = pays[sink] - pays[i_piv]
        if abs(lever) < 1e-9:
            break
        move = int(round(gap / lever))
        if move == 0:
            move = 1
        move = min(abs(move), lookup_rows[i_piv][1] - 1)
        if move <= 0:
            break
        lookup_rows[i_piv][1] -= move
        lookup_rows[sink][1] += move


def _enforce_buy100_max_std(lookup_rows: list[list[int]], target_mean_raw: float) -> None:
    """Cap the per-mode STD (raw multiplier basis) at MAX_STD for buy100 modes.

    The 100-ball Monte-Carlo can leave the heaviest expert tables above the STD ceiling. We
    reduce the variance with an EV-preserving mixture: move a fraction ``t`` of the mass onto the
    two existing rows straddling the mean (their split reproduces the mean exactly), which scales
    the variance by ``(1 - t)`` without altering any payout value, row id, or the 100-ball replay
    sequence attached to each row."""
    mult = np.array([p for _, _, p in lookup_rows], dtype=np.float64) / PAYOUT_SCALE
    weights = np.array([w for _, w, _ in lookup_rows], dtype=np.float64)
    probs = weights / weights.sum()

    def std_of(p: np.ndarray) -> float:
        mean = float(np.dot(p, mult))
        e_x2 = float(np.dot(p, mult * mult))
        return math.sqrt(max(0.0, e_x2 - mean * mean))

    cur = std_of(probs)
    if cur <= MAX_STD:
        return

    mean_mult = target_mean_raw / PAYOUT_SCALE
    below = [i for i in range(len(mult)) if mult[i] <= mean_mult]
    above = [i for i in range(len(mult)) if mult[i] > mean_mult]
    if not below or not above:
        return
    i_lo = max(below, key=lambda i: mult[i])
    i_hi = min(above, key=lambda i: mult[i])
    v_lo, v_hi = float(mult[i_lo]), float(mult[i_hi])
    if v_hi - v_lo <= 1e-12:
        return
    frac_hi = (mean_mult - v_lo) / (v_hi - v_lo)

    # Target variance scaling; aim at STD_CEIL_TARGET for headroom against integer rounding and
    # the tiny residual variance of the near-mean straddle pair.
    t = 1.0 - (STD_CEIL_TARGET / cur) ** 2
    t = min(max(t, 0.0), 0.99)

    new_p = (1.0 - t) * probs
    new_p[i_hi] += t * frac_hi
    new_p[i_lo] += t * (1.0 - frac_hi)

    total_w = int(weights.sum())
    new_w = np.maximum(1, np.rint(new_p * total_w).astype(np.int64))
    for i in range(len(lookup_rows)):
        lookup_rows[i][1] = int(new_w[i])


def write_books_buy100(path: Path, name: str, mode_type: str, difficulty: str, n_rows: int,
                       lookup_rows: Sequence[Sequence[int]], row_balls: dict[int, list[int]],
                       ball_payout: list[int]) -> None:
    """One book record per distinct round outcome, each replaying the full 100-ball sequence:
    round_init -> 100x ball_landed -> settlement(totalPayoutMultiplier = per-stake average)."""
    lines = []
    for sid, weight, payout in lookup_rows:
        balls = row_balls[sid]
        ball_events = []
        for i, b in enumerate(balls):
            if b < 0:
                ball_events.append({
                    "type": "ball_landed", "ballIndex": i, "outcomeBucketId": -1,
                    "payoutMultiplier": int(-b),
                })
            else:
                ball_events.append({
                    "type": "ball_landed", "ballIndex": i, "outcomeBucketId": int(b),
                    "payoutMultiplier": int(ball_payout[b]),
                })
        obj = {
            "id": sid,
            "mode": name,
            "modeType": mode_type,
            "difficulty": difficulty,
            "rows": n_rows,
            "weight": int(weight),
            "ballCount": N_BALLS,
            "outcomeBucketId": -1,
            "payoutMultiplier": int(payout),
            "criteria": "true_100balls_per_stake_average",
            "events": [
                {"type": "round_init", "mode": name, "modeType": mode_type,
                 "difficulty": difficulty, "rows": n_rows, "ballCount": N_BALLS},
                *ball_events,
                {"type": "settlement", "totalPayoutMultiplier": int(payout), "ballCount": N_BALLS},
            ],
        }
        lines.append(json.dumps(obj, separators=(",", ":"), ensure_ascii=False))
    text = "\n".join(lines) + "\n"
    path.write_bytes(zstd.ZstdCompressor(level=19).compress(text.encode("utf-8")))


def mode_metrics(rows: Sequence[Sequence[int]], cost: float) -> tuple[float, float, float]:
    total = float(sum(w for _, w, _ in rows))
    mults = [p / PAYOUT_SCALE for _, _, p in rows]
    probs = [w / total for _, w, _ in rows]
    rtp = math.fsum(pr * m for pr, m in zip(probs, mults)) / cost
    e_x2 = math.fsum(pr * (m / cost) ** 2 for pr, m in zip(probs, mults))
    std = math.sqrt(max(0.0, e_x2 - rtp ** 2))
    return rtp, std, max(mults)


def main() -> int:
    paytables = load_paytables()
    index = json.loads((PUBLISH / "index.json").read_text(encoding="utf-8"))

    prob_rows: list[list[object]] = []
    new_modes: list[dict] = []
    report: list[tuple[str, float, float, float]] = []

    for mode in index["modes"]:
        name = mode["name"]
        mode_type = mode["mode_type"]
        difficulty = mode["difficulty"]
        n_rows = int(mode["rows"])
        cost = float(mode["cost"])
        # The single-ball distribution is ALWAYS the authoritative NORMAL paytable for this
        # (difficulty, rows). normal modes publish it directly; buy100 modes resolve 100
        # independent balls from the same P(k) and settle on the per-stake average.
        key = ("normal", difficulty.lower(), n_rows)
        if key not in paytables:
            raise ValueError(f"Missing authoritative paytable for {key}")
        # Clamp every bucket to the live marketing cap so no realised multiplier
        # exceeds MAX_MULTIPLIER (100,000x). The theta
        # calibration below then re-solves the pmf to hold RTP at target after clamping.
        multipliers = [min(m, MAX_MULTIPLIER) for m in paytables[key]]
        if len(multipliers) != n_rows + 1:
            raise ValueError(f"Paytable length mismatch for {key}: {len(multipliers)} != {n_rows + 1}")

        if mode_type == "100balls":
            # True 100-ball buy under product contract (cost=99x).
            cost = BUY100_COST
            normal_rows, theta, _ = build_rows(multipliers, 1.0, difficulty)
            seed = MC_SEED + zlib.crc32(name.encode("utf-8"))
            rows, row_balls, ball_payout, design_note = build_buy100_rows(normal_rows, seed, difficulty)
            write_lookup(PUBLISH / f"lookUpTable_{name}_0.csv", rows)
            write_books_buy100(PUBLISH / f"books_{name}.jsonl.zst", name, mode_type, difficulty,
                               n_rows, rows, row_balls, ball_payout)
        else:
            rows, theta, design_note = build_rows(multipliers, cost, difficulty)
            write_lookup(PUBLISH / f"lookUpTable_{name}_0.csv", rows)
            write_books(PUBLISH / f"books_{name}.jsonl.zst", name, mode_type, difficulty, n_rows, rows)

        rtp, std, max_win = mode_metrics(rows, cost)
        total_w = float(sum(w for _, w, _ in rows))
        for (sid, weight, payout) in rows:
            prob_rows.append([
                mode_type, difficulty, n_rows, sid - 1, payout / PAYOUT_SCALE,
                f"{weight / total_w:.18e}",
                "authoritative_multiplier_table+symmetric_design",
                f"mode={name}; theta={theta:.6f}; {design_note}",
            ])

        new_modes.append({
            "name": name,
            "mode_type": mode_type,
            "difficulty": difficulty,
            "rows": n_rows,
            "cost": cost,
            "rtp": round(rtp, 6),
            "max_win": round(max_win, 6),
            "weights": f"lookUpTable_{name}_0.csv",
            "events": f"books_{name}.jsonl.zst",
            "status": "std-bounded-symmetric-design-calibrated",
        })
        report.append((name, rtp, std, max_win))

    # Probability table.
    prob_path = INPUTS / "azteck_plinko_probability_tables.csv"
    with prob_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["mode_type", "difficulty", "rows", "bucket_index", "multiplier",
                         "probability", "source", "notes"])
        writer.writerows(prob_rows)

    # Index.
    index["version"] = VERSION
    index["target_rtp"] = TARGET_RTP
    index["base_std"] = BASE_STD
    index["std_rule"] = {"min": MIN_STD, "max": MAX_STD, "basis": "normalized_payout_multiplier"}
    index["modes"] = new_modes
    (PUBLISH / "index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")

    worst = max(abs(r - TARGET_RTP) for _, r, _, _ in report)
    print(f"Rebuilt {len(report)} modes. Worst |RTP-target| = {worst:.3e}")
    print(f"{'mode':28s} {'rtp':>10s} {'std':>10s} {'max_win':>12s}")
    for name, rtp, std, max_win in report:
        print(f"{name:28s} {rtp:10.6f} {std:10.4f} {max_win:12.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
