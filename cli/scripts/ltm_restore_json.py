import os
import uuid
import json
from chromadb import PersistentClient

# === CONFIG ===
CHROMA_DIR = "user_data/chroma_db"
COLLECTION_NAME = "orion_ltm"
LOG_DIR = "cli/data/logs"

def load_json_file(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Failed to load JSON from {path}: {e}")
        return None

def main():
    client = PersistentClient(path=CHROMA_DIR)
    collection = client.get_or_create_collection(name=COLLECTION_NAME)

    added_count = 0

    # Auto-scan log directory for .json files
    for file in os.listdir(LOG_DIR):
        if not file.endswith(".json"):
            continue

        full_path = os.path.join(LOG_DIR, file)
        data = load_json_file(full_path)

        if not data:
            continue

        if "internal" not in data:
            print(f"⚠️ Missing 'internal' block in: {file}")
            continue

        for idx, pair in enumerate(data["internal"]):
            if not isinstance(pair, list) or len(pair) != 2:
                print(f"⚠️ Skipping malformed entry #{idx} in: {file}")
                continue

            user_input, assistant_reply = pair
            combined_text = f"User: {user_input.strip()}\nOrion: {assistant_reply.strip()}"
            doc_id = str(uuid.uuid4())

            metadata = {
                "source_file": file,
                "index": idx,
                "kind": "ltm",
                "timestamp": data.get("metadata", {}).get(f"assistant_{idx}", {}).get("timestamp"),
            }

            try:
                collection.add(
                    ids=[doc_id],
                    documents=[combined_text],
                    metadatas=[metadata],
                )
                added_count += 1
                print(f"✅ Added entry from {file} #{idx}")
            except Exception as e:
                print(f"❌ Failed to add entry #{idx} in {file}: {e}")

    print(f"\n✅ Restored {added_count} complete entries to: {COLLECTION_NAME}")

if __name__ == "__main__":
    main()
