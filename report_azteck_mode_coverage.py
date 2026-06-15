from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Report per-mode coverage quality from probability table")
    parser.add_argument("--root", required=True, help="Package root path")
    return parser.parse_args()


def read_prob_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [{k: (v or "").strip() for k, v in row.items() if k is not None} for row in reader]


def normalize_mode_type(v: str) -> str:
    x = v.strip().lower()
    if x in {"normal", "base", "basegame"}:
        return "normal"
    if x in {"100balls", "buy100", "buy", "feature"}:
        return "100balls"
    return x


def mode_to_tuple(name: str) -> tuple[str, str, str]:
    parts = name.split("_")
    if len(parts) < 3:
        return ("", "", "")
    p = parts[0].lower()
    diff = parts[1].capitalize()
    rows = parts[2]
    mode_type = "100balls" if p == "buy100" else "normal"
    return (mode_type, diff, rows)


def as_float(text: str) -> float | None:
    t = (text or "").strip()
    if not t or t.upper() == "TODO":
        return None
    try:
        return float(t)
    except ValueError:
        return None


def main() -> int:
    args = parse_args()
    root = Path(args.root).resolve()
    index_path = root / "artifacts" / "publish_files" / "index.json"
    prob_path = root / "inputs" / "azteck_plinko_probability_tables.csv"

    if not index_path.exists() or not prob_path.exists():
        raise FileNotFoundError("Missing index or probability table")

    index = json.loads(index_path.read_text(encoding="utf-8"))
    modes = index.get("modes", [])
    prob_rows = read_prob_rows(prob_path)

    grouped: dict[tuple[str, str, str], list[dict[str, str]]] = {}
    for row in prob_rows:
        key = (normalize_mode_type(row.get("mode_type", "")), row.get("difficulty", ""), row.get("rows", ""))
        grouped.setdefault(key, []).append(row)

    coverage_rows: list[dict[str, str | float | int]] = []

    complete_count = 0
    partial_count = 0
    missing_count = 0

    for mode in modes:
        if not isinstance(mode, dict):
            continue
        mode_name = mode.get("name")
        if not isinstance(mode_name, str):
            continue

        mode_type, difficulty, rows = mode_to_tuple(mode_name)
        key = (mode_type, difficulty, rows)
        entries = grouped.get(key, [])

        valid_prob = 0
        valid_mult = 0
        prob_sum = 0.0

        for e in entries:
            p = as_float(e.get("probability", ""))
            m = as_float(e.get("multiplier", ""))
            if p is not None and p > 0:
                valid_prob += 1
                prob_sum += p
            if m is not None:
                valid_mult += 1

        if valid_prob > 0 and valid_mult > 0:
            status = "complete" if abs(prob_sum - 1.0) <= 0.02 else "partial"
        elif entries:
            status = "partial"
        else:
            status = "missing"

        if status == "complete":
            complete_count += 1
        elif status == "partial":
            partial_count += 1
        else:
            missing_count += 1

        coverage_rows.append(
            {
                "mode": mode_name,
                "mode_type": mode_type,
                "difficulty": difficulty,
                "rows": rows,
                "entries": len(entries),
                "valid_multiplier_count": valid_mult,
                "valid_probability_count": valid_prob,
                "probability_sum": round(prob_sum, 6),
                "status": status,
            }
        )

    docs = root / "docs"
    docs.mkdir(parents=True, exist_ok=True)

    csv_out = docs / "mode_coverage_report.csv"
    with csv_out.open("w", encoding="utf-8", newline="") as handle:
        headers = [
            "mode",
            "mode_type",
            "difficulty",
            "rows",
            "entries",
            "valid_multiplier_count",
            "valid_probability_count",
            "probability_sum",
            "status",
        ]
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        for row in coverage_rows:
            writer.writerow(row)

    md_out = docs / "mode_coverage_report.md"
    md_lines = [
        "# Azteck Mode Coverage Report",
        "",
        f"- total modes: {len(coverage_rows)}",
        f"- complete: {complete_count}",
        f"- partial: {partial_count}",
        f"- missing: {missing_count}",
        "",
        "A mode is marked complete when it has at least one valid multiplier and probability rows and probability sum is within 0.02 of 1.0.",
    ]
    md_out.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print(f"Wrote {csv_out}")
    print(f"Wrote {md_out}")
    print(f"complete={complete_count} partial={partial_count} missing={missing_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
