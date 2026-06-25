#!/usr/bin/env python3
"""Test guide's Buy100 logic (Крок 7) with a higher-variance mode."""

import json
import random
from pathlib import Path


def load_mode(index_entry, publish_dir):
    mode = {
        "name": index_entry["name"],
        "mode_type": index_entry["mode_type"],
        "N": int(index_entry["rows"]),
        "cost": float(index_entry["cost"]),
        "rtp": float(index_entry["rtp"]),
    }
    rows = []
    with open(publish_dir / index_entry["weights"]) as f:
        for line in f:
            sim_id, weight, payout_raw = line.strip().split(",")
            rows.append({
                "sim_id": int(sim_id),
                "bucket_index": int(sim_id) - 1,
                "weight": int(weight),
                "payout_raw": int(payout_raw),
            })
    mode["rows"] = rows
    mode["total_weight"] = sum(r["weight"] for r in rows)
    return mode


def resolve_bucket(mode, rng_seed=None):
    if rng_seed is not None:
        random.seed(rng_seed)
    draw = random.randint(0, mode["total_weight"] - 1)
    cumulative = 0
    for row in mode["rows"]:
        cumulative += row["weight"]
        if draw < cumulative:
            return row
    return mode["rows"][-1]


def settle_single(mode, bet, row):
    multiplier = row["payout_raw"] / 100.0
    gross_payout = bet * multiplier
    return gross_payout, multiplier


def play_buy100(mode, bet, rng_seed=None):
    """Крок 7: Simulate a Buy100 (100-balls) round."""
    if rng_seed is not None:
        random.seed(rng_seed)
    assert mode["mode_type"] == "100balls"
    buy_cost = bet * mode["cost"]
    balls, total_payout = [], 0.0
    for ball_idx in range(100):
        row = resolve_bucket(mode)  # Independent draw for each ball
        gross, mult = settle_single(mode, bet, row)
        total_payout += gross
        balls.append({
            "sim_id": row["sim_id"],
            "bucket_index": row["bucket_index"],
            "multiplier": mult,
            "payout": gross,
        })
    return {
        "balls": balls,
        "buy_cost": buy_cost,
        "total_gross": total_payout,
        "net": total_payout - buy_cost,
    }


def main():
    root = Path("math-sdk/games/azteck_plinko_final")
    pub = root / "artifacts/publish_files"
    
    idx = json.loads((pub / "index.json").read_text())
    
    # Test Buy100 Expert: high variance
    target_mode_name = "buy100_expert_16"
    mode_entry = next(m for m in idx["modes"] if m["name"] == target_mode_name)
    
    print(f"=== TESTING MODE: {target_mode_name} (Buy100 Expert) ===\n")
    
    mode = load_mode(mode_entry, pub)
    
    print(f"Mode info:")
    print(f"  Type: {mode['mode_type']} (100 independent balls)")
    print(f"  Rows: {mode['N']} → {mode['N']+1} buckets")
    print(f"  Cost per ball: {1.0}")
    print(f"  Total cost: {mode['cost']} = 99x bet")
    print(f"  Target RTP: {mode['rtp']}")
    print(f"  Lookup rows: {len(mode['rows'])}\n")
    
    # Show a few lookup entries
    print("Sample lookup entries:")
    for row in mode["rows"][:3] + mode["rows"][-3:]:
        prob = row["weight"] / mode["total_weight"]
        mult = row["payout_raw"] / 100
        print(f"  k={row['bucket_index']:>2} mult={mult:>8.1f}x weight={row['weight']:>15} "
              f"prob={prob:.12f}")
    
    # Simulate
    bet = 1.0
    num_rounds = 5000
    
    print(f"\nSimulating {num_rounds} Buy100 rounds (bet={bet}, cost=99x)...")
    total_cost = 0.0
    total_gross = 0.0
    max_single_win = 0.0
    
    for round_id in range(num_rounds):
        result = play_buy100(mode, bet, rng_seed=round_id)
        cost = result["buy_cost"]
        gross = result["total_gross"]
        total_cost += cost
        total_gross += gross
        max_single_win = max(max_single_win, gross)
    
    measured_rtp = total_gross / total_cost
    rtp_error = abs(measured_rtp - mode["rtp"])
    
    print(f"\n=== RESULTS ===")
    print(f"Total cost: {total_cost:.2f}")
    print(f"Total gross payout: {total_gross:.2f}")
    print(f"Measured RTP: {measured_rtp:.6f}")
    print(f"Target RTP:   {mode['rtp']:.6f}")
    print(f"Error:        {rtp_error:.6f}")
    print(f"Max single round win: {max_single_win:.2f}")
    
    print(f"\n=== COMPLIANCE CHECK ===")
    print("✓ Loaded Buy100 mode via guide's Крок 1")
    print("✓ For each of 100 balls: independent resolve_bucket (guide's Крок 3A)")
    print("✓ Each ball's payout: settle_single (guide's Крок 4)")
    print("✓ Total payout: sum of 100 balls")
    print("✓ RTP = total_gross / total_cost (with cost = 99x bet)")
    
    if rtp_error < 0.01:  # Within 1% for Buy100 (higher variance)
        print(f"\n✅ GUIDE VALIDATION PASSED (Buy100): RTP within tolerance")
    else:
        print(f"\n⚠️  GUIDE VALIDATION: RTP diff = {rtp_error:.2%}")


if __name__ == "__main__":
    main()
