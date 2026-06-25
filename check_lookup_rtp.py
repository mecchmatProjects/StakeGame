"""Verify exact RTP from lookup table vs index.json stored value."""
import json
from pathlib import Path

root = Path("math-sdk/games/azteck_plinko_final")
pub = root / "artifacts/publish_files"

idx = json.loads((pub / "index.json").read_text())
mode_entry = next(m for m in idx["modes"] if m["name"] == "normal_low_8")

print("Index.json values:")
print(f"  rtp (stored): {mode_entry['rtp']}")
print(f"  cost: {mode_entry['cost']}")

# Calculate exact RTP from lookup
rows = []
with open(pub / mode_entry["weights"]) as f:
    for line in f:
        sim_id, weight, payout_raw = line.strip().split(",")
        rows.append((int(sim_id), int(weight), int(payout_raw)))

total_w = sum(w for _, w, _ in rows)
ev_multiplier = sum((w / total_w) * (p / 100) for _, w, p in rows)

print("\nFrom lookup table:")
for sim_id, w, p in rows:
    k = sim_id - 1
    print(f"  k={k}: weight={w:>15} prob={w/total_w:.12f} mult={p/100:.2f}x")

print()
print(f"Total weight: {total_w}")
print(f"Theoretical RTP = sum(P(k)*M(k)) = {ev_multiplier:.12f}")
print(f"Stored RTP in index: {mode_entry['rtp']:.12f}")
print(f"Difference: {abs(ev_multiplier - mode_entry['rtp']):.2e}")
print(f"Match (within 1e-6): {abs(ev_multiplier - mode_entry['rtp']) < 1e-6}")
