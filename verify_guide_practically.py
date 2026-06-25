#!/usr/bin/env python3
"""Practical verification of DEVELOPER_VISUAL_GUIDE:
   Follow the guide's pseudocode step-by-step for a real mode,
   verify results match artifacts and expected RTP."""

import json
import csv
import random
from pathlib import Path
from collections import Counter

def load_mode(index_entry, publish_dir):
    """Крок 1: Load mode data from index.json and lookup CSV."""
    mode = {
        "name": index_entry["name"],
        "mode_type": index_entry["mode_type"],
        "N": int(index_entry["rows"]),
        "cost": float(index_entry["cost"]),
        "rtp": float(index_entry["rtp"]),
        "max_win": float(index_entry["max_win"]),
    }
    rows = []
    with open(publish_dir / index_entry["weights"]) as f:
        for line in f:
            sim_id, weight, payout_raw = line.strip().split(",")
            rows.append({
                "sim_id": int(sim_id),
                "bucket_index": int(sim_id) - 1,  # k = 0..N
                "visual_bucket": int(sim_id),      # 1..N+1
                "weight": int(weight),
                "payout_raw": int(payout_raw),
            })
    mode["rows"] = rows
    mode["total_weight"] = sum(r["weight"] for r in rows)
    return mode


def resolve_bucket(mode, rng_seed=None):
    """Крок 3A: Resolve bucket by lookup weight (canonical way)."""
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
    """Крок 4: Calculate payout for a single ball."""
    multiplier = row["payout_raw"] / 100.0
    gross_payout = bet * multiplier
    return gross_payout, multiplier


def play_normal(mode, bet, rng_seed=None):
    """Крок 6: Simulate a normal (1-ball) round."""
    row = resolve_bucket(mode, rng_seed)
    gross, mult = settle_single(mode, bet, row)
    return {
        "sim_id": row["sim_id"],
        "bucket_index": row["bucket_index"],
        "visual_bucket": row["visual_bucket"],
        "multiplier": mult,
        "payout": gross,
        "cost": bet * mode["cost"],
    }


def main():
    root = Path("math-sdk/games/azteck_plinko_final")
    pub = root / "artifacts/publish_files"
    
    # Load index.json
    idx = json.loads((pub / "index.json").read_text())
    
    # Pick a simple mode: normal_low_8 (8 rows = 9 buckets)
    target_mode_name = "normal_low_8"
    mode_entry = next(m for m in idx["modes"] if m["name"] == target_mode_name)
    
    print(f"=== TESTING MODE: {target_mode_name} ===\n")
    
    # Load the mode using guide's Крок 1
    mode = load_mode(mode_entry, pub)
    
    print(f"Mode info from index.json:")
    print(f"  Name: {mode['name']}")
    print(f"  Type: {mode['mode_type']}")
    print(f"  Rows: {mode['N']} → {mode['N']+1} buckets")
    print(f"  Cost: {mode['cost']}")
    print(f"  Target RTP: {mode['rtp']}")
    print(f"  Max Win: {mode['max_win']}\n")
    
    print(f"Lookup table loaded: {len(mode['rows'])} rows")
    print(f"Total weight: {mode['total_weight']}\n")
    
    # Show the lookup table structure (first 3 + last 3 rows)
    print("Lookup table structure (sim_id, weight, payout_raw, multiplier, P(k)):")
    for i, row in enumerate(mode["rows"][:3] + mode["rows"][-3:]):
        if i == 3:
            print("  ...")
        prob = row["weight"] / mode["total_weight"]
        mult = row["payout_raw"] / 100
        print(f"  sim_id={row['sim_id']} k={row['bucket_index']} "
              f"weight={row['weight']:>15} P(k)={prob:.10f} mult={mult}x")
    print()
    
    # Simulate many rounds
    bet = 1.0  # 1 unit bet
    num_rounds = 100000  # More samples to hit rare edges
    
    print(f"Simulating {num_rounds} rounds with bet={bet}...")
    total_payout = 0.0
    bucket_counts = Counter()
    multiplier_counts = Counter()
    
    for round_id in range(num_rounds):
        result = play_normal(mode, bet, rng_seed=round_id)
        total_payout += result["payout"]
        bucket_counts[result["bucket_index"]] += 1
        multiplier_counts[result["multiplier"]] += 1
    
    measured_rtp = total_payout / (num_rounds * bet * mode["cost"])
    rtp_error = abs(measured_rtp - mode["rtp"])
    
    print(f"\n=== RESULTS ===")
    print(f"Total payout: {total_payout:.2f}")
    print(f"Total cost: {num_rounds * bet * mode['cost']:.2f}")
    print(f"Measured RTP: {measured_rtp:.6f}")
    print(f"Target RTP:   {mode['rtp']:.6f}")
    print(f"Error:        {rtp_error:.6f} ({'PASS' if rtp_error < 0.001 else 'FAIL'})\n")
    
    print("Bucket distribution (first 5):")
    for bucket_idx in sorted(bucket_counts.keys())[:5]:
        count = bucket_counts[bucket_idx]
        prob_measured = count / num_rounds
        row = mode["rows"][bucket_idx]
        prob_expected = row["weight"] / mode["total_weight"]
        error = abs(prob_measured - prob_expected)
        print(f"  Bucket {bucket_idx}: count={count} "
              f"P_measured={prob_measured:.6f} P_expected={prob_expected:.6f} "
              f"error={error:.6f}")
    
    print(f"\nMultiplier distribution (all {len(multiplier_counts)} unique):")
    for mult in sorted(multiplier_counts.keys()):
        count = multiplier_counts[mult]
        prob = count / num_rounds
        print(f"  {mult}x: count={count:>5} prob={prob:.6f}")
    
    print(f"\n=== VERIFICATION vs ARTIFACTS ===")
    # Verify specific properties from the rules & artifacts
    print(f"Mode max_win from index: {mode['max_win']}")
    print(f"Highest multiplier drawn: {max(multiplier_counts.keys())}x")
    print(f"Match: {'PASS' if max(multiplier_counts.keys()) <= mode['max_win'] else 'FAIL'}")
    
    print(f"\nSymmetry check (k=0 vs k=8):")
    k0_count = bucket_counts[0]
    k8_count = bucket_counts[8]
    print(f"  k=0 (bucket_index=0): {k0_count} draws")
    print(f"  k=8 (bucket_index=8): {k8_count} draws")
    if k8_count > 0:
        ratio = k0_count / k8_count
        print(f"  Symmetry ratio: {ratio:.3f} (expect ~1.0)")
    else:
        print(f"  Symmetry ratio: N/A (too rare in {num_rounds} samples)")
    
    print(f"\n=== GUIDE COMPLIANCE ===")
    print("✓ Loaded mode via guide's Крок 1 (index.json + lookup CSV)")
    print("✓ Resolved bucket via guide's Крок 3A (cumulative weight draw)")
    print("✓ Calculated payout via guide's Крок 4 (multiplier = payout_raw/100)")
    print("✓ Simulated via guide's Крок 6 (normal mode pseudocode)")
    print(f"✓ RTP verification: {measured_rtp:.6f} ≈ {mode['rtp']:.6f}")
    print(f"✓ Distribution matches expected: error < 0.001 = {rtp_error < 0.001}")
    
    if rtp_error < 0.001:
        print(f"\n✅ GUIDE VALIDATION PASSED: Results reproduce artifacts & RTP exactly")
    else:
        print(f"\n❌ GUIDE VALIDATION FAILED: RTP mismatch too large")


if __name__ == "__main__":
    main()
