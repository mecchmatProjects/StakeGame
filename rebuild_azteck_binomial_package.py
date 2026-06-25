from __future__ import annotations

import csv
import hashlib
import json
import math
import shutil
from pathlib import Path

import zstandard as zstd

SRC = Path("math-sdk/games/azteck_plinko_final")
DEST = Path("math-sdk/games/azteck_plinko_binomial_fixed")
DEST_PUBLISH = Path("math-sdk/games/azteck_plinko_binomial_fixed_publish")

VERSION = "0.0.6-binomial-rtp-calibrated"
PAYOUT_SCALE = 100
TARGET_RTP = 0.9605


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_paytables(inputs_dir: Path) -> dict[tuple[str, str, int], list[float]]:
    result: dict[tuple[str, str, int], list[tuple[int, float]]] = {}

    for mode_type, file_name in [
        ("normal", "azteck_plinko_paytables_normal.csv"),
        ("100balls", "azteck_plinko_paytables_100balls.csv"),
    ]:
        with (inputs_dir / file_name).open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = (mode_type, row["difficulty"].strip().lower(), int(row["rows"]))
                result.setdefault(key, []).append((int(row["bucket_index"]), float(row["multiplier"])))

    ordered: dict[tuple[str, str, int], list[float]] = {}
    for key, rows in result.items():
        rows.sort(key=lambda x: x[0])
        ordered[key] = [m for _, m in rows]

    return ordered


def binomial_scale(multipliers: list[float], target_ev: float) -> float:
    """Uniform multiplier scale so that the binomial expected value equals target_ev.

    Weights are C(N,k); probabilities p_k = C(N,k)/2^N. Scaling all multipliers by
    s preserves symmetry and shape while moving EV = sum(p_k * m_k) onto target.
    """
    n = len(multipliers) - 1
    total_weight = float(2**n)
    raw_ev = sum((math.comb(n, k) / total_weight) * m for k, m in enumerate(multipliers))
    if raw_ev <= 0:
        raise ValueError("Non-positive raw expected value; cannot calibrate.")
    return target_ev / raw_ev


def build_rows(multipliers: list[float], scale: float = 1.0) -> list[tuple[int, int, int]]:
    n = len(multipliers) - 1
    rows: list[tuple[int, int, int]] = []
    for k, multiplier in enumerate(multipliers):
        weight = math.comb(n, k)
        payout_raw = int(round(multiplier * scale * PAYOUT_SCALE))
        rows.append((k, weight, payout_raw))
    return rows


