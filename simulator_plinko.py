from __future__ import annotations

import argparse
import bisect
import csv
import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class ModeResult:
    mode: str
    cost: float
    target_rtp: float
    configured_mode_rtp: float
    spins: int
    exact_rtp_normalized: float
    sim_rtp_normalized: float
    exact_delta_to_target: float
    sim_delta_to_target: float
    sim_standard_error: float
    sim_allowed_delta: float
    weight_sum: int
    configured_max_win: float | None
    table_max_win: float
    sampled_max_win: float
    pass_weight: bool
    pass_max_reachability: bool
    pass_exact_rtp: bool
    pass_sim_rtp: bool
    pass_sampled_max_bound: bool

    @property
    def passed(self) -> bool:
        return (
            self.pass_weight
            and self.pass_max_reachability
            and self.pass_exact_rtp
            and self.pass_sim_rtp
            and self.pass_sampled_max_bound
        )


@dataclass
class ModeLookupData:
    mode_name: str
    cost: float
    configured_mode_rtp: float
    configured_max_win: float | None
    lookup_path: Path
    rows: list[tuple[int, int, float]]
    weights: list[int]
    payouts: list[float]
    sim_ids: list[int]
    weight_sum: int
    table_max: float
    cum_weights: list[int]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Monte Carlo simulator for Azteck Plinko package modes."
    )
    parser.add_argument(
        "--root",
        default="math-sdk/games/azteck_plinko_final",
        help="Package root containing artifacts/publish_files/index.json",
    )
    parser.add_argument(
        "--spins",
        type=int,
        default=100_000,
        help="Spins per mode for Monte Carlo simulation",
    )
    parser.add_argument(
        "--target-rtp",
        type=float,
        default=0.9605,
        help="Target normalized RTP used for pass/fail checks",
    )
    parser.add_argument(
        "--rtp-tol",
        type=float,
        default=0.01,
        help="Absolute RTP tolerance against target",
    )
    parser.add_argument(
        "--payout-scale",
        type=float,
        default=100.0,
        help="Scale divisor applied to payout values in lookup CSV",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=2026,
        help="RNG seed for reproducible simulation",
    )
    parser.add_argument(
        "--zscore",
        type=float,
        default=4.0,
        help="Z-score multiplier for Monte Carlo confidence envelope",
    )
    parser.add_argument(
        "--mode",
        help="Optional single mode name. By default all modes are simulated.",
    )
    parser.add_argument(
        "--output-json",
        help="Optional output summary JSON path. Default: <root>/docs/simulator_plinko_summary.json",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run a few traced games with full terminal explanation for one mode",
    )
    parser.add_argument(
        "--demo-games",
        type=int,
        default=10,
        help="Number of traced games when --demo is enabled",
    )
    return parser.parse_args()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def detect_lookup_name(mode_entry: dict[str, Any]) -> str:
    for key in ("weights", "lookup", "lookup_file"):
        value = mode_entry.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return f"lookUpTable_{mode_entry['name']}_0.csv"


def load_lookup_rows(path: Path) -> list[tuple[int, int, float]]:
    rows: list[tuple[int, int, float]] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        for row in reader:
            if len(row) < 3:
                continue
            try:
                sim_id = int(float(row[0]))
                weight = int(float(row[1]))
                payout = float(row[2])
            except ValueError:
                continue
            rows.append((sim_id, weight, payout))
    return rows


def cumulative_weights(weights: list[int]) -> list[int]:
    out: list[int] = []
    running = 0
    for value in weights:
        running += value
        out.append(running)
    return out


def sample_index(cum_weights: list[int], rng: random.Random) -> int:
    total = cum_weights[-1]
    point = rng.randrange(total)
    return bisect.bisect_right(cum_weights, point)


def sample_point_and_index(cum_weights: list[int], rng: random.Random) -> tuple[int, int]:
    total = cum_weights[-1]
    point = rng.randrange(total)
    idx = bisect.bisect_right(cum_weights, point)
    return point, idx


