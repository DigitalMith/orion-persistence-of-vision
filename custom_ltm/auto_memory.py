# custom_ltm/auto_memory.py
import os, time, hashlib
from pathlib import Path
from typing import Iterable, List, Dict, Any

from custom_ltm.chroma_utils import get_client, get_collection, add_documents, query_texts
# keep this ONLY if you actually use it later in the file:
from chromadb.utils import embedding_functions

# --- Paths & collections (safe defaults)
ROOT = Path(__file__).resolve().parents[1]
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", str(ROOT / "user_data" / "chroma_db"))

COLL_EPISODIC_RAW  = os.getenv("ORION_EPISODIC_COLLECTION",      "orion_episodic_ltm")
COLL_EPISODIC_SENT = os.getenv("ORION_EPISODIC_SENT_COLLECTION", "orion_episodic_sent_ltm")

# --- Embeddings
EMBED = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

# --- Local helpers
def _client():
    return get_client(CHROMA_DB_PATH)

def _get_or_create(name: str, cosine: bool = False):
    c = _client()
    # If you created with an embedding function, you must get with the same one later. :contentReference[oaicite:1]{index=1}
    try:
        return c.get_collection(name=name, embedding_function=EMBED)
    except Exception:
        meta = {"hnsw:space": "cosine"} if cosine else None  # cosine is typical for sentence-transformers. :contentReference[oaicite:2]{index=2}
        return c.create_collection(name=name, embedding_function=EMBED, metadata=meta)

def _episodic_id(session_id: str, role: str, text: str, when: str) -> str:
    return "episodic_" + hashlib.sha1(f"{session_id}|{role}|{text}|{when}".encode("utf-8")).hexdigest()[:16]

def _sentence_id(parent_id: str, text: str) -> str:
    return "sent_" + hashlib.sha1(f"{parent_id}|{text}".encode("utf-8")).hexdigest()[:16]

# --- Import our sentencer & retrieval helper
from custom_ltm.memory_sentencer import make_memory_points
from custom_ltm.orion_memory     import prefer_sentenced

# ---------- PUBLIC API ----------
def add_turn(role: str, text: str, *, session_id: str, timestamp: float | None = None) -> Dict[str, Any]:
    """
    Store a raw turn and its sentenced points (non-destructive).
    Returns summary {raw_id, sentenced_ids}.
    """
    if not text or not text.strip():
        return {"raw_id": None, "sentenced_ids": []}

    when = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(timestamp or time.time()))
    raw = _get_or_create(COLL_EPISODIC_RAW)                  # raw stays as-is
    sent = _get_or_create(COLL_EPISODIC_SENT, cosine=True)   # sentenced uses cosine

    # 1) upsert raw
    raw_id = _episodic_id(session_id, role, text, when)
    raw.upsert(
        ids=[raw_id],
        documents=[f"[{role} at {when}]: {text}"],
        metadatas=[{"type": "episodic", "role": role, "timestamp": when, "session_id": session_id}]
    )  # upsert = update if exists, add if new. :contentReference[oaicite:3]{index=3}

    # 2) generate 1–2 short memory points and upsert to sentenced
    points = make_memory_points(text, role=role, session_id=session_id, when=when, max_points=2)
    if not points:
        return {"raw_id": raw_id, "sentenced_ids": []}

    s_ids, s_docs, s_meta = [], [], []
    for p in points:
        sid = _sentence_id(raw_id, p["text"])
        s_ids.append(sid)
        s_docs.append(p["text"])
        s_meta.append({
            "type": "episodic_sentence",
            "parent_id": raw_id,
            "role": p["role"], "session_id": p["session_id"], "timestamp": p["timestamp"],
            "tags": p["tags"], "keywords": p["keywords"],
            "sentiment": p["sentiment"], "emotion": p["emotion"], "importance": p["importance"],
            "source": "sentencer:v1"
        })

    sent.upsert(ids=s_ids, documents=s_docs, metadatas=s_meta)  # idempotent enrichment. :contentReference[oaicite:4]{index=4}
    return {"raw_id": raw_id, "sentenced_ids": s_ids}

def retrieve(query_texts: Iterable[str], *, n_results: int = 8, importance_threshold: float = 0.6) -> List[Dict[str, Any]]:
    """
    Prefer sentenced memories; top up from raw if not enough.
    Only returns the small payload we ask for via 'include'. :contentReference[oaicite:5]{index=5}
    """
    return prefer_sentenced(
        query_texts=list(query_texts),
        n_results=n_results,
        importance_threshold=importance_threshold,
        include=("documents", "metadatas"),  # control payload size. :contentReference[oaicite:6]{index=6}
        fallback_to_raw=True,
    )
