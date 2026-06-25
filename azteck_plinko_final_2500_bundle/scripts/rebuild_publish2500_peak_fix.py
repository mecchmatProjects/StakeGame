from __future__ import annotations

import csv
import hashlib
import json
import math
import shutil
from pathlib import Path

import zstandard as zstd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

TARGET = Path("math-sdk/games/azteck_plinko_final/azteck_plinko_final_publish2500")
BACKUP = Path("math-sdk/games/azteck_plinko_final/azteck_plinko_final_publish2500_prev")
OUT_XLSX = Path("Plinko2500.xlsx")

# Strict payout-level peak caps.
CAP_NORMAL = 0.25
CAP_BUY100 = 0.20
MIN_STD = 0.6
MAX_STD = 60.0
MIN_STD_ENFORCE = 0.6005
MAX_WIN_MAX_ODDS = 20_000_000.0


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


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


def weighted_mean_raw(rows: list[tuple[int, int, int]]) -> float:
    total = float(sum(w for _, w, _ in rows))
    if total <= 0:
        return 0.0
    return sum(w * raw for _, w, raw in rows) / total


def payout_level_concentration(rows: list[tuple[int, int, int]]) -> tuple[float, float]:
    total = sum(w for _, w, _ in rows)
    if total <= 0:
        return 0.0, 0.0
    by_raw: dict[int, int] = {}
    for _, w, raw in rows:
        by_raw[raw] = by_raw.get(raw, 0) + int(w)
    probs = [v / total for v in by_raw.values()]
    top = max(probs) if probs else 0.0
    hhi = sum(p * p for p in probs)
    return top, hhi


def mean_bounds_for_cap(raw_levels: list[int], cap: float) -> tuple[float, float]:
    xs = sorted(raw_levels)
    if not xs:
        return 0.0, 0.0

    rem = 1.0
    mn = 0.0
    for x in xs:
        take = min(cap, rem)
        mn += take * x
        rem -= take
        if rem <= 1e-15:
            break

    rem = 1.0
    mx = 0.0
    for x in reversed(xs):
        take = min(cap, rem)
        mx += take * x
        rem -= take
        if rem <= 1e-15:
            break

    return mn, mx


def min_feasible_cap_for_mean(raw_levels: list[int], target_mean: float) -> float:
    xs = sorted(set(raw_levels))
    if not xs:
        return 1.0

    lo = 1.0 / max(1, len(xs))
    hi = 1.0

    for _ in range(70):
        mid = (lo + hi) * 0.5
        mn, mx = mean_bounds_for_cap(xs, mid)
        if mn - 1e-9 <= target_mean <= mx + 1e-9:
            hi = mid
        else:
            lo = mid

    return hi


