from __future__ import annotations

import argparse
import csv
import hashlib
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

import zstandard as zstd


@dataclass
class ModeCheck:
    mode: str
    lookup_rows: int
    book_rows: int
    payout_array_match: bool
    settlement_match: bool
    table_hash_match: bool
    book_hash_match: bool
    max_win_match: bool
    issues: list[str]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_lookup_payouts(path: Path) -> list[int]:
    payouts: list[int] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.reader(handle):
            if len(row) < 3:
                continue
            payouts.append(int(float(row[2])))
    return payouts


def read_books(path: Path) -> list[dict]:
    dctx = zstd.ZstdDecompressor()
    with path.open("rb") as handle:
        text = dctx.stream_reader(handle).read().decode("utf-8")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def get_round_settlement_payout_int(row: dict) -> int:
    for event in row.get("events", []):
        if event.get("type") == "round_settlement":
            return int(round(float(event.get("payoutMultiplier", 0.0)) * 100))
    raise ValueError(f"Row {row.get('id')} missing round_settlement event")


def mode_check(package_root: Path, config_mode: dict) -> ModeCheck:
    publish_dir = package_root / "artifacts" / "publish_files"
    configs_dir = package_root / "artifacts" / "configs"

    mode = str(config_mode["name"])
    table_file = publish_dir / str(config_mode["tables"][0]["file"])
    book_file = publish_dir / str(config_mode["booksFile"]["file"])
    event_config_file = configs_dir / f"event_config_{mode}.json"

    issues: list[str] = []
    lut_payouts = read_lookup_payouts(table_file)
    books = read_books(book_file)
    book_root_payouts = [int(row["payoutMultiplier"]) for row in books]
    settlement_payouts = [get_round_settlement_payout_int(row) for row in books]

    payout_array_match = lut_payouts == book_root_payouts
    if not payout_array_match:
        issues.append("lookup table payouts do not match top-level book payoutMultiplier array")

    settlement_match = lut_payouts == settlement_payouts
    if not settlement_match:
        issues.append("lookup table payouts do not match round_settlement event payouts")

    table_hash_match = sha256(table_file) == str(config_mode["tables"][0]["sha256"])
    if not table_hash_match:
        issues.append("lookup table sha256 mismatch vs config.json")

    book_hash_match = sha256(book_file) == str(config_mode["booksFile"]["sha256"])
    if not book_hash_match:
        issues.append("books sha256 mismatch vs config.json")

    max_win_match = True
    if event_config_file.exists():
        event_cfg = load_json(event_config_file)
        settlement = event_cfg.get("round_settlement", {})
        settlement_max = float(settlement.get("payoutMultiplier", 0.0))
        config_max = float(config_mode.get("maxWin", 0.0))
        max_win_match = abs(settlement_max - config_max) < 1e-9
        if not max_win_match:
            issues.append("event_config round_settlement payout does not match config maxWin")

    if len(lut_payouts) != len(books):
        issues.append("lookup row count does not match books row count")

    return ModeCheck(
        mode=mode,
        lookup_rows=len(lut_payouts),
        book_rows=len(books),
        payout_array_match=payout_array_match,
        settlement_match=settlement_match,
        table_hash_match=table_hash_match,
        book_hash_match=book_hash_match,
        max_win_match=max_win_match,
        issues=issues,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify a static Stake Engine package before submission")
    parser.add_argument("--root", required=True, help="Package root, e.g. math-sdk/games/treasure_dice_final")
    parser.add_argument("--report", default="", help="Optional JSON report output path")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    config_path = root / "artifacts" / "configs" / "config.json"
    fe_path = root / "artifacts" / "configs" / "config_fe_treasure_dice.json"
    index_path = root / "artifacts" / "publish_files" / "index.json"

    config = load_json(config_path)
    frontend = load_json(fe_path)
    index = load_json(index_path)

    config_modes = [entry["name"] for entry in config["bookShelfConfig"]]
    index_modes = [entry["name"] for entry in index["modes"]]
    frontend_modes = list(frontend.get("betModes", {}).keys())

    package_issues: list[str] = []
    if config_modes != index_modes:
        package_issues.append("config.json bookShelfConfig order/content does not match index.json modes")
    if sorted(config_modes) != sorted(frontend_modes):
        package_issues.append("frontend betModes do not match backend active modes")

    fe_ref = config.get("frontendConfig", {})
    if str(fe_ref.get("file", "")) != fe_path.name:
        package_issues.append("config.json frontendConfig file does not point to active frontend config")
    elif sha256(fe_path) != str(fe_ref.get("sha256", "")):
        package_issues.append("frontend config sha256 mismatch vs config.json")

    mode_results = [mode_check(root, entry) for entry in config["bookShelfConfig"]]
    all_ok = not package_issues and all(not result.issues for result in mode_results)

    report = {
        "package_root": str(root),
        "ready_for_submission": all_ok,
        "package_issues": package_issues,
        "modes": [asdict(result) for result in mode_results],
    }

    if args.report:
        Path(args.report).write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps(report, indent=2))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())