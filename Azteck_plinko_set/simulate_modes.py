"""Simulator and validator for Azteck Plinko Set."""
from __future__ import annotations

import json
import csv
import random
from pathlib import Path
from collections import defaultdict
from statistics import mean, stdev


def parse_lookup(csv_path: Path) -> list[tuple[int, int, int]]:
    """Parse lookup CSV: (sim_id, weight, payout_raw)."""
    outcomes = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            sim_id = int(row['sim_id'])
            weight = int(row['weight'])
            payout_raw = int(row['payout_raw'])
            outcomes.append((sim_id, weight, payout_raw))
    return outcomes


def simulate_mode(
    outcomes: list[tuple[int, int, int]],
    num_spins: int = 500000,
) -> dict[str, float]:
    """Run Monte Carlo simulation for a mode."""
    
    # Build weighted distribution
    total_weight = sum(w for _, w, _ in outcomes)
    payouts = [p for _, _, p in outcomes]
    weights = [w for _, w, _ in outcomes]
    
    # Simulate spins
    sampled_payouts = random.choices(payouts, weights=weights, k=num_spins)
    
    # Compute statistics
    emp_mean = mean(sampled_payouts)
    emp_std = stdev(sampled_payouts) if len(sampled_payouts) > 1 else 0.0
    
    # Normalize by payout_scale (100)
    emp_rtp = emp_mean / 100.0
    emp_std_norm = emp_std / 100.0
    
    # Expected value (theoretical)
    theory_mean = sum(p * w for p, w in zip(payouts, weights)) / total_weight
    theory_rtp = theory_mean / 100.0
    
    # Max payout
    max_payout = max(payouts) / 100.0
    
    return {
        'empirical_rtp': emp_rtp,
        'theoretical_rtp': theory_rtp,
        'empirical_std': emp_std_norm,
        'max_payout': max_payout,
        'num_outcomes': len(outcomes),
    }


def main() -> int:
    """Run simulation and validation."""
    
    publish_dir = Path('artifacts/publish_files')
    docs_dir = Path('docs')
    docs_dir.mkdir(parents=True, exist_ok=True)
    
    # Read index
    with open(publish_dir / 'index.json', 'r', encoding='utf-8') as f:
        index = json.load(f)
    
    results = []
    all_pass = True
    
    for mode in index['modes']:
        mode_name = mode['mode']
        lookup_file = mode['lookupFile']
        
        # Parse lookup
        lookup_path = publish_dir / lookup_file
        outcomes = parse_lookup(lookup_path)
        
        # Simulate
        sim_result = simulate_mode(outcomes, num_spins=500000)
        
        # Validate RTP (target 0.9605 ±0.01)
        emp_rtp = sim_result['empirical_rtp']
        theory_rtp = sim_result['theoretical_rtp']
        rtp_ok = abs(emp_rtp - 0.9605) < 0.01
        
        # Validate volatility (target 0.6-50.0)
        std = sim_result['empirical_std']
        std_ok = 0.6 <= std <= 50.0
        
        mode_pass = rtp_ok and std_ok
        if not mode_pass:
            all_pass = False
        
        result = {
            'mode': mode_name,
            'theoretical_rtp': round(theory_rtp, 6),
            'empirical_rtp': round(emp_rtp, 6),
            'rtp_delta': round(abs(emp_rtp - theory_rtp), 6),
            'empirical_std': round(std, 4),
            'std_ok': std_ok,
            'rtp_ok': rtp_ok,
            'max_payout': round(sim_result['max_payout'], 4),
            'num_outcomes': sim_result['num_outcomes'],
            'pass': mode_pass,
        }
        results.append(result)
        
        if mode_pass:
            status = '[PASS]'
        else:
            status = '[FAIL]'
        print(f'{status} {mode_name}: RTP={emp_rtp:.4f} STD={std:.2f}')
    
    # Summary
    passed = sum(1 for r in results if r['pass'])
    total = len(results)
    
    print(f'\nResults: {passed}/{total} modes pass')
    print(f'All modes pass: {all_pass}')
    
    # Save detailed CSV
    csv_path = docs_dir / 'simulation_report.csv'
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
    
    print(f'Saved {csv_path}')
    
    # Save summary JSON
    summary = {
        'total_modes': total,
        'passed': passed,
        'all_modes_pass': all_pass,
        'results': results,
    }
    
    summary_path = docs_dir / 'simulation_summary.json'
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    
    print(f'Saved {summary_path}')
    
    return 0 if all_pass else 1


if __name__ == '__main__':
    raise SystemExit(main())
