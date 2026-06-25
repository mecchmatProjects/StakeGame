"""Generate Stake Engine SDK-compliant config.json + force files for azteck_plinko_final."""
from __future__ import annotations
import csv, hashlib, json, math, os
from pathlib import Path


# Bet ladder per official game rules: Min Bet 0.01, Max Bet 500.00.
BET_VALUES = [
    0.01, 0.02, 0.05, 0.10, 0.20, 0.40, 0.60, 0.80, 1.00, 1.20,
    1.40, 1.60, 1.80, 2.00, 3.00, 4.00, 5.00, 6.00, 7.00, 8.00,
    9.00, 10.00, 12.00, 14.00, 16.00, 18.00, 20.00, 30.00, 40.00,
    50.00, 75.00, 100.00, 150.00, 200.00, 250.00, 300.00, 350.00,
    400.00, 450.00, 500.00,
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            d = f.read(65536)
            if not d:
                break
            h.update(d)
    return h.hexdigest()


def lookup_stats(path: Path, cost: float, payout_scale: float = 100.0):
    rows = []
    with open(path, "r", encoding="utf-8", newline="") as f:
        for r in csv.reader(f):
            if len(r) >= 3:
                try:
                    rows.append((int(r[0]), int(r[1]), int(r[2])))
                except ValueError:
                    pass
    if not rows:
        return 0, 0.0, 0.0
    tw = sum(w for _, w, _ in rows)
    vals = [p / payout_scale for _, _, p in rows]
    mean = sum((w / tw) * v for (_, w, _), v in zip(rows, vals))
    var = sum((w / tw) * ((v - mean) ** 2) for (_, w, _), v in zip(rows, vals))
    std = math.sqrt(var)
    max_win = max(vals)
    return tw, std / cost if cost else 0.0, max_win


def main() -> None:
    root = Path("math-sdk/games/azteck_plinko_final")
    pub = root / "artifacts" / "publish_files"
    cfg_dir = root / "artifacts" / "configs"
    cfg_dir.mkdir(parents=True, exist_ok=True)

    idx = json.loads((pub / "index.json").read_text("utf-8"))
    modes = idx.get("modes", [])

    # force.json stub (empty per-mode keys)
    force_json_path = pub / "force.json"
    force_data = {m["name"]: {} for m in modes}
    force_json_path.write_text(json.dumps(force_data, indent=4), encoding="utf-8")
    print(f"wrote force.json  ({len(force_data)} modes)")

    # per-mode force_record stubs
    for m in modes:
        fr = pub / f"force_record_{m['name']}.json"
        fr.write_text("[]", encoding="utf-8")
    force_rec_hash = sha256(pub / f"force_record_{modes[0]['name']}.json")
    print(f"wrote {len(modes)} force_record stubs")

    # fe_config.json stub
    fe_cfg_path = cfg_dir / "fe_config.json"
    fe_cfg = {
        "gameId": "azteck_plinko",
        "version": idx.get("version", "0.0.4"),
        "rtpTarget": idx.get("target_rtp", 0.9605),
        "betValues": BET_VALUES,
        "minBet": BET_VALUES[0],
        "maxBet": BET_VALUES[-1],
        "modes": [{"name": m["name"], "cost": m["cost"], "maxWin": m["max_win"]} for m in modes],
    }
    fe_cfg_path.write_text(json.dumps(fe_cfg, indent=4), encoding="utf-8")
    fe_sha = sha256(fe_cfg_path)
    print(f"wrote fe_config.json  sha={fe_sha[:16]}")

    # bookShelfConfig entries
    bsc = []
    for m in modes:
        name = m["name"]
        lut_file = m["weights"]
        book_file = m["events"]
        lut_path = pub / lut_file
        book_path = pub / book_file
        force_rec_file = f"force_record_{name}.json"
        cost = float(m.get("cost", 1.0))
        tw, std_norm, max_win = lookup_stats(lut_path, cost)
        is_buy = m.get("mode_type", "") == "100balls"
        bsc.append({
            "name": name,
            "tables": [{"file": lut_file, "sha256": sha256(lut_path)}],
            "cost": cost,
            "rtp": float(m.get("rtp", 0.9605)),
            "std": round(std_norm, 6),
            "bookLength": tw,
            "feature": True,
            "autoEndRoundDisabled": False,
            "buyBonus": is_buy,
            "maxWin": float(m.get("max_win", max_win)),
            "booksFile": {"file": book_file, "sha256": sha256(book_path)},
            "forceFile": {"file": force_rec_file, "sha256": force_rec_hash},
        })

    be_config = {
        "workingName": "azteck_plinko",
        "frontendConfig": {"file": "fe_config.json", "sha256": fe_sha},
        "gameID": "azteck_plinko",
        "rtp": round(idx.get("target_rtp", 0.9605) * 100, 4),
        "betDenomination": 100,
        "minDenomination": 1,
        "betValues": BET_VALUES,
        "providerNumber": 1,
        "standardForceFile": {"file": "force.json", "sha256": sha256(force_json_path)},
        "bookShelfConfig": bsc,
    }

    out_path = cfg_dir / "config.json"
    out_path.write_text(json.dumps(be_config, indent=4), encoding="utf-8")
    print(f"wrote config.json  ({len(bsc)} bookShelfConfig entries)")


if __name__ == "__main__":
    main()