def reduce_peak(rows: list[tuple[int, int, int]], cap: float) -> tuple[list[tuple[int, int, int]], bool]:
    """Lower the largest-probability bucket by shifting weight to low/high tails, preserving total weight.

    Mean is re-centered after this transform by `recenter_mean_raw`.
    """
    sids = [sid for sid, _, _ in rows]
    weights = [int(w) for _, w, _ in rows]
    raws = [int(raw) for _, _, raw in rows]

    total = sum(weights)
    if total <= 0:
        return rows, False

    changed = False
    for _ in range(24):
        # Peak is measured at payout level (aggregated equal-payout rows), not per row.
        by_raw: dict[int, int] = {}
        for i, raw in enumerate(raws):
            by_raw[raw] = by_raw.get(raw, 0) + weights[i]
        peak_raw, peak_weight = max(by_raw.items(), key=lambda kv: kv[1])
        peak_share = peak_weight / total
        if peak_share <= cap:
            break

        # Move from all rows that belong to the peak payout.
        peak_rows = [i for i, raw in enumerate(raws) if raw == peak_raw and weights[i] > 1]
        if not peak_rows:
            break

        x0 = peak_raw
        low_raws = sorted({x for x in raws if x < x0}, reverse=True)
        high_raws = sorted({x for x in raws if x > x0})

        # Prefer nearest levels to keep volatility changes contained.
        low_raw = low_raws[0] if low_raws else None
        high_raw = high_raws[0] if high_raws else None

        i_low = None
        i_high = None
        x_low = None
        x_high = None
        if low_raw is not None:
            low_candidates = [i for i, x in enumerate(raws) if x == low_raw]
            i_low = max(low_candidates, key=lambda i: weights[i])
            x_low = raws[i_low]
        if high_raw is not None:
            high_candidates = [i for i, x in enumerate(raws) if x == high_raw]
            i_high = max(high_candidates, key=lambda i: weights[i])
            x_high = raws[i_high]
        if i_low is None and i_high is None:
            break

        remove_units = int(math.ceil(peak_weight - cap * total))
        if remove_units <= 0:
            break

        max_removable = sum(weights[i] - 1 for i in peak_rows)
        remove_units = min(remove_units, max_removable)
        if remove_units <= 0:
            break

        if i_low is not None and i_high is not None and x_high != x_low:
            frac_high = (x0 - x_low) / (x_high - x_low)
            add_high = int(round(remove_units * frac_high))
            add_high = max(0, min(remove_units, add_high))
            add_low = remove_units - add_high
        elif i_low is not None:
            add_low = remove_units
            add_high = 0
        else:
            add_low = 0
            add_high = remove_units

        # Drain from peak rows proportionally to their weights (while keeping each row >= 1).
        to_remove = remove_units
        for i in sorted(peak_rows, key=lambda idx: weights[idx], reverse=True):
            if to_remove <= 0:
                break
            can = weights[i] - 1
            if can <= 0:
                continue
            take = min(can, to_remove)
            weights[i] -= take
            to_remove -= take
        removed = remove_units - to_remove
        if removed <= 0:
            break
        if i_low is not None and add_low > 0:
            weights[i_low] += add_low
        if i_high is not None and add_high > 0:
            weights[i_high] += add_high
        changed = True

    new_rows = [(sids[i], int(weights[i]), int(raws[i])) for i in range(len(rows))]
    return new_rows, changed


def recenter_mean_raw(rows: list[tuple[int, int, int]], target_raw: float) -> list[tuple[int, int, int]]:
    """Integer re-centering by donor->receiver unit transfers until mean is near target."""
    sids = [sid for sid, _, _ in rows]
    weights = [int(w) for _, w, _ in rows]
    raws = [int(raw) for _, _, raw in rows]

    total = sum(weights)
    if total <= 0:
        return rows

    for _ in range(300):
        num = sum(weights[i] * raws[i] for i in range(len(weights)))
        gap = target_raw * total - num
        if abs(gap) < 0.5:
            break

        if gap > 0:
            donors = sorted([i for i in range(len(weights)) if weights[i] > 1], key=lambda i: raws[i])
            receivers = sorted(range(len(weights)), key=lambda i: raws[i], reverse=True)
        else:
            donors = sorted([i for i in range(len(weights)) if weights[i] > 1], key=lambda i: raws[i], reverse=True)
            receivers = sorted(range(len(weights)), key=lambda i: raws[i])

        moved = False
        for d in donors[:8]:
            for r in receivers[:8]:
                if d == r:
                    continue
                lever = raws[r] - raws[d]
                if lever == 0:
                    continue
                units = int(round(gap / lever))
                if units == 0:
                    units = 1 if gap > 0 else -1
                units = abs(units)
                units = max(1, min(units, weights[d] - 1))
                if units <= 0:
                    continue
                weights[d] -= units
                weights[r] += units
                moved = True
                break
            if moved:
                break
        if not moved:
            break

    return [(sids[i], int(weights[i]), int(raws[i])) for i in range(len(rows))]


