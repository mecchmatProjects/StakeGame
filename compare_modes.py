"""Compare multipliers and RTP between normal and buy100 modes."""
import json
from pathlib import Path

root = Path("math-sdk/games/azteck_plinko_final")
pub = root / "artifacts/publish_files"

idx = json.loads((pub / "index.json").read_text())

print("Comparing modes:\n")
for mode_name in ["normal_low_8", "buy100_low_8", "normal_expert_16", "buy100_expert_16"]:
    mode = next(x for x in idx["modes"] if x["name"] == mode_name)
    
    rows = []
    with open(pub / mode["weights"]) as f:
        for line in f:
            sim_id, w, p = line.strip().split(",")
            rows.append((int(sim_id), int(w), int(p)))
    
    total_w = sum(w for _, w, _ in rows)
    ev = sum((w / total_w) * (p / 100) for _, w, p in rows)
    max_mult = max(p / 100 for _, _, p in rows)
    min_mult = min(p / 100 for _, _, p in rows)
    
    print(f"{mode_name:20} | cost={mode['cost']:4.0f}x | "
          f"multiplier range {min_mult:>8.1f}x..{max_mult:>8.0f}x | "
          f"EV={ev:.6f} | stored_rtp={mode['rtp']}")
