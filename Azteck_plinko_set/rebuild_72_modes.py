"""
Rebuild Azteck Plinko Set for 72 modes:
  - 36 normal modes  (cost=1, multipliers from Excel)
  - 36 buy100 modes  (cost=99, multipliers = normal * 99, capped)
Mode names: normal_low_8 ... normal_expert_16, buy100_low_8 ... buy100_expert_16
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import zstandard as zstd

# ── constants ───────────────────────────────────────────────────────────────
PAYOUT_SCALE   = 100.0
RTP_TARGET_PCT = 96.05
RTP_MIN_PCT    = 90.0
RTP_MAX_PCT    = 96.70
NORMAL_COST    = 1.0
BUY100_COST    = 99.0
BUY100_MULTIPLIER = 99.0

# Max win caps per difficulty (buy100)
BUY100_MAX_WIN_CAP = {
    "low":    1_584.0,
    "medium": 10_890.0,
    "high":   99_000.0,
    "expert": 100_000.0,
}

# Expert normal max win by rows (from doc P29), row→max_multiplier
EXPERT_NORMAL_MAX = {
    8: 500.0, 9: 1_000.0, 10: 2_000.0, 11: 3_200.0,
    12: 6_200.0, 13: 10_000.0, 14: 23_000.0, 15: 50_000.0, 16: 100_000.0,
}

DIFFICULTIES = ["low", "medium", "high", "expert"]
ROWS_RANGE   = list(range(8, 17))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def rtp_pct(rows: list[tuple[int, int, int]], cost: float) -> float:
    tw = sum(w for _, w, _ in rows)
    if tw <= 0 or cost <= 0:
        return 0.0
    ev = sum(w * p for _, w, p in rows) / tw
    return (ev / PAYOUT_SCALE / cost) * 100.0


def retune_to_target(
    rows: list[tuple[int, int, int]],
    cost: float,
    target_pct: float = RTP_TARGET_PCT,
) -> list[tuple[int, int, int]]:
    """Scale payouts to hit target RTP, then fine-adjust."""
    cur = rtp_pct(rows, cost)
    if cur <= 0:
        return rows
    scale = target_pct / cur
    rows = [(sid, w, max(1, int(round(p * scale)))) for sid, w, p in rows]
    # Fine correction loop
    for _ in range(10):
        cur = rtp_pct(rows, cost)
        diff = target_pct - cur
        if abs(diff) <= 0.03:
            break
        step = 1 if diff > 0 else -1
        rows = [(sid, w, max(1, p + step)) for sid, w, p in rows]
    # Cap to RTP_MAX_PCT
    for _ in range(12):
        if rtp_pct(rows, cost) <= RTP_MAX_PCT:
            break
        rows = [(sid, w, max(1, p - 1)) for sid, w, p in rows]
    return rows


def make_buy100_rows(
    normal_rows: list[tuple[int, int, int]],
    difficulty: str,
) -> list[tuple[int, int, int]]:
    """Scale normal multipliers ×99, then cap each bucket to difficulty's max win."""
    cap_raw = BUY100_MAX_WIN_CAP[difficulty] * PAYOUT_SCALE
    scaled = [(sid, w, min(int(round(p * BUY100_MULTIPLIER)), int(cap_raw))) for sid, w, p in normal_rows]
    return [(sid, w, max(1, p)) for sid, w, p in scaled]


def write_lookup(path: Path, rows: list[tuple[int, int, int]]) -> bytes:
    text = "\n".join(f"{sid},{w},{p}" for sid, w, p in rows) + "\n"
    data = text.encode("utf-8")
    path.write_bytes(data)
    return data


def write_books(
    path: Path,
    rows: list[tuple[int, int, int]],
    mode_name: str,
    mode_type: str,
    difficulty: str,
    n_rows: int,
) -> bytes:
    lines = []
    for sid, w, p in rows:
        obj = {
            "id": sid,
            "mode": mode_name,
            "modeType": mode_type,
            "difficulty": difficulty,
            "rows": n_rows,
            "weight": int(w),
            "outcomeBucketId": sid,
            "payoutMultiplier": int(p),
            "criteria": "deterministic_static_outcome",
            "events": [{"type": "payout", "amount": int(p), "currency": "credit", "id": 1}],
        }
        lines.append(json.dumps(obj, separators=(",", ":"), ensure_ascii=False))
    text = "\n".join(lines) + "\n"
    data = zstd.ZstdCompressor(level=19).compress(text.encode("utf-8"))
    path.write_bytes(data)
    return data


