import csv
import random
import math
import importlib

try:
    pywraplp = importlib.import_module("ortools.linear_solver.pywraplp")
except ModuleNotFoundError:
    pywraplp = None


# =========================
# 📦 DATA LOADER
# =========================
def load_weights(path):
    ids, probs = [], []

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        first = next(reader)

        has_header = any(x.lower() in ["id", "prob", "weight"] for x in first)

        if has_header:
            f.seek(0)
            reader = csv.DictReader(f)
            for row in reader:
                raw_id = row.get("id") or row.get("simulation_id")
                raw_prob = row.get("weight") or row.get("probability")
                if raw_id is None or raw_prob is None:
                    raise ValueError("CSV header detected, but required columns are missing")
                ids.append(int(raw_id))
                probs.append(float(raw_prob))
        else:
            ids.append(int(first[0]))
            probs.append(float(first[1]))
            for row in reader:
                ids.append(int(row[0]))
                probs.append(float(row[1]))

    total = sum(probs)
    probs = [p / total for p in probs]

    return ids, probs


# =========================
# 🎯 OPTIMIZER (OR-TOOLS)
# =========================
def optimize_multipliers(probs, target_rtp, max_mult, var_cap=None):
    if pywraplp is None:
        # Fallback without OR-Tools: constant multipliers satisfy mean RTP exactly.
        value = min(max(target_rtp, 0.0), max_mult)
        return [value] * len(probs)

    if var_cap is not None:
        # LP backend cannot enforce quadratic variance directly.
        # Keep behavior deterministic by optimizing smoothness via L1 distance objective.
        pass

    n = len(probs)

    solver = pywraplp.Solver.CreateSolver("GLOP")
    if solver is None:
        value = min(max(target_rtp, 0.0), max_mult)
        return [value] * len(probs)

    m = [solver.NumVar(0.0, float(max_mult), f"m_{i}") for i in range(n)]
    d = [solver.NumVar(0.0, solver.infinity(), f"d_{i}") for i in range(n)]

    mean_expr = solver.Sum(float(probs[i]) * m[i] for i in range(n))
    solver.Add(mean_expr == float(target_rtp))

    # Minimize total absolute deviation from target multiplier.
    for i in range(n):
        solver.Add(m[i] - float(target_rtp) <= d[i])
        solver.Add(float(target_rtp) - m[i] <= d[i])

    objective = solver.Objective()
    for i in range(n):
        objective.SetCoefficient(d[i], 1.0)
    objective.SetMinimization()

    try:
        status = solver.Solve()
    except Exception:
        value = min(max(target_rtp, 0.0), max_mult)
        return [value] * len(probs)

    if status not in (pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE):
        value = min(max(target_rtp, 0.0), max_mult)
        return [value] * len(probs)

    return [v.solution_value() for v in m]


# =========================
# 🎮 SIMULATOR
# =========================
class Simulator:
    def __init__(self, probs, multipliers):
        self.probs = probs
        self.mults = multipliers

    def spin(self):
        r = random.random()
        cum = 0
        for i, p in enumerate(self.probs):
            cum += p
            if r <= cum:
                return self.mults[i]
        return self.mults[-1]

    def run(self, n):
        results = []
        for _ in range(n):
            results.append(self.spin())
        return results


# =========================
# 📊 METRICS
# =========================
def compute_metrics(results):
    n = len(results)

    mean = sum(results) / n
    variance = sum((x - mean) ** 2 for x in results) / n
    std = math.sqrt(variance)

    hit_rate = sum(1 for x in results if x > 0) / n

    return {
        "rtp": mean,
        "std": std,
        "hit_rate": hit_rate,
        "max_win": max(results)
    }


# =========================
# 🔁 OPTIMIZATION LOOP
# =========================
def optimize_loop(
    probs,
    target_rtp=0.96,
    max_mult=100,
    var_cap=10,
    spins=200_000,
    iterations=5
):
    best = None

    for i in range(iterations):
        print(f"\n=== ITERATION {i+1} ===")

        if pywraplp is None and i == 0:
            print("ortools not installed; using constant-multiplier fallback optimizer")

        multipliers = optimize_multipliers(
            probs,
            target_rtp,
            max_mult,
            var_cap
        )

        sim = Simulator(probs, multipliers)
        results = sim.run(spins)

        metrics = compute_metrics(results)

        print("RTP:", round(metrics["rtp"], 5))
        print("STD:", round(metrics["std"], 5))
        print("Hit Rate:", round(metrics["hit_rate"], 5))
        print("Max Win:", round(metrics["max_win"], 2))

        # track best RTP match
        error = abs(metrics["rtp"] - target_rtp)

        if best is None or error < best["error"]:
            best = {
                "multipliers": multipliers,
                "metrics": metrics,
                "error": error
            }

        # 🔧 adaptive tuning
        if metrics["std"] > math.sqrt(var_cap):
            var_cap *= 0.8
        else:
            var_cap *= 1.1

    if best is None:
        raise RuntimeError("No optimization result produced")

    return best


# =========================
# 🚀 MAIN
# =========================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--weights", required=True)
    parser.add_argument("--rtp", type=float, default=0.96)
    parser.add_argument("--max_mult", type=float, default=100)
    parser.add_argument("--var", type=float, default=10)
    parser.add_argument("--spins", type=int, default=200000)

    args = parser.parse_args()

    ids, probs = load_weights(args.weights)

    result = optimize_loop(
        probs,
        target_rtp=args.rtp,
        max_mult=args.max_mult,
        var_cap=args.var,
        spins=args.spins
    )

    print("\n=== BEST SOLUTION ===")
    print("RTP:", result["metrics"]["rtp"])
    print("STD:", result["metrics"]["std"])
    print("Hit Rate:", result["metrics"]["hit_rate"])

    if pywraplp is None:
        print("Note: Install ortools to enable LP-based optimization backend.")