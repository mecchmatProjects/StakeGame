"""Compute theoretical RTP directly from lookup tables."""
import json
from pathlib import Path

root = Path("math-sdk/games/azteck_plinko_final")
pub = root / "artifacts/publish_files"

# Load index to get cost for each mode
idx = json.loads((pub / "index.json").read_text())

print("=" * 80)
print("THEORETICAL RTP FROM LOOKUP TABLES (WITH COST CORRECTION)")
print("=" * 80)
print()

for mode_obj in idx["modes"]:
    mode_name = mode_obj["name"]
    cost = mode_obj["cost"]
    
    lookup_path = pub / f"lookUpTable_{mode_name}_0.csv"
    if not lookup_path.exists():
        continue
    
    # Compute theoretical RTP
    total_weight = 0
    total_payout_weighted = 0
    
    for line in lookup_path.read_text().strip().split("\n")[1:]:  # Skip header
        parts = line.split(",")
        if len(parts) >= 3:
            weight = int(parts[1])
            payout_raw = int(parts[2])
            total_weight += weight
            total_payout_weighted += weight * payout_raw
    
    if total_weight > 0:
        # RTP = (sum(weight*payout) / total_weight) / (PAYOUT_SCALE * cost)
        # Since payout_raw is already in units of PAYOUT_SCALE=100, we divide by 100
        avg_payout_multiplier = total_payout_weighted / (100 * total_weight)
        theoretical_rtp = avg_payout_multiplier / cost
        
        print(f"{mode_name:20} | cost={cost:5.1f} | Theoretical RTP: {theoretical_rtp:.6f} (= {theoretical_rtp*100:.2f}%)")

print()
print("Expected RTP from index: 0.960500 (= 96.05%)")
