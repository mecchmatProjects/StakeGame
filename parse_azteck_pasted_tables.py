from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Parse pasted Azteck table lines into normalized import CSV with columns: "
            "mode_type,difficulty,rows,bucket_index,multiplier,probability,aggregation_rule,source,notes"
        )
    )
    parser.add_argument("--input", required=True, help="Text file containing pasted table lines")
    parser.add_argument("--output", required=True, help="Output normalized CSV path")
    parser.add_argument("--default-source", default="pasted-input", help="Default source text when not provided in line")
    return parser.parse_args()


KEY_PATTERN = re.compile(r"(mode|mode_type|difficulty|rows|multipliers|probs|probabilities|source|notes|aggregation_rule)\s*=\s*(\[[^\]]*\]|[^;]+)", re.IGNORECASE)


def clean_value(text: str) -> str:
    return text.strip().strip('"').strip("'")


def parse_list(raw: str) -> list[str]:
    value = raw.strip()
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1]
    if not value.strip():
        return []
    parts = [p.strip() for p in value.split(",")]
    return [p for p in parts if p != ""]


def normalize_mode_type(raw: str) -> str:
    val = raw.strip().lower()
    if val in {"normal", "base", "basegame"}:
        return "normal"
    if val in {"100balls", "buy100", "buy", "feature"}:
        return "100balls"
    return val


def parse_line(line: str, line_no: int, default_source: str) -> tuple[list[dict[str, str]], str | None]:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return [], None

    kv: dict[str, str] = {}
    for match in KEY_PATTERN.finditer(stripped):
        key = match.group(1).lower()
        value = clean_value(match.group(2))
        kv[key] = value

    mode = normalize_mode_type(kv.get("mode", kv.get("mode_type", "")))
    difficulty = kv.get("difficulty", "")
    rows = kv.get("rows", "")
    multipliers = parse_list(kv.get("multipliers", ""))
    probs = parse_list(kv.get("probs", kv.get("probabilities", "")))
    source = kv.get("source", default_source)
    notes = kv.get("notes", "")
    aggregation_rule = kv.get("aggregation_rule", "")

    if not mode or not difficulty or not rows:
        return [], f"line {line_no}: missing required mode/difficulty/rows"

    if len(multipliers) == 0:
        return [], f"line {line_no}: multipliers list is empty"

    if len(probs) > 0 and len(probs) != len(multipliers):
        return [], f"line {line_no}: multipliers/probs length mismatch"

    rows_out: list[dict[str, str]] = []
    for idx, m in enumerate(multipliers):
        prob = probs[idx] if idx < len(probs) else ""
        rows_out.append(
            {
                "mode_type": mode,
                "difficulty": difficulty,
                "rows": rows,
                "bucket_index": str(idx),
                "multiplier": m,
                "probability": prob,
                "aggregation_rule": aggregation_rule if mode == "100balls" else "",
                "source": source,
                "notes": notes,
            }
        )

    # Also emit an explicit MAX bucket row using last multiplier.
    rows_out.append(
        {
            "mode_type": mode,
            "difficulty": difficulty,
            "rows": rows,
            "bucket_index": "MAX",
            "multiplier": multipliers[-1],
            "probability": "",
            "aggregation_rule": aggregation_rule if mode == "100balls" else "",
            "source": source,
            "notes": (notes + "; auto MAX from last multiplier").strip("; "),
        }
    )

    return rows_out, None


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    headers = [
        "mode_type",
        "difficulty",
        "rows",
        "bucket_index",
        "multiplier",
        "probability",
        "aggregation_rule",
        "source",
        "notes",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow({h: row.get(h, "") for h in headers})


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        raise FileNotFoundError(input_path)

    lines = input_path.read_text(encoding="utf-8").splitlines()
    all_rows: list[dict[str, str]] = []
    errors: list[str] = []

    for i, line in enumerate(lines, start=1):
        parsed, err = parse_line(line, i, args.default_source)
        if err:
            errors.append(err)
            continue
        all_rows.extend(parsed)

    write_csv(output_path, all_rows)

    print(f"Parsed rows: {len(all_rows)}")
    print(f"Output CSV: {output_path}")
    if errors:
        print("Parse warnings:")
        for e in errors:
            print(f"- {e}")

    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
