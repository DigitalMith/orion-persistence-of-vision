#!/usr/bin/env python3
# Delete entries from Chroma by EXACT topic match, with preview & confirm.

from __future__ import annotations
from typing import List
from chromadb import PersistentClient
# Defaults aligned with your project layout
DEFAULT_DB_PATH = "user_data/chroma_db"
DEFAULT_COLLECTION = "orion_episodic_sent_ltm"

def _collection(db_path: str = DEFAULT_DB_PATH, collection: str = DEFAULT_COLLECTION):
    client = PersistentClient(path=db_path)
    # ❌ No embedding_function attached (prevents dim mismatch)
    return client.get_or_create_collection(name=collection)

def count_by_topic(topic: str,
                   db_path: str = DEFAULT_DB_PATH,
                   collection: str = DEFAULT_COLLECTION) -> int:
    col = _collection(db_path, collection)
    res = col.get(where={"topic": topic}, include=[], limit=1_000_000)
    return len(res.get("ids") or [])

def preview_topic(topic: str,
                  k: int = 3,
                  db_path: str = DEFAULT_DB_PATH,
                  collection: str = DEFAULT_COLLECTION) -> List[str]:
    """Return up to k example docs for this exact topic without embedding."""
    col = _collection(db_path, collection)
    res = col.get(where={"topic": topic}, include=["documents"], limit=k)
    docs = res.get("documents") or []
    return [ (d or "")[:160].replace("\n"," ") + ("…" if d and len(d)>160 else "") for d in docs ]

def delete_by_topic(topic: str,
                    dry_run: bool = False,
                    db_path: str = DEFAULT_DB_PATH,
                    collection: str = DEFAULT_COLLECTION) -> int:
    """Delete all records where metadata.topic == topic. Returns count removed (or would remove)."""
    col = _collection(db_path, collection)
    res = col.get(where={"topic": topic}, include=[], limit=1_000_000)
    ids = res.get("ids") or []
    if dry_run or not ids:
        return len(ids)
    col.delete(ids=ids)  # exact set delete is safer
    return len(ids)
