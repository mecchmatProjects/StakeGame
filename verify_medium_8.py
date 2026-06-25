"""Verify buy100_medium_8 RTP."""
from pathlib import Path

lookup_path = Path("math-sdk/games/azteck_plinko_final/artifacts/publish_files/lookUpTable_buy100_medium_8_0.csv")

lines = lookup_path.read_text().strip().split("\n")

total_weight = 0
total_payout_weighted = 0

print(f"File: {lookup_path.name}\n")
print(f"{'sim_id':<8} {'weight':<20} {'payout':<15} {'mult':<12}")
print("-" * 60)

for i, line in enumerate(lines):
    parts = [p.strip() for p in line.split(",")]
    if len(parts) >= 3:
        sim_id = int(parts[0])
        weight = int(parts[1])
        payout = int(parts[2])
        mult = payout / 100.0
        
        total_weight += weight
        total_payout_weighted += weight * payout
        
        print(f"{sim_id:<8} {weight:<20} {payout:<15} {mult:>11.2f}x")

print()
print(f"Total weight: {total_weight}")
print(f"Total payout-weighted: {total_payout_weighted}")
print()

if total_weight > 0:
    # For 100 independent balls with cost=99
    avg_mult = total_payout_weighted / (100 * total_weight)
    rtp = avg_mult / 99
    
    print(f"Average multiplier: {avg_mult:.6f}")
    print(f"RTP (with cost=99): {rtp:.6f} (= {rtp*100:.2f}%)")
    print(f"\nExpected: 0.960500 (= 96.05%)")
    print(f"Error: {rtp - 0.9605:.6f} ({(rtp - 0.9605)*100:.3f}%)")
