from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

DIFFICULTIES = ["Low", "Medium", "High", "Expert"]
ROWS = list(range(8, 17))
TARGET_RTP = 0.9605
BUY100_COST = 99.0
DEFAULT_BETS = [
    0.01, 0.02, 0.05, 0.10, 0.20, 0.40, 0.60, 0.80, 1.00, 1.20,
    1.40, 1.60, 1.80, 2.00, 3.00, 4.00, 5.00, 6.00, 7.00, 8.00,
    9.00, 10.00, 12.00, 14.00, 16.00, 18.00, 20.00, 30.00, 40.00,
    50.00, 75.00, 100.00, 150.00, 200.00, 250.00, 300.00, 350.00,
    400.00, 450.00, 500.00,
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build Azteck Plinko artifacts from TXT game data on a clean machine."
    )
    parser.add_argument("--txt-dir", default=".", help="Folder containing TXT/RTF/DOCX game data files.")
    parser.add_argument("--root", default="math-sdk/games/azteck_plinko_final", help="Azteck package root to build.")
    parser.add_argument(
        "--variant",
        choices=["current", "2500", "biased", "all"],
        default="current",
        help="Artifact variant to produce. 'all' builds current, 2500, and biased-binomial where scripts exist.",
    )
    parser.add_argument("--multipliers", default="", help="Multiplier TXT file. Auto-detected if omitted.")
    parser.add_argument("--bets", default="", help="Optional bets TXT file. Auto-detected if omitted.")
    parser.add_argument(
        "--bet-source",
        choices=["default", "txt"],
        default="default",
        help="Use official 0.01-500 ladder or parse bet values from --bets.",
    )
    parser.add_argument("--max-bet", type=float, default=500.0, help="Filter parsed TXT bets at this maximum.")
    parser.add_argument("--skip-validation", action="store_true", help="Skip readiness/workbook validation commands.")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without writing or running generators.")
    return parser.parse_args()


def find_first(root: Path, patterns: list[str]) -> Path | None:
    for pattern in patterns:
        matches = sorted(root.glob(pattern))
        if matches:
            return matches[0]
    return None


def parse_multiplier_token(token: str) -> float:
    text = token.strip().lower().replace(",", "")
    if not text:
        raise ValueError("Empty multiplier token")
    multiplier = 1.0
    if text.endswith("k"):
        multiplier = 1000.0
        text = text[:-1]
    return float(text) * multiplier


def split_multiplier_line(line: str) -> tuple[int, str, str] | None:
    stripped = line.strip().lstrip("\ufeff")
    if not stripped or stripped.lower().startswith("rows"):
        return None

    tab_parts = [p.strip() for p in stripped.split("\t") if p.strip()]
    if len(tab_parts) >= 3 and tab_parts[0].isdigit():
        return int(tab_parts[0]), tab_parts[1].title(), tab_parts[2]

    match = re.match(r"^(8|9|1[0-6])\s+(Low|Medium|High|Expert)\s+(.+)$", stripped, re.IGNORECASE)
    if match:
        return int(match.group(1)), match.group(2).title(), match.group(3)
    return None


def parse_multipliers(path: Path) -> dict[tuple[str, int], list[float]]:
    parsed: dict[tuple[str, int], list[float]] = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        item = split_multiplier_line(line)
        if item is None:
            continue
        rows, difficulty, values_text = item
        values = [parse_multiplier_token(t) for t in re.split(r"\s*-\s*", values_text) if t.strip()]
        if len(values) != rows + 1:
            raise ValueError(f"{path}: {difficulty} {rows} has {len(values)} multipliers, expected {rows + 1}")
        parsed[(difficulty, rows)] = values

    missing = [(d, r) for d in DIFFICULTIES for r in ROWS if (d, r) not in parsed]
    if missing:
        raise ValueError(f"Missing multiplier rows: {missing[:10]}{'...' if len(missing) > 10 else ''}")
    return parsed


def parse_bets(path: Path | None, max_bet: float) -> list[float]:
    if path is None or not path.exists():
        return DEFAULT_BETS[:]
    text = path.read_text(encoding="utf-8-sig", errors="ignore")
    values = []
    for match in re.finditer(r"\$?\b\d{1,3}(?:,\d{3})*(?:\.\d+)?\b", text):
        value = float(match.group(0).replace("$", "").replace(",", ""))
        if 0 < value <= max_bet:
            values.append(round(value, 2))
    values = sorted(set(values))
    if 0.01 not in values:
        values.insert(0, 0.01)
    return values or DEFAULT_BETS[:]