def mode_std_base(rows: list[tuple[int, int, int]]) -> float:
    total = sum(w for _, w, _ in rows)
    if total <= 0:
        return 0.0
    mean = sum(w * (raw / 100.0) for _, w, raw in rows) / total
    ex2 = sum(w * (raw / 100.0) * (raw / 100.0) for _, w, raw in rows) / total
    return math.sqrt(max(0.0, ex2 - mean * mean))


def _pick_idx_for_raw(rows: list[tuple[int, int, int]], raw_value: int) -> int | None:
    candidates = [i for i, (_, _, raw) in enumerate(rows) if raw == raw_value]
    if not candidates:
        return None
    return max(candidates, key=lambda i: rows[i][1])


def _add_to_raw(rows: list[tuple[int, int, int]], raw_value: int, amount: int) -> bool:
    if amount <= 0:
        return False
    i = _pick_idx_for_raw(rows, raw_value)
    if i is None:
        return False
    sid, wt, raw = rows[i]
    rows[i] = (sid, int(wt + amount), raw)
    return True


def _nearest_bracket(raw_levels: list[int], target_raw: float) -> tuple[int | None, int | None]:
    lo = None
    hi = None
    for x in sorted(set(raw_levels)):
        if x <= target_raw:
            lo = x
        if x >= target_raw and hi is None:
            hi = x
    return lo, hi


def _add_pair_preserve_mean(
    rows: list[tuple[int, int, int]],
    x_lo: int,
    x_hi: int,
    target_raw: float,
    total_add: int,
) -> bool:
    if total_add <= 0:
        return False
    if x_lo == x_hi:
        return _add_to_raw(rows, x_lo, total_add)

    denom = float(x_hi - x_lo)
    if denom <= 0:
        return False

    w_hi = (target_raw - x_lo) / denom
    w_hi = max(0.0, min(1.0, w_hi))
    add_hi = int(round(total_add * w_hi))
    add_hi = max(0, min(total_add, add_hi))
    add_lo = total_add - add_hi

    ok_lo = _add_to_raw(rows, x_lo, add_lo)
    ok_hi = _add_to_raw(rows, x_hi, add_hi)
    return ok_lo and ok_hi


def enforce_max_win_achievability(rows: list[tuple[int, int, int]], target_raw: float, max_odds: float) -> bool:
    if max_odds <= 1.0:
        return False

    total = sum(w for _, w, _ in rows)
    if total <= 0:
        return False

    max_raw = max(raw for _, _, raw in rows)
    min_raw = min(raw for _, _, raw in rows)
    cur_max = sum(w for _, w, raw in rows if raw == max_raw)
    if cur_max <= 0:
        return False
    if total <= max_odds * cur_max:
        return False

    # Solve edge+center additive lift so mean stays approximately fixed.
    num = sum(w * raw for _, w, raw in rows)
    denom_r = float(num) - float(total) * float(min_raw)
    r = 0.0
    if denom_r > 0:
        r = (float(total) * float(max_raw) - float(num)) / denom_r

    denom_x = max_odds - 1.0 - r
    if denom_x <= 0:
        r = 0.0
        denom_x = max_odds - 1.0
    if denom_x <= 0:
        return False

    numerator = float(total) - max_odds * float(cur_max)
    if numerator <= 0:
        return False
    x_required = int(math.ceil(numerator / denom_x))
    if x_required <= 0:
        return False

    changed = _add_to_raw(rows, max_raw, x_required)
    if r > 0:
        y_required = int(math.ceil(r * x_required))
        changed = _add_to_raw(rows, min_raw, y_required) or changed
    return changed


