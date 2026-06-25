"""
Verify and correct buy100 artifacts according to spec:
- Cost: 99x bet
- 100 independent balls with multipliers
- Total payout range: 1584x (Low) to 100,000x (Expert)
- RTP: 0.9605 (cost-adjusted)
"""

import json
from pathlib import Path
from collections import defaultdict

root = Path("math-sdk/games/azteck_plinko_final")
pub = root / "artifacts/publish_files"

idx = json.loads((pub / "index.json").read_text())

# Verify buy100 modes have correct cost and RTP
print("=" * 80)
print("BUY100 MODE VERIFICATION")
print("=" * 80)

buy_modes = [m for m in idx["modes"] if m["mode_type"] == "100balls"]
print(f"\nFound {len(buy_modes)} buy100 modes\n")

# Check cost
costs = set(m["cost"] for m in buy_modes)
print(f"Costs found: {costs} (Expected: {{99.0}})")
assert costs == {99.0}, "❌ Buy100 cost is not 99x!"
print("✓ All buy100 modes have cost=99\n")

# Check RTP uniformity
rtps = set(m["rtp"] for m in buy_modes)
print(f"RTP values: {rtps} (Expected: {{0.9605}})")
assert len(rtps) == 1 and 0.9605 in rtps, "❌ Buy100 RTP not uniform!"
print("✓ All buy100 modes have RTP=0.9605\n")

# Now check the multiplier ranges in lookup tables
print("Checking multiplier ranges from lookup tables:")
print("-" * 80)

for difficulty in ["Low", "Medium", "High", "Expert"]:
    # Get a representative mode (8-row is smallest, easiest to verify)
    mode_name = f"buy100_{difficulty.lower()}_8"
    mode_obj = next((m for m in buy_modes if m["name"] == mode_name), None)
    if not mode_obj:
        continue
    
    # Load lookup
    lookup_path = pub / f"lookUpTable_buy100_{difficulty.lower()}_8_0.csv"
    if not lookup_path.exists():
        print(f"⚠️  {lookup_path.name} not found")
        continue
    
    lines = lookup_path.read_text().strip().split("\n")
    # Skip header, parse rows
    multipliers = []
    for line in lines[1:]:  # Skip "sim_id,weight,payout_raw"
        parts = line.split(",")
        if len(parts) >= 3:
            payout_raw = int(parts[2])
            mult = payout_raw / 100.0
            multipliers.append(mult)
    
    if multipliers:
        min_mult = min(multipliers)
        max_mult = max(multipliers)
        print(f"\nbuy100_{difficulty.lower()}_8:")
        print(f"  Min multiplier: {min_mult}x")
        print(f"  Max multiplier: {max_mult}x")
        
        # Check if max is capped at 100,000x
        if max_mult > 100000:
            print(f"  ⚠️  MAX EXCEEDS 100,000x! Found {max_mult}x")
        else:
            print(f"  ✓ Within max 100,000x cap")

print("\n" + "=" * 80)
print("COST-ADJUSTED EXPECTED PAYOUT (bet=$1, cost=$99):")
print("=" * 80)

# For each difficulty, show expected payout
for difficulty in ["Low", "Medium", "High", "Expert"]:
    mode_name = f"buy100_{difficulty.lower()}_8"
    mode_obj = next((m for m in buy_modes if m["name"] == mode_name), None)
    if mode_obj:
        cost = mode_obj["cost"]
        rtp = mode_obj["rtp"]
        expected_payout = cost * rtp
        print(f"buy100 {difficulty:8} | bet=$1 | cost=${cost} | RTP={rtp} | E[payout]=${expected_payout:.2f}")

print("\n" + "=" * 80)
