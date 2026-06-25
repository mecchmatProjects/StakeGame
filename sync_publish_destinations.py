"""Propagate the freshly rebuilt publish_files (single source of truth) into the
upload publish folder and rebuild the flat archives, then verify integrity."""
from __future__ import annotations

import hashlib
import json
import shutil
import zipfile
from pathlib import Path

ROOT = Path("math-sdk/games/azteck_plinko_final")
SRC = ROOT / "artifacts" / "publish_files"
NESTED_FOLDER = ROOT / "azteck_plinko_final_publish"

TARGET_ZIPS = [
    ROOT / "azteck_plinko_final_publish.zip",
    ROOT / "artifacts.zip",
    Path("math-sdk/games/azteck_plinko_final_publish.zip"),
]


def main() -> None:
    files = sorted(p for p in SRC.iterdir() if p.is_file())

    # 1) Mirror source -> nested upload folder
    if NESTED_FOLDER.exists():
        shutil.rmtree(NESTED_FOLDER)
    NESTED_FOLDER.mkdir(parents=True)
    for f in files:
        shutil.copy2(f, NESTED_FOLDER / f.name)

    # 2) Rebuild flat zips from source
    for t in TARGET_ZIPS:
        with zipfile.ZipFile(t, "w", zipfile.ZIP_DEFLATED) as z:
            for f in files:
                z.write(f, f.name)

    # 3) Verify
    for t in TARGET_ZIPS:
        with zipfile.ZipFile(t) as z:
            names = set(z.namelist())
            base_std = json.loads(z.read("index.json")).get("base_std")
            cfg = json.loads(z.read("config.json"))
            mis = miss = 0
            for e in cfg["bookShelfConfig"]:
                for ref in [e["booksFile"], e["forceFile"], *e["tables"]]:
                    fn = ref["file"]
                    if fn not in names:
                        miss += 1
                        continue
                    if hashlib.sha256(z.read(fn)).hexdigest() != ref["sha256"]:
                        mis += 1
            print(
                f"{t.name:42} entries={len(names)} base_std={base_std} "
                f"sha_mismatch={mis} missing={miss}"
            )

    folder_std = json.loads(
        (NESTED_FOLDER / "index.json").read_text(encoding="utf-8")
    ).get("base_std")
    print(
        f"nested_folder base_std={folder_std} "
        f"files={len(list(NESTED_FOLDER.iterdir()))}"
    )


if __name__ == "__main__":
    main()
