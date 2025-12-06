"""
persona_ingest.py — Orion CNS 4.0
Minimal, clean persona ingestion pipeline.

Loads multi-document YAML → normalizes → embeds → stores
persona vectors in the "persona" Chroma collection.

Reports:
  - number of valid persona blocks
  - number of malformed entries skipped
  - list of "topic" fields successfully ingested
"""

import uuid
import json
import yaml
from pathlib import Path

from orion_cli.utils.chroma_utils import get_client, _get_or_create, EMBED_FN


# -------------------------------
# Metadata safety: flatten + scalar conversion
# -------------------------------
def _normalize_metadata(block: dict) -> dict:
    """
    Chroma 0.5.x requires metadata to be scalar:
      - str, int, float, bool
    Lists → pipe-joined string
    Dicts → JSON string
    """
    out = {}
    for k, v in block.items():
        if k == "text":
            continue

        if isinstance(v, (list, tuple, set)):
            out[k] = "|".join(str(x) for x in v)
        elif isinstance(v, dict):
            out[k] = json.dumps(v, ensure_ascii=False)
        else:
            out[k] = v
    return out


# -------------------------------
# YAML loader (multi-doc support)
# -------------------------------
def _load_yaml(path: str):
    """Returns list of persona blocks."""
    with open(path, "r", encoding="utf-8") as f:
        docs = list(yaml.safe_load_all(f))

    out = []
    for doc in docs:
        if not doc:
            continue

        if isinstance(doc, dict):
            out.append(doc)
        elif isinstance(doc, list):
            for item in doc:
                if isinstance(item, dict):
                    out.append(item)
                else:
                    raise ValueError(f"Invalid YAML list item: {item}")
        else:
            raise ValueError(f"Unexpected YAML structure: {doc}")

    return out


# -------------------------------
# Main ingestion function
# -------------------------------
def persona_ingest(yaml_path: str, replace: bool = False):
    """
    Normalize persona blocks → embed → insert into ChromaDB.
    """

    # Load raw
    raw_blocks = _load_yaml(yaml_path)

    valid = []
    malformed = []
    topics = []

    # Normalize
    for block in raw_blocks:
        try:
            text = str(block["text"]).strip()
            if not text:
                raise ValueError("Empty text")

            meta = _normalize_metadata(block)
            entry_id = str(uuid.uuid4())

            topic = meta.get("topic", "<none>")
            topics.append(topic)

            valid.append({
                "id": entry_id,
                "text": text,
                "meta": meta
            })
        except Exception as e:
            malformed.append((block, str(e)))

    if not valid:
        raise RuntimeError("No valid persona entries found.")

    # Chroma setup
    client = get_client()
    coll = _get_or_create("persona")

    # Replace option
    if replace:
        try:
            coll.delete()
            coll = _get_or_create("persona")
        except Exception as e:
            print(f"[WARN] Could not clear persona collection: {e}")

    # Prepare insertion
    ids = [v["id"] for v in valid]
    texts = [v["text"] for v in valid]
    metas = [v["meta"] for v in valid]

    # Compute embeddings
    embeddings = [EMBED_FN(t) for t in texts]

    # Insert
    coll.add(ids=ids, documents=texts, metadatas=metas, embeddings=embeddings)

    # Summary
    print("\n[PERSONA INGEST COMPLETE]")
    print(f"Valid entries: {len(valid)}")
    print(f"Malformed skipped: {len(malformed)}")

    # Print topics (unique, sorted)
    uniq_topics = sorted(set(topics))
    print("\nTopics ingested:")
    for t in uniq_topics:
        print(f" - {t}")

    print("\n")

    return len(valid)
