#!/usr/bin/env python3
"""Portable Excel -> Stake Engine artifact builder for Azteck Plinko.

Run this on any environment that has Python 3.10+, ``openpyxl`` and
``zstandard`` installed. It reads an *audit workbook* produced by
``build_static_game_full_xlsx.py`` (the "...audit_formulas.xlsx" format) and
regenerates a complete publishable package from it:

    artifacts/publish_files/
        lookUpTable_<mode>_0.csv      (exact, copied from the workbook)
        books_<mode>.jsonl.zst        (regenerated, zstd-compressed JSONL)
        index.json
        config.json
        fe_config.json
        force.json
        force_record_<mode>.json

How the data is recovered from the workbook
--------------------------------------------
The audit workbook stores one detail sheet per mode (sheet title == mode name)
whose ``sim_id / weight / payout_raw`` columns ARE the lookup table. Those rows
are copied verbatim, so the published lookup tables and all normal-mode books
are byte-for-byte faithful to the audited package.

Buy-bonus (``100balls``) books additionally need a 100-ball replay sequence per
outcome, which the audit workbook does NOT store (only the settled payout is
recorded). For those modes we synthesise a *settlement-consistent* 100-ball
sequence: 100 marker balls whose per-stake average settles to exactly the
audited payout (``round((sum/100) * 99) == payout_raw``). The settlement value,
lookup weights and payouts therefore match the audit exactly; only the
purely-cosmetic individual ball path differs from the original generator run.

Usage
-----
    python build_azteck_artifacts_from_excel.py \
        --excel AzteckPlinkoFull_audit_formulas.xlsx \
        --root  out_package \
        --zip

    python build_azteck_artifacts_from_excel.py --excel audit.xlsx --dry-run
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import sys
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

try:
    import openpyxl
except ImportError:  # pragma: no cover - dependency guard
    sys.exit("ERROR: openpyxl is required. Install with: pip install openpyxl")

try:
    import zstandard as zstd
except ImportError:  # pragma: no cover - dependency guard
    sys.exit("ERROR: zstandard is required. Install with: pip install zstandard")


# --------------------------------------------------------------------------- #
# Constants (kept in sync with rebuild_azteck_final_symmetric.py).
# --------------------------------------------------------------------------- #
VERSION = "0.0.6-std-bounded-symmetric-design"
PAYOUT_SCALE = 100
TARGET_RTP = 0.9605
MIN_STD = 0.6
MAX_STD = 60.0
N_BALLS = 100
BUY100_COST = 99.0
NORMAL_COST = 1.0
GAME_ID = "azteck_plinko"

SKIP_SHEETS = {"Summary", "TestVectors"}

# Official bet ladder per game rules (Min 0.01, Max 500.00).
BET_VALUES = [
    0.01, 0.02, 0.05, 0.10, 0.20, 0.40, 0.60, 0.80, 1.00, 1.20,
    1.40, 1.60, 1.80, 2.00, 3.00, 4.00, 5.00, 6.00, 7.00, 8.00,
    9.00, 10.00, 12.00, 14.00, 16.00, 18.00, 20.00, 30.00, 40.00,
    50.00, 75.00, 100.00, 150.00, 200.00, 250.00, 300.00, 350.00,
    400.00, 450.00, 500.00,
]


# --------------------------------------------------------------------------- #
# Parsed model.
# --------------------------------------------------------------------------- #
@dataclass
class ModeData:
    name: str
    mode_type: str          # "normal" | "100balls"
    difficulty: str         # "Low" | "Medium" | "High" | "Expert"
    rows: int
    cost: float
    rtp_target: float
    lookup: list[tuple[int, int, int]] = field(default_factory=list)  # (sim_id, weight, payout_raw)


# --------------------------------------------------------------------------- #
# CLI.
# --------------------------------------------------------------------------- #
def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Build a Stake Engine package from an Azteck Plinko audit workbook.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--excel", required=True, help="Path to the audit workbook (*.xlsx).")
    p.add_argument("--root", default="azteck_plinko_from_excel",
                   help="Output package root; artifacts/publish_files is written under it.")
    p.add_argument("--target-rtp", type=float, default=TARGET_RTP,
                   help="Fallback RTP target when the workbook omits one.")
    p.add_argument("--zip", action="store_true",
                   help="Also write a flat <root>/<root_name>_publish.zip of the publish folder.")
    p.add_argument("--skip-validation", action="store_true",
                   help="Skip the post-build consistency report.")
    p.add_argument("--dry-run", action="store_true",
                   help="Parse and report mode coverage only; write nothing.")
    return p.parse_args(argv)


# --------------------------------------------------------------------------- #
# Workbook parsing.
# --------------------------------------------------------------------------- #
def _as_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return None


def _as_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_mode_identity(name: str) -> tuple[str, str, int]:
    """Return (mode_type, difficulty, rows) parsed from a mode/sheet name.

    Examples: ``normal_low_8`` -> ("normal", "Low", 8);
    ``buy100_expert_16`` -> ("100balls", "Expert", 16).
    """
    tokens = name.split("_")
    if len(tokens) < 3:
        raise ValueError(f"Cannot parse mode name {name!r} (expected <prefix>_<difficulty>_<rows>)")
    prefix = tokens[0].lower()
    rows = _as_int(tokens[-1])
    if rows is None:
        raise ValueError(f"Cannot parse row count from mode name {name!r}")
    difficulty = tokens[-2].capitalize()
    mode_type = "100balls" if prefix in {"buy100", "100balls", "buy", "buy100balls"} else "normal"
    return mode_type, difficulty, rows


def find_header_row(ws) -> int | None:
    """Locate the detail header row whose first column is ``sim_id``."""
    limit = min(ws.max_row or 0, 40)
    for r in range(1, limit + 1):
        if str(ws.cell(r, 1).value).strip().lower() == "sim_id":
            return r
    return None


def read_detail_sheet(ws) -> tuple[float | None, float | None, list[tuple[int, int, int]]]:
    """Read (cost, target_rtp, lookup_rows) from a per-mode detail sheet."""
    cost = None
    rtp_target = None
    # The header band stores Cost in B3 and Target RTP in D3 (label/value pairs).
    for r in range(1, min(ws.max_row or 0, 6) + 1):
        for c in range(1, min(ws.max_column or 0, 14) + 1):
            label = ws.cell(r, c).value
            if isinstance(label, str):
                key = label.strip().lower()
                if key == "cost":
                    cost = _as_float(ws.cell(r, c + 1).value)
                elif key in {"target rtp", "rtp target"}:
                    rtp_target = _as_float(ws.cell(r, c + 1).value)

    header_row = find_header_row(ws)
    rows: list[tuple[int, int, int]] = []
    if header_row is None:
        return cost, rtp_target, rows

    for r in range(header_row + 1, (ws.max_row or 0) + 1):
        sid = _as_int(ws.cell(r, 1).value)
        weight = _as_int(ws.cell(r, 2).value)
        payout_raw = _as_int(ws.cell(r, 3).value)
        if sid is None or weight is None or payout_raw is None:
            # First fully-empty / non-numeric row terminates the table
            # (e.g. the CHECK_SUMS footer).
            if ws.cell(r, 1).value in (None, "") and ws.cell(r, 2).value in (None, ""):
                break
            continue
        rows.append((sid, weight, payout_raw))
    return cost, rtp_target, rows


def load_workbook_modes(xlsx_path: Path, fallback_rtp: float) -> list[ModeData]:
    wb = openpyxl.load_workbook(xlsx_path, read_only=True, data_only=True)
    modes: list[ModeData] = []
    try:
        for title in wb.sheetnames:
            if title in SKIP_SHEETS:
                continue
            ws = wb[title]
            try:
                mode_type, difficulty, rows = parse_mode_identity(title)
            except ValueError:
                # Not a recognisable mode sheet; skip quietly.
                continue
            cost, rtp_target, lookup = read_detail_sheet(ws)
            if not lookup:
                print(f"  WARNING: sheet {title!r} has no lookup rows; skipping")
                continue
            if cost is None:
                cost = BUY100_COST if mode_type == "100balls" else NORMAL_COST
            modes.append(ModeData(
                name=title,
                mode_type=mode_type,
                difficulty=difficulty,
                rows=rows,
                cost=float(cost),
                rtp_target=float(rtp_target) if rtp_target is not None else fallback_rtp,
                lookup=lookup,
            ))
    finally:
        wb.close()
    modes.sort(key=lambda m: m.name)
    return modes


# --------------------------------------------------------------------------- #
# Artifact writers.
# --------------------------------------------------------------------------- #
def write_lookup(path: Path, rows: list[tuple[int, int, int]]) -> None:
    payload = "\n".join(f"{sid},{weight},{payout}" for sid, weight, payout in rows) + "\n"
    path.write_bytes(payload.encode("utf-8"))


def write_books_normal(path: Path, mode: ModeData) -> None:
    lines = []
    for sid, weight, payout in mode.lookup:
        bucket = sid - 1
        obj = {
            "id": sid,
            "mode": mode.name,
            "modeType": mode.mode_type,
            "difficulty": mode.difficulty,
            "rows": mode.rows,
            "weight": int(weight),
            "outcomeBucketId": bucket,
            "payoutMultiplier": int(payout),
            "criteria": "deterministic_static_outcome",
            "events": [
                {"type": "round_init", "mode": mode.name, "modeType": mode.mode_type,
                 "difficulty": mode.difficulty, "rows": mode.rows},
                {"type": "trajectory_selected", "outcomeBucketId": bucket},
                {"type": "bucket_landed", "outcomeBucketId": bucket, "payoutMultiplier": int(payout)},
                {"type": "settlement", "totalPayoutMultiplier": int(payout)},
            ],
        }
        lines.append(json.dumps(obj, separators=(",", ":"), ensure_ascii=False))
    text = "\n".join(lines) + "\n"
    path.write_bytes(zstd.ZstdCompressor(level=19).compress(text.encode("utf-8")))


def settlement_raw(ball_sum_raw: int) -> int:
    """Round-half-to-even settlement matching the original generator (np.rint)."""
    return int(round((ball_sum_raw / N_BALLS) * BUY100_COST))


def synth_balls_for_payout(payout_raw: int) -> list[int]:
    """Build 100 marker ball payouts whose settlement equals ``payout_raw`` exactly.

    Returns a list of 100 raw ball payouts (>=0). Stored later with
    ``outcomeBucketId = -1`` because they are settlement markers, not real
    bucket landings (the audit workbook does not retain per-ball buckets).
    """
    if payout_raw <= 0:
        return [0] * N_BALLS
    target_sum = int(round(payout_raw * N_BALLS / BUY100_COST))
    # Nudge the integer ball-sum so the round-half-to-even settlement is exact.
    chosen = target_sum
    if settlement_raw(target_sum) != payout_raw:
        for delta in range(1, N_BALLS + 1):
            if settlement_raw(target_sum + delta) == payout_raw:
                chosen = target_sum + delta
                break
            if target_sum - delta >= 0 and settlement_raw(target_sum - delta) == payout_raw:
                chosen = target_sum - delta
                break
    base = chosen // N_BALLS
    rem = chosen - base * N_BALLS
    balls = [base + 1] * rem + [base] * (N_BALLS - rem)
    return balls


def write_books_buy100(path: Path, mode: ModeData) -> int:
    """Write buy100 books; return the count of settlement mismatches (should be 0)."""
    lines = []
    mismatches = 0
    for sid, weight, payout in mode.lookup:
        balls = synth_balls_for_payout(int(payout))
        if settlement_raw(sum(balls)) != int(payout):
            mismatches += 1
        ball_events = [
            {"type": "ball_landed", "ballIndex": i, "outcomeBucketId": -1,
             "payoutMultiplier": int(b)}
            for i, b in enumerate(balls)
        ]
        obj = {
            "id": sid,
            "mode": mode.name,
            "modeType": mode.mode_type,
            "difficulty": mode.difficulty,
            "rows": mode.rows,
            "weight": int(weight),
            "ballCount": N_BALLS,
            "outcomeBucketId": -1,
            "payoutMultiplier": int(payout),
            "criteria": "settlement_consistent_100balls_from_audit",
            "events": [
                {"type": "round_init", "mode": mode.name, "modeType": mode.mode_type,
                 "difficulty": mode.difficulty, "rows": mode.rows, "ballCount": N_BALLS},
                *ball_events,
                {"type": "settlement", "totalPayoutMultiplier": int(payout), "ballCount": N_BALLS},
            ],
        }
        lines.append(json.dumps(obj, separators=(",", ":"), ensure_ascii=False))
    text = "\n".join(lines) + "\n"
    path.write_bytes(zstd.ZstdCompressor(level=19).compress(text.encode("utf-8")))
    return mismatches


def mode_metrics(rows: list[tuple[int, int, int]], cost: float) -> tuple[float, float, float]:
    total = sum(w for _, w, _ in rows)
    if total <= 0 or cost <= 0:
        return 0.0, 0.0, 0.0
    vals = [p / PAYOUT_SCALE for _, _, p in rows]
    mean = sum((w / total) * v for (_, w, _), v in zip(rows, vals))
    var = sum((w / total) * ((v - mean) ** 2) for (_, w, _), v in zip(rows, vals))
    return mean / cost, math.sqrt(var) / cost, max(vals)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def lookup_stats(path: Path, cost: float) -> tuple[int, float, float]:
    rows: list[tuple[int, int, int]] = []
    with open(path, "r", encoding="utf-8", newline="") as f:
        for r in csv.reader(f):
            if len(r) >= 3:
                try:
                    rows.append((int(r[0]), int(r[1]), int(r[2])))
                except ValueError:
                    pass
    if not rows:
        return 0, 0.0, 0.0
    tw = sum(w for _, w, _ in rows)
    _, std_norm, max_win = mode_metrics(rows, cost)
    return tw, std_norm, max_win


def write_index(publish_dir: Path, modes: list[ModeData], target_rtp: float) -> list[dict]:
    mode_entries: list[dict] = []
    for m in modes:
        rtp, _std, max_win = mode_metrics(m.lookup, m.cost)
        mode_entries.append({
            "name": m.name,
            "mode_type": m.mode_type,
            "difficulty": m.difficulty,
            "rows": m.rows,
            "cost": m.cost,
            "rtp": round(rtp, 6),
            "max_win": round(max_win, 6),
            "weights": f"lookUpTable_{m.name}_0.csv",
            "events": f"books_{m.name}.jsonl.zst",
            "status": "rebuilt-from-audit-workbook",
        })
    index = {
        "game_id": GAME_ID,
        "version": VERSION,
        "target_rtp": target_rtp,
        "std_rule": {"min": MIN_STD, "max": MAX_STD, "basis": "normalized_payout_multiplier"},
        "source": "build_azteck_artifacts_from_excel.py",
        "modes": mode_entries,
    }
    (publish_dir / "index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")
    return mode_entries


def write_force_files(publish_dir: Path, mode_entries: list[dict]) -> str:
    force_data = {m["name"]: {} for m in mode_entries}
    (publish_dir / "force.json").write_text(json.dumps(force_data, indent=4), encoding="utf-8")
    for m in mode_entries:
        (publish_dir / f"force_record_{m['name']}.json").write_text("[]", encoding="utf-8")
    return sha256(publish_dir / f"force_record_{mode_entries[0]['name']}.json")


def write_configs(publish_dir: Path, mode_entries: list[dict], target_rtp: float,
                  force_rec_hash: str) -> None:
    force_json_path = publish_dir / "force.json"

    fe_cfg = {
        "gameId": GAME_ID,
        "version": VERSION,
        "rtpTarget": target_rtp,
        "betValues": BET_VALUES,
        "minBet": BET_VALUES[0],
        "maxBet": BET_VALUES[-1],
        "modes": [{"name": m["name"], "cost": m["cost"], "maxWin": m["max_win"]} for m in mode_entries],
    }
    fe_path = publish_dir / "fe_config.json"
    fe_path.write_text(json.dumps(fe_cfg, indent=4), encoding="utf-8")
    fe_sha = sha256(fe_path)

    bsc = []
    for m in mode_entries:
        name = m["name"]
        lut_path = publish_dir / m["weights"]
        book_path = publish_dir / m["events"]
        cost = float(m["cost"])
        tw, std_norm, max_win = lookup_stats(lut_path, cost)
        bsc.append({
            "name": name,
            "tables": [{"file": m["weights"], "sha256": sha256(lut_path)}],
            "cost": cost,
            "rtp": float(m.get("rtp", target_rtp)),
            "std": round(std_norm, 6),
            "bookLength": tw,
            "feature": True,
            "autoEndRoundDisabled": False,
            "buyBonus": m["mode_type"] == "100balls",
            "maxWin": float(m.get("max_win", max_win)),
            "booksFile": {"file": m["events"], "sha256": sha256(book_path)},
            "forceFile": {"file": f"force_record_{name}.json", "sha256": force_rec_hash},
        })

    be_config = {
        "workingName": GAME_ID,
        "frontendConfig": {"file": "fe_config.json", "sha256": fe_sha},
        "gameID": GAME_ID,
        "rtp": round(target_rtp * 100, 4),
        "betDenomination": 100,
        "minDenomination": 1,
        "betValues": BET_VALUES,
        "providerNumber": 1,
        "standardForceFile": {"file": "force.json", "sha256": sha256(force_json_path)},
        "bookShelfConfig": bsc,
    }
    (publish_dir / "config.json").write_text(json.dumps(be_config, indent=4), encoding="utf-8")


def zip_publish_flat(publish_dir: Path, zip_path: Path) -> None:
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in sorted(publish_dir.iterdir()):
            if file.is_file():
                zf.write(file, arcname=file.name)


# --------------------------------------------------------------------------- #
# Orchestration.
# --------------------------------------------------------------------------- #
def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    xlsx_path = Path(args.excel).resolve()
    if not xlsx_path.exists():
        sys.exit(f"ERROR: workbook not found: {xlsx_path}")

    print(f"Reading audit workbook: {xlsx_path}")
    modes = load_workbook_modes(xlsx_path, args.target_rtp)
    if not modes:
        sys.exit("ERROR: no mode detail sheets found in the workbook.")

    normal_modes = [m for m in modes if m.mode_type == "normal"]
    buy_modes = [m for m in modes if m.mode_type == "100balls"]
    print(f"Parsed {len(modes)} modes ({len(normal_modes)} normal, {len(buy_modes)} buy100).")

    if args.dry_run:
        worst = 0.0
        for m in modes:
            rtp, _std, max_win = mode_metrics(m.lookup, m.cost)
            worst = max(worst, abs(rtp - m.rtp_target))
            print(f"  {m.name:<20} rows={m.rows:<2} cost={m.cost:<5} "
                  f"buckets={len(m.lookup):<6} rtp={rtp:.5f} max_win={max_win:g}")
        print(f"DRY RUN OK. Worst |RTP-target| = {worst:.3e}. No files written.")
        return 0

    root = Path(args.root).resolve()
    publish_dir = root / "artifacts" / "publish_files"
    publish_dir.mkdir(parents=True, exist_ok=True)

    total_mismatch = 0
    worst_drift = 0.0
    for m in modes:
        write_lookup(publish_dir / f"lookUpTable_{m.name}_0.csv", m.lookup)
        if m.mode_type == "100balls":
            total_mismatch += write_books_buy100(publish_dir / f"books_{m.name}.jsonl.zst", m)
        else:
            write_books_normal(publish_dir / f"books_{m.name}.jsonl.zst", m)
        rtp, _std, _max_win = mode_metrics(m.lookup, m.cost)
        worst_drift = max(worst_drift, abs(rtp - m.rtp_target))

    mode_entries = write_index(publish_dir, modes, args.target_rtp)
    force_rec_hash = write_force_files(publish_dir, mode_entries)
    write_configs(publish_dir, mode_entries, args.target_rtp, force_rec_hash)
    print(f"Wrote {len(modes)} lookups + books, index.json, config.json, fe_config.json, "
          f"force.json -> {publish_dir}")

    if args.zip:
        zip_path = root / f"{root.name}_publish.zip"
        zip_publish_flat(publish_dir, zip_path)
        print(f"Wrote flat publish zip: {zip_path}")

    if not args.skip_validation:
        print("--- Validation ---")
        print(f"  Modes written            : {len(modes)}")
        print(f"  Worst |RTP - target|     : {worst_drift:.3e}")
        print(f"  buy100 settlement misses : {total_mismatch}")
        status = "OK" if total_mismatch == 0 else "CHECK"
        print(f"  STATUS: {status}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
