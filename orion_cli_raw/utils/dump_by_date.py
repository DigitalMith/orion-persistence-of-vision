import time
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
from datetime import datetime
from orion_cli.orion_ltm_integration import initialize_chromadb_for_ltm

# Set your target date (e.g., 2025-11-08)
TARGET_DATE = "2025-11-08"


def dump_episodic_by_date(target_date):
    _, episodic = initialize_chromadb_for_ltm()
    target_ts = time.mktime(datetime.strptime(target_date, "%Y-%m-%d").timetuple())
    next_day_ts = target_ts + 86400

    results = episodic.query(
        query_texts=[" "],
        n_results=100,
        where={
            "$and": [
                {"timestamp": {"$gt": target_ts}},
                {"timestamp": {"$lt": next_day_ts}},
            ]
        },
        include=["documents", "metadatas"],
    )

    docs = results.get("documents", [])
    metas = results.get("metadatas", [])
    if not docs:
        print("⚠️ No episodic memory found for that date.")
        return

    for doc, meta in zip(docs, metas):
        print("\n📜 Memory:")
        print(doc)

        print("🧠 Metadata:")
        if isinstance(meta, dict):
            for k, v in meta.items():
                print(f"  {k}: {v}")
        elif isinstance(meta, list):
            for item in meta:
                k = item.get("key")
                v = item.get("value")
                if k:
                    print(f"  {k}: {v}")
        else:
            print("  ⚠️ Unknown metadata format:", meta)


if __name__ == "__main__":
    print("[orion_cli] 🧠 Loading embedding model: intfloat/e5-large-v2")
    dump_episodic_by_date(TARGET_DATE)
