from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import sys
import zipfile

import zstandard as zstd


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def main() -> int:
    zp = "Azteck_plinko_set_publish.zip"
    issues: list[tuple] = []

    with zipfile.ZipFile(zp, "r") as z:
        names = set(z.namelist())

        # Required top-level files
        for req in ["index.json", "config.json", "force.json"]:
            if req not in names:
                issues.append(("missing_required_file", req))

        idx = json.loads(z.read("index.json"))
        cfg = json.loads(z.read("config.json"))

        modes = idx.get("modes", [])
        bsc = cfg.get("bookShelfConfig", [])

        if len(modes) == 0:
            issues.append(("empty_modes",))
        if len(bsc) != len(modes):
            issues.append(("bookShelfConfig_count_mismatch", len(bsc), len(modes)))

        # Index checks
        for m in modes:
            for k in ["name", "mode_type", "difficulty", "rows", "cost", "rtp", "weights", "events"]:
                if k not in m:
                    issues.append(("index_missing_key", k))
            if not str(m.get("name", "")).strip():
                issues.append(("index_empty_mode_name", m))
            if m.get("weights") not in names:
                issues.append(("index_missing_lookup_file", m.get("name"), m.get("weights")))
            if m.get("events") not in names:
                issues.append(("index_missing_books_file", m.get("name"), m.get("events")))

        # Config checks + file integrity checks
        for e in bsc:
            for req in ["name", "tables", "cost", "rtp", "std", "bookLength", "booksFile", "forceFile"]:
                if req not in e:
                    issues.append(("config_missing_key", e.get("name"), req))
            nm = str(e.get("name", "")).strip()
            if not nm:
                issues.append(("config_empty_mode_name",))

            # lookup file checks
            if e.get("tables"):
                t0 = e["tables"][0]
                lut = t0.get("file")
                if lut not in names:
                    issues.append(("missing_lookup", nm, lut))
                else:
                    raw = z.read(lut)
                    if t0.get("sha256") != sha256_bytes(raw):
                        issues.append(("sha_mismatch_lookup", nm))
                    rows = list(csv.reader(io.StringIO(raw.decode("utf-8"))))
                    if not rows:
                        issues.append(("lookup_empty", nm))
                    for ln, r in enumerate(rows, 1):
                        if len(r) != 3:
                            issues.append(("lookup_col_count", nm, ln, len(r)))
                            break
                        try:
                            int(r[0]); int(r[1]); int(r[2])
                        except Exception:
                            issues.append(("lookup_non_int", nm, ln, r))
                            break

            # books checks
            bf = e.get("booksFile", {})
            bk = bf.get("file")
            if bk not in names:
                issues.append(("missing_books", nm, bk))
            else:
                raw = z.read(bk)
                if bf.get("sha256") != sha256_bytes(raw):
                    issues.append(("sha_mismatch_books", nm))
                if not raw.startswith(b"\x28\xb5\x2f\xfd"):
                    issues.append(("books_not_zstd", nm))
                else:
                    txt = zstd.ZstdDecompressor().decompress(raw).decode("utf-8")
                    for ln, line in enumerate([x for x in txt.splitlines() if x.strip()], 1):
                        try:
                            json.loads(line)
                        except Exception as ex:
                            issues.append(("books_json_err", nm, ln, str(ex)))
                            break
                        if re.search(r":\d+\.0[,}\]]", line):
                            issues.append(("books_float_dot_zero", nm, ln))
                            break

            # force checks
            ff = e.get("forceFile", {})
            fr = ff.get("file")
            if fr not in names:
                issues.append(("missing_force_record", nm, fr))
            else:
                raw = z.read(fr)
                if ff.get("sha256") != sha256_bytes(raw):
                    issues.append(("sha_mismatch_force", nm))

        print(json.dumps({
            "zip": zp,
            "modes": len(modes),
            "bookShelfConfig_entries": len(bsc),
            "issues": len(issues),
        }, indent=2))

        if issues:
            print("\nISSUES:")
            for i in issues[:50]:
                print(i)
            return 1

    print("\nALL CHECKS PASSED - Stake Engine format compliant")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