def write_paytable_csvs(root: Path, multipliers: dict[tuple[str, int], list[float]]) -> None:
    inputs = root / "inputs"
    inputs.mkdir(parents=True, exist_ok=True)
    normal_path = inputs / "azteck_plinko_paytables_normal.csv"
    buy_path = inputs / "azteck_plinko_paytables_100balls.csv"

    with normal_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["difficulty", "rows", "bucket_index", "multiplier", "payout_unit", "source", "notes"])
        for difficulty in DIFFICULTIES:
            for rows in ROWS:
                mode = f"normal_{difficulty.lower()}_{rows}"
                for bucket, value in enumerate(multipliers[(difficulty, rows)]):
                    writer.writerow([difficulty, rows, bucket, f"{value:.6f}", "x", "txt_multiplier_table", f"mode={mode}"])

    with buy_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow([
            "difficulty", "rows", "bucket_index", "multiplier", "payout_unit",
            "aggregation_rule", "cost_multiplier", "source", "notes",
        ])
        for difficulty in DIFFICULTIES:
            for rows in ROWS:
                mode = f"buy100_{difficulty.lower()}_{rows}"
                for bucket, value in enumerate(multipliers[(difficulty, rows)]):
                    writer.writerow([
                        difficulty, rows, bucket, f"{value:.6f}", "x",
                        "mean_100_independent", 1, "single_ball_equals_normal_table",
                        f"mode={mode}; round_multiplier=mean_of_100_balls",
                    ])


def seed_index(root: Path) -> None:
    publish = root / "artifacts" / "publish_files"
    publish.mkdir(parents=True, exist_ok=True)
    modes = []
    for difficulty in DIFFICULTIES:
        for rows in ROWS:
            for mode_type, cost in [("normal", 1.0), ("100balls", BUY100_COST)]:
                prefix = "buy100" if mode_type == "100balls" else "normal"
                name = f"{prefix}_{difficulty.lower()}_{rows}"
                modes.append({
                    "name": name,
                    "mode_type": mode_type,
                    "difficulty": difficulty,
                    "rows": rows,
                    "cost": cost,
                    "rtp": TARGET_RTP,
                    "max_win": 0.0,
                    "weights": f"lookUpTable_{name}_0.csv",
                    "events": f"books_{name}.jsonl.zst",
                    "status": "seeded-from-txt",
                })
    index = {
        "game_id": "azteck_plinko",
        "version": "seeded-from-txt",
        "target_rtp": TARGET_RTP,
        "modes": modes,
    }
    (publish / "index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")


def ensure_supporting_inputs(root: Path) -> None:
    inputs = root / "inputs"
    inputs.mkdir(parents=True, exist_ok=True)
    defaults = {
        "azteck_plinko_replay_contract.json": {"gameId": "azteck_plinko", "source": "generated-from-txt"},
        "azteck_plinko_known_constraints.json": {
            "targetRtp": TARGET_RTP,
            "buy100Cost": BUY100_COST,
            "normalRows": [8, 9, 10, 11, 12, 13, 14, 15, 16],
            "difficulties": DIFFICULTIES,
        },
    }
    for name, content in defaults.items():
        path = inputs / name
        if not path.exists():
            path.write_text(json.dumps(content, indent=2), encoding="utf-8")
    rounding = inputs / "azteck_plinko_rounding_policy.md"
    if not rounding.exists():
        rounding.write_text(
            "# Rounding Policy\n\nPayout multipliers are encoded as multiplier * 100 integer raw values. "
            "Buy100 settlement is round((sum(ball_payouts) / 100) * 99).\n",
            encoding="utf-8",
        )


def run(cmd: list[str], dry_run: bool) -> None:
    print("RUN", " ".join(cmd))
    if dry_run:
        return
    subprocess.run(cmd, check=True)


def python_path_literal(path: Path) -> str:
    return repr(path.resolve().as_posix())


def run_with_root(script: str, root: Path, dry_run: bool) -> None:
    """Run a legacy helper script after replacing its hardcoded package root."""
    script_path = Path(script)
    patched = script_path.read_text(encoding="utf-8")
    root_literal = python_path_literal(root)
    patched = patched.replace(
        'ROOT = Path("math-sdk/games/azteck_plinko_final")',
        f"ROOT = Path({root_literal})",
    )
    patched = patched.replace(
        'root = Path("math-sdk/games/azteck_plinko_final")',
        f"root = Path({root_literal})",
    )
    if dry_run:
        print("RUN", sys.executable, script, f"[patched root={root}]")
        return
    with tempfile.TemporaryDirectory(prefix="azteck_txt_build_") as tmp:
        tmp_script = Path(tmp) / script_path.name
        tmp_script.write_text(patched, encoding="utf-8")
        run([sys.executable, str(tmp_script)], dry_run=False)


