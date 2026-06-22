from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import zstandard as zstd

PAYOUT_SCALE = 100.0


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    pub = Path("artifacts/publish_files")
    cfg_path = Path("artifacts/configs/config.json")
    idx_path = pub / "index.json"

    idx = json.loads(idx_path.read_text(encoding="utf-8"))
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    cfg_by_name = {e.get("name"): e for e in cfg.get("bookShelfConfig", [])}

    books_regen = 0
    force_regen = 0

    for m in idx.get("modes", []):
        name = m["name"]
        mode_type = m.get("mode_type", "normal")
        difficulty = m.get("difficulty", "Low")
        rows_count = int(m.get("rows", 8))
        cost = float(m.get("cost", 1.0))

        # Read lookup CSV
        lut_path = pub / m["weights"]
        rows: list[tuple[int, int, int]] = []
        with open(lut_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) != 3:
                    continue
                try:
                    sid, w, p = int(row[0]), int(row[1]), int(row[2])
                except ValueError:
                    continue
                rows.append((sid, w, p))

        # Rebuild books JSONL from lookup rows
        lines: list[str] = []
        for sid, w, p in rows:
            obj = {
                "id": sid,
                "mode": name,
                "modeType": mode_type,
                "difficulty": difficulty,
                "rows": rows_count,
                "weight": int(w),
                "outcomeBucketId": sid,
                "payoutMultiplier": int(p),
                "criteria": "deterministic_static_outcome",
                "events": [{"type": "payout", "amount": int(p), "currency": "credit", "id": 1}],
            }
            lines.append(json.dumps(obj, separators=(",", ":"), ensure_ascii=False))

        books_text = "\n".join(lines) + "\n"
        books_bytes = zstd.ZstdCompressor(level=19).compress(books_text.encode("utf-8"))
        books_path = pub / m["events"]
        books_path.write_bytes(books_bytes)
        books_regen += 1

        # Rebuild force_record file
        fr_name = f"force_record_{name}.json"
        fr_bytes = b"[]\n"
        (pub / fr_name).write_bytes(fr_bytes)
        force_regen += 1

        # Update config hashes for lookup + books
        lut_bytes = lut_path.read_bytes()
        ce = cfg_by_name.get(name)
        if ce:
            if ce.get("tables") and isinstance(ce["tables"], list):
                ce["tables"][0]["sha256"] = sha256_bytes(lut_bytes)
            if isinstance(ce.get("booksFile"), dict):
                ce["booksFile"]["sha256"] = sha256_bytes(books_bytes)
            if isinstance(ce.get("forceFile"), dict):
                ce["forceFile"]["sha256"] = sha256_bytes(fr_bytes)

    cfg_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")

    print(f"books_regenerated={books_regen}")
    print(f"force_records_regenerated={force_regen}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
