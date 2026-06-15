from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check static package readiness and report blocking gaps")
    parser.add_argument("--root", required=True, help="Package root path")
    return parser.parse_args()


def csv_missing_cells(path: Path) -> tuple[int, int]:
    rows = 0
    missing = 0
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows += 1
            bucket_index = (row.get("bucket_index") or "").strip().upper()
            for key, value in row.items():
                # MAX marker rows intentionally carry blank probability values.
                if key == "probability" and bucket_index == "MAX":
                    continue

                if isinstance(value, list):
                    tokens = [str(v).strip() for v in value]
                    if any(t == "" or t.upper() == "TODO" for t in tokens):
                        missing += 1
                    continue

                text = (value or "").strip()
                if text == "" or text.upper() == "TODO":
                    missing += 1
    return rows, missing


def main() -> int:
    args = parse_args()
    root = Path(args.root).resolve()
    inputs = root / "inputs"
    publish = root / "artifacts" / "publish_files"
    docs = root / "docs"

    required_files = [
        inputs / "azteck_plinko_paytables_normal.csv",
        inputs / "azteck_plinko_paytables_100balls.csv",
        inputs / "azteck_plinko_probability_tables.csv",
        inputs / "azteck_plinko_replay_contract.json",
        inputs / "azteck_plinko_rounding_policy.md",
        inputs / "azteck_plinko_known_constraints.json",
        publish / "index.json",
    ]

    print("READINESS CHECK")
    print(f"root={root}")

    missing_paths = [p for p in required_files if not p.exists()]
    for p in required_files:
        print(f"- exists {p.relative_to(root)}: {p.exists()}")

    if missing_paths:
        print("\nBLOCKER: missing required files")
        for p in missing_paths:
            print(f"  - {p}")
        return 2

    csv_files = [
        inputs / "azteck_plinko_paytables_normal.csv",
        inputs / "azteck_plinko_paytables_100balls.csv",
        inputs / "azteck_plinko_probability_tables.csv",
    ]

    total_rows = 0
    total_missing_cells = 0
    for csv_path in csv_files:
        rows, missing = csv_missing_cells(csv_path)
        total_rows += rows
        total_missing_cells += missing
        print(f"- csv {csv_path.name}: rows={rows}, missing_or_todo_cells={missing}")

    index = json.loads((publish / "index.json").read_text(encoding="utf-8"))
    modes = index.get("modes", [])
    lookup_missing = 0
    books_missing = 0

    for mode in modes:
        if not isinstance(mode, dict):
            continue
        lookup = mode.get("weights")
        books = mode.get("events")
        if isinstance(lookup, str) and lookup.strip():
            if not (publish / lookup).exists():
                lookup_missing += 1
        if isinstance(books, str) and books.strip():
            if not (publish / books).exists():
                books_missing += 1

    print(f"- modes in index: {len(modes)}")
    print(f"- missing lookup files referenced by index: {lookup_missing}")
    print(f"- missing books files referenced by index: {books_missing}")

    summary = {
        "root": str(root),
        "csv_rows": total_rows,
        "csv_missing_or_todo_cells": total_missing_cells,
        "modes": len(modes),
        "missing_lookup_files": lookup_missing,
        "missing_books_files": books_missing,
        "ready_for_publish_generation": total_missing_cells == 0,
        "ready_for_validation_pass": len(modes) > 0 and lookup_missing == 0,
    }

    docs.mkdir(parents=True, exist_ok=True)
    out = docs / "readiness_report.json"
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"- wrote readiness report: {out.relative_to(root)}")

    if not summary["ready_for_publish_generation"]:
        print("\nSTATUS: BLOCKED (input templates still contain TODO or empty fields)")
        return 1

    print("\nSTATUS: INPUTS READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
