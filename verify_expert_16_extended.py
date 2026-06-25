"""Verify expert_16 with extended MC runs."""
import json
import random
from pathlib import Path

root = Path("math-sdk/games/azteck_plinko_final")
pub = root / "artifacts/publish_files"

def load_mode(mode_name):
    idx = json.loads((pub / "index.json").read_text())
    mode = next((m for m in idx["modes"] if m["name"] == mode_name), None)
    if not mode:
        raise ValueError(f"Mode {mode_name} not found")
    
    lookup_path = pub / f"lookUpTable_{mode_name}_0.csv"
    rows = []
    cumulative_weight = 0
    for line in lookup_path.read_text().strip().split("\n"):
        parts = line.split(",")
        if len(parts) >= 3:
            sim_id = int(parts[0])
            weight = int(parts[1])
            payout_raw = int(parts[2])
            cumulative_weight += weight
            rows.append({
                "payout_raw": payout_raw,
                "cumulative": cumulative_weight,
                "multiplier": payout_raw / 100.0
            })
    
    mode["rows"] = rows
    mode["total_weight"] = cumulative_weight
    return mode

def resolve_bucket(mode):
    draw = random.randint(0, mode["total_weight"] - 1)
    for row in mode["rows"]:
        if draw < row["cumulative"]:
            return row
    return mode["rows"][-1]

mode = load_mode("buy100_expert_16")
print(f"Mode: {mode['name']}")
print(f"Cost: {mode['cost']}x")
print(f"Rows in lookup: {len(mode['rows'])}")
print(f"Total weight: {mode['total_weight']}")
print()

# Run 50k rounds
results = []
for round_idx in range(50000):
    cost = 1.0 * mode["cost"]
    total_payout = 0.0
    
    for _ in range(100):
        row = resolve_bucket(mode)
        total_payout += 1.0 * row["multiplier"]
    
    rtp_pct = total_payout / cost
    results.append(rtp_pct)

import statistics
mean_rtp = statistics.mean(results)
stdev = statistics.stdev(results)
min_rtp = min(results)
max_rtp = max(results)

print(f"50,000 rounds (100 balls each = 5M balls total)")
print(f"Mean RTP (as return):        {mean_rtp:.6f}x (player gets back {mean_rtp:.2f}x for buy100 cost of 99x)")
print(f"Mean RTP (as decimal):       {mean_rtp/100:.6f} ({mean_rtp/100*100:.2f}%)")
print(f"Std Dev:         {stdev:.6f}")
print(f"Min/Max:         {min_rtp:.6f}x / {max_rtp:.6f}x")
print(f"Target RTP (decimal): 0.960500 (96.05%)")
print(f"Target RTP (return): 96.05x (from 99x cost)")
print()
mean_rtp_decimal = mean_rtp / 100
error_vs_target = mean_rtp_decimal - 0.9605
print(f"Mean RTP decimal: {mean_rtp_decimal:.6f}")
print(f"Error vs target:  {error_vs_target:.6f} ({error_vs_target*100:.3f}%)")
print()
if abs(error_vs_target) < 0.002:
    print("✅ PASS (within 0.2% of target)")
else:
    print(f"❌ FAIL (beyond 0.2% of target)")
