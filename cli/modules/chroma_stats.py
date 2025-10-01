# modules/chroma_stats.py

import chromadb
from collections import Counter

def print_stats(group_by="topic"):
    client = chromadb.Client()
    collection = client.get_or_create_collection("orion_episodic_sent_ltm")

    try:
        results = collection.get()
        metadatas = results.get("metadatas", [])
        total = len(metadatas)

        counter = Counter()
        for meta in metadatas:
            key = str(meta.get(group_by, "unknown")).strip()
            counter[key] += 1

        print(f"\n📊 Chroma Memory Stats (Group by: '{group_by}')")
        print(f"Total entries: {total}\n")

        for value, count in counter.most_common():
            print(f"  • {value}: {count}")

    except Exception as e:
        print(f"❌ Stats failed: {e}")