def load_mode_lookup_data(
    mode: dict[str, Any], publish_path: Path, payout_scale: float, target_rtp: float
) -> ModeLookupData:
    mode_name = str(mode["name"])
    cost = float(mode.get("cost", 1.0))
    configured_mode_rtp = float(mode.get("rtp", target_rtp))
    configured_max_win = (
        float(mode.get("max_win"))
        if mode.get("max_win") is not None
        else (float(mode.get("maxWin")) if mode.get("maxWin") is not None else None)
    )

    lookup_name = detect_lookup_name(mode)
    lookup_path = publish_path / lookup_name
    if not lookup_path.exists():
        alt = publish_path / f"lookup_table_{mode_name}.csv"
        if alt.exists():
            lookup_path = alt
        else:
            raise FileNotFoundError(f"Missing lookup file for mode {mode_name}: {lookup_name}")

    rows = load_lookup_rows(lookup_path)
    weights = [max(0, row[1]) for row in rows]
    payouts = [row[2] / payout_scale for row in rows]
    sim_ids = [row[0] for row in rows]
    weight_sum = sum(weights)
    table_max = max(payouts) if payouts else 0.0
    cum_weights = cumulative_weights(weights) if weight_sum > 0 else []

    return ModeLookupData(
        mode_name=mode_name,
        cost=cost,
        configured_mode_rtp=configured_mode_rtp,
        configured_max_win=configured_max_win,
        lookup_path=lookup_path,
        rows=rows,
        weights=weights,
        payouts=payouts,
        sim_ids=sim_ids,
        weight_sum=weight_sum,
        table_max=table_max,
        cum_weights=cum_weights,
    )


def run_demo_mode(
    mode: dict[str, Any],
    publish_path: Path,
    payout_scale: float,
    target_rtp: float,
    demo_games: int,
    rng: random.Random,
) -> int:
    if demo_games <= 0:
        raise ValueError("--demo-games must be > 0")

    data = load_mode_lookup_data(mode, publish_path, payout_scale, target_rtp)
    if data.weight_sum <= 0:
        raise ValueError(f"Mode has empty or zero-weight lookup: {data.mode_name}")

    exact_raw = sum((w / data.weight_sum) * p for w, p in zip(data.weights, data.payouts))
    exact_norm = exact_raw / data.cost if data.cost > 0 else 0.0

    print("DEMO MODE START")
    print(f"mode: {data.mode_name}")
    print(f"lookup: {data.lookup_path.name}")
    print(f"cost: {data.cost:.6f}")
    print(f"target_rtp: {target_rtp:.6f}")
    print(f"configured_mode_rtp: {data.configured_mode_rtp:.6f}")
    print(f"exact_rtp_from_table: {exact_norm:.6f}")
    print(f"configured_max_win: {data.configured_max_win}")
    print(f"table_max_win: {data.table_max:.6f}")
    print(f"total_weight: {data.weight_sum}")
    print(f"outcome_rows: {len(data.rows)}")
    print("-")

    running_raw_return = 0.0
    running_norm_return = 0.0
    sampled_max = 0.0

    for spin_no in range(1, demo_games + 1):
        point, idx = sample_point_and_index(data.cum_weights, rng)
        left = 0 if idx == 0 else data.cum_weights[idx - 1]
        right = data.cum_weights[idx] - 1

        sim_id = data.sim_ids[idx]
        weight = data.weights[idx]
        payout = data.payouts[idx]
        prob = weight / data.weight_sum
        normalized_payout = payout / data.cost if data.cost > 0 else 0.0

        running_raw_return += payout
        running_norm_return += normalized_payout
        sampled_max = payout if payout > sampled_max else sampled_max
        running_rtp_norm = running_norm_return / spin_no

        print(
            f"spin={spin_no:03d} draw={point} interval=[{left},{right}] "
            f"outcome_id={sim_id} outcome_prob={prob:.8f}"
        )
        print(
            f"  payout_raw={payout:.6f} payout_normalized={normalized_payout:.6f} "
            f"running_rtp_normalized={running_rtp_norm:.6f}"
        )
        print("")
        print("-" * 60)

    print("-")
    print("DEMO MODE SUMMARY")
    print(f"demo_games: {demo_games}")
    print(f"sampled_max_win: {sampled_max:.6f}")
    print(f"final_rtp_normalized: {(running_norm_return / demo_games):.6f}")
    print(f"exact_rtp_normalized: {exact_norm:.6f}")
    print(f"delta_to_exact: {(running_norm_return / demo_games) - exact_norm:+.6f}")
    print("DEMO MODE END")
    return 0


