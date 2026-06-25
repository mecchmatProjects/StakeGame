"""
Generate comprehensive Excel audit workbook with proper buy100 display.
Shows both normal and buy100 modes with bet=1, cost=1 (normal) or cost=99 (buy100).
"""

import json
import csv
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

root = Path("math-sdk/games/azteck_plinko_final")
pub = root / "artifacts/publish_files"

# Load index
idx = json.loads((pub / "index.json").read_text())
modes = idx["modes"]

# Separate normal and buy100
normal_modes = [m for m in modes if m["mode_type"] == "normal"]
buy100_modes = [m for m in modes if m["mode_type"] == "100balls"]

print(f"Loading {len(normal_modes)} normal + {len(buy100_modes)} buy100 modes...")

# Create workbook
wb = Workbook()
wb.remove(wb.active)

# ============================================================================
# SHEET 1: Summary by Difficulty
# ============================================================================
ws_summary = wb.create_sheet("Summary by Difficulty")

# Header
headers = ["Difficulty", "Type", "Rows", "Bet", "Cost", "RTP", "Max Win", "Avg Multiplier", "Min Mult", "Max Mult"]
for col, h in enumerate(headers, 1):
    cell = ws_summary.cell(1, col)
    cell.value = h
    cell.font = Font(bold=True, color="FFFFFF")
    cell.fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    cell.alignment = Alignment(horizontal="center", vertical="center")

row = 2
for difficulty in ["Low", "Medium", "High", "Expert"]:
    for mode_type, mode_list in [("Normal", normal_modes), ("Buy100", buy100_modes)]:
        filtered = [m for m in mode_list if m["difficulty"] == difficulty and m["rows"] == 8]  # 8-row representative
        if not filtered:
            continue
        m = filtered[0]
        
        # Load lookup to get multiplier stats
        lookup_path = pub / f"lookUpTable_{m['name']}_0.csv"
        multipliers = []
        if lookup_path.exists():
            for line in lookup_path.read_text().strip().split("\n")[1:]:
                parts = line.split(",")
                if len(parts) >= 3:
                    mult = int(parts[2]) / 100.0
                    multipliers.append(mult)
        
        min_mult = min(multipliers) if multipliers else 0
        max_mult = max(multipliers) if multipliers else 0
        avg_mult = sum(multipliers) / len(multipliers) if multipliers else 0
        
        # Calculate expected values
        bet = 1.0
        cost = m["cost"]
        rtp = m["rtp"]
        expected_payout = cost * rtp
        
        ws_summary.cell(row, 1).value = difficulty
        ws_summary.cell(row, 2).value = mode_type
        ws_summary.cell(row, 3).value = m["rows"]
        ws_summary.cell(row, 4).value = bet
        ws_summary.cell(row, 5).value = cost
        ws_summary.cell(row, 6).value = f"{rtp:.4f}" if isinstance(rtp, float) else rtp
        ws_summary.cell(row, 7).value = m.get("max_win", 100000)
        ws_summary.cell(row, 8).value = f"{expected_payout:.2f}"  # avg multiplier = expected_payout / bet
        ws_summary.cell(row, 9).value = f"{min_mult:.2f}x"
        ws_summary.cell(row, 10).value = f"{max_mult:.2f}x"
        
        # Format row
        for col in range(1, 11):
            cell = ws_summary.cell(row, col)
            cell.alignment = Alignment(horizontal="center")
            if row % 2 == 0:
                cell.fill = PatternFill(start_color="E7E6E6", end_color="E7E6E6", fill_type="solid")
        
        row += 1

# Auto-width columns
for col in range(1, 11):
    ws_summary.column_dimensions[get_column_letter(col)].width = 14

# ============================================================================
# SHEET 2: Full Mode Details (Normal + Buy100 side-by-side)
# ============================================================================
ws_details = wb.create_sheet("Mode Details")

# Build comparison rows
comparison_data = []
for difficulty in ["Low", "Medium", "High", "Expert"]:
    for rows in range(8, 17):  # 8-16 rows
        normal = next((m for m in normal_modes if m["difficulty"] == difficulty and m["rows"] == rows), None)
        buy100 = next((m for m in buy100_modes if m["difficulty"] == difficulty and m["rows"] == rows), None)
        
        if not normal:
            continue
        
        # Load both lookups
        normal_mults = []
        if (pub / f"lookUpTable_{normal['name']}_0.csv").exists():
            for line in (pub / f"lookUpTable_{normal['name']}_0.csv").read_text().strip().split("\n")[1:]:
                parts = line.split(",")
                if len(parts) >= 3:
                    normal_mults.append(int(parts[2]) / 100.0)
        
        buy100_mults = []
        if buy100 and (pub / f"lookUpTable_{buy100['name']}_0.csv").exists():
            for line in (pub / f"lookUpTable_{buy100['name']}_0.csv").read_text().strip().split("\n")[1:]:
                parts = line.split(",")
                if len(parts) >= 3:
                    buy100_mults.append(int(parts[2]) / 100.0)
        
        comparison_data.append({
            "difficulty": difficulty,
            "rows": rows,
            "normal_name": normal["name"],
            "normal_cost": normal["cost"],
            "normal_rtp": normal["rtp"],
            "normal_min": min(normal_mults) if normal_mults else 0,
            "normal_max": max(normal_mults) if normal_mults else 0,
            "normal_avg": sum(normal_mults) / len(normal_mults) if normal_mults else 0,
            "buy100_name": buy100["name"] if buy100 else "N/A",
            "buy100_cost": buy100["cost"] if buy100 else 0,
            "buy100_rtp": buy100["rtp"] if buy100 else 0,
            "buy100_min": min(buy100_mults) if buy100_mults else 0,
            "buy100_max": max(buy100_mults) if buy100_mults else 0,
            "buy100_avg": sum(buy100_mults) / len(buy100_mults) if buy100_mults else 0,
        })

