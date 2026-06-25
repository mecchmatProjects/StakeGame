"""
CORRECTED Buy100 Simulation - Validates the spec:
- Player bets $1 on buy100
- Pays $99 (99x cost)
- Receives 100 independent ball outcomes
- Expected payout = RTP × Cost = 0.9605 × $99 = $95.09
"""

import json
import random
from pathlib import Path

root = Path("math-sdk/games/azteck_plinko_final")
pub = root / "artifacts/publish_files"

def load_mode(mode_name):
    """Load mode from index.json and corresponding lookup table."""
    idx = json.loads((pub / "index.json").read_text())
    mode = next((m for m in idx["modes"] if m["name"] == mode_name), None)
    if not mode:
        raise ValueError(f"Mode {mode_name} not found")
    
    # Load lookup table
    lookup_path = pub / f"lookUpTable_{mode_name}_0.csv"
    rows = []
    cumulative_weight = 0
    for line in lookup_path.read_text().strip().split("\n")[1:]:
        parts = line.split(",")
        if len(parts) >= 3:
            sim_id = int(parts[0])
            weight = int(parts[1])
            payout_raw = int(parts[2])
            cumulative_weight += weight
            rows.append({
                "sim_id": sim_id,
                "weight": weight,
                "payout_raw": payout_raw,
                "cumulative": cumulative_weight,
                "multiplier": payout_raw / 100.0
            })
    
    mode["rows"] = rows
    mode["total_weight"] = cumulative_weight
    return mode

def resolve_bucket(mode, rng=None):
    """Resolve which bucket the ball lands in (weighted random)."""
    draw = random.randint(0, mode["total_weight"] - 1)
    for row in mode["rows"]:
        if draw < row["cumulative"]:
            return row
    return mode["rows"][-1]

def settle_single(bet, row):
    """Calculate payout for single ball."""
    multiplier = row["multiplier"]
    gross_payout = bet * multiplier
    return gross_payout, multiplier

def play_buy100(mode, bet):
    """Play buy100: 100 independent balls, sum payouts."""
    cost = bet * mode["cost"]
    total_payout = 0.0
    
    for _ in range(100):
        row = resolve_bucket(mode)  # Independent draw each ball
        gross, _ = settle_single(bet, row)
        total_payout += gross
    
    return {
        "cost": cost,
        "total_payout": total_payout,
        "rtp": total_payout / cost if cost > 0 else 0
    }

# ============================================================================
# TEST on multiple modes
# ============================================================================

print("=" * 80)
print("BUY100 CORRECTED SIMULATION TEST")
print("=" * 80)

modes_to_test = [
    "buy100_low_8",
    "buy100_medium_8", 
    "buy100_high_8",
    "buy100_expert_8",
    "buy100_expert_16",
]

for mode_name in modes_to_test:
    print(f"\n{'='*80}")
    print(f"Mode: {mode_name}")
    print(f"{'='*80}")
    
    try:
        mode = load_mode(mode_name)
        print(f"Specification:")
        print(f"  Cost: {mode['cost']}x bet")
        print(f"  Stored RTP: {mode['rtp']:.4f} (cost-adjusted)")
        
        # For bet=$1, calculate expected values
        bet = 1.0
        cost = bet * mode["cost"]
        expected_payout = cost * mode["rtp"]
        
        print(f"\nFor bet=$1:")
        print(f"  Total cost: ${cost:.2f}")
        print(f"  Expected payout: ${expected_payout:.2f} (RTP={mode['rtp']:.4f} × ${cost:.2f})")
        print(f"  Expected multiplier: {expected_payout:.2f}x")
        
        # Run simulation
        num_rounds = 10000
        print(f"\nSimulation ({num_rounds:,} rounds):")
        
        results = []
        for _ in range(num_rounds):
            result = play_buy100(mode, bet)
            results.append(result)
        
        avg_payout = sum(r["total_payout"] for r in results) / num_rounds
        avg_rtp = sum(r["rtp"] for r in results) / num_rounds
        
        print(f"  Measured avg payout: ${avg_payout:.4f}")
        print(f"  Measured avg RTP: {avg_rtp:.4f}")
        print(f"  Target RTP: {mode['rtp']:.4f}")
        print(f"  Error: {abs(avg_rtp - mode['rtp']):.6f} ({100*abs(avg_rtp - mode['rtp'])/mode['rtp']:.2f}%)")
        
        if abs(avg_rtp - mode['rtp']) < 0.002:
            print(f"  ✅ PASS (within tolerance <0.2%)")
        else:
            print(f"  ❌ FAIL (error exceeds tolerance)")
    
    except Exception as e:
        print(f"❌ Error: {e}")

print(f"\n{'='*80}")
print("CONCLUSION:")
print("  If measured RTP ≈ target RTP ± 0.2%, then:")
print("  ✅ Buy100 feature works correctly")
print("  ✅ Cost-adjusted RTP model is validated")
print("  ✅ DEVELOPER_VISUAL_GUIDE pseudocode is correct")
print(f"{'='*80}")
