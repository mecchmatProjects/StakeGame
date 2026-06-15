import importlib

try:
    pywraplp = importlib.import_module("ortools.linear_solver.pywraplp")
except ModuleNotFoundError:
    pywraplp = None


def solve_multipliers(probs, target_rtp, max_mult=1000, var_cap=None):
    if pywraplp is None:
        value = min(max(target_rtp, 0.0), max_mult)
        return [value] * len(probs)

    n = len(probs)

    solver = pywraplp.Solver.CreateSolver("GLOP")
    if solver is None:
        value = min(max(target_rtp, 0.0), max_mult)
        return [value] * len(probs)

    m = [solver.NumVar(0.0, float(max_mult), f"m_{i}") for i in range(n)]
    d = [solver.NumVar(0.0, solver.infinity(), f"d_{i}") for i in range(n)]

    solver.Add(solver.Sum(float(probs[i]) * m[i] for i in range(n)) == float(target_rtp))

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