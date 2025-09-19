# cli/scripts/ltm_restore_jsonl.py

import os
import json
from chromadb import PersistentClient
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from cli.lib.chroma_utils import reset_collection

# === Configuration ===
CHROMA_DIR = "user_data/chroma_db"
COLLECTION_NAME = "orion_ltm_v4"  # ← bump version for safety
INPUT_FILE = "cli/data/merged_ltm_v3(Chroma_Ready).jsonl"

# === Embedding Function Setup ===
def get_embed_fn():
    model_name = os.environ.get("ORION_EMBED_MODEL", "all-MiniLM-L6-v2")
    print(f"[DEBUG] Using embedding model: {model_name}")
    return SentenceTransformerEmbeddingFunction(model_name=model_name)

EMBED_FN = get_embed_fn()

# === Helpers ===
def sanitize_metadata(metadata):
    clean_meta = {}
    for k, v in metadata.items():
        if isinstance(v, list):
            clean_meta[k] = ", ".join(map(str, v))
        elif isinstance(v, (str, int, float, bool)) or v is None:
            clean_meta[k] = v
        else:
            clean_meta[k] = str(v)
    return clean_meta

def restore_ltm_from_jsonl(input_path, collection_name):
    if not os.path.exists(input_path):
        print(f"❌ File not found: {input_path}")
        return

    client = PersistentClient(path=CHROMA_DIR)
    collection = client.get_or_create_collection(
        name=collection_name,
        embedding_function=EMBED_FN
    )

    reset_collection(collection_name, EMBED_FN)
    print(f"🧹 Reset collection: {collection_name}")

    added = 0

    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                entry = json.loads(line)
                doc_id = entry.get("id")
                document = entry.get("text", "")
                metadata = sanitize_metadata(entry.get("metadata", {}))

                collection.add(
                    ids=[doc_id],
                    documents=[document],
                    metadatas=[metadata]
                )
                print(f"✅ Added: {doc_id}")
                added += 1
            except Exception as e:
                print(f"⚠️ Failed to ingest entry: {e}")

    print(f"\n✅ Restored {added} entries to: {collection_name}")

# === Main Entry ===
if __name__ == "__main__":
    restore_ltm_from_jsonl(INPUT_FILE, COLLECTION_NAME)
