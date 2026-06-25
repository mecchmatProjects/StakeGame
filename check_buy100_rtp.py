"""Check if stored RTP for buy100 is actually meant to be per-ball or per-round."""
import json
from pathlib import Path

root = Path("math-sdk/games/azteck_plinko_final")
pub = root / "artifacts/publish_files"

idx = json.loads((pub / "index.json").read_text())

# Get all unique RTP values
rtps = sorted(set(m["rtp"] for m in idx["modes"]))
print(f"Unique RTP values in index: {rtps}\n")

# Check a few modes
print("Sample modes:")
for m in idx["modes"][:36]:
    if m["mode_type"] == "normal" and m["difficulty"] in ["Low", "Expert"]:
        print(f"{m['name']:20} type={'normal':10} rtp={m['rtp']} cost={m['cost']}")

print()
for m in idx["modes"][36:72]:
    if m["mode_type"] == "100balls" and m["difficulty"] in ["Low", "Expert"]:
        print(f"{m['name']:20} type={'100balls':10} rtp={m['rtp']} cost={m['cost']}")

# The key question: is buy100 RTP supposed to be interpreted differently?
print("\n=== HYPOTHESIS TEST ===")
print("If buy100 multipliers are 99x the normal ones:")
print("  Expected RTP = (100 * normal_EV * 99) / 99 = 100 * normal_EV")
print("  But stored RTP = 0.9605 for both normal and buy100")
print("  So either:")
print("    A) Buy100 multipliers are NOT 99x (contradicts paytables)")
print("    B) RTP for buy100 is per-ball, not per-round")
print("    C) There's a bug in the artifacts")
