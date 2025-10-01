# modules/summary.py

import chromadb
from collections import Counter

COLLECTION_NAME = "orion_episodic_sent_ltm"
client = chromadb.Client()
collection = client.get_or_create_collection(COLLECTION_NAME)

def summarize_memory():
    try:
        print("📡 Fetching memory entries from ChromaDB...")
        all_docs = collection.get()
        docs = all_docs.get("documents", [])
        metadatas = all_docs.get("metadatas", [])

        print(f"📦 Retrieved {len(docs)} entries.")

        # Basic tag/topic extraction
        topic_counter = Counter()
        for meta in metadatas:
            tag = meta.get("topic") or meta.get("source") or "misc"
            topic_counter[tag] += 1

        print("\n🧾 Top Memory Topics:")
        for topic, count in topic_counter.most_common():
            print(f"• {topic}: {count} entries")

    except Exception as e:
        print(f"❌ Summary failed: {e}")
