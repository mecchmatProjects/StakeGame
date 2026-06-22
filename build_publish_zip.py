from __future__ import annotations

import json
import zipfile
from pathlib import Path

pub = Path("math-sdk/games/azteck_plinko_final/artifacts/publish_files")
out = Path("math-sdk/games/azteck_plinko_final_publish.zip")

idx = json.loads((pub / "index.json").read_text("utf-8"))
needed: set[str] = {"index.json", "force.json"}

for m in idx.get("modes", []):
    if not isinstance(m, dict):
        continue
    name = m.get("name")
    weights = m.get("weights")
    events = m.get("events")
    if isinstance(weights, str):
        needed.add(weights)
    if isinstance(events, str):
        needed.add(events)
    if isinstance(name, str) and name:
        needed.add(f"force_record_{name}.json")

missing = [n for n in sorted(needed) if not (pub / n).exists()]
if missing:
    print("missing_files", len(missing))
    for x in missing[:20]:
        print(" ", x)
    raise SystemExit(1)

with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_STORED) as z:
    for n in sorted(needed):
        z.write(pub / n, arcname=n)

with zipfile.ZipFile(out, "r") as z:
    names = set(z.namelist())

print("created", out)
print("entries", len(names), "has_root_index", "index.json" in names)
print("sample", list(sorted(names))[:10])
