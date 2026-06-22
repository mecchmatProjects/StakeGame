"""Full Stake Engine compilation readiness audit for azteck_plinko_final.zip"""
from __future__ import annotations
import csv, hashlib, io, json, os, re, zipfile, zstandard as zstd


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def main() -> None:
    zp = "math-sdk/games/azteck_plinko_final.zip"
    issues: list = []
    results: dict = {}

    with zipfile.ZipFile(zp, "r") as z:
        names = z.namelist()
        pub_prefix = "azteck_plinko_final/artifacts/publish_files/"
        cfg_prefix = "azteck_plinko_final/artifacts/configs/"

        # 1. index.json
        idx = json.loads(z.read(pub_prefix + "index.json"))
        mode_count = len(idx.get("modes", []))
        results["modes_in_index"] = mode_count
        if mode_count != 72:
            issues.append(("index_mode_count", mode_count))

        # 2. config.json structure
        cfg = json.loads(z.read(cfg_prefix + "config.json"))
        bsc = cfg.get("bookShelfConfig", [])
        results["bookShelfConfig_entries"] = len(bsc)
        if len(bsc) != 72:
            issues.append(("bookShelfConfig_count", len(bsc)))
        for entry in bsc:
            for req in ("name", "tables", "cost", "rtp", "std", "bookLength", "booksFile", "forceFile"):
                if req not in entry:
                    issues.append(("bookShelfConfig_missing_key", entry.get("name"), req))

        # 3. force.json present
        if (pub_prefix + "force.json") not in names:
            issues.append(("missing_force_json",))

        # 4. Build filename maps
        pub_map = {os.path.basename(n): n for n in names if n.startswith(pub_prefix) and not n.endswith("/")}
        cfg_map = {os.path.basename(n): n for n in names if n.startswith(cfg_prefix) and not n.endswith("/")}

        lut_pass = 0
        bk_pass = 0

        for entry in bsc:
            name = entry["name"]

            # lookup CSV: present, sha, integer-only
            lut_file = entry["tables"][0]["file"]
            if lut_file not in pub_map:
                issues.append(("missing_lookup", name))
            else:
                raw_bytes = z.read(pub_map[lut_file])
                if sha256_bytes(raw_bytes) != entry["tables"][0]["sha256"]:
                    issues.append(("sha_mismatch_lookup", name))
                raw_str = raw_bytes.decode("utf-8")
                ok = True
                for ln, row in enumerate(csv.reader(io.StringIO(raw_str)), 1):
                    if len(row) != 3:
                        issues.append(("lookup_col_count", name, ln)); ok = False; break
                    try:
                        int(row[0]); int(row[1]); int(row[2])
                    except ValueError:
                        issues.append(("lookup_non_int", name, ln, row)); ok = False; break
                if ok:
                    lut_pass += 1

            # books: present, sha, zstd magic, valid JSONL, no float.0
            bk_file = entry["booksFile"]["file"]
            if bk_file not in pub_map:
                issues.append(("missing_books", name))
            else:
                raw = z.read(pub_map[bk_file])
                if sha256_bytes(raw) != entry["booksFile"]["sha256"]:
                    issues.append(("sha_mismatch_books", name))
                if not raw.startswith(b"\x28\xb5\x2f\xfd"):
                    issues.append(("books_not_zstd", name))
                else:
                    try:
                        data = zstd.ZstdDecompressor().decompress(raw).decode("utf-8")
                    except Exception as ex:
                        issues.append(("books_decompress_err", name, str(ex)))
                        continue
                    ok = True
                    for ln_no, line in enumerate(data.strip().split("\n"), 1):
                        try:
                            json.loads(line)
                        except Exception as ex:
                            issues.append(("books_json_err", name, f"line{ln_no}", str(ex))); ok = False; break
                        if re.search(r":\d+\.0[,}\]]", line):
                            issues.append(("books_float_dot_zero", name, f"line{ln_no}")); ok = False; break
                    if ok:
                        bk_pass += 1

            # force_record present
            fr_file = entry["forceFile"]["file"]
            if fr_file not in pub_map:
                issues.append(("missing_force_record", name, fr_file))

        results["lookup_csvs_pass"] = f"{lut_pass}/72"
        results["books_files_pass"] = f"{bk_pass}/72"
        results["total_issues"] = len(issues)

    print(json.dumps(results, indent=2))
    if issues:
        print("\nISSUES:")
        for i in issues[:40]:
            print(" ", i)
    else:
        print("\nALL CHECKS PASSED - zip is ready for Stake Engine upload")


if __name__ == "__main__":
    main()
