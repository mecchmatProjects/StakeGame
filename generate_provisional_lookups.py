from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import zstandard as zstd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate lookup tables and zstd-compressed books from probability tables")
    parser.add_argument("--root", required=True, help="Package root path, for example math-sdk/games/azteck_plinko_final")
    parser.add_argument("--payout-scale", type=float, default=100.0, help="Scale applied for lookup payout field")
    parser.add_argument("--strict", action="store_true", help="Fail if any mode has invalid or missing probabilities")
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
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
    # format: normal_low_8 or buy100_expert_16
    parts = name.split("_")
    if len(parts) < 3:
        return ("", "", "")
    prefix = parts[0].lower()
    difficulty = parts[1].capitalize()
    rows = parts[2]
    mode_type = "100balls" if prefix == "buy100" else "normal"
    return (mode_type, difficulty, rows)


def parse_float(text: str) -> float | None:
    if text is None:
        return None
    t = text.strip()
    if not t or t.upper() == "TODO":
        return None
    try:
        return float(t)
    except ValueError:
        return None


def write_lookup(path: Path, rows: list[tuple[int, int, float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        for sim_id, weight, payout_raw in rows:
            writer.writerow([sim_id, weight, int(round(payout_raw))])


def build_event_payload(mode_name: str, payout_mult: float, bucket_index: int, mode_type: str, difficulty: str, rows: str) -> list[dict]:
    if mode_type == "100balls":
        return [
            {
                "type": "round_init",
                "mode": mode_name,
                "modeType": mode_type,
                "difficulty": difficulty,
                "rows": int(rows),
            },
            {
                "type": "batch_trajectories_selected",
                "outcomeBucketId": bucket_index,
                "batchSize": 100,
            },
            {
                "type": "batch_buckets_landed",
                "outcomeBucketId": bucket_index,
                "payoutMultiplier": payout_mult,
            },
            {
                "type": "settlement",
                "totalPayoutMultiplier": payout_mult,
            },
        ]

    return [
        {
            "type": "round_init",
            "mode": mode_name,
            "modeType": mode_type,
            "difficulty": difficulty,
            "rows": int(rows),
        },
        {
            "type": "trajectory_selected",
            "outcomeBucketId": bucket_index,
        },
        {
            "type": "bucket_landed",
            "outcomeBucketId": bucket_index,
            "payoutMultiplier": payout_mult,
        },
        {
            "type": "settlement",
            "totalPayoutMultiplier": payout_mult,
        },
    ]


def write_deterministic_book(
    path: Path,
    mode_name: str,
    mode_type: str,
    difficulty: str,
    rows: str,
    lookup_rows: list[tuple[int, int, float]],
    payout_scale: float,
) -> None:
    # Stake Engine publish ingestion expects real zstd-compressed .jsonl.zst payloads.
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for bucket_index, (sim_id, weight, payout_raw) in enumerate(lookup_rows):
        payout_mult = payout_raw / payout_scale
        record = {
            "id": sim_id,
            "mode": mode_name,
            "modeType": mode_type,
            "difficulty": difficulty,
            "rows": int(rows),
            "weight": weight,
            "outcomeBucketId": bucket_index,
            "payoutRaw": payout_raw,
            "payoutMultiplier": payout_mult,
            "criteria": "deterministic_static_outcome",
            "events": build_event_payload(mode_name, payout_mult, bucket_index, mode_type, difficulty, rows),
        }
        lines.append(json.dumps(record, separators=(",", ":")))
        payload = ("\n".join(lines) + "\n").encode("utf-8")
        compressed = zstd.ZstdCompressor(level=3).compress(payload)
        path.write_bytes(compressed)


def main() -> int:
    args = parse_args()
    root = Path(args.root).resolve()
    inputs = root / "inputs"
    publish = root / "artifacts" / "publish_files"

    index_path = publish / "index.json"
    if not index_path.exists():
        raise FileNotFoundError(index_path)

    prob_path = inputs / "azteck_plinko_probability_tables.csv"
    if not prob_path.exists():
        raise FileNotFoundError(prob_path)

    index = json.loads(index_path.read_text(encoding="utf-8"))
    modes = index.get("modes", [])
    prob_rows = read_csv(prob_path)

    grouped: dict[tuple[str, str, str], list[dict[str, str]]] = {}
    for row in prob_rows:
        key = (normalize_mode_type(row.get("mode_type", "")), row.get("difficulty", ""), row.get("rows", ""))
        grouped.setdefault(key, []).append(row)

    generated = 0
    skipped = 0
    errors: list[str] = []

    for mode in modes:
        if not isinstance(mode, dict):
            continue

        mode_name = mode.get("name")
        if not isinstance(mode_name, str):
            continue

        mode_type, difficulty, rows = mode_to_tuple(mode_name)
        key = (mode_type, difficulty, rows)
        candidates = grouped.get(key, [])

        normalized: list[tuple[int, float, float]] = []  # sim_id, prob, multiplier
        sim_id = 1
        for row in candidates:
            m = parse_float(row.get("multiplier", ""))
            p = parse_float(row.get("probability", ""))
            if m is None:
                continue
            if p is None:
                p = 0.0
            normalized.append((sim_id, p, m))
            sim_id += 1

        if not normalized:
            skipped += 1
            msg = f"missing valid probabilities/multipliers for mode {mode_name}"
            if args.strict:
                errors.append(msg)
            continue

        prob_sum = sum(p for _, p, _ in normalized if p > 0)
        if prob_sum <= 0:
            skipped += 1
            msg = f"non-positive probability sum for mode {mode_name}"
            if args.strict:
                errors.append(msg)
            continue

        # Scale to integer weights with 1e6 precision while preserving the rare top bucket.
        weight_scale = 1_000_000
        quotas: list[tuple[int, float, float, int, float]] = []
        for sid, p, m in normalized:
            quota = ((p / prob_sum) * weight_scale) if p > 0 else 0.0
            base = int(quota)
            frac = quota - base
            quotas.append((sid, p, m, base, frac))

        allocated = sum(base for _, _, _, base, _ in quotas)
        remainder = weight_scale - allocated

        order = sorted(range(len(quotas)), key=lambda i: quotas[i][4], reverse=True)
        weights = [base for _, _, _, base, _ in quotas]
        for i in order[:max(0, remainder)]:
            weights[i] += 1

        # Force the highest multiplier bucket to be reachable with at least one weight.
        # When symmetric ladders contain duplicate maxima, choose the max bucket with the
        # highest modeled probability (not just the first occurrence).
        max_multiplier = max(quotas[i][2] for i in range(len(quotas)))
        max_candidates = [i for i in range(len(quotas)) if quotas[i][2] == max_multiplier]
        max_idx = max(max_candidates, key=lambda i: (quotas[i][1], quotas[i][4], -i))

        if weights[max_idx] == 0:
            donor_idx = max(
                (i for i in range(len(weights)) if i != max_idx and weights[i] > 1),
                key=lambda i: weights[i],
                default=None,
            )
            if donor_idx is not None:
                weights[donor_idx] -= 1
                weights[max_idx] = 1

        lookup_rows: list[tuple[int, int, float]] = []
        for (sid, _, m, _, _), weight in zip(quotas, weights):
            if weight <= 0:
                continue
            payout_raw = int(round(m * args.payout_scale))
            lookup_rows.append((sid, weight, payout_raw))

        lookup_name = mode.get("weights") or f"lookUpTable_{mode_name}_0.csv"
        book_name = mode.get("events") or f"books_{mode_name}.jsonl.zst"

        lookup_path = publish / lookup_name
        book_path = publish / book_name

        write_lookup(lookup_path, lookup_rows)
        write_deterministic_book(book_path, mode_name, mode_type, difficulty, rows, lookup_rows, args.payout_scale)

        generated += 1

    if errors:
        for e in errors:
            print(f"ERROR: {e}")
        return 2

    print(f"Generated provisional lookup/book artifacts for modes: {generated}")
    print(f"Skipped modes (insufficient inputs): {skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
