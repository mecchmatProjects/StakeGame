from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import zstandard as zstd

PAYOUT_SCALE = 100.0
TARGET_RTP_PCT = 96.0
MAX_ALLOWED_VARIANCE_PCT = 1.0


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_lookup_rows(path: Path) -> list[tuple[int, int, int]]:
    rows: list[tuple[int, int, int]] = []
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) != 3:
                continue
            try:
                sim_id = int(row[0])
                weight = int(row[1])
                payout_raw = int(row[2])
            except ValueError:
                continue
            rows.append((sim_id, weight, payout_raw))
    return rows


def write_lookup_rows(path: Path, rows: list[tuple[int, int, int]]) -> bytes:
    text = "\n".join(f"{sid},{w},{p}" for sid, w, p in rows) + "\n"
    data = text.encode("utf-8")
    path.write_bytes(data)
    return data


def expected_scaled_payout(rows: list[tuple[int, int, int]]) -> float:
    total_weight = sum(w for _, w, _ in rows)
    if total_weight <= 0:
        return 0.0
    expected_raw = sum(w * p for _, w, p in rows) / total_weight
    return expected_raw / PAYOUT_SCALE


def mode_rtp_pct(rows: list[tuple[int, int, int]], cost: float) -> float:
    if cost <= 0:
        return 0.0
    return (expected_scaled_payout(rows) / cost) * 100.0


def load_books(path: Path) -> list[dict]:
    raw = path.read_bytes()
    txt = zstd.ZstdDecompressor().decompress(raw).decode("utf-8")
    return [json.loads(line) for line in txt.splitlines() if line.strip()]


def write_books(path: Path, objs: list[dict]) -> bytes:
    txt = "\n".join(json.dumps(o, separators=(",", ":"), ensure_ascii=False) for o in objs) + "\n"
    raw = zstd.ZstdCompressor(level=19).compress(txt.encode("utf-8"))
    path.write_bytes(raw)
    return raw


def find_weight(rows: list[tuple[int, int, int]], sim_id: int) -> int:
    for sid, w, _ in rows:
        if sid == sim_id:
            return w
    return 1


def find_payout(rows: list[tuple[int, int, int]], sim_id: int) -> int:
    for sid, _, p in rows:
        if sid == sim_id:
            return p
    return 1


def main() -> int:
    root = Path(".")
    publish_dir = root / "artifacts" / "publish_files"
    config_path = root / "artifacts" / "configs" / "config.json"
    index_path = publish_dir / "index.json"

    index_data = json.loads(index_path.read_text(encoding="utf-8"))
    config_data = json.loads(config_path.read_text(encoding="utf-8"))

    cfg_by_name = {entry.get("name"): entry for entry in config_data.get("bookShelfConfig", [])}

    before: list[tuple[str, float]] = []
    after: list[tuple[str, float]] = []

    for mode in index_data.get("modes", []):
        name = mode["name"]
        cost = float(mode["cost"])
        lookup_file = mode["weights"]
        books_file = mode["events"]

        lookup_path = publish_dir / lookup_file
        books_path = publish_dir / books_file

        rows = read_lookup_rows(lookup_path)
        if not rows:
            continue

        current_pct = mode_rtp_pct(rows, cost)
        before.append((name, current_pct))

        if current_pct <= 0:
            continue

        scale = TARGET_RTP_PCT / current_pct
        tuned_rows = [(sid, w, max(1, int(round(p * scale)))) for sid, w, p in rows]

        # Small correction loop to reduce rounding drift
        for _ in range(5):
            tuned_pct = mode_rtp_pct(tuned_rows, cost)
            drift = TARGET_RTP_PCT - tuned_pct
            if abs(drift) <= 0.02:
                break
            step = 1 if drift > 0 else -1
            tuned_rows = [(sid, w, max(1, p + step)) for sid, w, p in tuned_rows]

        lookup_bytes = write_lookup_rows(lookup_path, tuned_rows)

        # Sync books payload with lookup payouts and weights
        books_objs = load_books(books_path)
        for obj in books_objs:
            sim_id = int(obj.get("id", 0))
            payout = find_payout(tuned_rows, sim_id)
            weight = find_weight(tuned_rows, sim_id)
            obj["payoutMultiplier"] = int(payout)
            obj["weight"] = int(weight)
            events = obj.get("events")
            if isinstance(events, list):
                for event in events:
                    if isinstance(event, dict) and "amount" in event:
                        event["amount"] = int(payout)

        books_bytes = write_books(books_path, books_objs)

        tuned_pct = mode_rtp_pct(tuned_rows, cost)
        after.append((name, tuned_pct))

        mode["rtp"] = round(tuned_pct / 100.0, 6)
        mode["max_win"] = round(max(p for _, _, p in tuned_rows) / PAYOUT_SCALE, 4)

        cfg_entry = cfg_by_name.get(name)
        if cfg_entry:
            cfg_entry["rtp"] = round(tuned_pct / 100.0, 6)
            cfg_entry["maxWin"] = round(max(p for _, _, p in tuned_rows) / PAYOUT_SCALE, 4)
            if cfg_entry.get("tables") and isinstance(cfg_entry["tables"], list):
                cfg_entry["tables"][0]["sha256"] = sha256_bytes(lookup_bytes)
            if isinstance(cfg_entry.get("booksFile"), dict):
                cfg_entry["booksFile"]["sha256"] = sha256_bytes(books_bytes)

    index_path.write_text(json.dumps(index_data, indent=2), encoding="utf-8")
    config_path.write_text(json.dumps(config_data, indent=2), encoding="utf-8")

    if before and after:
        bvals = [v for _, v in before]
        avals = [v for _, v in after]
        before_range = max(bvals) - min(bvals)
        after_range = max(avals) - min(avals)
        print(f"before_range_pct={before_range:.4f}")
        print(f"after_range_pct={after_range:.4f}")
        print(f"after_min_pct={min(avals):.4f}")
        print(f"after_max_pct={max(avals):.4f}")
        print(f"within_limit={after_range <= MAX_ALLOWED_VARIANCE_PCT}")

    print("retune_all_modes_done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