def enforce_std_band(rows: list[tuple[int, int, int]], target_raw: float) -> bool:
    total = sum(w for _, w, _ in rows)
    if total <= 0:
        return False

    std = mode_std_base(rows)
    changed = False
    raws = sorted(set(raw for _, _, raw in rows))
    if not raws:
        return False

    # Raise STD by adding mass to support edges with mean-preserving ratio.
    if std < MIN_STD_ENFORCE:
        x_lo = min(raws)
        x_hi = max(raws)
        if x_hi > x_lo:
            mu = target_raw / 100.0
            d2_edge = (mu - x_lo / 100.0) * (x_hi / 100.0 - mu)
            v = std * std
            tgt = MIN_STD_ENFORCE * MIN_STD_ENFORCE
            if d2_edge > tgt and tgt > v:
                need = int(math.ceil(total * (tgt - v) / (d2_edge - tgt)))
                if need > 0 and _add_pair_preserve_mean(rows, x_lo, x_hi, target_raw, need):
                    changed = True

    # Lower STD by adding mass near mean with mean-preserving bracket.
    std = mode_std_base(rows)
    if std > MAX_STD:
        lo, hi = _nearest_bracket(raws, target_raw)
        if lo is not None and hi is not None:
            if lo == hi:
                # Exact mean bucket exists; adding there strictly lowers variance.
                x0 = lo / 100.0
                mu = target_raw / 100.0
                d2_mid = (x0 - mu) * (x0 - mu)
                v = std * std
                tgt = MAX_STD * MAX_STD
                if tgt > d2_mid and v > tgt:
                    need = int(math.ceil(total * (v - tgt) / (tgt - d2_mid)))
                    if need > 0 and _add_to_raw(rows, lo, need):
                        changed = True
            else:
                mu = target_raw / 100.0
                d2_mid = (mu - lo / 100.0) * (hi / 100.0 - mu)
                v = std * std
                tgt = MAX_STD * MAX_STD
                if tgt > d2_mid and v > tgt:
                    need = int(math.ceil(total * (v - tgt) / (tgt - d2_mid)))
                    if need > 0 and _add_pair_preserve_mean(rows, lo, hi, target_raw, need):
                        changed = True

    return changed


def rewrite_books_weight(path: Path, weight_by_id: dict[int, int]) -> None:
    dctx = zstd.ZstdDecompressor()
    cctx = zstd.ZstdCompressor(level=19)
    with path.open("rb") as f:
        txt = dctx.stream_reader(f).read().decode("utf-8")

    lines = []
    for line in txt.splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        sid = int(row.get("id", 0))
        if sid in weight_by_id:
            row["weight"] = int(weight_by_id[sid])
        lines.append(json.dumps(row, separators=(",", ":"), ensure_ascii=False))

    payload = ("\n".join(lines) + "\n").encode("utf-8")
    path.write_bytes(cctx.compress(payload))


