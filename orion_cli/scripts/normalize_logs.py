# orion_cli/scripts/normalize_logs.py

import json
from pathlib import Path

from orion_cli.utils.normalize_annotate_chat import normalize_entries


def main():
    base_dir = Path(__file__).resolve().parents[2]  # project root
    ingest_dir = base_dir / "orion_cli" / "data" / "ingest"
    out_dir = base_dir / "orion_cli" / "data" / "normalized"
    out_dir.mkdir(parents=True, exist_ok=True)

    output_file = out_dir / "normalized_logs.jsonl"

    files = sorted(p for p in ingest_dir.glob("*.json") if p.name not in {"mock_compatible.json", "persona.yaml"})
    print(f"[normalize] Found {len(files)} ingest logs in {ingest_dir}")

    total_pairs = 0

    with output_file.open("w", encoding="utf-8") as out_f:
        for path in files:
            try:
                entries = normalize_entries(path)
                print(f"[normalize] {path.name}: {len(entries)} pairs")
                total_pairs += len(entries)
                for entry in entries:
                    json.dump(entry, out_f, ensure_ascii=False)
                    out_f.write("\n")
            except Exception as e:
                print(f"[normalize] ⚠️ Skipping {path.name}: {e}")

    print(f"[normalize] ✅ Done. Wrote {total_pairs} pairs to: {output_file}")


if __name__ == "__main__":
    main()
