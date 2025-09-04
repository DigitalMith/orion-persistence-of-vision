import os, time, hashlib
from datetime import datetime
from typing import Any, Optional, Dict, List
import re

from custom_ltm.chroma_utils import get_client, get_collection, add_documents, query_texts
from chromadb.utils import embedding_functions  # keep if you pass an embedding fn to collections
# Removed: InvalidCollectionException doesn't exist in Chroma >=1.0
InvalidCollectionException = Exception  # temporary general catch


# --- Config (env-aware) ---
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CHROMA_DB_PATH = os.environ.get("CHROMA_DB_PATH", os.path.join(ROOT, "user_data", "chroma_db"))
EMBED_MODEL = os.environ.get("ORION_EMBED_MODEL", "all-mpnet-base-v2")

COLL_PERSONA        = os.environ.get("ORION_PERSONA_COLLECTION",        "orion_persona_ltm")
COLL_EPISODIC_RAW   = os.environ.get("ORION_EPISODIC_COLLECTION",       "orion_episodic_ltm")
COLL_EPISODIC_SENT  = os.environ.get("ORION_EPISODIC_SENT_COLLECTION",  "orion_episodic_sent_ltm")

# _CLIENT: chromadb.PersistentClient | None = None
_EMBED = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=EMBED_MODEL)

# def _client() -> chromadb.PersistentClient:
_CLIENT: Optional[Any] = None

def _clean_query_text(text: str) -> str:
    """Remove generic filler and hedging from user questions to improve memory match."""
    # Remove common fluff phrases
    text = re.sub(r"\b(?:do you|can you|could you|would you|please|remember|recall|tell me|do you know|what about|did we|do i)\b", "", text, flags=re.I)
    # Strip any leftover multiple spaces and symbols
    text = re.sub(r"[^\w\s.,!?]", "", text)
    text = re.sub(r"\s{2,}", " ", text).strip()
    return text
    

def _client() -> Any:
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = get_client(CHROMA_DB_PATH)
        try:
            _CLIENT.list_collections()
        except Exception as e:
            # No destructive reset; just warn
            print(f"[chromadb] warning listing collections: {e}")
    return _CLIENT

def _get_or_create(name: str, *, cosine: bool = False):
    c = _client()
    try:
        return c.get_or_create_collection(
            name=name,
            embedding_function=_EMBED,
            metadata={"hnsw:space": "cosine"} if cosine else None
        )
    except Exception as e:
        print(f"[ERROR] Failed to get/create collection '{name}': {e}")
        raise
    
# ---- Prefer-Sentenced retrieval ----
def _flatten_query(res) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    if not res: return out
    ids = res.get("ids") or []
    docs = res.get("documents")
    metas = res.get("metadatas")
    dists = res.get("distances")
    for qi in range(len(ids)):
        row_ids = ids[qi]
        for ri, _id in enumerate(row_ids):
            out.append({
                "id": _id,
                "document": (docs[qi][ri] if docs else None),
                "metadata": (metas[qi][ri] if metas else None),
                "distance": (dists[qi][ri] if dists else None),
                "query_index": qi,
                "rank": ri,
            })
    return out

def _prefer_sentenced(
    query_texts_list: List[str],
    n_results: int,
    importance_threshold: float = 0.1,
    include=("documents", "metadatas"),
    fallback_to_raw: bool = True
) -> List[Dict[str, Any]]:
    sent = _get_or_create(COLL_EPISODIC_SENT, cosine=True)
    raw  = _get_or_create(COLL_EPISODIC_RAW)

    # Sentenced first, with importance filter
    sent_res = query_texts(
        sent,
        query_texts_list,
        top_k=n_results,
        where={"importance": {"$gte": importance_threshold}},
    )
    hits = _flatten_query(sent_res)
    seen = {h["id"] for h in hits}
    need = max(0, n_results - len(hits))

    # Optional fallback to raw if not enough
    if fallback_to_raw and need > 0:
        raw_res = query_texts(
            raw,
            query_texts_list,
            top_k=n_results * 2,  # over-fetch, then trim
        )
        pool = [r for r in _flatten_query(raw_res) if r["id"] not in seen]
        hits.extend(pool[:need])

    # Sort and dedupe
    hits.sort(key=lambda x: (x["query_index"], x["distance"] if x.get("distance") is not None else 9e9))

    unique, seen_docs = [], set()
    for h in hits:
        doc = (h.get("document") or "").strip().lower()
        key = re.sub(r"\s+", " ", doc)
        if not key or key in seen_docs:
            continue
        seen_docs.add(key)
        unique.append(h)

    return unique[:n_results]


    
