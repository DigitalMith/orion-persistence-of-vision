import os
import json
from chromadb import PersistentClient

CHROMA_DIR = "user_data/chroma_db"
COLLECTION_NAME = "orion_ltm"

def dump_ltm_entries(collection_name, persist_dir=CHROMA_DIR):
    client = PersistentClient(path=persist_dir)
    collection = client.get_or_create_collection(name=collection_name)
    results = collection.get()

    ltm_entries = []
    for idx, doc_id in enumerate(results["ids"]):
        metadata = results["metadatas"][idx]
        # if metadata.get("kind") != "ltm":
            # continue  # Skip non-ltm entries

        entry = {
            "id": doc_id,
            "text": results["documents"][idx],
            "metadata": metadata
        }
        with open("ltm_dump.txt", "a", encoding="utf-8") as f:
            f.write(f"\n=== {doc_id} ===\n")
            f.write(f"Text:\n{entry['text']}\n")
            f.write("Metadata:\n" + json.dumps(metadata, indent=2) + "\n")
        ltm_entries.append(entry)

    print(f"\nTotal LTM entries: {len(ltm_entries)}")
    return ltm_entries

if __name__ == "__main__":
    dump_ltm_entries(COLLECTION_NAME)
