from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import zstandard as zstd


def mode_rtp_pct(rows: list[tuple[int, int, int]], cost: float) -> float:
    tw = sum(w for _, w, _ in rows)
    if tw <= 0 or cost <= 0:
        return 0.0
    ev = sum(w * p for _, w, p in rows) / tw
    return (ev / 100.0 / cost) * 100.0


def main() -> int:
    mode_name = "normal_medium_16"
    rtp_cap = 96.70
    rtp_target = 96.55

    pub = Path("artifacts/publish_files")
    idx_path = pub / "index.json"
    cfg_path = Path("artifacts/configs/config.json")

    idx = json.loads(idx_path.read_text(encoding="utf-8"))
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))

    mode = next(m for m in idx["modes"] if m["name"] == mode_name)
    lookup_path = pub / mode["weights"]
    books_path = pub / mode["events"]
    cost = float(mode["cost"])

    rows: list[tuple[int, int, int]] = []
    with open(lookup_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) != 3:
                continue
            try:
                sid, w, p = int(row[0]), int(row[1]), int(row[2])
            except ValueError:
                continue
            rows.append((sid, w, p))

    before = mode_rtp_pct(rows, cost)
    scale = rtp_target / before if before > 0 else 1.0
    rows = [(sid, w, max(1, int(round(p * scale)))) for sid, w, p in rows]

    for _ in range(12):
        now = mode_rtp_pct(rows, cost)
        if now <= rtp_cap:
            break
        rows = [(sid, w, max(1, p - 1)) for sid, w, p in rows]

    after = mode_rtp_pct(rows, cost)

    lookup_text = "\n".join(f"{sid},{w},{p}" for sid, w, p in rows) + "\n"
    lookup_bytes = lookup_text.encode("utf-8")
    lookup_path.write_bytes(lookup_bytes)

    raw_books = books_path.read_bytes()
    books_text = zstd.ZstdDecompressor().decompress(raw_books).decode("utf-8")
    objs = [json.loads(line) for line in books_text.splitlines() if line.strip()]

    by_id = {sid: (w, p) for sid, w, p in rows}
    for obj in objs:
        sid = int(obj.get("id", 0))
        if sid in by_id:
            w, p = by_id[sid]
            obj["weight"] = int(w)
            obj["payoutMultiplier"] = int(p)
            if isinstance(obj.get("events"), list):
                for ev in obj["events"]:
                    if isinstance(ev, dict) and "amount" in ev:
                        ev["amount"] = int(p)

    books_text_new = "\n".join(
        json.dumps(obj, separators=(",", ":"), ensure_ascii=False) for obj in objs
    ) + "\n"
    books_bytes = zstd.ZstdCompressor(level=19).compress(books_text_new.encode("utf-8"))
    books_path.write_bytes(books_bytes)

    mode["rtp"] = round(after / 100.0, 6)
    mode["max_win"] = round(max(p for _, _, p in rows) / 100.0, 4)

    entry = next(e for e in cfg["bookShelfConfig"] if e.get("name") == mode_name)
    entry["rtp"] = round(after / 100.0, 6)
    entry["maxWin"] = round(max(p for _, _, p in rows) / 100.0, 4)
    entry["tables"][0]["sha256"] = hashlib.sha256(lookup_bytes).hexdigest()
    entry["booksFile"]["sha256"] = hashlib.sha256(books_bytes).hexdigest()

    idx_path.write_text(json.dumps(idx, indent=2), encoding="utf-8")
    cfg_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")

    print("mode", mode_name)
    print("before_pct", round(before, 6))
    print("after_pct", round(after, 6))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
