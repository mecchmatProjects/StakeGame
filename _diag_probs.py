import json, math, pathlib

root = pathlib.Path('math-sdk/games/azteck_plinko_biased_binomial/artifacts/publish_files')
idx = json.loads((root / 'index.json').read_text())

print(f"{'mode':<22} {'p_right':>7} {'N':>3} {'min_prob':>12} {'max_prob':>12} {'ratio':>10} {'min_weight':>12} {'max_weight':>12}")
print("-" * 110)

extremes = []
for m in idx['modes']:
    N = m['rows']; p = m['p_right']
    rows = []
    with (root / m['weights']).open() as f:
        for line in f:
            a = line.strip().split(',')
            if len(a) >= 3:
                rows.append((int(a[0]), int(a[1]), int(a[2])))
    weights = [w for _, w, _ in rows]
    total_w = sum(weights)
    probs = [w / total_w for w in weights]
    min_p, max_p = min(probs), max(probs)
    ratio = max_p / min_p
    print(f"{m['name']:<22} {p:>7.4f} {N:>3} {min_p:>12.6f} {max_p:>12.6f} {ratio:>10.1f} {min(weights):>12} {max(weights):>12}")
    if ratio > 4000 or min_p < 0.01:
        extremes.append((m['name'], p, N, min_p, ratio))

print()
print(f"Modes with min_prob < 0.01 or ratio > 4000: {len(extremes)}")
for e in extremes:
    print(f"  {e[0]}: p={e[1]:.4f} N={e[2]} min_p={e[3]:.6f} ratio={e[4]:.1f}")
