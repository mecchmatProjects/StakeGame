from __future__ import annotations

import argparse
import csv
import datetime
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Recalculate and refresh static package validation summary from lookup files.")
    parser.add_argument("--root", required=True, help="Package root path, for example math-sdk/games/azteck_plinko_final")
    parser.add_argument("--target-rtp", type=float, default=0.96, help="Target RTP for tolerance checks")
    parser.add_argument("--rtp-tol", type=float, default=0.01, help="Absolute RTP tolerance")
    parser.add_argument("--payout-scale", type=float, default=100.0, help="Divide lookup payout value by this scale")
    parser.add_argument("--title", default="Static Game", help="Title prefix used in markdown output")
    parser.add_argument("--summary-json", default="validation_summary.json", help="Summary JSON filename under docs")
    parser.add_argument("--summary-md", default="Phase_5_Final_Validation_Summary.md", help="Summary markdown filename under docs")
    return parser.parse_args()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def detect_lookup_name(mode_entry: dict[str, Any]) -> str | None:
    for key in ("weights", "lookup", "lookup_file"):
        value = mode_entry.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def lookup_rows(path: Path) -> list[tuple[int, int, float]]:
    out: list[tuple[int, int, float]] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        for row in reader:
            if len(row) < 3:
                continue
            try:
                sim_id = int(float(row[0]))
                weight = int(float(row[1]))
                payout_raw = float(row[2])
            except ValueError:
                continue
            out.append((sim_id, weight, payout_raw))
    return out