# Write headers
headers_det = ["Difficulty", "Rows", "NORMAL Mode", "Bet", "Cost", "RTP", "Min Mult", "Avg Mult", "Max Mult",
               "BUY100 Mode", "Bet", "Cost", "Expected Payout", "RTP", "Min Mult", "Avg Mult", "Max Mult"]
for col, h in enumerate(headers_det, 1):
    cell = ws_details.cell(1, col)
    cell.value = h
    cell.font = Font(bold=True, color="FFFFFF", size=10)
    cell.fill = PatternFill(start_color="203864", end_color="203864", fill_type="solid")
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

# Write data
row = 2
for data in comparison_data:
    ws_details.cell(row, 1).value = data["difficulty"]
    ws_details.cell(row, 2).value = data["rows"]
    ws_details.cell(row, 3).value = data["normal_name"]
    ws_details.cell(row, 4).value = 1.0
    ws_details.cell(row, 5).value = data["normal_cost"]
    ws_details.cell(row, 6).value = f"{data['normal_rtp']:.4f}"
    ws_details.cell(row, 7).value = f"{data['normal_min']:.2f}x"
    ws_details.cell(row, 8).value = f"{data['normal_avg']:.2f}x"
    ws_details.cell(row, 9).value = f"{data['normal_max']:.2f}x"
    
    ws_details.cell(row, 10).value = data["buy100_name"]
    ws_details.cell(row, 11).value = 1.0
    ws_details.cell(row, 12).value = data["buy100_cost"]
    expected_payout = data["buy100_cost"] * data["buy100_rtp"] if data["buy100_rtp"] else 0
    ws_details.cell(row, 13).value = f"${expected_payout:.2f}"
    ws_details.cell(row, 14).value = f"{data['buy100_rtp']:.4f}"
    ws_details.cell(row, 15).value = f"{data['buy100_min']:.2f}x"
    ws_details.cell(row, 16).value = f"{data['buy100_avg']:.2f}x"
    ws_details.cell(row, 17).value = f"{data['buy100_max']:.2f}x"
    
    # Format
    for col in range(1, 18):
        cell = ws_details.cell(row, col)
        cell.alignment = Alignment(horizontal="center")
        if row % 2 == 0:
            cell.fill = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")
    
    row += 1

# Auto-width
for col in range(1, 18):
    ws_details.column_dimensions[get_column_letter(col)].width = 13

# ============================================================================
# SHEET 3: Buy100 Feature Specification
# ============================================================================
ws_buy100_spec = wb.create_sheet("Buy100 Spec")

spec_content = [
    ["BUY100 FEATURE SPECIFICATION", ""],
    ["", ""],
    ["Feature", "Buy100 Bonus"],
    ["Description", "100 independent balls dropped onto the game grid"],
    ["Cost Multiplier", "99x the player's base bet"],
    ["Example Bet", "$1.00 base bet"],
    ["Example Cost", "$99.00 (99x $1)"],
    ["Example Payout (Low)", "Min $49.50 × 99 cost = RTP 0.9605 → ~$95.09 expected"],
    ["Example Payout (Expert)", "Min $9.90, Max $49,500 × 99 cost = RTP 0.9605 → ~$95.09 expected"],
    ["", ""],
    ["Return-to-Player (RTP)", "96.05% (cost-adjusted)"],
    ["Max Win", "100,000x the base bet"],
    ["Tail Cap", "P(multiplier ≥ 5,000x) < 1% on all difficulties"],
    ["", ""],
    ["KEY INSIGHT", "Cost-Adjusted RTP"],
    ["Formula", "Expected_Payout = Base_Bet × RTP × Cost"],
    ["Example", "$1 bet × 0.9605 RTP × $99 cost = $95.0895 expected return"],
    ["", ""],
    ["Calculation for Excel", ""],
    ["Bet Amount (B)", "$1.00"],
    ["Cost Multiplier (C)", "99"],
    ["RTP (R)", "0.9605"],
    ["Total Cost (T)", "= B × C = $1 × 99 = $99"],
    ["Expected Payout (E)", "= T × R = $99 × 0.9605 = $95.09"],
    ["Average Multiplier", "= E / B = $95.09 / $1 = 95.09x"],
]

for row_idx, row_data in enumerate(spec_content, 1):
    for col_idx, value in enumerate(row_data, 1):
        cell = ws_buy100_spec.cell(row_idx, col_idx)
        cell.value = value
        if row_idx in [1, 15, 19]:  # Section headers
            cell.font = Font(bold=True, size=12, color="FFFFFF")
            cell.fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
        elif row_idx in [3, 10, 11]:  # Sub-headers
            cell.font = Font(bold=True, size=11)
            cell.fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
        cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)

ws_buy100_spec.column_dimensions["A"].width = 30
ws_buy100_spec.column_dimensions["B"].width = 50

# ============================================================================
# Save
# ============================================================================
output_path = pub / "AzteckPlinkoFull_with_Buy100.xlsx"
wb.save(str(output_path))
print(f"\n✓ Created {output_path}")
print(f"  - Sheet 'Summary by Difficulty': Quick overview of all modes")
print(f"  - Sheet 'Mode Details': Side-by-side normal vs buy100 comparison")
print(f"  - Sheet 'Buy100 Spec': Feature specification with calculations")