def simulate_mode(
    mode: dict[str, Any],
    publish_path: Path,
    spins: int,
    payout_scale: float,
    target_rtp: float,
    rtp_tol: float,
    zscore: float,
    rng: random.Random,
) -> ModeResult:
    data = load_mode_lookup_data(mode, publish_path, payout_scale, target_rtp)
    pass_weight = data.weight_sum > 0 and len(data.rows) > 0
    if not pass_weight:
        return ModeResult(
            mode=data.mode_name,
            cost=data.cost,
            target_rtp=target_rtp,
            configured_mode_rtp=data.configured_mode_rtp,
            spins=spins,
            exact_rtp_normalized=0.0,
            sim_rtp_normalized=0.0,
            exact_delta_to_target=-target_rtp,
            sim_delta_to_target=-target_rtp,
            sim_standard_error=0.0,
            sim_allowed_delta=rtp_tol,
            weight_sum=data.weight_sum,
            configured_max_win=data.configured_max_win,
            table_max_win=0.0,
            sampled_max_win=0.0,
            pass_weight=False,
            pass_max_reachability=False,
            pass_exact_rtp=False,
            pass_sim_rtp=False,
            pass_sampled_max_bound=False,
        )

    exact_raw = sum((w / data.weight_sum) * p for w, p in zip(data.weights, data.payouts))
    exact_rtp_normalized = exact_raw / data.cost if data.cost > 0 else 0.0

    second_raw = sum((w / data.weight_sum) * (p * p) for w, p in zip(data.weights, data.payouts))
    variance_raw = max(0.0, second_raw - exact_raw * exact_raw)
    variance_norm = variance_raw / (data.cost * data.cost) if data.cost > 0 else 0.0
    sim_standard_error = math.sqrt(variance_norm / spins) if spins > 0 else 0.0

    allowed_delta = max(rtp_tol, zscore * sim_standard_error)

    total_norm = 0.0
    sampled_max = 0.0

    for _ in range(spins):
        idx = sample_index(data.cum_weights, rng)
        payout = data.payouts[idx]
        sampled_max = payout if payout > sampled_max else sampled_max
        total_norm += payout / data.cost if data.cost > 0 else 0.0

    sim_rtp_normalized = total_norm / spins if spins > 0 else 0.0

    exact_delta = exact_rtp_normalized - target_rtp
    sim_delta = sim_rtp_normalized - target_rtp

    pass_max_reachability = True
    if data.configured_max_win is not None:
        pass_max_reachability = abs(data.table_max - data.configured_max_win) <= 1e-6

    pass_exact_rtp = abs(exact_delta) <= rtp_tol
    pass_sim_rtp = abs(sim_delta) <= allowed_delta
    pass_sampled_max_bound = (
        data.configured_max_win is None or sampled_max <= (data.configured_max_win + 1e-9)
    )

    return ModeResult(
        mode=data.mode_name,
        cost=data.cost,
        target_rtp=target_rtp,
        configured_mode_rtp=data.configured_mode_rtp,
        spins=spins,
        exact_rtp_normalized=exact_rtp_normalized,
        sim_rtp_normalized=sim_rtp_normalized,
        exact_delta_to_target=exact_delta,
        sim_delta_to_target=sim_delta,
        sim_standard_error=sim_standard_error,
        sim_allowed_delta=allowed_delta,
        weight_sum=data.weight_sum,
        configured_max_win=data.configured_max_win,
        table_max_win=data.table_max,
        sampled_max_win=sampled_max,
        pass_weight=pass_weight,
        pass_max_reachability=pass_max_reachability,
        pass_exact_rtp=pass_exact_rtp,
        pass_sim_rtp=pass_sim_rtp,
        pass_sampled_max_bound=pass_sampled_max_bound,
    )


