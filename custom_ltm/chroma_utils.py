# custom_ltm/chroma_utils.py
from __future__ import annotations
import os, hashlib, uuid
import chromadb
from chromadb.config import Settings

def get_client(persist_dir: str) -> chromadb.api.client.Client:
    os.makedirs(persist_dir, exist_ok=True)
    return chromadb.PersistentClient(
        path=persist_dir,
        settings=Settings(
            anonymized_telemetry=False,
            allow_reset=True,
        ),
    )

def get_collection(client, name: str, embedding_function=None):
    # Keep cosine as the default HNSW space; pass embedding_function if you use it
    return client.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
        embedding_function=embedding_function
    )

def make_id(text: str, salt: str = "") -> str:
    base = (text or "").strip().lower()
    h = hashlib.sha256((base + "|" + salt).encode("utf-8")).hexdigest()
    # prettify to uuid format (optional)
    return str(uuid.UUID(h[:32])) if len(h) >= 32 else h

def add_documents(coll, docs, metas, ids=None):
    if ids is None:
        ids = [make_id(d, (m.get("source_time","") + m.get("role",""))) for d, m in zip(docs, metas)]
    coll.add(ids=ids, documents=docs, metadatas=metas)
    return ids

def query_texts(coll, queries, top_k: int = 5, where: dict | None = None, include=None):
    if include is None:
        include = ["documents", "metadatas", "distances"]
    kwargs = {"query_texts": queries, "n_results": top_k, "include": include}
    if where is not None:
        kwargs["where"] = where
    return coll.query(**kwargs)