def build_excel(folder: Path, output: Path) -> dict[str, int]:
    index = json.loads((folder / "index.json").read_text(encoding="utf-8"))
    config = json.loads((folder / "config.json").read_text(encoding="utf-8"))
    fe = json.loads((folder / "fe_config.json").read_text(encoding="utf-8"))

    modes_idx = {m["name"]: m for m in index.get("modes", []) if isinstance(m, dict) and "name" in m}
    modes_cfg = {m["name"]: m for m in config.get("bookShelfConfig", []) if isinstance(m, dict) and "name" in m}
    modes_fe = {m["name"]: m for m in fe.get("modes", []) if isinstance(m, dict) and "name" in m}

    all_modes = sorted(set(modes_idx) | set(modes_cfg) | set(modes_fe))

    consistency_rows = []
    peaks = []
    feasibility_rows = []

    for name in all_modes:
        i = modes_idx.get(name)
        c = modes_cfg.get(name)
        f = modes_fe.get(name)

        lookup = folder / i["weights"]
        books = folder / i["events"]
        force = folder / c["forceFile"]["file"] if c else None

        lut = read_lookup(lookup)
        total = sum(w for _, w, _ in lut)
        top_prob = 0.0
        hhi = 0.0
        peak_flag = False
        if total > 0:
            top_prob, hhi = payout_level_concentration(lut)
            cap = CAP_BUY100 if name.startswith("buy100_") else CAP_NORMAL
            peak_flag = top_prob > cap

            by_raw = sorted({raw for _, _, raw in lut})
            target_raw = float(i.get("rtp", 0.9605)) * float(i.get("cost", 1.0)) * 100.0 if i else 0.0
            min_cap = min_feasible_cap_for_mean(by_raw, target_raw) if by_raw else 1.0
            strict_feasible = min_cap <= (cap + 1e-9)
            feasibility_rows.append([
                name,
                i.get("mode_type") if i else None,
                cap,
                top_prob,
                min_cap,
                strict_feasible,
                (top_prob <= cap),
                target_raw,
                len(by_raw),
            ])

        dctx = zstd.ZstdDecompressor()
        with books.open("rb") as bf:
            btxt = dctx.stream_reader(bf).read().decode("utf-8")
        bro = [json.loads(x) for x in btxt.splitlines() if x.strip()]

        lut_p = [int(raw) for _, _, raw in lut]
        book_p = [int(float(r.get("payoutMultiplier", 0))) for r in bro]

        consistency_rows.append([
            name,
            i is not None,
            c is not None,
            f is not None,
            i.get("cost") if i else None,
            c.get("cost") if c else None,
            f.get("cost") if f else None,
            (i and c and f and i.get("cost") == c.get("cost") == f.get("cost")),
            i.get("rtp") if i else None,
            c.get("rtp") if c else None,
            i.get("max_win") if i else None,
            c.get("maxWin") if c else None,
            f.get("maxWin") if f else None,
            (i and c and f and abs(float(i.get("max_win", 0)) - float(c.get("maxWin", 0))) <= 1e-9 and abs(float(i.get("max_win", 0)) - float(f.get("maxWin", 0))) <= 1e-9),
            len(lut),
            (i.get("rows") + 1) if i else None,
            (i and len(lut) == i.get("rows") + 1),
            lookup.exists(),
            books.exists(),
            bool(force and force.exists()),
            (lut_p == book_p),
            top_prob,
            hhi,
            peak_flag,
        ])
        peaks.append((name, top_prob, hhi, peak_flag))

    wb = Workbook()
    hdr = PatternFill("solid", fgColor="B4C6E7")
    ok = PatternFill("solid", fgColor="C6EFCE")
    bad = PatternFill("solid", fgColor="FFC7CE")
    warn = PatternFill("solid", fgColor="FFF2CC")

    ws = wb.active
    ws.title = "Summary"
    ws["A1"] = "Plinko2500 Rebuild Audit"
    ws["A2"] = f"Source: {folder.as_posix()}"
    ws["A3"] = f"Modes: {len(all_modes)}"

    cws = wb.create_sheet("Consistency")
    headers = [
        "mode","in_index","in_config","in_fe",
        "cost_idx","cost_cfg","cost_fe","cost_consistent",
        "rtp_idx","rtp_cfg",
        "maxwin_idx","maxwin_cfg","maxwin_fe","maxwin_consistent",
        "lookup_rows","expected_buckets","bucket_rows_match",
        "lookup_exists","books_exists","force_exists",
        "lookup_books_payout_match",
        "top_bucket_probability","HHI","peak_flag",
    ]
    for c, h in enumerate(headers, 1):
        cws.cell(1, c, h)
        cws.cell(1, c).fill = hdr
        cws.cell(1, c).font = Font(bold=True)

    for r, row in enumerate(consistency_rows, 2):
        for c, v in enumerate(row, 1):
            cws.cell(r, c, v)

    bool_cols = [2,3,4,8,14,17,18,19,20,21]
    for r in range(2, cws.max_row + 1):
        for c in bool_cols:
            v = cws.cell(r, c).value
            if v is True:
                cws.cell(r, c).fill = ok
            elif v is False:
                cws.cell(r, c).fill = bad
        if cws.cell(r, 24).value is True:
            cws.cell(r, 24).fill = warn

    pws = wb.create_sheet("Distribution_Peaks")
    for c, h in enumerate(["mode", "top_bucket_probability", "HHI", "peak_flag"], 1):
        pws.cell(1, c, h)
        pws.cell(1, c).fill = hdr
        pws.cell(1, c).font = Font(bold=True)
    for r, (m, tp, hhi, flg) in enumerate(peaks, 2):
        pws.cell(r, 1, m)
        pws.cell(r, 2, tp)
        pws.cell(r, 3, hhi)
        pws.cell(r, 4, flg)
        if flg:
            pws.cell(r, 4).fill = warn

    fws = wb.create_sheet("Feasible_Caps")
    f_headers = [
        "mode",
        "mode_type",
        "strict_cap",
        "current_top_bucket_probability",
        "min_feasible_cap",
        "strict_cap_feasible",
        "strict_cap_met",
        "target_raw_mean",
        "unique_payout_levels",
    ]
    for c, h in enumerate(f_headers, 1):
        fws.cell(1, c, h)
        fws.cell(1, c).fill = hdr
        fws.cell(1, c).font = Font(bold=True)

    for r, row in enumerate(feasibility_rows, 2):
        for c, v in enumerate(row, 1):
            fws.cell(r, c, v)
        if fws.cell(r, 6).value is True:
            fws.cell(r, 6).fill = ok
        else:
            fws.cell(r, 6).fill = warn
        if fws.cell(r, 7).value is True:
            fws.cell(r, 7).fill = ok
        else:
            fws.cell(r, 7).fill = bad

    wb.save(output)

    peak_count = sum(1 for _, _, _, f in peaks if f)
    infeasible_strict = sum(1 for row in feasibility_rows if row[5] is False)
    return {"modes": len(all_modes), "peak_modes": peak_count, "strict_infeasible_modes": infeasible_strict}


