from __future__ import annotations

import csv
import json
import random
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from math import sqrt
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import zstandard as zstd


ROOT = Path(__file__).resolve().parent
SDK_DIR = ROOT / "math-sdk" / "games" / "treasure_dice" / "library"
PUBLISH_DIR = SDK_DIR / "publish_files"
CONFIG_DIR = SDK_DIR / "configs"
FORCE_DIR = SDK_DIR / "forces"
LOOKUP_DIR = SDK_DIR / "lookup_tables"
MAPPING_PATH = ROOT / "treasure_dice_phase3_mapping_spec.json"

OUT_JSON = ROOT / "treasure_dice_full_consistency_mc_audit.json"
OUT_MD = ROOT / "Treasure_Dice_Full_Consistency_MC_Audit.md"

MONTE_CARLO_ROUNDS_PER_MODE = 1_000_000

DOCS_TO_CHECK = [
    ROOT / "Treasure_Dice_Mathematician_Handoff.md",
    ROOT / "Treasure_Dice_Phase_1_Math_Report.md",
    ROOT / "Treasure_Dice_Phase_2_Bonus_Report.md",
    ROOT / "Treasure_Dice_Phase_3_Event_Mapping_Report.md",
    ROOT / "Treasure_Dice_Phase_4_Package_Completeness_Report.md",
    ROOT / "Treasure_Dice_Phase_5_Simulation_Report.md",
    ROOT / "Treasure_Dice_Phase_5_Volatility_Report.md",
    ROOT / "Treasure_Dice_Phase_5_Replay_Audit_Report.md",
    ROOT / "Treasure_Dice_Phase_5_Final_Validation_Summary.md",
    ROOT / "Treasure_Dice_Phase_6_Delivery_Manifest.md",
    ROOT / "Treasure_Dice_Phase_6_Risk_Assessment.md",
    ROOT / "Treasure_Dice_Phase_6_Acceptance_Checklist.md",
    ROOT / "Treasure_Dice_Phase_6_Publication_Status_Note.md",
    ROOT / "Treasure_Dice_Mathematician_Artifacts_Package.docx",
]


@dataclass
class ModeCheck:
    mode_id: str
    cost: float
    theoretical_rtp: float
    lookup_rtp: float
    lookup_rtp_delta: float
    theoretical_std: float
    lookup_std: float
    lookup_std_error: float
    lookup_drift_sigma: float
    configured_max_win: float
    mapped_max_win: float
    observed_max_win: float
    weights_sum: int
    books_len: int
    consistency_pass: bool


@dataclass
class MonteCarloCheck:
    mode_id: str
    rounds: int
    theoretical_rtp: float
    simulated_rtp: float
    drift: float
    std_error: float
    z_score: float


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_lookup_rows(mode_id: str) -> List[Tuple[int, int, float]]:
    path = PUBLISH_DIR / f"lookUpTable_{mode_id}_0.csv"
    rows: List[Tuple[int, int, float]] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        for row in reader:
            rows.append((int(row[0]), int(row[1]), int(row[2]) / 100.0))
    return rows


def read_books(mode_id: str) -> List[dict]:
    path = PUBLISH_DIR / f"books_{mode_id}.jsonl.zst"
    dctx = zstd.ZstdDecompressor()
    with path.open("rb") as handle:
        text = dctx.stream_reader(handle).read().decode("utf-8")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def normalize_book_multiplier(raw_value: float, configured_max_win: float) -> float:
    if raw_value > configured_max_win * 5:
        return raw_value / 100.0
    return raw_value


def get_mapping_modes(mapping: dict) -> Dict[str, Tuple[float, List[Tuple[float, float]]]]:
    by_mode: Dict[str, Tuple[float, List[Tuple[float, float]]]] = {}
    for mode in mapping["regular_modes"]:
        by_mode[mode["mode_id"]] = (
            float(mode["cost_multiplier"]),
            [(float(item["probability"]), float(item["payout_multiplier"])) for item in mode["outcomes"]],
        )

    bonus = mapping["bonus_mode"]
    by_mode[bonus["mode_id"]] = (
        float(bonus["cost_multiplier"]),
        [
            (float(item["probability"]), float(item["payout_multiplier_vs_base_bet"]))
            for item in bonus["outcomes"]
        ],
    )
    return by_mode


