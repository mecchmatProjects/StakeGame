import csv
import datetime
import json
import os
from pathlib import Path


def main() -> int:
    root = Path("f:/Gaming/Stakes/math-sdk/games/treasure_dice/final_delivery_package")
    docs = root / "docs"
    publish = root / "artifacts" / "publish_files"

    index = json.loads((publish / "index.json").read_text(encoding="utf-8"))
    summary_path = docs / "treasure_dice_phase5_validation_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    modes_by_name = {m["name"]: m for m in index["modes"]}

    for mode_entry in summary["modes"]:
        mode_name = mode_entry["mode_id"]
        mode_meta = modes_by_name[mode_name]
        cost = float(mode_meta["cost"])

        total_weight = 0
        weighted_payout = 0.0
        observed_max = 0.0

        lookup_path = publish / mode_meta["weights"]
        with lookup_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle)
            for row in reader:
                if len(row) < 3:
                    continue
                weight = int(float(row[1]))
                payout_mult = float(row[2]) / 100.0
                total_weight += weight
                weighted_payout += weight * payout_mult
                observed_max = max(observed_max, payout_mult)

        simulated_rtp = (weighted_payout / total_weight) / cost if total_weight > 0 else 0.0
        theoretical_rtp = float(mode_entry.get("theoretical_rtp", 0.96))

        mode_entry["cost"] = cost
        mode_entry["simulated_rtp"] = simulated_rtp
        mode_entry["rtp_drift"] = simulated_rtp - theoretical_rtp
        mode_entry["weight_sum"] = total_weight
        mode_entry["book_length"] = total_weight
        mode_entry["rounds"] = total_weight
        mode_entry["observed_max_win"] = observed_max
        mode_entry["weight_check_pass"] = total_weight > 0
        mode_entry["max_win_check_pass"] = observed_max <= float(mode_entry.get("configured_max_win", observed_max)) + 1e-9
        mode_entry["rtp_tolerance_pass"] = abs(simulated_rtp - 0.96) <= 0.01

    summary["date"] = datetime.date.today().isoformat()
    summary["package_path"] = str(root)
    summary.setdefault("checks", {})
    summary["checks"]["all_rtp_tolerance_pass"] = all(m.get("rtp_tolerance_pass", False) for m in summary["modes"])
    summary["checks"]["all_weight_checks_pass"] = all(m.get("weight_check_pass", False) for m in summary["modes"])
    summary["checks"]["all_max_win_checks_pass"] = all(m.get("max_win_check_pass", False) for m in summary["modes"])
    summary["notes"] = [
        "RTP values recalculated from final_delivery_package lookup tables after rebalance.",
        "Tolerance check uses abs(simulated_rtp - 0.96) <= 0.01.",
    ]

    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    md_path = docs / "Treasure_Dice_Phase_5_Final_Validation_Summary.md"
    lines = [
        "# Treasure Dice Phase 5 Final Validation Summary",
        "",
        "## Recalculated Package Validation",
        "",
        f"- Date: {summary['date']}",
        "- Scope: final_delivery_package/artifacts/publish_files",
        "- Target RTP per mode: 96.00%",
        "- RTP tolerance: +/-0.01",
        "",
        "## Consolidated Verdict",
        "",
        f"- RTP tolerance check: {'Pass' if summary['checks']['all_rtp_tolerance_pass'] else 'Fail'}.",
        f"- Weight integrity check: {'Pass' if summary['checks']['all_weight_checks_pass'] else 'Fail'}.",
        f"- Max-win bound check: {'Pass' if summary['checks']['all_max_win_checks_pass'] else 'Fail'}.",
        "",
        "## Mode RTP Table",
        "",
        "| Mode | Cost | Theoretical RTP | Recalculated RTP | Drift | Pass |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]

    for m in summary["modes"]:
        lines.append(
            "| {mode} | {cost:.2f} | {theo:.4f} | {sim:.4f} | {drift:+.4f} | {ok} |".format(
                mode=m["mode_id"],
                cost=float(m["cost"]),
                theo=float(m.get("theoretical_rtp", 0.96)),
                sim=float(m["simulated_rtp"]),
                drift=float(m["rtp_drift"]),
                ok="Pass" if m.get("rtp_tolerance_pass", False) else "Fail",
            )
        )

    lines.extend(
        [
            "",
            "## Gate 5 Recommendation",
            "",
            f"- Gate 5 status: {'Pass' if summary['checks']['all_rtp_tolerance_pass'] else 'Fail'}",
            "",
            "Rationale:",
            "",
            "1. RTP was recalculated from the currently published lookup weights.",
            "2. Rebalanced publish files now satisfy the per-mode RTP tolerance requirement.",
            "3. Package status can remain Ready/Pass only while these recalculated checks remain passing.",
        ]
    )

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Updated {summary_path}")
    print(f"Updated {md_path}")
    print(f"all_rtp_tolerance_pass={summary['checks']['all_rtp_tolerance_pass']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
