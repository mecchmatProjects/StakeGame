from __future__ import annotations

import argparse
import csv
from pathlib import Path


ROOT = Path("math-sdk/games/azteck_plinko_final")
INPUTS = ROOT / "inputs"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import normalized Azteck reference rows into canonical templates")
    parser.add_argument(
        "--source",
        required=True,
        help=(
            "Normalized CSV source with columns: "
            "mode_type,difficulty,rows,bucket_index,multiplier,probability[,aggregation_rule][,source][,notes]"
        ),
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace existing template files with imported rows for matching mode type",
    )
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        out: list[dict[str, str]] = []
        for row in reader:
            out.append({k: (v or "").strip() for k, v in row.items() if k is not None})
        return out


def write_csv(path: Path, headers: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow({h: row.get(h, "") for h in headers})


def normalize_mode_type(raw: str) -> str:
    value = raw.strip().lower()
    if value in {"normal", "base", "basegame"}:
        return "normal"
    if value in {"100balls", "buy100", "buy", "feature"}:
        return "100balls"
    return value


def key_for(row: dict[str, str], include_bucket: bool = True) -> tuple[str, str, str, str] | tuple[str, str, str]:
    mt = normalize_mode_type(row.get("mode_type", ""))
    diff = row.get("difficulty", "")
    rows = row.get("rows", "")
    if include_bucket:
        return (mt, diff, rows, row.get("bucket_index", ""))
    return (mt, diff, rows)


def import_probability_rows(source_rows: list[dict[str, str]], current_rows: list[dict[str, str]], replace: bool) -> list[dict[str, str]]:
    src = [r for r in source_rows if normalize_mode_type(r.get("mode_type", "")) in {"normal", "100balls"}]

    if replace:
        out: list[dict[str, str]] = []
    else:
        out = list(current_rows)

    existing_keys = {key_for(r): i for i, r in enumerate(out)}

    for s in src:
        row = {
            "mode_type": normalize_mode_type(s.get("mode_type", "")),
            "difficulty": s.get("difficulty", ""),
            "rows": s.get("rows", ""),
            "bucket_index": s.get("bucket_index", ""),
            "multiplier": s.get("multiplier", ""),
            "probability": s.get("probability", ""),
            "source": s.get("source", "imported"),
            "notes": s.get("notes", ""),
        }
        k = key_for(row)
        if k in existing_keys:
            out[existing_keys[k]] = row
        else:
            out.append(row)

    return out


def import_paytable_rows(
    source_rows: list[dict[str, str]],
    current_normal: list[dict[str, str]],
    current_buy: list[dict[str, str]],
    replace: bool,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    normal_src = [r for r in source_rows if normalize_mode_type(r.get("mode_type", "")) == "normal"]
    buy_src = [r for r in source_rows if normalize_mode_type(r.get("mode_type", "")) == "100balls"]

    if replace:
        n_out: list[dict[str, str]] = []
        b_out: list[dict[str, str]] = []
    else:
        n_out = list(current_normal)
        b_out = list(current_buy)

    n_keys = {(r.get("difficulty", ""), r.get("rows", ""), r.get("bucket_index", "")): i for i, r in enumerate(n_out)}
    b_keys = {(r.get("difficulty", ""), r.get("rows", ""), r.get("bucket_index", "")): i for i, r in enumerate(b_out)}

    for s in normal_src:
        row = {
            "difficulty": s.get("difficulty", ""),
            "rows": s.get("rows", ""),
            "bucket_index": s.get("bucket_index", ""),
            "multiplier": s.get("multiplier", ""),
            "payout_unit": "x",
            "source": s.get("source", "imported"),
            "notes": s.get("notes", ""),
        }
        k = (row["difficulty"], row["rows"], row["bucket_index"])
        if k in n_keys:
            n_out[n_keys[k]] = row
        else:
            n_out.append(row)

    for s in buy_src:
        row = {
            "difficulty": s.get("difficulty", ""),
            "rows": s.get("rows", ""),
            "bucket_index": s.get("bucket_index", ""),
            "multiplier": s.get("multiplier", ""),
            "payout_unit": "x",
            "aggregation_rule": s.get("aggregation_rule", "TBD_AGGREGATION_RULE"),
            "cost_multiplier": "99",
            "source": s.get("source", "imported"),
            "notes": s.get("notes", ""),
        }
        k = (row["difficulty"], row["rows"], row["bucket_index"])
        if k in b_keys:
            b_out[b_keys[k]] = row
        else:
            b_out.append(row)

    return n_out, b_out


def main() -> int:
    args = parse_args()
    source_path = Path(args.source)
    if not source_path.exists():
        raise FileNotFoundError(source_path)

    source_rows = read_csv(source_path)

    prob_path = INPUTS / "azteck_plinko_probability_tables.csv"
    normal_path = INPUTS / "azteck_plinko_paytables_normal.csv"
    buy_path = INPUTS / "azteck_plinko_paytables_100balls.csv"

    current_prob = read_csv(prob_path)
    current_normal = read_csv(normal_path)
    current_buy = read_csv(buy_path)

    merged_prob = import_probability_rows(source_rows, current_prob, args.replace)
    merged_normal, merged_buy = import_paytable_rows(source_rows, current_normal, current_buy, args.replace)

    write_csv(
        prob_path,
        ["mode_type", "difficulty", "rows", "bucket_index", "multiplier", "probability", "source", "notes"],
        merged_prob,
    )
    write_csv(
        normal_path,
        ["difficulty", "rows", "bucket_index", "multiplier", "payout_unit", "source", "notes"],
        merged_normal,
    )
    write_csv(
        buy_path,
        [
            "difficulty",
            "rows",
            "bucket_index",
            "multiplier",
            "payout_unit",
            "aggregation_rule",
            "cost_multiplier",
            "source",
            "notes",
        ],
        merged_buy,
    )

    print(f"Imported source rows: {len(source_rows)}")
    print(f"Updated {prob_path}")
    print(f"Updated {normal_path}")
    print(f"Updated {buy_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