def moments(outcomes: Sequence[Tuple[float, float]]) -> Tuple[float, float]:
    mean = sum(prob * payout for prob, payout in outcomes)
    variance = sum(prob * ((payout - mean) ** 2) for prob, payout in outcomes)
    return mean, sqrt(variance)


def weighted_lookup_moments(rows: Sequence[Tuple[int, int, float]]) -> Tuple[int, float, float]:
    total = sum(weight for _, weight, _ in rows)
    if total <= 0:
        return 0, 0.0, 0.0
    mean = sum(weight * payout for _, weight, payout in rows) / total
    variance = sum(weight * ((payout - mean) ** 2) for _, weight, payout in rows) / total
    return total, mean, sqrt(variance)


def check_books_vs_lookup(rows: Sequence[Tuple[int, int, float]], books: Sequence[dict], configured_max: float) -> bool:
    payout_by_id: Dict[int, float] = {}
    for rec in books:
        payout_by_id[int(rec["id"])] = normalize_book_multiplier(float(rec["payoutMultiplier"]), configured_max)

    for rec_id, _, payout in rows:
        if rec_id not in payout_by_id:
            return False
        if abs(payout_by_id[rec_id] - payout) > 1e-9:
            return False
    return True


def check_replay(books: Sequence[dict]) -> bool:
    seq_by_outcome: Dict[str, set] = {}
    payout_by_outcome: Dict[str, set] = {}

    for record in books:
        outcome_id = None
        settlement = None
        seq: List[str] = []

        for event in record.get("events", []):
            if event.get("type") == "round_settlement":
                outcome_id = str(event.get("outcomeId"))
                settlement = float(event.get("payoutMultiplier", 0.0))

        if outcome_id is None:
            return False

        for event in record.get("events", []):
            if event.get("outcomeId") == outcome_id and event.get("type") != "round_settlement":
                seq.append(str(event.get("type")))

        seq_by_outcome.setdefault(outcome_id, set()).add(tuple(seq))
        payout_by_outcome.setdefault(outcome_id, set()).add(settlement)

    for outcome_id in seq_by_outcome:
        if len(seq_by_outcome[outcome_id]) != 1:
            return False
        if len(payout_by_outcome.get(outcome_id, set())) != 1:
            return False
    return True


def run_mc(mode_id: str, outcomes: Sequence[Tuple[float, float]], cost: float, rounds: int, seed: int) -> MonteCarloCheck:
    rng = random.Random(seed)
    cumulative: List[Tuple[float, float]] = []
    running = 0.0
    for prob, payout in outcomes:
        running += prob
        cumulative.append((running, payout))

    payout_sum = 0.0
    for _ in range(rounds):
        r = rng.random()
        for threshold, payout in cumulative:
            if r <= threshold:
                payout_sum += payout
                break

    theo_mean, theo_std = moments(outcomes)
    theoretical_rtp = theo_mean / cost
    simulated_rtp = (payout_sum / rounds) / cost
    drift = simulated_rtp - theoretical_rtp
    std_error = (theo_std / cost) / sqrt(rounds)
    z = drift / std_error if std_error > 0 else 0.0
    return MonteCarloCheck(
        mode_id=mode_id,
        rounds=rounds,
        theoretical_rtp=theoretical_rtp,
        simulated_rtp=simulated_rtp,
        drift=drift,
        std_error=std_error,
        z_score=z,
    )


def check_markdown_links(path: Path) -> List[str]:
    if path.suffix.lower() != ".md":
        return []
    text = path.read_text(encoding="utf-8")
    link_pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    broken: List[str] = []
    for target in link_pattern.findall(text):
        if target.startswith("http://") or target.startswith("https://"):
            continue
        clean = target.split("#", 1)[0]
        if not clean:
            continue
        resolved = (path.parent / clean).resolve()
        if not resolved.exists():
            broken.append(target)
    return broken


