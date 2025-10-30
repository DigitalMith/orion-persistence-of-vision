# orion_cli/persona.py
import os
from pathlib import Path
from typing import Dict, List
from uuid import uuid4

import yaml

from orion_cli.orion_ltm_integration import initialize_chromadb_for_ltm
from orion_cli.utils.ltm_helpers import get_embedding_model

embed_fn = get_embedding_model()

CHROMA_PATH = Path(os.environ.get("ORION_CHROMA_PATH", "user_data/Chroma-DB"))


def load_persona_catalog(path: str):
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    catalog = raw.get("persona", {}).get("catalog", [])

    docs = []
    for i, entry in enumerate(catalog):
        text = entry.get("document") or entry.get("text") or entry.get("content") or ""
        if not text:
            continue

        docs.append(
            {
                "id": entry.get("uuid") or f"catalog-{i}-{uuid4().hex[:6]}",
                "content": text.strip(),
                "metadata": {
                    "category": entry.get("category", "catalog"),
                    "importance": entry.get("importance", 0.5),
                    "tone": entry.get("tone", "neutral"),
                },
            }
        )

    return docs


def load_emotion_blocks(yaml_path: str) -> List[Dict]:
    with open(yaml_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    entries = raw.get("persona", {}).get("emotions", [])
    docs = []
    for i, item in enumerate(entries):
        content = item.get("text", "").strip()
        if not content:
            continue

        metadata = {}
        for k, v in item.items():
            if k == "text":
                continue
            if isinstance(v, list):
                metadata[k] = ", ".join(str(i) for i in v)
            elif isinstance(v, (str, int, float, bool)):
                metadata[k] = v
            else:
                metadata[k] = str(v)

        metadata["category"] = "emotion"

        docs.append(
            {
                "id": f"{metadata.get('topic', 'emotion')}-{i}",
                "content": content,
                "metadata": metadata,
            }
        )
    return docs


def ingest_documents(docs: List[Dict], collection_name: str, replace=False):
    persona_coll, _ = initialize_chromadb_for_ltm()

    if replace:
        try:
            from chromadb import PersistentClient

            client = PersistentClient(path=str(CHROMA_PATH))
            client.delete_collection(name=collection_name)
            # bind the same embedder used by LTM
            from orion_cli.core.ltm import get_or_create_embed_fn

            persona_coll = client.get_or_create_collection(
                name=collection_name, embedding_function=get_or_create_embed_fn()
            )
        except Exception as e:
            print(f"⚠️ Failed to replace collection: {e}")

    if not docs:
        print("⚠️ No entries to ingest.")
        return

    persona_coll.add(
        documents=[d["content"] for d in docs],
        metadatas=[d["metadata"] for d in docs],
        ids=[d["id"] for d in docs],
    )

    print(f"✅ Ingested {len(docs)} documents into collection: {collection_name}")


def ingest_persona_catalog(
    yaml_path: str, collection_name: str = "orion_persona", replace=False
):
    docs = load_persona_catalog(yaml_path)
    ingest_documents(docs, collection_name, replace)


def ingest_emotions(
    yaml_path: str, collection_name: str = "orion-emotions", replace=False
):
    docs = load_emotion_blocks(yaml_path)
    ingest_documents(docs, collection_name, replace)