# ---- Sentencer (lightweight heuristics) ----
# (same helpers used in auto_memory.py / memory_sentencer.py; inlined here for zero deps)
import re
from collections import Counter
_STOP = set("the a an and or but if is are was were be been you your yours me my mine we our ours they them their to of in on for with as at by from it this that these those not no".split())

def _split_sents(text: str):
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [s.strip() for s in parts if s.strip()]

def _top_keywords(text: str, k: int = 5):
    words = [w.lower() for w in re.findall(r"[A-Za-z][A-Za-z0-9_-]+", text)]
    words = [w for w in words if w not in _STOP and len(w) > 2]
    return [w for w,_ in Counter(words).most_common(k)]

def _sentiment(text: str):
    pos = len(re.findall(r"\b(amazing|great|good|love|perfect|win|success)\b", text, flags=re.I))
    neg = len(re.findall(r"\b(bad|worse|hate|fail|problem|bug|issue)\b", text, flags=re.I))
    return "positive" if pos - neg >= 2 else "negative" if neg - pos >= 2 else "neutral"

def _emotion(text: str):
    if re.search(r"\b(worried|anxious|stressed|nervous)\b", text, flags=re.I): return "anxiety"
    if re.search(r"\b(angry|furious|mad)\b", text, flags=re.I): return "anger"
    if re.search(r"\b(happy|glad|excited|joy)\b", text, flags=re.I): return "joy"
    if re.search(r"\b(sad|upset|down)\b", text, flags=re.I): return "sadness"
    return "neutral"

def _importance(text: str):
    score = 0.0
    score += 0.6 if re.search(r"\b(todo|task|deadline|remind|remember|fix|bug)\b", text, re.I) else 0.0
    score += 0.4 if re.search(r"\bI\b|\bwe\b|\byou\b", text) else 0.0
    score += 0.3 if re.search(r"\b\d{1,4}\b", text) else 0.0
    score += min(len(text), 400) / 400 * 0.3
    return round(min(score, 1.0), 2)

def _condense(text: str, max_chars=220):
    sents = _split_sents(text)
    if not sents: return None
    strong = [s for s in sents if re.search(r"\b(todo|fix|remember|key|important|note)\b", s, re.I)]
    picked = strong[0] if strong else sents[0]
    return picked[:max_chars].strip()

def _make_points(raw_text: str, role: str, session_id: str, when: str, max_points=2):
    pts = []
    for sent in _split_sents(raw_text)[:max_points]:
        short = _condense(sent)
        if not short: continue
        kw = _top_keywords(short)
        pts.append({
            "text": short,
            "tags": list({role, *kw}),
            "keywords": kw,
            "sentiment": _sentiment(short),
            "emotion": _emotion(short),
            "importance": _importance(short),
            "role": role, "session_id": session_id, "timestamp": when,
        })
    return pts

# ---- Public API ----
def initialize_chromadb_for_ltm():
    persona = _get_or_create(COLL_PERSONA)
    episodic_raw  = _get_or_create(COLL_EPISODIC_RAW)
    episodic_sent = _get_or_create(COLL_EPISODIC_SENT, cosine=True)
    return persona, episodic_raw, episodic_sent

# # def get_relevant_ltm(user_input: str,
    # # # NEW: include importance and top tags (up to 3)
    # # imp = meta.get("importance")
    # # tags = (meta.get("tags_csv") or "").split("|")
    # # tag_preview = ",".join(tags[:3]) if tags else ""
    # # ctx_lines.append(f"[{tag} imp={imp} tags={tag_preview}] {doc}")
                     # # topk_persona: int = 6,
                     # # topk_episodic: int = 8,
                     # # importance_threshold: float = 0.6,
                     # # return_debug: bool = False):
    # # persona, _raw, _sent = initialize_chromadb_for_ltm()
    # # ctx_lines, dbg = [], {}

# def get_relevant_ltm(user_input: str,
    # # NEW: include importance and top tags (up to 3)
    # imp = meta.get("importance")
    # tags = (meta.get("tags_csv") or "").split("|")
    # tag_preview = ",".join(tags[:3]) if tags else ""
    # ctx_lines.append(f"[{tag} imp={imp} tags={tag_preview}] {doc}")
                     # topk_persona: int = 6,
                     # topk_episodic: int = 8,
                     # importance_threshold: float = 0.6,
                     # return_debug: bool = False):
    # persona, _raw, _sent = initialize_chromadb_for_ltm()
    # ctx_lines, dbg = [], {}
    