def main() -> int:
    mapping = load_json(MAPPING_PATH)
    config = load_json(CONFIG_DIR / "config.json")
    index = load_json(PUBLISH_DIR / "index.json")

    mapping_modes = get_mapping_modes(mapping)
    config_modes = [item["name"] for item in config["bookShelfConfig"]]
    index_modes = [item["name"] for item in index["modes"]]

    expected_files = {
        "publish_books": sorted([f"books_{mode}.jsonl.zst" for mode in config_modes]),
        "publish_lookups": sorted([f"lookUpTable_{mode}_0.csv" for mode in config_modes]),
        "lookup_tables": sorted([f"lookUpTable_{mode}.csv" for mode in config_modes]),
        "force_files": sorted([f"force_record_{mode}.json" for mode in config_modes]),
    }

    observed_files = {
        "publish_books": sorted([p.name for p in PUBLISH_DIR.glob("books_*.jsonl.zst")]),
        "publish_lookups": sorted([p.name for p in PUBLISH_DIR.glob("lookUpTable_*_0.csv")]),
        "lookup_tables": sorted([p.name for p in LOOKUP_DIR.glob("lookUpTable_*.csv")]),
        "force_files": sorted([p.name for p in FORCE_DIR.glob("force_record_*.json")]),
    }

    mode_checks: List[ModeCheck] = []
    mc_checks: List[MonteCarloCheck] = []

    for i, mode_id in enumerate(config_modes):
        cost, outcomes = mapping_modes[mode_id]
        theo_mean, theo_std = moments(outcomes)
        theoretical_rtp = theo_mean / cost

        lookup_rows = read_lookup_rows(mode_id)
        books = read_books(mode_id)
        configured_max = float(next(item for item in config["bookShelfConfig"] if item["name"] == mode_id)["maxWin"])

        weights_sum, lookup_mean, lookup_std = weighted_lookup_moments(lookup_rows)
        lookup_rtp = lookup_mean / cost if cost > 0 else 0.0
        lookup_std_error = (theo_std / cost) / sqrt(max(weights_sum, 1)) if cost > 0 else 0.0
        lookup_drift_sigma = ((lookup_rtp - theoretical_rtp) / lookup_std_error) if lookup_std_error > 0 else 0.0

        mapped_max = max(payout for _, payout in outcomes)
        observed_max = max(
            normalize_book_multiplier(float(rec.get("payoutMultiplier", 0.0)), configured_max)
            for rec in books
        ) if books else 0.0

        books_lookup_ok = check_books_vs_lookup(lookup_rows, books, configured_max)
        replay_ok = check_replay(books)

        consistency_ok = (
            abs(lookup_drift_sigma) <= 5.0
            and abs(mapped_max - configured_max) < 1e-9
            and observed_max <= configured_max + 1e-9
            and weights_sum == len(books)
            and books_lookup_ok
            and replay_ok
        )

        mode_checks.append(
            ModeCheck(
                mode_id=mode_id,
                cost=cost,
                theoretical_rtp=theoretical_rtp,
                lookup_rtp=lookup_rtp,
                lookup_rtp_delta=lookup_rtp - theoretical_rtp,
                theoretical_std=theo_std,
                lookup_std=lookup_std,
                lookup_std_error=lookup_std_error,
                lookup_drift_sigma=lookup_drift_sigma,
                configured_max_win=configured_max,
                mapped_max_win=mapped_max,
                observed_max_win=observed_max,
                weights_sum=weights_sum,
                books_len=len(books),
                consistency_pass=consistency_ok,
            )
        )

        mc_checks.append(
            run_mc(
                mode_id=mode_id,
                outcomes=outcomes,
                cost=cost,
                rounds=MONTE_CARLO_ROUNDS_PER_MODE,
                seed=20260603 + i,
            )
        )

    docs_existence = {str(path.relative_to(ROOT)).replace("\\", "/"): path.exists() for path in DOCS_TO_CHECK}

    broken_links: Dict[str, List[str]] = {}
    for path in DOCS_TO_CHECK:
        if path.exists() and path.suffix.lower() == ".md":
            missing = check_markdown_links(path)
            if missing:
                broken_links[str(path.relative_to(ROOT)).replace("\\", "/")] = missing

    structure_consistency = {
        "mapping_config_mode_match": sorted(mapping_modes.keys()) == sorted(config_modes),
        "index_config_mode_match": sorted(index_modes) == sorted(config_modes),
        "publish_books_match": expected_files["publish_books"] == observed_files["publish_books"],
        "publish_lookups_match": expected_files["publish_lookups"] == observed_files["publish_lookups"],
        "lookup_tables_match": expected_files["lookup_tables"] == observed_files["lookup_tables"],
        "force_files_match": expected_files["force_files"] == observed_files["force_files"],
    }

    all_mode_consistent = all(item.consistency_pass for item in mode_checks)
    mc_within_5sigma = all(abs(item.z_score) <= 5.0 for item in mc_checks)
    docs_present = all(docs_existence.values())
    no_broken_links = len(broken_links) == 0

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "rounds_per_mode": MONTE_CARLO_ROUNDS_PER_MODE,
        "structure_consistency": structure_consistency,
        "docs_existence": docs_existence,
        "broken_markdown_links": broken_links,
        "expected_files": expected_files,
        "observed_files": observed_files,
        "mode_consistency": [item.__dict__ for item in mode_checks],
        "monte_carlo": [item.__dict__ for item in mc_checks],
        "overall": {
            "all_mode_consistent": all_mode_consistent,
            "monte_carlo_within_5sigma": mc_within_5sigma,
            "docs_present": docs_present,
            "no_broken_markdown_links": no_broken_links,
            "pass": all(
                [
                    all(structure_consistency.values()),
                    all_mode_consistent,
                    mc_within_5sigma,
                    docs_present,
                    no_broken_links,
                ]
            ),
        },
    }

    OUT_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    md_lines: List[str] = []
    md_lines.append("# Treasure Dice Full Consistency and Monte Carlo Audit")
    md_lines.append("")
    md_lines.append(f"- Generated at: {summary['generated_at_utc']}")
    md_lines.append(f"- Monte Carlo rounds per mode: {MONTE_CARLO_ROUNDS_PER_MODE:,}")
    md_lines.append("")
    md_lines.append("## Overall Result")
    md_lines.append("")
    md_lines.append(f"- Pass: {summary['overall']['pass']}")
    md_lines.append(f"- All mode consistency checks: {all_mode_consistent}")
    md_lines.append(f"- Monte Carlo within 5 sigma for all modes: {mc_within_5sigma}")
    md_lines.append(f"- Required docs present: {docs_present}")
    md_lines.append(f"- Broken markdown links: {not no_broken_links}")
    md_lines.append("")

    md_lines.append("## Structure Consistency")
    md_lines.append("")
    for k, v in structure_consistency.items():
        md_lines.append(f"- {k}: {v}")
    md_lines.append("")

    md_lines.append("## Mode Consistency")
    md_lines.append("")
    md_lines.append("| Mode | Theoretical RTP | Lookup RTP | Delta | Drift Sigma | MaxWin Config | MaxWin Mapping | MaxWin Observed | Weights | Books | Pass |")
    md_lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |")
    for row in mode_checks:
        md_lines.append(
            "| {mode} | {trtp:.6f} | {lrpt:.6f} | {delta:.6e} | {sigma:.3f} | {cmax:.4f} | {mmax:.4f} | {omax:.4f} | {w} | {b} | {ok} |".format(
                mode=row.mode_id,
                trtp=row.theoretical_rtp,
                lrpt=row.lookup_rtp,
                delta=row.lookup_rtp_delta,
                sigma=row.lookup_drift_sigma,
                cmax=row.configured_max_win,
                mmax=row.mapped_max_win,
                omax=row.observed_max_win,
                w=row.weights_sum,
                b=row.books_len,
                ok=row.consistency_pass,
            )
        )
    md_lines.append("")

    md_lines.append("## Monte Carlo by Mode")
    md_lines.append("")
    md_lines.append("| Mode | Rounds | Theoretical RTP | Simulated RTP | Drift | Std Error | Z-Score |")
    md_lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: |")
    for row in mc_checks:
        md_lines.append(
            "| {mode} | {rounds} | {trtp:.6f} | {srpt:.6f} | {drift:.6e} | {se:.6e} | {z:.3f} |".format(
                mode=row.mode_id,
                rounds=row.rounds,
                trtp=row.theoretical_rtp,
                srpt=row.simulated_rtp,
                drift=row.drift,
                se=row.std_error,
                z=row.z_score,
            )
        )
    md_lines.append("")

    if broken_links:
        md_lines.append("## Broken Markdown Links")
        md_lines.append("")
        for doc, links in broken_links.items():
            md_lines.append(f"- {doc}")
            for link in links:
                md_lines.append(f"  - {link}")

    OUT_MD.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print(f"Wrote {OUT_JSON}")
    print(f"Wrote {OUT_MD}")
    print(f"Overall pass: {summary['overall']['pass']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
