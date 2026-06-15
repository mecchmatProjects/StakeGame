from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path("math-sdk/games/azteck_plinko_final")
INPUTS = ROOT / "inputs"
CONSTRAINTS = INPUTS / "azteck_plinko_known_constraints.json"


def write_csv(path: Path, headers: list[str], rows: list[list[object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerows(rows)


def main() -> int:
    c = json.loads(CONSTRAINTS.read_text(encoding="utf-8"))

    difficulties = c["difficulty_levels"]
    rows_supported = c["rows_supported"]

    normal_cost = int(c["feature_modes"]["normal"]["cost_multiplier"])
    normal_global_max = c["feature_modes"]["normal"]["max_win_by_difficulty"]
    normal_expert_rows = c["feature_modes"]["normal"]["expert_max_win_by_rows"]

    buy_cost = int(c["feature_modes"]["100balls"]["cost_multiplier"])
    buy_global_max = c["feature_modes"]["100balls"]["max_win_by_difficulty"]
    buy_expert_rows = c["feature_modes"]["100balls"]["expert_max_win_by_rows"]

    normal_rows: list[list[object]] = []
    buy_rows: list[list[object]] = []
    prob_rows: list[list[object]] = []

    for difficulty in difficulties:
        for row_count in rows_supported:
            multiplier = ""
            source = "TODO"
            notes = f"Known global max for {difficulty}: {normal_global_max[difficulty]}x; fill full buckets"
            if difficulty == "Expert":
                multiplier = normal_expert_rows[str(row_count)]
                source = "Azteck Plinko Math.docx"
                notes = "Known Expert max-win-by-rows reference"

            normal_rows.append([
                difficulty,
                row_count,
                "MAX",
                multiplier,
                "x",
                source,
                notes,
            ])

            buy_multiplier = ""
            buy_source = "TODO"
            buy_notes = f"Known 100balls global max for {difficulty}: {buy_global_max[difficulty]}x; fill full buckets"
            if difficulty == "Expert":
                buy_multiplier = buy_expert_rows[str(row_count)]
                buy_source = "Azteck Plinko Math.docx"
                buy_notes = "Known 100balls Expert max-win-by-rows reference"

            buy_rows.append([
                difficulty,
                row_count,
                "MAX",
                buy_multiplier,
                "x",
                "TBD_AGGREGATION_RULE",
                buy_cost,
                buy_source,
                buy_notes,
            ])

            prob_rows.append([
                "normal",
                difficulty,
                row_count,
                "MAX",
                multiplier if difficulty == "Expert" else "",
                "",
                source,
                f"Target RTP {c['target_rtp']}; full bucket probabilities pending",
            ])
            prob_rows.append([
                "100balls",
                difficulty,
                row_count,
                "MAX",
                buy_multiplier if difficulty == "Expert" else "",
                "",
                buy_source,
                f"Target RTP {c['target_rtp']}; full bucket probabilities pending",
            ])

    write_csv(
        INPUTS / "azteck_plinko_paytables_normal.csv",
        ["difficulty", "rows", "bucket_index", "multiplier", "payout_unit", "source", "notes"],
        normal_rows,
    )

    write_csv(
        INPUTS / "azteck_plinko_paytables_100balls.csv",
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
        buy_rows,
    )

    write_csv(
        INPUTS / "azteck_plinko_probability_tables.csv",
        ["mode_type", "difficulty", "rows", "bucket_index", "multiplier", "probability", "source", "notes"],
        prob_rows,
    )

    print("Seeded input templates with known constraints")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
