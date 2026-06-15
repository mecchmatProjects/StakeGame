from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate paste-ready mode stub lines for Azteck Plinko")
    parser.add_argument(
        "--root",
        default="math-sdk/games/azteck_plinko_final",
        help="Package root path",
    )
    parser.add_argument(
        "--output",
        default="math-sdk/games/azteck_plinko_final/inputs/azteck_plinko_pasted_stubs_all_modes.txt",
        help="Output text file path",
    )
    parser.add_argument(
        "--default-aggregation-rule",
        default="sum_100_independent",
        help="Default aggregation rule for 100balls stubs",
    )
    return parser.parse_args()


def mode_to_fields(mode_name: str) -> tuple[str, str, str]:
    parts = mode_name.split("_")
    if len(parts) < 3:
        return ("", "", "")
    prefix = parts[0].lower()
    difficulty = parts[1].capitalize()
    rows = parts[2]
    mode_type = "100balls" if prefix == "buy100" else "normal"
    return (mode_type, difficulty, rows)


def main() -> int:
    args = parse_args()
    root = Path(args.root)
    index_path = root / "artifacts" / "publish_files" / "index.json"

    if not index_path.exists():
        raise FileNotFoundError(index_path)

    index = json.loads(index_path.read_text(encoding="utf-8"))
    modes = index.get("modes", [])

    lines: list[str] = [
        "# Auto-generated paste stubs for all index modes",
        "# Fill multipliers=[...] and probs=[...] per mode, then parse/import/generate.",
    ]

    for mode in modes:
        if not isinstance(mode, dict):
            continue
        mode_name = mode.get("name")
        if not isinstance(mode_name, str):
            continue

        mode_type, difficulty, rows = mode_to_fields(mode_name)
        if not mode_type:
            continue

        max_win = mode.get("max_win")
        max_note = f"known_max={max_win}" if max_win is not None else "known_max=UNKNOWN"
        source = "screenshot_batch"

        if mode_type == "normal":
            line = (
                f"mode={mode_type}; difficulty={difficulty}; rows={rows}; "
                f"multipliers=[0,TODO_MAX]; probs=[TODO]; source={source}; notes={max_note}"
            )
        else:
            line = (
                f"mode={mode_type}; difficulty={difficulty}; rows={rows}; "
                f"multipliers=[0,TODO_MAX]; probs=[TODO]; aggregation_rule={args.default_aggregation_rule}; "
                f"source={source}; notes={max_note}"
            )

        lines.append(line)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Generated stubs: {out}")
    print(f"Mode lines: {max(0, len(lines) - 2)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