def main() -> int:
    root = Path(".")
    pub  = root / "artifacts" / "publish_files"
    cfg_dir = root / "artifacts" / "configs"
    pub.mkdir(parents=True, exist_ok=True)
    cfg_dir.mkdir(parents=True, exist_ok=True)

    # Load multipliers from Excel-derived JSON (36 configs)
    presets: dict[str, list[float]] = json.loads(
        (root / "inputs" / "preset_multipliers.json").read_text(encoding="utf-8")
    )

    # Helper: get multiplier list for difficulty+rows
    def get_mults(difficulty: str, n_rows: int) -> list[float]:
        diff_cap = difficulty.capitalize()
        key = f"{n_rows}_{diff_cap}"
        return presets.get(key, [])

    index_modes: list[dict] = []
    bookshelf: list[dict] = []

    # Standard force file
    force_bytes = b"{}\n"
    (pub / "force.json").write_bytes(force_bytes)
    force_sha = sha256_bytes(force_bytes)

    mode_id = 0

    for n_rows in ROWS_RANGE:
        for difficulty in DIFFICULTIES:
            mults = get_mults(difficulty, n_rows)
            if not mults:
                print(f"SKIP missing presets for {difficulty} rows={n_rows}")
                continue

            # Convert multipliers to payout_raw (×PAYOUT_SCALE)
            base_rows = [
                (i, 1000, max(1, int(round(m * PAYOUT_SCALE))))
                for i, m in enumerate(mults)
            ]

            # ── NORMAL mode ─────────────────────────────────────────────────
            mode_id += 1
            normal_name = f"normal_{difficulty}_{n_rows}"
            normal_rows = retune_to_target(list(base_rows), NORMAL_COST)

            lut_file = f"lookUpTable_{normal_name}_0.csv"
            bks_file = f"books_{normal_name}.jsonl.zst"
            fr_file  = f"force_record_{normal_name}.json"

            lut_bytes = write_lookup(pub / lut_file, normal_rows)
            bks_bytes = write_books(pub / bks_file, normal_rows, normal_name, "normal", difficulty.capitalize(), n_rows)
            fr_bytes  = b"[]\n"
            (pub / fr_file).write_bytes(fr_bytes)

            max_win_n = max(p for _, _, p in normal_rows) / PAYOUT_SCALE
            rtp_n     = rtp_pct(normal_rows, NORMAL_COST)

            index_modes.append({
                "name": normal_name,
                "mode_type": "normal",
                "difficulty": difficulty.capitalize(),
                "rows": n_rows,
                "cost": NORMAL_COST,
                "rtp": round(rtp_n / 100.0, 6),
                "max_win": round(max_win_n, 4),
                "weights": lut_file,
                "events": bks_file,
                "status": "model-synthesized",
            })
            bookshelf.append({
                "name": normal_name,
                "tables": [{"file": lut_file, "sha256": sha256_bytes(lut_bytes)}],
                "cost": NORMAL_COST,
                "rtp": round(rtp_n / 100.0, 6),
                "std": 1.0,
                "bookLength": 1_000_000,
                "feature": True,
                "autoEndRoundDisabled": False,
                "buyBonus": False,
                "maxWin": round(max_win_n, 4),
                "booksFile": {"file": bks_file, "sha256": sha256_bytes(bks_bytes)},
                "forceFile": {"file": fr_file,  "sha256": sha256_bytes(fr_bytes)},
            })

            # ── BUY100 mode ──────────────────────────────────────────────────
            mode_id += 1
            buy_name = f"buy100_{difficulty}_{n_rows}"
            buy_raw  = make_buy100_rows(base_rows, difficulty)
            buy_rows = retune_to_target(buy_raw, BUY100_COST)

            lut_file2 = f"lookUpTable_{buy_name}_0.csv"
            bks_file2 = f"books_{buy_name}.jsonl.zst"
            fr_file2  = f"force_record_{buy_name}.json"

            lut_bytes2 = write_lookup(pub / lut_file2, buy_rows)
            bks_bytes2 = write_books(pub / bks_file2, buy_rows, buy_name, "100balls", difficulty.capitalize(), n_rows)
            fr_bytes2  = b"[]\n"
            (pub / fr_file2).write_bytes(fr_bytes2)

            max_win_b = max(p for _, _, p in buy_rows) / PAYOUT_SCALE
            rtp_b     = rtp_pct(buy_rows, BUY100_COST)

            index_modes.append({
                "name": buy_name,
                "mode_type": "100balls",
                "difficulty": difficulty.capitalize(),
                "rows": n_rows,
                "cost": BUY100_COST,
                "rtp": round(rtp_b / 100.0, 6),
                "max_win": round(max_win_b, 4),
                "weights": lut_file2,
                "events": bks_file2,
                "status": "model-synthesized",
            })
            bookshelf.append({
                "name": buy_name,
                "tables": [{"file": lut_file2, "sha256": sha256_bytes(lut_bytes2)}],
                "cost": BUY100_COST,
                "rtp": round(rtp_b / 100.0, 6),
                "std": 1.0,
                "bookLength": 1_000_000,
                "feature": True,
                "autoEndRoundDisabled": False,
                "buyBonus": True,
                "maxWin": round(max_win_b, 4),
                "booksFile": {"file": bks_file2, "sha256": sha256_bytes(bks_bytes2)},
                "forceFile": {"file": fr_file2, "sha256": sha256_bytes(fr_bytes2)},
            })

            print(f"  {normal_name}  RTP={rtp_n:.4f}%  max={max_win_n:.1f}x")
            print(f"  {buy_name}  RTP={rtp_b:.4f}%  max={max_win_b:.1f}x")

    # ── index.json ───────────────────────────────────────────────────────────
    index = {
        "game_id": "azteck_plinko_set",
        "version": "2.0.0-72modes",
        "target_rtp": 0.9605,
        "modes": index_modes,
    }
    (pub / "index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")

    # ── config.json ──────────────────────────────────────────────────────────
    fe_path = cfg_dir / "fe_config.json"
    if fe_path.exists():
        fe_sha = sha256_bytes(fe_path.read_bytes())
    else:
        fe_sha = ""

    config = {
        "workingName": "azteck_plinko_set",
        "frontendConfig": {"file": "fe_config.json", "sha256": fe_sha},
        "gameID": "azteck_plinko_set",
        "rtp": 96.05,
        "betDenomination": 100,
        "minDenomination": 1,
        "providerNumber": 1,
        "standardForceFile": {"file": "force.json", "sha256": force_sha},
        "bookShelfConfig": bookshelf,
    }
    (cfg_dir / "config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")

    # Summary
    normal_rtps = [rtp_pct([], NORMAL_COST)]  # placeholder
    all_rtps = [m["rtp"] * 100 for m in index_modes]
    lo, hi = min(all_rtps), max(all_rtps)

    print(f"\nmodes_generated={len(index_modes)}")
    print(f"rtp_range={lo:.4f}%..{hi:.4f}%")
    print(f"variance_span={hi-lo:.4f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
