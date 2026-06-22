from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import zstandard as zstd

PAYOUT_SCALE = 100.0
RTP_CAP_PCT = 96.70
TARGET_PCT = 96.50


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_lookup_rows(path: Path) -> list[tuple[int, int, int]]:
    out: list[tuple[int, int, int]] = []
    with open(path, "r", encoding="utf-8", newline="") as f:
        r = csv.reader(f)
        for row in r:
            if len(row) != 3:
                continue
            try:
                sid, w, p = int(row[0]), int(row[1]), int(row[2])
            except ValueError:
                continue
            out.append((sid, w, p))
    return out


def write_lookup_rows(path: Path, rows: list[tuple[int, int, int]]) -> bytes:
    txt = "\n".join(f"{sid},{w},{p}" for sid, w, p in rows) + "\n"
    data = txt.encode("utf-8")
    path.write_bytes(data)
    return data


def rtp_pct(rows: list[tuple[int, int, int]], cost: float) -> float:
    tw = sum(w for _, w, _ in rows)
    if tw <= 0 or cost <= 0:
        return 0.0
    ev_raw = sum(w * p for _, w, p in rows) / tw
    return (ev_raw / PAYOUT_SCALE / cost) * 100.0


def load_books(path: Path) -> list[dict]:
    raw = path.read_bytes()
    txt = zstd.ZstdDecompressor().decompress(raw).decode("utf-8")
    return [json.loads(ln) for ln in txt.splitlines() if ln.strip()]


def write_books(path: Path, objs: list[dict]) -> bytes:
    txt = "\n".join(json.dumps(o, separators=(",", ":"), ensure_ascii=False) for o in objs) + "\n"
    raw = zstd.ZstdCompressor(level=19).compress(txt.encode("utf-8"))
    path.write_bytes(raw)
    return raw


def main() -> int:
    root = Path(".")
    pub = root / "artifacts" / "publish_files"
    idx_path = pub / "index.json"
    cfg_path = root / "artifacts" / "configs" / "config.json"

    idx = json.loads(idx_path.read_text(encoding="utf-8"))
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))

    cfg_by_name = {e.get("name"): e for e in cfg.get("bookShelfConfig", [])}

    touched = 0
    for m in idx.get("modes", []):
        name = m.get("name", "")
        if not str(name).startswith("normal_expert_"):
            continue

        cost = float(m.get("cost", 1.0))
        lut = pub / m["weights"]
        bks = pub / m["events"]

        rows = read_lookup_rows(lut)
        if not rows:
            continue

        cur = rtp_pct(rows, cost)
        if cur <= RTP_CAP_PCT:
            continue

        # Scale payouts to target below cap.
        scale = TARGET_PCT / cur
        tuned = [(sid, w, max(1, int(round(p * scale)))) for sid, w, p in rows]

        # Fine adjustment if still above cap due to rounding.
        for _ in range(8):
            now = rtp_pct(tuned, cost)
            if now <= RTP_CAP_PCT:
                break
            tuned = [(sid, w, max(1, p - 1)) for sid, w, p in tuned]

        now = rtp_pct(tuned, cost)

        lut_bytes = write_lookup_rows(lut, tuned)

        by_id = {sid: (w, p) for sid, w, p in tuned}
        objs = load_books(bks)
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
        bks_bytes = write_books(bks, objs)

        m["rtp"] = round(now / 100.0, 6)
        m["max_win"] = round(max(p for _, _, p in tuned) / PAYOUT_SCALE, 4)

        ce = cfg_by_name.get(name)
        if ce:
            ce["rtp"] = round(now / 100.0, 6)
            ce["maxWin"] = round(max(p for _, _, p in tuned) / PAYOUT_SCALE, 4)
            if ce.get("tables") and isinstance(ce["tables"], list):
                ce["tables"][0]["sha256"] = sha256_bytes(lut_bytes)
            if isinstance(ce.get("booksFile"), dict):
                ce["booksFile"]["sha256"] = sha256_bytes(bks_bytes)

        touched += 1
        print(f"retuned {name}: {cur:.6f}% -> {now:.6f}%")

    idx_path.write_text(json.dumps(idx, indent=2), encoding="utf-8")
    cfg_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")

    print(f"retuned_modes={touched}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