def build_summary(results: list[ModeResult], args: argparse.Namespace, root: Path) -> dict[str, Any]:
    return {
        "package_root": str(root),
        "spins_per_mode": args.spins,
        "target_rtp": args.target_rtp,
        "rtp_tolerance": args.rtp_tol,
        "payout_scale": args.payout_scale,
        "seed": args.seed,
        "zscore": args.zscore,
        "all_modes_pass": all(r.passed for r in results) if results else False,
        "check_counts": {
            "mode_count": len(results),
            "pass_weight": sum(1 for r in results if r.pass_weight),
            "pass_max_reachability": sum(1 for r in results if r.pass_max_reachability),
            "pass_exact_rtp": sum(1 for r in results if r.pass_exact_rtp),
            "pass_sim_rtp": sum(1 for r in results if r.pass_sim_rtp),
            "pass_sampled_max_bound": sum(1 for r in results if r.pass_sampled_max_bound),
            "pass_all": sum(1 for r in results if r.passed),
        },
        "modes": [
            {
                "mode": r.mode,
                "cost": r.cost,
                "target_rtp": r.target_rtp,
                "configured_mode_rtp": r.configured_mode_rtp,
                "spins": r.spins,
                "weight_sum": r.weight_sum,
                "exact_rtp_normalized": r.exact_rtp_normalized,
                "sim_rtp_normalized": r.sim_rtp_normalized,
                "exact_delta_to_target": r.exact_delta_to_target,
                "sim_delta_to_target": r.sim_delta_to_target,
                "sim_standard_error": r.sim_standard_error,
                "sim_allowed_delta": r.sim_allowed_delta,
                "configured_max_win": r.configured_max_win,
                "table_max_win": r.table_max_win,
                "sampled_max_win": r.sampled_max_win,
                "pass_weight": r.pass_weight,
                "pass_max_reachability": r.pass_max_reachability,
                "pass_exact_rtp": r.pass_exact_rtp,
                "pass_sim_rtp": r.pass_sim_rtp,
                "pass_sampled_max_bound": r.pass_sampled_max_bound,
                "passed": r.passed,
            }
            for r in results
        ],
    }


def print_report(results: list[ModeResult], all_pass: bool) -> None:
    print(
        "mode,exact_norm_rtp,sim_norm_rtp,exact_delta,sim_delta,allowed_sim_delta,"
        "weight_ok,max_reachable,exact_rtp_ok,sim_rtp_ok,sampled_max_ok,pass"
    )
    for r in results:
        print(
            f"{r.mode},{r.exact_rtp_normalized:.6f},{r.sim_rtp_normalized:.6f},"
            f"{r.exact_delta_to_target:+.6f},{r.sim_delta_to_target:+.6f},"
            f"{r.sim_allowed_delta:.6f},{r.pass_weight},{r.pass_max_reachability},"
            f"{r.pass_exact_rtp},{r.pass_sim_rtp},{r.pass_sampled_max_bound},{r.passed}"
        )
    print(f"all_modes_pass: {all_pass}")


def main() -> int:
    args = parse_args()

    if args.spins <= 0:
        raise ValueError("--spins must be > 0")
    if args.demo_games <= 0:
        raise ValueError("--demo-games must be > 0")

    root = Path(args.root).resolve()
    publish = root / "artifacts" / "publish_files"
    index_path = publish / "index.json"

    if not index_path.exists():
        raise FileNotFoundError(f"Missing index file: {index_path}")

    index = load_json(index_path)
    modes = index.get("modes", [])
    if not isinstance(modes, list):
        raise ValueError("index.json must contain a list at key 'modes'")

    if args.mode:
        modes = [m for m in modes if isinstance(m, dict) and m.get("name") == args.mode]
        if not modes:
            raise ValueError(f"Mode not found: {args.mode}")
    else:
        modes = [m for m in modes if isinstance(m, dict) and isinstance(m.get("name"), str)]

    rng = random.Random(args.seed)

    if args.demo:
        demo_mode = modes[0]
        return run_demo_mode(
            mode=demo_mode,
            publish_path=publish,
            payout_scale=args.payout_scale,
            target_rtp=args.target_rtp,
            demo_games=args.demo_games,
            rng=rng,
        )

    results: list[ModeResult] = []
    for mode in modes:
        result = simulate_mode(
            mode=mode,
            publish_path=publish,
            spins=args.spins,
            payout_scale=args.payout_scale,
            target_rtp=args.target_rtp,
            rtp_tol=args.rtp_tol,
            zscore=args.zscore,
            rng=rng,
        )
        results.append(result)

    all_pass = all(r.passed for r in results) if results else False
    print_report(results, all_pass)

    out_path = (
        Path(args.output_json).resolve()
        if args.output_json
        else (root / "docs" / "simulator_plinko_summary.json")
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    summary = build_summary(results, args, root)
    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"summary_json: {out_path}")

    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
