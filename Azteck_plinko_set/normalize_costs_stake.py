from __future__ import annotations

import json
from pathlib import Path


def mode_is_buy100(mode_type: str | None, name: str | None) -> bool:
    if (mode_type or "") == "100balls":
        return True
    return (name or "").startswith("buy100_")


def main() -> int:
    publish_dir = Path("artifacts/publish_files")
    config_dir = Path("artifacts/configs")

    index_path = publish_dir / "index.json"
    config_path = config_dir / "config.json"
    fe_path = config_dir / "fe_config.json"

    idx = json.loads(index_path.read_text(encoding="utf-8"))
    cfg = json.loads(config_path.read_text(encoding="utf-8"))

    for m in idx.get("modes", []):
        mt = m.get("mode_type") or m.get("modeType")
        nm = m.get("name") or m.get("mode")
        m["cost"] = 99.0 if mode_is_buy100(mt, nm) else 1.0

    for e in cfg.get("bookShelfConfig", []):
        nm = e.get("name")
        buy = bool(e.get("buyBonus")) or (nm or "").startswith("buy100_")
        e["cost"] = 99.0 if buy else 1.0

    if fe_path.exists():
        fe = json.loads(fe_path.read_text(encoding="utf-8"))
        for m in fe.get("modes", []):
            nm = m.get("name") or ""
            m["cost"] = 99.0 if nm.startswith("buy100_") else 1.0
        fe_path.write_text(json.dumps(fe, indent=2), encoding="utf-8")

    index_path.write_text(json.dumps(idx, indent=2), encoding="utf-8")
    config_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")

    idx_costs = [m.get("cost") for m in idx.get("modes", [])]
    cfg_costs = [e.get("cost") for e in cfg.get("bookShelfConfig", [])]
    print("index_min_cost", min(idx_costs) if idx_costs else None)
    print("config_min_cost", min(cfg_costs) if cfg_costs else None)
    print("index_unique_costs", sorted(set(idx_costs)))
    print("config_unique_costs", sorted(set(cfg_costs)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