def main() -> int:
    args = parse_args()

    root = Path(args.root).resolve()
    docs = root / "docs"
    publish = root / "artifacts" / "publish_files"
    index_path = publish / "index.json"

    if not index_path.exists():
        raise FileNotFoundError(f"Missing index file: {index_path}")

    index = load_json(index_path)
    modes = index.get("modes", [])
    if not isinstance(modes, list):
        raise ValueError("index.json: modes must be a list")

    summary_modes: list[dict[str, Any]] = []

    for mode in modes:
        if not isinstance(mode, dict):
            continue

        mode_name = mode.get("name") or mode.get("mode")
        if not isinstance(mode_name, str) or not mode_name:
            continue

        cost = float(mode.get("cost", 1.0))
        theoretical_rtp = float(mode.get("rtp", mode.get("target_rtp", mode.get("rtp_target", args.target_rtp))))
        configured_max_win = None
        if "max_win" in mode or "maxWin" in mode:
            raw_max = mode.get("max_win", mode.get("maxWin"))
            if raw_max is not None:
                configured_max_win = float(raw_max)

        lookup_name = detect_lookup_name(mode)
        if not lookup_name:
            # Default naming convention fallback.
            lookup_name = f"lookUpTable_{mode_name}_0.csv"

        lookup_path = publish / lookup_name
        if not lookup_path.exists():
            # Secondary fallback for lowercase naming conventions.
            secondary = publish / f"lookup_table_{mode_name}.csv"
            if secondary.exists():
                lookup_path = secondary
            else:
                summary_modes.append(
                    {
                        "mode_id": mode_name,
                        "cost": cost,
                        "theoretical_rtp": theoretical_rtp,
                        "simulated_rtp": 0.0,
                        "rtp_drift": 0.0 - theoretical_rtp,
                        "weight_sum": 0,
                        "book_length": 0,
                        "rounds": 0,
                        "observed_max_win": 0.0,
                        "configured_max_win": configured_max_win,
                        "weight_check_pass": False,
                        "max_win_check_pass": False,
                        "rtp_tolerance_pass": False,
                        "lookup_file": lookup_name,
                        "error": f"lookup file missing: {lookup_name}",
                    }
                )
                continue

        rows = lookup_rows(lookup_path)
        total_weight = sum(weight for _, weight, _ in rows)
        weighted_payout = sum((weight * (payout_raw / args.payout_scale)) for _, weight, payout_raw in rows)
        observed_max = max((payout_raw / args.payout_scale for _, _, payout_raw in rows), default=0.0)

        simulated_rtp = (weighted_payout / total_weight) / cost if (total_weight > 0 and cost > 0) else 0.0
        rtp_drift = simulated_rtp - theoretical_rtp
        rtp_pass = abs(simulated_rtp - args.target_rtp) <= args.rtp_tol
        max_win_pass = True
        if configured_max_win is not None:
            max_win_pass = abs(observed_max - configured_max_win) <= 1e-6

        summary_modes.append(
            {
                "mode_id": mode_name,
                "cost": cost,
                "theoretical_rtp": theoretical_rtp,
                "simulated_rtp": simulated_rtp,
                "rtp_drift": rtp_drift,
                "weight_sum": total_weight,
                "book_length": total_weight,
                "rounds": total_weight,
                "observed_max_win": observed_max,
                "configured_max_win": configured_max_win,
                "weight_check_pass": total_weight > 0,
                "max_win_check_pass": max_win_pass,
                "rtp_tolerance_pass": rtp_pass,
                "lookup_file": str(lookup_path.relative_to(publish)),
            }
        )

    checks = {
        "all_rtp_tolerance_pass": all(m.get("rtp_tolerance_pass", False) for m in summary_modes) if summary_modes else False,
        "all_weight_checks_pass": all(m.get("weight_check_pass", False) for m in summary_modes) if summary_modes else False,
        "all_max_win_checks_pass": all(m.get("max_win_check_pass", False) for m in summary_modes) if summary_modes else False,
    }

    summary = {
        "date": datetime.date.today().isoformat(),
        "package_path": str(root),
        "target_rtp": args.target_rtp,
        "rtp_tolerance": args.rtp_tol,
        "payout_scale": args.payout_scale,
        "checks": checks,
        "modes": summary_modes,
        "notes": [
            "Validation summary refreshed from lookup tables in artifacts/publish_files.",
            "Tolerance check uses abs(simulated_rtp - target_rtp) <= rtp_tolerance.",
        ],
    }

    docs.mkdir(parents=True, exist_ok=True)

    summary_json_path = docs / args.summary_json
    summary_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    md_lines = [
        f"# {args.title} Phase 5 Final Validation Summary",
        "",
        "## Recalculated Package Validation",
        "",
        f"- Date: {summary['date']}",
        "- Scope: artifacts/publish_files",
        f"- Target RTP per mode: {args.target_rtp:.4f}",
        f"- RTP tolerance: +/-{args.rtp_tol:.4f}",
        "",
        "## Consolidated Verdict",
        "",
        f"- RTP tolerance check: {'Pass' if checks['all_rtp_tolerance_pass'] else 'Fail'}.",
        f"- Weight integrity check: {'Pass' if checks['all_weight_checks_pass'] else 'Fail'}.",
        f"- Max-win reachability check: {'Pass' if checks['all_max_win_checks_pass'] else 'Fail'}.",
        "",
        "## Mode RTP Table",
        "",
        "| Mode | Cost | Theoretical RTP | Recalculated RTP | Drift | Pass |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]

    for m in summary_modes:
        md_lines.append(
            "| {mode} | {cost:.4f} | {theo:.6f} | {sim:.6f} | {drift:+.6f} | {ok} |".format(
                mode=m["mode_id"],
                cost=float(m.get("cost", 1.0)),
                theo=float(m.get("theoretical_rtp", 0.0)),
                sim=float(m.get("simulated_rtp", 0.0)),
                drift=float(m.get("rtp_drift", 0.0)),
                ok="Pass" if m.get("rtp_tolerance_pass", False) else "Fail",
            )
        )

    md_lines.extend(
        [
            "",
            "## Gate 5 Recommendation",
            "",
            f"- Gate 5 status: {'Pass' if checks['all_rtp_tolerance_pass'] else 'Fail'}",
            "",
            "Rationale:",
            "",
            "1. RTP is recalculated from the currently published lookup weights.",
            "2. Gate remains passing only while per-mode tolerance checks continue to pass.",
            "3. Any missing lookup file is treated as a blocking package defect.",
        ]
    )

    summary_md_path = docs / args.summary_md
    summary_md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print(f"Updated {summary_json_path}")
    print(f"Updated {summary_md_path}")
    print(f"all_rtp_tolerance_pass={checks['all_rtp_tolerance_pass']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
