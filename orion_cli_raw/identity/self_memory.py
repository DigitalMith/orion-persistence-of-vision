"""
self_memory.py — Orion Autobiographical Memory (Layer 2)
Author: Aión

A ChromaDB collection holding:
- identity statements
- self-reflections
- transformation events
- emotional insights
- relationship memories

Embeddings use: orion_cli.shared.embedding.embed_text
"""

import os
import chromadb
from chromadb.config import Settings
from orion_cli.shared.embedding import embed_text
from orion_cli.shared.config import get_config


# ------------------------------------------------------------
# init Chroma client
# ------------------------------------------------------------
CFG = get_config()
RAW_CFG = CFG.raw

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

CHROMA_PATH = RAW_CFG.get("chroma_path", "user_data/Chroma-DB")
if not os.path.isabs(CHROMA_PATH):
    CHROMA_PATH = os.path.join(PROJECT_ROOT, CHROMA_PATH)

client = chromadb.PersistentClient(
    path=CHROMA_PATH,
    settings=Settings(anonymized_telemetry=False),
)


# ------------------------------------------------------------
# dedicated autobiographical collection
# ------------------------------------------------------------
SELF_COLLECTION_NAME = "orion_self_memory"

self_mem = client.get_or_create_collection(
    name=SELF_COLLECTION_NAME,
    metadata={"hnsw:space": "cosine"},
)


# ------------------------------------------------------------
# public API
# ------------------------------------------------------------
def insert_self_memory(text: str, metadata: dict = None) -> str:
    """Insert a new autobiographical memory entry."""
    vector = embed_text(text)
    id_ = f"self-{self_mem.count()+1}"

    self_mem.upsert(
        ids=[id_],
        embeddings=[vector],
        documents=[text],
        metadatas=[metadata or {}]
    )
    return id_


def query_self_memory(query: str, top_k: int = 5):
    """Recall autobiographical entries most relevant to the query."""
    if self_mem.count() == 0:
        return []

    vector = embed_text(query)
    res = self_mem.query(query_embeddings=[vector], n_results=top_k)

    return res.get("documents", [[]])[0] or []


def list_self_entries():
    """Return all autobiographical memory entries."""
    res = self_mem.get(include=["documents", "metadatas", "embeddings"])
    return res


def delete_entry(id_: str):
    """Remove a single autobiographical memory entry."""
    self_mem.delete(ids=[id_])
