import json, pathlib
root = pathlib.Path('math-sdk/games/azteck_plinko_biased_binomial/artifacts/publish_files')
idx = json.loads((root / 'index.json').read_text())

print('mode_type,difficulty,rows,p_right,prob_ge_5000,bonus_included')
for m in idx['modes']:
    rows = []
    with (root / m['weights']).open() as f:
        for line in f:
            a = line.strip().split(',')
            if len(a) >= 3:
                rows.append((int(a[0]), int(a[1]), int(a[2])))
    total = sum(w for _, w, _ in rows)
    prob = sum((w / total) for _, w, p in rows if (p / 100) >= 5000)
    if prob > 0:
        print(f"{m['mode_type']},{m['difficulty']},{m['rows']},{m.get('p_right', 0):.4f},{prob:.6f},yes")