def main() -> int:
    if not TARGET.exists():
        raise FileNotFoundError(f"Missing folder: {TARGET}")

    # Backup current package then clear target folder as requested.
    if BACKUP.exists():
        shutil.rmtree(BACKUP)
    shutil.copytree(TARGET, BACKUP)

    shutil.rmtree(TARGET)
    TARGET.mkdir(parents=True, exist_ok=True)
    for src in sorted(BACKUP.iterdir()):
        if src.is_file():
            shutil.copy2(src, TARGET / src.name)

    index = json.loads((TARGET / "index.json").read_text(encoding="utf-8"))
    config = json.loads((TARGET / "config.json").read_text(encoding="utf-8"))
    fe = json.loads((TARGET / "fe_config.json").read_text(encoding="utf-8"))

    shelf_by_name = {
        m["name"]: m
        for m in config.get("bookShelfConfig", [])
        if isinstance(m, dict) and "name" in m
    }
    fe_by_name = {
        m["name"]: m
        for m in fe.get("modes", [])
        if isinstance(m, dict) and "name" in m
    }

    changed_modes = 0

    for mode in index.get("modes", []):
        if not isinstance(mode, dict):
            continue
        name = mode.get("name")
        if not isinstance(name, str):
            continue

        lookup_file = TARGET / mode["weights"]
        books_file = TARGET / mode["events"]
        rows = read_lookup(lookup_file)
        if not rows:
            continue

        peak, _hhi = payout_level_concentration(rows)
        cap = CAP_BUY100 if name.startswith("buy100_") else CAP_NORMAL

        target_raw = float(mode.get("rtp", 0.9605)) * float(mode.get("cost", 1.0)) * 100.0

        # If strict cap is mathematically infeasible for this support/mean pair,
        # drive toward the tightest feasible cap instead of stalling at a hard limit.
        cap_work = cap
        if not name.startswith("buy100_"):
            raw_levels = [raw for _, _, raw in rows]
            min_cap = min_feasible_cap_for_mean(raw_levels, target_raw)
            cap_work = max(cap, min_cap + 1e-9)

        touched = False
        if peak > cap_work:
            for _ in range(10):
                rows, changed = reduce_peak(rows, cap_work)
                if not changed:
                    break
                rows = recenter_mean_raw(rows, target_raw)
                touched = True
                peak_now, _ = payout_level_concentration(rows)
                if peak_now <= cap_work:
                    break

        # Borderline cleanup: when strict cap is feasible, force a tiny margin so
        # numeric/round-trip effects do not leave 1e-6 style overshoots.
        peak_now, _ = payout_level_concentration(rows)
        if (not name.startswith("buy100_")) and peak_now > cap and cap_work <= (cap + 1e-6):
            for _ in range(6):
                rows, changed = reduce_peak(rows, cap - 1e-6)
                if not changed:
                    break
                rows = recenter_mean_raw(rows, target_raw)
                touched = True
                peak_now, _ = payout_level_concentration(rows)
                if peak_now <= cap:
                    break

        # Stake compliance gates: max-win achievability and base STD band.
        for _ in range(3):
            changed_gate = False
            if enforce_max_win_achievability(rows, target_raw, MAX_WIN_MAX_ODDS):
                rows = recenter_mean_raw(rows, target_raw)
                touched = True
                changed_gate = True
            if enforce_std_band(rows, target_raw):
                rows = recenter_mean_raw(rows, target_raw)
                touched = True
                changed_gate = True
            if not changed_gate:
                break

        # Keep max win metadata aligned with final lookup state.
        max_win_lookup = max(raw for _, _, raw in rows) / 100.0
        mode["max_win"] = round(max_win_lookup, 6)

        # Write lookup and book weights.
        write_lookup(lookup_file, rows)
        weight_by_id = {sid: wt for sid, wt, _ in rows}
        rewrite_books_weight(books_file, weight_by_id)

        # Update config / FE maxWin mirror.
        cfg_mode = shelf_by_name.get(name)
        if cfg_mode is not None:
            cfg_mode["maxWin"] = round(max_win_lookup, 6)
        fe_mode = fe_by_name.get(name)
        if fe_mode is not None:
            fe_mode["maxWin"] = round(max_win_lookup, 6)

        if touched:
            changed_modes += 1

    # Refresh sha references in config.
    for entry in config.get("bookShelfConfig", []):
        if not isinstance(entry, dict):
            continue
        table_file = TARGET / entry["tables"][0]["file"]
        books_file = TARGET / entry["booksFile"]["file"]
        force_file = TARGET / entry["forceFile"]["file"]
        entry["tables"][0]["sha256"] = sha256(table_file)
        entry["booksFile"]["sha256"] = sha256(books_file)
        entry["forceFile"]["sha256"] = sha256(force_file)

    # frontend hash ref
    fe_name = config.get("frontendConfig", {}).get("file", "fe_config.json")
    config["frontendConfig"]["sha256"] = sha256(TARGET / fe_name)

    (TARGET / "index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")
    (TARGET / "config.json").write_text(json.dumps(config, indent=4), encoding="utf-8")
    (TARGET / "fe_config.json").write_text(json.dumps(fe, indent=4), encoding="utf-8")

    excel_stats = build_excel(TARGET, OUT_XLSX)

    print(f"Rebuilt folder: {TARGET.as_posix()}")
    print(f"Backup saved: {BACKUP.as_posix()}")
    print(f"Modes changed by anti-peak transform: {changed_modes}")
    print(f"Excel regenerated: {OUT_XLSX.as_posix()}")
    print(f"Peak modes after rebuild: {excel_stats['peak_modes']} / {excel_stats['modes']}")
    print(f"Strict-cap infeasible modes: {excel_stats['strict_infeasible_modes']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
