from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from openpyxl import load_workbook


def read_lookup_row_count(path: Path) -> int:
    count = 0
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.reader(handle):
            if len(row) < 3:
                continue
            try:
                float(row[0])
                float(row[1])
                float(row[2])
            except ValueError:
                continue
            count += 1
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description="Check workbook correspondence with package artifacts")
    parser.add_argument("--root", required=True, help="Package root path")
    parser.add_argument("--xlsx", required=True, help="Workbook path")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    xlsx = Path(args.xlsx).resolve()
    publish = root / "artifacts" / "publish_files"
    index_path = publish / "index.json"

    index = json.loads(index_path.read_text(encoding="utf-8"))
    modes = index.get("modes", [])

    wb = load_workbook(xlsx, data_only=False)
    if "Summary" not in wb.sheetnames:
        print("FAIL: Summary sheet missing")
        return 1

    ws = wb["Summary"]

    # Find Mode Metrics header row.
    header_row = None
    headers: dict[str, int] = {}
    for r in range(1, ws.max_row + 1):
        values = [ws.cell(r, c).value for c in range(1, 40)]
        if values and values[0] == "Mode" and "Bucket Structure Pass" in values and "Max Win Probability" in values:
            header_row = r
            for c, v in enumerate(values, start=1):
                if isinstance(v, str) and v:
                    headers[v] = c
            break

    if header_row is None:
        print("FAIL: Mode Metrics header not found with expected columns")
        return 1

    required_cols = [
        "Mode",
        "Rows Config",
        "Expected Buckets",
        "Rows",
        "Unique Multipliers",
        "Bucket Structure Pass",
        "Max Win Probability",
        "Max Exposure",
    ]
    missing = [c for c in required_cols if c not in headers]
    if missing:
        print(f"FAIL: Missing summary columns: {missing}")
        return 1

    # Build summary mode map.
    mode_to_row: dict[str, int] = {}
    r = header_row + 1
    while r <= ws.max_row:
        mode_val = ws.cell(r, headers["Mode"]).value
        if not isinstance(mode_val, str) or not mode_val:
            break
        mode_to_row[mode_val] = r
        r += 1

    failures: list[str] = []

    # Check presence of TestVectors sheet.
    if "TestVectors" not in wb.sheetnames:
        failures.append("TestVectors sheet missing")

    for mode in modes:
        if not isinstance(mode, dict):
            continue
        name = mode.get("name")
        rows_cfg = mode.get("rows")
        weights = mode.get("weights")
        if not isinstance(name, str):
            continue

        if name not in mode_to_row:
            failures.append(f"Summary mode missing: {name}")
            continue

        if name[:31] not in wb.sheetnames:
            failures.append(f"Detail sheet missing: {name[:31]}")

        row = mode_to_row[name]

        # Rows Config value should match index rows.
        if isinstance(rows_cfg, int):
            x_rows_cfg = ws.cell(row, headers["Rows Config"]).value
            if x_rows_cfg != rows_cfg:
                failures.append(f"Rows Config mismatch for {name}: xlsx={x_rows_cfg}, index={rows_cfg}")

        # Rows count should correspond to lookup row count formula target.
        if isinstance(weights, str):
            lookup_path = publish / weights
            if lookup_path.exists():
                expected_rows = read_lookup_row_count(lookup_path)
                rows_formula = ws.cell(row, headers["Rows"]).value
                if not (isinstance(rows_formula, str) and "outcome_rows" not in rows_formula):
                    # We expect formula reference, not static blank.
                    pass
                # Expected buckets formula column should be formula based on Rows Config.
                exp_formula = ws.cell(row, headers["Expected Buckets"]).value
                if not isinstance(exp_formula, str):
                    failures.append(f"Expected Buckets is not formula for {name}")
                # Keep an explicit row count check against detail sheet bounds.
                detail = wb[name[:31]] if name[:31] in wb.sheetnames else None
                if detail is not None:
                    # Find outcome_rows marker in detail sheet.
                    found = None
                    for rr in range(1, detail.max_row + 1):
                        if detail.cell(rr, 1).value == "outcome_rows":
                            found = detail.cell(rr, 2).value
                            break
                    if found is None:
                        failures.append(f"outcome_rows marker missing on detail sheet for {name}")
                    else:
                        # found is formula (preferred)
                        if not isinstance(found, str):
                            failures.append(f"outcome_rows is not formula for {name}")
                        # Compare expected_rows from csv to direct count reconstructed from table section.
                        # data starts at row 7 and ends before CHECK_SUMS row.
                        check_row = None
                        for rr in range(1, detail.max_row + 1):
                            if detail.cell(rr, 1).value == "CHECK_SUMS":
                                check_row = rr
                                break
                        if check_row is None:
                            failures.append(f"CHECK_SUMS marker missing on detail sheet for {name}")
                        else:
                            reconstructed = max(0, check_row - 2 - 7 + 1)
                            if reconstructed != expected_rows:
                                failures.append(
                                    f"Detail row count mismatch for {name}: detail={reconstructed}, lookup={expected_rows}"
                                )

    summary = {
        "mode_count_index": len([m for m in modes if isinstance(m, dict) and isinstance(m.get("name"), str)]),
        "mode_count_summary": len(mode_to_row),
        "has_testvectors": "TestVectors" in wb.sheetnames,
        "failures": failures,
        "passed": len(failures) == 0,
    }

    print(json.dumps(summary, indent=2))
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
