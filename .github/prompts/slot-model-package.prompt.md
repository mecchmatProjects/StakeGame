---
mode: ask
model: GPT-5.4
description: Create a full slot-game artifact package from a rules PDF using the repo playbook.
---

Use the repo workflow in [SLOT_MODELING_RAG_PLAYBOOK.md](../../SLOT_MODELING_RAG_PLAYBOOK.md).

Task:
Create the full artifact package for a new slot game from a rules PDF with the least prompt cost and the highest consistency across artifacts.

Inputs to collect or confirm:
- Game name
- PDF path
- Optional workbook path
- Target RTP list
- Closest existing template game, if any
- Any known assumptions or missing rule details

Required workflow:
1. Run `extract_sources.py` to populate `output/catalog/`:
   ```powershell
   python extract_sources.py --pdf "<PDF path>" [--workbook "<XLSX path>"] --game-name <game>
   ```
   This produces `<game>_pdf_text.txt` and (if workbook supplied) `<game>_workbook_catalog.txt`.
2. Create a compact `output/catalog/<game>_rag_packet.md` as the reusable source of truth.
3. Generate the deterministic artifacts first:
   - `<GameName>_model.tex`
   - `output/python/<game>_verify_rtp.py`
   - `output/python/<game>_pyomo_model.py` — include both `BASELINE_STRIPS` (design anchor) and `RTP85_STRIPS` (optimized)
4a. Build the base workbook:
   ```powershell
   python output/python/build_excel.py
   ```
   Script must set `ACTIVE_STRIPS = RTP85_STRIPS` (never `BASELINE_STRIPS`).
   Produces sheets: Reels, RTP\_Analysis, StripCounts, Paytable, ScaledPaytable, Summary.
4b. Add simulation and volatility sheets:
   ```powershell
   python output/python/update_<game>_workbook.py
   ```
   Adds: Simulation Test, Confidence & Volatility. Always run **after** step 4a.
5. Generate the search and validation scripts:
   - `output/python/search_<game>_tables.py` — exact coordinate descent or MILP heuristic (label which)
   - `testGame<GameName>.py` — MC simulation; `EXACT` dict must match `<game>_verify_rtp.py` to < 1e-4
   - `_parity_check.py` — cross-artifact consistency (verify\_rtp + MC `EXACT` dict + Excel cached values)
6. Run a final consistency pass across PDF, workbook, TeX, and Python files and fix any drift.

Output requirements:
- Keep one consistent naming scheme across all artifacts.
- Reuse the closest workbook structure where efficient.
- Mark any approximation or heuristic step explicitly.
- Distinguish exact deterministic models from Monte Carlo validation.
- If exact inverse optimization is not supported, still provide `search_<game>_tables.py` and clearly label it heuristic.
- `<game>_pyomo_model.py` must export both `BASELINE_STRIPS` and `RTP85_STRIPS`; `build_excel.py` selects via `ACTIVE_STRIPS = RTP85_STRIPS`.

Final response requirements:
- State what files were created or updated.
- State what assumptions were required.
- State which strip set was used to build the workbook (BASELINE\_STRIPS or RTP85\_STRIPS).
- State which strip search method was used (exact coordinate descent / heuristic MILP) and why.
- State which artifact is the authoritative source of truth for RTP.
- Report whether deterministic artifacts reconcile exactly and whether Monte Carlo statistically supports them.
- Report `_parity_check.py` result (all checks OK or list failures).
