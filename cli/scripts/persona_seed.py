# cli/scripts/persona_seed.py

import os
import sys
import yaml
import uuid
import argparse
from chromadb import PersistentClient
from modules.logging_colors import logger

DEFAULT_YAML = "cli/data/persona.yaml"
COLLECTION_NAME = "orion_persona"
CHROMA_PATH = "user_data/chroma_db"  # Use TGWUI default

def clean_metadata(meta):
    return {
        k: (
            ", ".join(v) if isinstance(v, list) else
            str(v) if v is not None else ""
        )
        for k, v in meta.items()
    }
    
def flatten_metadata(meta):
    """Convert metadata dict values to Chroma-compatible formats."""
    flat = {}
    for k, v in meta.items():
        if isinstance(v, list):
            flat[k] = ", ".join(str(i) for i in v)
        elif isinstance(v, (str, int, float, bool)) or v is None:
            flat[k] = v
        else:
            flat[k] = str(v)
    return flat

def seed_persona(yaml_path):
    logger.info(f"[persona_seed] Seeding '{COLLECTION_NAME}' from {yaml_path}")

    path = os.path.abspath(yaml_path)
    if not os.path.exists(path):
        raise FileNotFoundError(f"YAML file not found: {yaml_path}")

    with open(path, "r", encoding="utf-8") as f:
        raw = list(yaml.safe_load_all(f))

    client = PersistentClient(path=CHROMA_PATH)
    collection = client.get_or_create_collection(COLLECTION_NAME)

    # 🔥 Wipe existing data
    # ✅ Delete all entries safely (backwards-compatible)
    ids = [doc_id for doc_id in collection.get(include=[])["ids"]]
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

                # Fill missing priority
                if "priority" not in meta and kind in default_priority:
                    meta["priority"] = default_priority[kind]

                meta = flatten_metadata(meta)
                entries.append((doc_id, text, meta))

    added = 0
    for doc_id, text, meta in entries:
        try:
            cleaned_meta = clean_metadata(meta)  # 👈 Clean the metadata before sending
            collection.add(
                ids=[doc_id],
                documents=[text],
                metadatas=[cleaned_meta],
            )
            added += 1
            logger.info(f"✅ Added: {doc_id}")
        except Exception as e:
            logger.warning(f"❌ Failed to add {doc_id}: {e}")

    logger.info(f"\n✅ Seed complete — Added {added} entries to: {COLLECTION_NAME}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--yaml", default=DEFAULT_YAML, help="Path to persona.yaml")
    args = parser.parse_args()
    seed_persona(args.yaml)

if __name__ == "__main__":
    main()