def sync_publish(root: Path, dry_run: bool) -> None:
    publish = root / "artifacts" / "publish_files"
    nested = root / "azteck_plinko_final_publish"
    zips = [root / "azteck_plinko_final_publish.zip", root / "artifacts.zip"]
    if dry_run:
        print(f"Would mirror {publish} -> {nested} and write {len(zips)} flat zips")
        return
    files = sorted(p for p in publish.iterdir() if p.is_file())
    if nested.exists():
        shutil.rmtree(nested)
    nested.mkdir(parents=True)
    for file in files:
        shutil.copy2(file, nested / file.name)
    for target in zips:
        zip_folder_flat(publish, target)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def patch_bets(root: Path, bets: list[float]) -> None:
    cfg_dir = root / "artifacts" / "configs"
    publish = root / "artifacts" / "publish_files"
    fe_path = cfg_dir / "fe_config.json"
    cfg_path = cfg_dir / "config.json"
    if not fe_path.exists() or not cfg_path.exists():
        return

    fe = json.loads(fe_path.read_text(encoding="utf-8"))
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    fe["betValues"] = bets
    fe["minBet"] = bets[0]
    fe["maxBet"] = bets[-1]
    cfg["betValues"] = bets
    fe_path.write_text(json.dumps(fe, indent=4), encoding="utf-8")
    cfg["frontendConfig"]["sha256"] = sha256(fe_path)
    cfg_path.write_text(json.dumps(cfg, indent=4), encoding="utf-8")
    shutil.copy2(fe_path, publish / "fe_config.json")
    shutil.copy2(cfg_path, publish / "config.json")


def copy_configs_to_publish(root: Path) -> None:
    cfg_dir = root / "artifacts" / "configs"
    publish = root / "artifacts" / "publish_files"
    for name in ["config.json", "fe_config.json"]:
        src = cfg_dir / name
        if src.exists():
            shutil.copy2(src, publish / name)


def zip_folder_flat(folder: Path, target_zip: Path) -> None:
    with zipfile.ZipFile(target_zip, "w", zipfile.ZIP_DEFLATED) as archive:
        for item in sorted(folder.iterdir()):
            if item.is_file():
                archive.write(item, item.name)


def build_current(root: Path, bets: list[float], dry_run: bool, skip_validation: bool) -> None:
    run_with_root("rebuild_azteck_final_symmetric.py", root, dry_run)
    run_with_root("gen_sdk_config.py", root, dry_run)
    if not dry_run:
        patch_bets(root, bets)
        copy_configs_to_publish(root)
    sync_publish(root, dry_run)
    run([
        sys.executable, "build_static_game_full_xlsx.py",
        "--root", str(root),
        "--output", str(root / "AzteckPlinkoFull_audit_formulas.xlsx"),
        "--name", "AzteckPlinkoFull",
    ], dry_run)
    if not skip_validation:
        run([sys.executable, "check_static_package_readiness.py", "--root", str(root)], dry_run)
        run([
            sys.executable, "check_excel_artifact_consistency.py",
            "--root", str(root),
            "--xlsx", str(root / "AzteckPlinkoFull_audit_formulas.xlsx"),
        ], dry_run)


def build_2500(root: Path, dry_run: bool) -> None:
    src = root / "azteck_plinko_final_publish"
    target = root / "azteck_plinko_final_publish2500"
    if not dry_run:
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(src, target)
    run([sys.executable, "rebuild_publish2500_peak_fix.py"], dry_run)
    if not dry_run:
        zip_folder_flat(target, root / "azteck_plinko_final_publish2500.zip")


def build_biased(dry_run: bool) -> None:
    run([sys.executable, "rebuild_azteck_biased_binomial_package.py"], dry_run)


def main() -> int:
    args = parse_args()
    txt_dir = Path(args.txt_dir)
    root = Path(args.root)
    multiplier_file = Path(args.multipliers) if args.multipliers else find_first(
        txt_dir, ["*multipliers*.txt", "*Multiplier*.txt", "*.txt"]
    )
    if multiplier_file is None:
        raise FileNotFoundError(f"No multiplier TXT file found in {txt_dir}")
    bets_file = Path(args.bets) if args.bets else find_first(txt_dir, ["bets.txt", "*bet*.txt", "*Bet*.txt"])

    print(f"Using multipliers: {multiplier_file}")
    if args.bet_source == "txt":
        print(f"Using bets: {bets_file if bets_file else 'not found; defaults'}")
    bets = parse_bets(bets_file, args.max_bet) if args.bet_source == "txt" else DEFAULT_BETS[:]
    multipliers = parse_multipliers(multiplier_file)

    if not args.dry_run:
        write_paytable_csvs(root, multipliers)
        seed_index(root)
        ensure_supporting_inputs(root)
    else:
        print(f"Would write inputs/index under {root}")

    variants = ["current", "2500", "biased"] if args.variant == "all" else [args.variant]
    if "current" in variants or "2500" in variants:
        build_current(root, bets, args.dry_run, args.skip_validation)
    if "2500" in variants:
        build_2500(root, args.dry_run)
    if "biased" in variants:
        build_biased(args.dry_run)

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
