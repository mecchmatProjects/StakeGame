"""Check if buy100 modes have different RTPs than expected."""
import json
from pathlib import Path

root = Path("math-sdk/games/azteck_plinko_final")
pub = root / "artifacts/publish_files"

idx = json.loads((pub / "index.json").read_text())

print("=" * 80)
print("COMPARING NORMAL vs BUY100 MODE RTPs")
print("=" * 80)
print()

for difficulty in ["Low", "Medium", "High", "Expert"]:
    for rows in [8, 10, 12, 14, 16]:
        normal = next((m for m in idx["modes"] if m["mode_type"] == "normal" and m["difficulty"] == difficulty and m["rows"] == rows), None)
        buy100 = next((m for m in idx["modes"] if m["mode_type"] == "100balls" and m["difficulty"] == difficulty and m["rows"] == rows), None)
        
        if not normal or not buy100:
            continue
        
        print(f"{difficulty:8} {rows:2} rows:")
        print(f"  normal_RTP = {normal['rtp']:.6f} (expected payout for $1 bet: ${normal['cost'] * normal['rtp']:.4f})")
        print(f"  buy100_RTP = {buy100['rtp']:.6f} (expected payout for $1 bet: ${buy100['cost'] * buy100['rtp']:.4f})")
        
        if abs(normal['rtp'] - buy100['rtp']) > 0.0001:
            print(f"  ⚠️  RTPs ARE DIFFERENT!")
        else:
            print(f"  ✓ RTPs match")
        print()