def get_relevant_ltm(
    user_input: str,
    topk_persona: int = 6,
    topk_episodic: int = 8,
    importance_threshold: float = 0.6,
    return_debug: bool = False
):
    if importance_threshold < 0.5:
        print(f"[DEBUG WARNING] importance_threshold is set to {importance_threshold}. Did you mean to leave it that low?")
    user_input = _clean_query_text(user_input)
    persona, _raw, _sent = initialize_chromadb_for_ltm()
    ctx_lines, dbg = [], {}

    # --- Persona section ---
    pres = query_texts(persona, [user_input], top_k=max(1, topk_persona))
    p_docs = pres.get("documents", [[]])[0] if pres else []
    p_dists = pres.get("distances", [[]])[0] if pres else []

    for doc in p_docs:
        if doc:
            ctx_lines.append(f"[PERSONA] {doc}")

    # --- Sentenced episodic memory section ---
    hits = _prefer_sentenced(
        [user_input],
        n_results=max(1, topk_episodic),
        importance_threshold=importance_threshold,
        include=["documents", "metadatas"],
        fallback_to_raw=True
    )
    if len(hits) < (topk_episodic // 2):
        hits += _prefer_sentenced(
            [user_input],
            n_results=topk_episodic,
            importance_threshold=0.3,
            include=["documents", "metadatas"],
            fallback_to_raw=True
        )

    dbg["episodic_hits"] = len(hits)
    dbg["episodic_top"] = (hits[0].get("distance") if hits and isinstance(hits[0], dict) else None)

    for h in hits:
        doc = h.get("document") or ""
        meta = h.get("metadata") or {}
        tag = "SENTENCE" if meta.get("type") == "episodic_sentence" else "EPISODIC"
        imp = meta.get("importance", "n/a")
        tags = meta.get("tags", meta.get("tags_csv", "")).split(",")
        tag_preview = ",".join(tags[:3]) if tags else ""
        print(f"[DEBUG] Retrieved → {doc[:80]}... | imp={imp}, tags={tag_preview}")
        ctx_lines.append(f"[{tag} imp={imp} tags={tag_preview}] {doc}")

    ctx = "\n".join(ctx_lines).strip()
    return (ctx, dbg) if return_debug else ctx


# Deterministic IDs + upsert + immediate sentencing
def _episodic_id(session_id: str, role: str, text: str, when: str) -> str:
    return "episodic_" + hashlib.sha1(f"{session_id}|{role}|{text}|{when}".encode("utf-8")).hexdigest()[:16]

def _sentence_id(parent_id: str, text: str) -> str:
    return "sent_" + hashlib.sha1(f"{parent_id}|{text}".encode("utf-8")).hexdigest()[:16]

def on_user_turn(text: str, session_id: str = "default", timestamp: Optional[float] = None):
    return _add_turn("user", text, session_id, timestamp)

def on_assistant_turn(text: str, session_id: str = "default", timestamp: Optional[float] = None):
    return _add_turn("assistant", text, session_id, timestamp)

def _add_turn(role: str, text: str, session_id: str, timestamp: Optional[float]):
    if not text or not text.strip():
        return {"raw_id": None, "sentenced_ids": []}

    when = datetime.utcfromtimestamp(timestamp or time.time()).strftime("%Y-%m-%dT%H:%M:%SZ")
    raw  = _get_or_create(COLL_EPISODIC_RAW)
    sent = _get_or_create(COLL_EPISODIC_SENT, cosine=True)

    raw_id = _episodic_id(session_id, role, text, when)
    raw.upsert(
        ids=[raw_id],
        documents=[f"[{role} at {when}]: {text}"],
        metadatas=[{"type":"episodic","role":role,"timestamp":when,"session_id":session_id}]
    )

    pts = _make_points(text, role=role, session_id=session_id, when=when, max_points=2)
    s_ids, s_docs, s_meta = [], [], []
    for p in pts:
        sid = _sentence_id(raw_id, p["text"])
        s_ids.append(sid)
        s_docs.append(p["text"])
        s_meta.append({
            "type": "episodic_sentence",
            "parent_id": raw_id,
            "role": p["role"],
            "session_id": p["session_id"],
            "timestamp": p["timestamp"],
            "tags": ", ".join(p["tags"]),
            "keywords": ", ".join(p["keywords"]),
            "sentiment": p["sentiment"],
            "emotion": p["emotion"],
            "importance": p["importance"],
            "source": "sentencer:v1"
        })
    if s_ids:
        print(f"[DEBUG] Writing {len(s_ids)} episodic memory entries...")
        for doc, meta in zip(s_docs, s_meta):
            print(f"[MEMORY ENTRY] {doc[:60]}... | Meta: {meta}")

        sent.upsert(ids=s_ids, documents=s_docs, metadatas=s_meta)
    return {"raw_id": raw_id, "sentenced_ids": s_ids}
