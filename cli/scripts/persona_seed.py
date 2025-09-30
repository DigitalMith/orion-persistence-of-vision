import argparse
import os
import sys
import yaml
import json
import uuid
from datetime import datetime
import chromadb
from chromadb.utils import embedding_functions
from chromadb.config import Settings
from chromadb import PersistentClient

# Logging setup
class SimpleLogger:
    @staticmethod
    def info(msg):
        print(f"[INFO] {msg}")

    @staticmethod
    def warning(msg):
        print(f"[WARNING] {msg}")

    @staticmethod
    def error(msg):
        print(f"[ERROR] {msg}")

logger = SimpleLogger()

COLLECTION_NAME = "orion_persona"
CHROMA_PATH = "user_data/chroma"

# Flatten metadata values
def flatten_metadata(metadata):
    flat_meta = {}
    for k, v in metadata.items():
        if isinstance(v, list):
            flat_meta[k] = ", ".join(str(item) for item in v)
        elif isinstance(v, (str, int, float, bool)):
            flat_meta[k] = v
        else:
            flat_meta[k] = str(v)
    return flat_meta

def clean_metadata(meta):
    return {k: v for k, v in meta.items() if v is not None and isinstance(v, (str, int, float, bool))}

def seed_persona(yaml_path):
    logger.info(f"[persona_seed] Seeding '{COLLECTION_NAME}' from {yaml_path}")

    path = os.path.abspath(yaml_path)
    if not os.path.exists(path):
        raise FileNotFoundError(f"YAML file not found: {yaml_path}")

    with open(path, "r", encoding="utf-8") as f:
        raw = list(yaml.safe_load_all(f))

    # Support simple YAML personas
    if len(raw) == 1 and isinstance(raw[0], dict) and "text" not in raw[0]:
        text_blob = "\n".join(f"{k}: {v}" for k, v in raw[0].items())
        raw = [{
            "persona": [{
                "id": "orion_persona_v3",
                "text": text_blob,
                "tags": "persona_seed, orion_core, fallback",
                "version": "v3.0"
            }]
        }]

    client = PersistentClient(path=CHROMA_PATH)
    collection = client.get_or_create_collection(COLLECTION_NAME)

    # 🔥 Wipe existing data
    ids = [doc_id for doc_id in collection.get(include=[])['ids']]
    if ids:
        collection.delete(ids=ids)

    default_priority = {}
    entries = []

    for block in raw:
        if not block:
            continue
        if "collection" in block:
            continue
        if "default_priority" in block:
            default_priority = block["default_priority"]
            continue

        for kind, docs in block.items():
            for doc in docs:
                doc_id = doc.get("id") or str(uuid.uuid4())
                text = doc.get("text", "").strip()
                if not text:
                    continue

                meta = {
                    **doc,
                    "kind": kind,
                    "text": None,  # exclude full text from metadata
                }

                if "priority" not in meta and kind in default_priority:
                    meta["priority"] = default_priority[kind]

                meta = flatten_metadata(meta)
                entries.append((doc_id, text, meta))

    added = 0
    for doc_id, text, meta in entries:
        try:
            cleaned_meta = clean_metadata(meta)
            collection.add(
                ids=[doc_id],
                documents=[text],
                metadatas=[cleaned_meta]
            )
            added += 1
            logger.info(f"✅ Added: {doc_id}")
        except Exception as e:
            logger.warning(f"❌ Failed to add {doc_id}: {e}")

    logger.info(f"\n✅ Seed complete — Added {added} entries to: {COLLECTION_NAME}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--yaml", required=True, help="Path to persona.yaml file")
    args = parser.parse_args()
    seed_persona(args.yaml)

if __name__ == "__main__":
    main()