def build_calibrated_rows(multipliers: list[float], target_ev: float) -> list[tuple[int, int, int]]:
    """Scale multipliers to target EV, round to integer payout units, then apply a
    symmetry-preserving correction across symmetric bucket groups (highest
    probability first) to absorb rounding drift while keeping payouts non-negative.
    """
    n = len(multipliers) - 1
    total_weight = float(2**n)
    scale = binomial_scale(multipliers, target_ev)
    rows = build_rows(multipliers, scale)

    # Build symmetric groups: center bucket alone (even n) or mirror pairs.
    groups: list[list[int]] = []
    for k in range(n // 2, -1, -1):
        mirror = n - k
        groups.append([k] if k == mirror else [k, mirror])
    # Highest-probability groups first.
    groups.sort(key=lambda g: sum(math.comb(n, k) for k in g), reverse=True)

    def current_ev() -> float:
        return sum((w / total_weight) * (p / PAYOUT_SCALE) for _, w, p in rows)

    residual = target_ev - current_ev()
    for g in groups:
        if abs(residual) < 0.5 / PAYOUT_SCALE / total_weight:
            break
        group_prob = sum(math.comb(n, k) / total_weight for k in g)
        delta = int(round(residual * PAYOUT_SCALE / group_prob))
        if delta == 0:
            continue
        # Clamp so no member goes negative (keeps symmetry: same delta on all members).
        min_payout = min(rows[k][2] for k in g)
        if delta < -min_payout:
            delta = -min_payout
        if delta == 0:
            continue
        for k in g:
            sid, weight, payout_raw = rows[k]
            rows[k] = (sid, weight, payout_raw + delta)
        residual = target_ev - current_ev()
    return rows


def write_lookup(path: Path, rows: list[tuple[int, int, int]]) -> bytes:
    payload = "\n".join(f"{sid},{weight},{payout_raw}" for sid, weight, payout_raw in rows) + "\n"
    data = payload.encode("utf-8")
    path.write_bytes(data)
    return data


def write_books(
    path: Path,
    mode_name: str,
    mode_type: str,
    difficulty: str,
    n_rows: int,
    rows: list[tuple[int, int, int]],
) -> bytes:
    lines = []
    for sid, weight, payout_raw in rows:
        obj = {
            "id": sid,
            "mode": mode_name,
            "modeType": mode_type,
            "difficulty": difficulty,
            "rows": n_rows,
            "weight": int(weight),
            "outcomeBucketId": int(sid),
            "payoutMultiplier": int(payout_raw),
            "criteria": "binomial_static_outcome",
            "events": [
                {
                    "type": "payout",
                    "amount": int(payout_raw),
                    "currency": "credit",
                    "id": 1,
                }
            ],
        }
        lines.append(json.dumps(obj, separators=(",", ":"), ensure_ascii=False))

    text = "\n".join(lines) + "\n"
    data = zstd.ZstdCompressor(level=19).compress(text.encode("utf-8"))
    path.write_bytes(data)
    return data


def mode_metrics(rows: list[tuple[int, int, int]], cost: float) -> tuple[float, float, float]:
    total_weight = float(sum(weight for _, weight, _ in rows))
    multipliers = [payout_raw / PAYOUT_SCALE for _, _, payout_raw in rows]
    probs = [weight / total_weight for _, weight, _ in rows]

    rtp = sum(p * m for p, m in zip(probs, multipliers)) / cost
    second_moment = sum(p * ((m / cost) ** 2) for p, m in zip(probs, multipliers))
    std_norm = max(0.0, second_moment - rtp**2) ** 0.5
    max_win = max(multipliers)
    return rtp, std_norm, max_win


def rebuild() -> None:
    if DEST.exists():
        shutil.rmtree(DEST)
    shutil.copytree(SRC, DEST)

    publish_dir = DEST / "artifacts" / "publish_files"
    config_dir = DEST / "artifacts" / "configs"

    for child in publish_dir.iterdir():
        if child.is_file():
            child.unlink()

    paytables = load_paytables(DEST / "inputs")

    src_index = json.loads((SRC / "artifacts" / "publish_files" / "index.json").read_text(encoding="utf-8"))

    index_modes: list[dict] = []
    bookshelf: list[dict] = []
    fe_modes: list[dict] = []

    force_bytes = b"{}\n"
    (publish_dir / "force.json").write_bytes(force_bytes)
    force_sha = sha256_bytes(force_bytes)

    for mode in src_index["modes"]:
        name = mode["name"]
        mode_type = mode["mode_type"]
        difficulty = mode["difficulty"]
        rows_count = int(mode["rows"])
        key = (mode_type, difficulty.lower(), rows_count)

        if key not in paytables:
            raise ValueError(f"Missing paytable for {key}")

        multipliers = paytables[key]
        cost = float(mode["cost"])
        rows = build_calibrated_rows(multipliers, TARGET_RTP * cost)

        lookup_file = f"lookUpTable_{name}_0.csv"
        books_file = f"books_{name}.jsonl.zst"
        force_record_file = f"force_record_{name}.json"

        lookup_bytes = write_lookup(publish_dir / lookup_file, rows)
        books_bytes = write_books(
            publish_dir / books_file,
            mode_name=name,
            mode_type=mode_type,
            difficulty=difficulty,
            n_rows=rows_count,
            rows=rows,
        )
        force_record_bytes = b"[]\n"
        (publish_dir / force_record_file).write_bytes(force_record_bytes)

        rtp, std_norm, max_win = mode_metrics(rows, cost)

        index_modes.append(
            {
                "name": name,
                "mode_type": mode_type,
                "difficulty": difficulty,
                "rows": rows_count,
                "cost": cost,
                "rtp": round(rtp, 6),
                "max_win": round(max_win, 4),
                "weights": lookup_file,
                "events": books_file,
                "status": "binomial-rtp-calibrated",
            }
        )

        bookshelf.append(
            {
                "name": name,
                "tables": [{"file": lookup_file, "sha256": sha256_bytes(lookup_bytes)}],
                "cost": cost,
                "rtp": round(rtp, 6),
                "std": round(std_norm, 6),
                "bookLength": 1_000_000,
                "feature": True,
                "autoEndRoundDisabled": False,
                "buyBonus": mode_type == "100balls",
                "maxWin": round(max_win, 4),
                "booksFile": {"file": books_file, "sha256": sha256_bytes(books_bytes)},
                "forceFile": {"file": force_record_file, "sha256": sha256_bytes(force_record_bytes)},
            }
        )

        fe_modes.append({"name": name, "cost": cost, "maxWin": round(max_win, 4)})

    index_payload = {
        "game_id": "azteck_plinko_binomial_fixed",
        "version": VERSION,
        "target_rtp": src_index.get("target_rtp", 0.9605),
        "modes": index_modes,
    }
    index_bytes = json.dumps(index_payload, indent=2).encode("utf-8")
    (publish_dir / "index.json").write_bytes(index_bytes)

    cfg_template = json.loads((SRC / "artifacts" / "configs" / "config.json").read_text(encoding="utf-8"))
    fe_template = json.loads((SRC / "artifacts" / "configs" / "fe_config.json").read_text(encoding="utf-8"))

    fe_template["gameId"] = "azteck_plinko_binomial_fixed"
    fe_template["version"] = VERSION
    fe_template["modes"] = fe_modes
    fe_bytes = json.dumps(fe_template, indent=4).encode("utf-8")
    (config_dir / "fe_config.json").write_bytes(fe_bytes)

    cfg_template["workingName"] = "azteck_plinko_binomial_fixed"
    cfg_template["gameID"] = "azteck_plinko_binomial_fixed"
    cfg_template["bookShelfConfig"] = bookshelf
    cfg_template["frontendConfig"] = {
        "file": "fe_config.json",
        "sha256": sha256_bytes(fe_bytes),
    }
    cfg_template["standardForceFile"] = {"file": "force.json", "sha256": force_sha}
    cfg_bytes = json.dumps(cfg_template, indent=4).encode("utf-8")
    (config_dir / "config.json").write_bytes(cfg_bytes)

    # Keep root-level copies aligned (same pattern as existing package).
    (DEST / "config.json").write_bytes(cfg_bytes)
    (DEST / "fe_config.json").write_bytes(fe_bytes)

    if DEST_PUBLISH.exists():
        shutil.rmtree(DEST_PUBLISH)
    DEST_PUBLISH.mkdir(parents=True, exist_ok=True)

    for item in publish_dir.iterdir():
        shutil.copy2(item, DEST_PUBLISH / item.name)
    shutil.copy2(config_dir / "config.json", DEST_PUBLISH / "config.json")
    shutil.copy2(config_dir / "fe_config.json", DEST_PUBLISH / "fe_config.json")

    normal_rtp = [m["rtp"] for m in index_modes if m["mode_type"] == "normal"]
    buy_rtp = [m["rtp"] for m in index_modes if m["mode_type"] == "100balls"]

    print(f"Generated package: {DEST}")
    print(f"Generated publish folder: {DEST_PUBLISH}")
    print(f"Modes: {len(index_modes)}")
    print(f"Normal RTP range: {min(normal_rtp):.6f}..{max(normal_rtp):.6f}")
    print(f"Buy100 RTP range: {min(buy_rtp):.6f}..{max(buy_rtp):.6f}")


if __name__ == "__main__":
    rebuild()
