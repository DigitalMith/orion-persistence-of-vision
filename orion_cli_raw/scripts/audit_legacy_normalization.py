# orion_cli/scripts/audit_legacy_normalization.py

import json
from pathlib import Path
import html

BEGIN_SENTINEL = "<|BEGIN-VISIBLE-CHAT|>"

ROOT = Path(__file__).resolve().parents[2]  # text-generation-webui root
RAW_DIR = ROOT / "orion_cli" / "data" / "legacy_logs"
NORM_PATH = ROOT / "orion_cli" / "data" / "normalized" / "normalized_legacy.jsonl"

def count_raw_pairs(path: Path) -> int:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    visible = data.get("visible") or data.get("internal") or []
    count = 0

    for pair in visible:
        if not isinstance(pair, list) or len(pair) != 2:
            continue

        user, assistant = pair

        if not user:
            continue
        if isinstance(user, str) and user.strip() == BEGIN_SENTINEL:
            # Skip the dummy first row
            continue

        count += 1

    return count

def count_normalized(path: Path):
    counts = {}
    if not path.exists():
        print(f"[WARN] Normalized file not found: {path}")
        return counts

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            src = rec.get("source_file", "UNKNOWN")
            counts[src] = counts.get(src, 0) + 1
    return counts

def main():
    raw_counts = {}
    for p in sorted(RAW_DIR.glob("*.json")):
        raw_counts[p.name] = count_raw_pairs(p)

    norm_counts = count_normalized(NORM_PATH)

    print(f"[INFO] Auditing {len(raw_counts)} raw log files against {NORM_PATH.name}")
    print()

    total_raw = 0
    total_norm = 0

    for name, expected in raw_counts.items():
        got = norm_counts.get(name, 0)
        total_raw += expected
        total_norm += got
        status = "OK" if expected == got else "MISMATCH"
        print(f"{name:30} expected={expected:3d}  normalized={got:3d}  [{status}]")

    print()
    print(f"TOTAL raw pairs      = {total_raw}")
    print(f"TOTAL normalized rows= {total_norm}")

    if total_raw != total_norm:
        print("[WARN] Totals differ. Check files marked MISMATCH above.")
    else:
        print("[OK] All raw pairs accounted for in normalized file.")

if __name__ == "__main__":
    main()
