"""
Analyze a single mode's lookup table in detail to understand the RTP calculation.
"""
from pathlib import Path

root = Path("math-sdk/games/azteck_plinko_final")
pub = root / "artifacts/publish_files"

# Analyze normal_medium_8
mode_name = "normal_medium_8"
lookup_path = pub / f"lookUpTable_{mode_name}_0.csv"

print(f"Analyzing: {mode_name}\n")
print(f"File: {lookup_path}\n")

lines = lookup_path.read_text().strip().split("\n")
print(f"Total lines (including header): {len(lines)}\n")

print("Content of lookup table:")
print(f"{'sim_id':<8} {'weight':<20} {'payout_raw':<15} {'mult':<10}")
print("-" * 60)

total_weight = 0
total_payout_weighted = 0

for i, line in enumerate(lines[:15]):  # First 15 lines (including header)
    if i == 0:
        print(f"(header: {line})")
        continue
    
    parts = line.split(",")
    if len(parts) >= 3:
        sim_id = int(parts[0])
        weight = int(parts[1])
        payout_raw = int(parts[2])
        mult = payout_raw / 100.0
        
        total_weight += weight
        total_payout_weighted += weight * payout_raw
        
        print(f"{sim_id:<8} {weight:<20} {payout_raw:<15} {mult:>9.2f}x")

print()
print(f"After {len(lines)-1} rows:")
print(f"  Total weight: {total_weight}")
print(f"  Total payout-weighted: {total_payout_weighted}")

if total_weight > 0:
    avg_payout_per_100 = total_payout_weighted / total_weight
    rtp = avg_payout_per_100 / 100
    print(f"\nCalculated RTP:")
    print(f"  Average payout (per-100): {avg_payout_per_100:.4f}")
    print(f"  RTP: {rtp:.6f} (= {rtp*100:.2f}%)")
    print(f"\nExpected RTP: 0.960500 (= 96.05%)")
    print(f"Drift: {abs(rtp - 0.9605):.6f}")
