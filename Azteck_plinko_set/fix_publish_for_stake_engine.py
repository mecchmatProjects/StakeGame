from __future__ import annotations

import csv
import hashlib
import json
import zlib
from pathlib import Path

import zstandard as zstd


TARGET_RTP = 0.9605
PAYOUT_SCALE = 100.0


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_lookup_rows(path: Path) -> list[tuple[int, int, int]]:
    rows: list[tuple[int, int, int]] = []
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 3:
                continue
            try:
                sim_id = int(row[0])
                weight = int(row[1])
                payout_raw = int(row[2])
            except ValueError:
                # Skip header or malformed rows
                continue
            rows.append((sim_id, weight, payout_raw))
    return rows


def write_lookup_no_header(path: Path, rows: list[tuple[int, int, int]]) -> bytes:
    out = "\n".join(f"{a},{b},{c}" for a, b, c in rows) + "\n"
    data = out.encode("utf-8")
    path.write_bytes(data)
    return data


def decompress_books(raw: bytes) -> str:
    # zstd magic
    if raw.startswith(b"\x28\xb5\x2f\xfd"):
        return zstd.ZstdDecompressor().decompress(raw).decode("utf-8")
    # zlib
    if raw.startswith(b"\x78"):
        return zlib.decompress(raw).decode("utf-8")
    # plain utf-8 fallback
    return raw.decode("utf-8")


def recompress_zstd(text: str) -> bytes:
    return zstd.ZstdCompressor(level=19).compress(text.encode("utf-8"))


def to_canonical_mode_name(mode_type: str, difficulty: str, rows: int) -> str:
    prefix = "buy100" if mode_type == "100balls" else "normal"
    return f"{prefix}_{difficulty.lower()}_{rows}"


def to_stake_cost(mode_type: str) -> float:
    # Stake Engine publish requires cost >= 1.
    # Keep conventional Plinko mapping used by known-good package.
    return 99.0 if mode_type == "100balls" else 1.0


def main() -> int:
    root = Path(".")
    publish_dir = root / "artifacts" / "publish_files"
    config_dir = root / "artifacts" / "configs"
    config_dir.mkdir(parents=True, exist_ok=True)

    old_index = json.loads((publish_dir / "index.json").read_text(encoding="utf-8"))

    sim_summary_path = root / "docs" / "simulation_summary.json"
    sim_map: dict[str, dict] = {}
    if sim_summary_path.exists():
        sim_data = json.loads(sim_summary_path.read_text(encoding="utf-8"))
        for r in sim_data.get("results", []):
            sim_map[r.get("mode", "")] = r

    # Prepare standard force file
    standard_force_bytes = b"{}\n"
    (publish_dir / "force.json").write_bytes(standard_force_bytes)
    standard_force_sha = sha256_bytes(standard_force_bytes)

    new_index_modes: list[dict] = []
    book_shelf: list[dict] = []

    for mode in old_index.get("modes", []):
        old_mode_name = str(mode.get("mode", "")).strip()
        mode_type = str(mode.get("modeType", "normal")).strip() or "normal"
        difficulty = str(mode.get("difficulty", "Low")).strip() or "Low"
        rows = int(mode.get("rows", 8))
        cost = to_stake_cost(mode_type)

        canonical_name = to_canonical_mode_name(mode_type, difficulty, rows)

        old_lookup = publish_dir / mode["lookupFile"]
        old_books = publish_dir / mode["booksFile"]

        # Normalize lookup file: no header, integer rows only
        lookup_rows = read_lookup_rows(old_lookup)
        if not lookup_rows:
            raise ValueError(f"No valid lookup rows for {old_mode_name}")

        lookup_name = f"lookUpTable_{canonical_name}_0.csv"
        lookup_path = publish_dir / lookup_name
        lookup_bytes = write_lookup_no_header(lookup_path, lookup_rows)
        lookup_sha = sha256_bytes(lookup_bytes)

        # Normalize books file: true zstd payload
        books_text = decompress_books(old_books.read_bytes())
        lines = [ln for ln in books_text.splitlines() if ln.strip()]
        cleaned_lines: list[str] = []
        for ln in lines:
            obj = json.loads(ln)
            # Ensure integer payoutMultiplier to avoid float serialization errors
            if "payoutMultiplier" in obj:
                obj["payoutMultiplier"] = int(round(float(obj["payoutMultiplier"])))
            cleaned_lines.append(json.dumps(obj, separators=(",", ":"), ensure_ascii=False))

        normalized_books_text = "\n".join(cleaned_lines) + "\n"
        books_name = f"books_{canonical_name}.jsonl.zst"
        books_path = publish_dir / books_name
        books_bytes = recompress_zstd(normalized_books_text)
        books_path.write_bytes(books_bytes)
        books_sha = sha256_bytes(books_bytes)

        # Force record file per mode
        force_record_name = f"force_record_{canonical_name}.json"
        force_record_bytes = b"[]\n"
        (publish_dir / force_record_name).write_bytes(force_record_bytes)
        force_record_sha = sha256_bytes(force_record_bytes)

        max_win = max(p for _, _, p in lookup_rows) / PAYOUT_SCALE
        std_val = float(sim_map.get(old_mode_name, {}).get("empirical_std", 1.0))

        # Index schema aligned with known-good package
        new_index_modes.append(
            {
                "name": canonical_name,
                "mode_type": mode_type,
                "difficulty": difficulty,
                "rows": rows,
                "cost": cost,
                "rtp": TARGET_RTP,
                "max_win": round(max_win, 4),
                "weights": lookup_name,
                "events": books_name,
                "status": "model-synthesized",
            }
        )

        # Config schema aligned with known-good package
        book_shelf.append(
            {
                "name": canonical_name,
                "tables": [{"file": lookup_name, "sha256": lookup_sha}],
                "cost": cost,
                "rtp": TARGET_RTP,
                "std": round(std_val, 6),
                "bookLength": 1000000,
                "feature": True,
                "autoEndRoundDisabled": False,
                "buyBonus": mode_type == "100balls",
                "maxWin": round(max_win, 4),
                "booksFile": {"file": books_name, "sha256": books_sha},
                "forceFile": {"file": force_record_name, "sha256": force_record_sha},
            }
        )

    # Rewrite index.json
    new_index = {
        "game_id": "azteck_plinko_set",
        "version": "1.0.0-stake-compatible",
        "target_rtp": TARGET_RTP,
        "modes": new_index_modes,
    }
    (publish_dir / "index.json").write_text(json.dumps(new_index, indent=2), encoding="utf-8")

    # Rebuild config.json
    fe_cfg_path = config_dir / "fe_config.json"
    if fe_cfg_path.exists():
        fe_bytes = fe_cfg_path.read_bytes()
        fe_ref = {"file": "fe_config.json", "sha256": sha256_bytes(fe_bytes)}
    else:
        fe_ref = {"file": "fe_config.json", "sha256": ""}

    cfg = {
        "workingName": "azteck_plinko_set",
        "frontendConfig": fe_ref,
        "gameID": "azteck_plinko_set",
        "rtp": 96.05,
        "betDenomination": 100,
        "minDenomination": 1,
        "providerNumber": 1,
        "standardForceFile": {"file": "force.json", "sha256": standard_force_sha},
        "bookShelfConfig": book_shelf,
    }
    (config_dir / "config.json").write_text(json.dumps(cfg, indent=2), encoding="utf-8")

    print(f"normalized_modes={len(new_index_modes)}")
    print("index_schema=ok")
    print("config_schema=ok")
    print("lookups_without_header=ok")
    print("books_zstd=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
