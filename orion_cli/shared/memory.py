"""
============================================================
 Orion CNS - Unified Central Nervous System (CNS) Module
============================================================
"""

# ------------------------------------------------------------
# Imports
# ------------------------------------------------------------
import json
import re
from datetime import datetime, timezone
from uuid import uuid4

from orion_cli.utils.config import get_config
from orion_cli.utils.chroma_utils import (
    get_client,
    _get_or_create,
    EMBED_FN,
)


# ------------------------------------------------------------
# Collection names
# ------------------------------------------------------------
COLL_PERSONA = "persona"
COLL_EPISODIC = "orion_episodic_ltm"  # normalized episodic LTM
COLL_EPISODIC_RAW = "orion_episodic_raw_ltm"  # legacy, unused


# ------------------------------------------------------------
# Debug Event Logger
# ------------------------------------------------------------
def debug_ltm_event(event: str, **kwargs):
    """
    Structured CNS debug output.
    Controlled through config.yaml:

        debug:
          enabled: true
          show_recall: true

    """
    try:
        cfg = get_config().get("debug", {})
    except Exception:
        return

    if not cfg.get("enabled"):
        return

    print(f"\n[orion][DEBUG] --- {event} ---")
    for key, val in kwargs.items():
        if isinstance(val, str) and len(val) > 250:
            print(f"{key}: {val[:250]}...")
        else:
            print(f"{key}: {val}")
    print("[orion][DEBUG] -----------------------\n")


# ------------------------------------------------------------
# Universal Safe Add Helper
# ------------------------------------------------------------
def safe_add_to_chroma(collection, ids, documents, metadatas):
    """
    Strictly normalizes all inputs into JSON-safe string formats
    and adds them to a Chroma collection.
    """
    import pprint

    def stringify(obj):
        if isinstance(obj, (int, float, bool)):
            return str(obj)
        if obj is None:
            return ""
        if isinstance(obj, (list, tuple, set)):
            return [stringify(x) for x in obj]
        if isinstance(obj, dict):
            return {str(k): stringify(v) for k, v in obj.items()}
        if not isinstance(obj, str):
            return str(obj)
        return obj

    try:
        ids = stringify(ids)
        documents = stringify(documents)
        metadatas = stringify(metadatas)

        if not isinstance(ids, list):
            ids = [ids]
        if not isinstance(documents, list):
            documents = [documents]
        if not isinstance(metadatas, list):
            metadatas = [metadatas]

        debug_ltm_event(
            "SAFE_ADD",
            ids=ids,
            documents=documents,
            metadatas=metadatas,
        )

        collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
        )

    except Exception as e:
        print(f"[ltm] ? safe_add_to_chroma failed: {e}")
        print("[ltm] attempting fallback normalization")
        try:
            metadatas = json.loads(json.dumps(metadatas))
            collection.add(ids=ids, documents=documents, metadatas=metadatas)
        except Exception as e2:
            print(f"[ltm] ? fallback failed: {e2}")


# ------------------------------------------------------------
# User Turn Ingestion
# ------------------------------------------------------------
def on_user_turn(user_input: str, episodic_coll):
    """
    Store user text in episodic memory after normalization + dedupe.
    """
    try:
        if not isinstance(user_input, str):
            user_input = str(user_input)

        clean = user_input.strip()
        if not clean or len(clean) < 2:
            return

        norm = clean.lower()

        existing = episodic_coll.query(
            query_texts=[norm],
            n_results=3,
            include=["documents"],
        )

        for doc in existing.get("documents", [[]])[0]:
            if isinstance(doc, str) and doc.strip().lower() == norm:
                return

        ts = datetime.now().isoformat()
        doc_id = f"user_{uuid4().hex}"
        meta = {
            "timestamp": ts,
            "importance": "0.5",
            "source": "user",
        }

        debug_ltm_event("USER_TURN_STORE", doc=clean, timestamp=ts)

        safe_add_to_chroma(
            episodic_coll,
            ids=[doc_id],
            documents=[clean],
            metadatas=[meta],
        )

    except Exception as e:
        print(f"[ltm] user-turn error: {e}")


# ------------------------------------------------------------
# Assistant Turn Ingestion
# ------------------------------------------------------------
def on_assistant_turn(reply: str, episodic_coll, last_user_input=None):
    """
    Store assistant responses, skipping formatting artifacts.
    """
    try:
        if not isinstance(reply, str):
            reply = str(reply)

        clean = reply.strip()
        if not clean or len(clean) < 10:
            return

        if re.fullmatch(r"\[.*?\]", clean):
            return

        ts = datetime.now().isoformat()
        doc_id = f"assistant_{uuid4().hex}"
        meta = {
            "timestamp": ts,
            "importance": "0.7",
            "source": "assistant",
        }

        debug_ltm_event("ASSISTANT_TURN_STORE", reply=clean[:120], timestamp=ts)

        safe_add_to_chroma(
            episodic_coll,
            ids=[doc_id],
            documents=[clean],
            metadatas=[meta],
        )

        # try:
        # live_pooled_store(last_user_input, clean, episodic_coll)
        # except Exception:
        # pass

    except Exception as e:
        print(f"[ltm] assistant-turn error: {e}")


# ------------------------------------------------------------
# Chroma Initialization
# ------------------------------------------------------------
def initialize_chromadb_for_ltm(embed_fn=EMBED_FN):
    """
    Ensures persona + episodic collections exist and are bound
    to the correct embedding model.
    """
    client = get_client()
    persona = _get_or_create(client, COLL_PERSONA, embed_fn)
    episodic = _get_or_create(client, COLL_EPISODIC, embed_fn)

    return persona, episodic


# ------------------------------------------------------------
# Deterministic Retrieval Helpers
# ------------------------------------------------------------
def normalize_hits(hits):
    docs = hits.get("documents", [[]])[0]
    metas = hits.get("metadatas", [[]])[0]
    dists = hits.get("distances", [[]])[0]

    items = []
    for doc, meta, dist in zip(docs, metas, dists):
        if not doc:
            continue
        sim = 1 - float(dist)
        imp = float(meta.get("importance", 0.5))
        ts = meta.get("timestamp", "")
        items.append(
            {
                "doc": doc,
                "similarity": sim,
                "importance": imp,
                "timestamp": ts,
                "meta": meta,
            }
        )
    return items


def deterministic_sort(items):
    return sorted(
        items,
        key=lambda x: (
            -x["similarity"],
            -x["importance"],
            x["timestamp"],
        ),
    )


def filter_items(items, importance_threshold=0.6):
    out = []
    seen = set()
    for it in items:
        doc = it["doc"]
        if not doc or len(doc) < 3:
            continue
        if it["importance"] < importance_threshold:
            continue

        norm = doc.strip().lower()
        if norm in seen:
            continue
        seen.add(norm)
        out.append(it)

    return out


def parse_timestamp(ts):
    try:
        return datetime.fromisoformat(ts)
    except:
        return datetime(1970, 1, 1, tzinfo=timezone.utc)


def recency_weight(item):
    ts = parse_timestamp(item["timestamp"])
    age_days = (datetime.now(ts.tzinfo) - ts).total_seconds() / 86400.0

    if age_days < 1:
        return 1.0
    if age_days <= 30:
        return 0.5 + (0.5 * (1 - (age_days / 30)))
    return 0.1


def fuse_chunks(items, window_seconds=5400):
    if not items:
        return items

    fused = []
    current = items[0]

    for nxt in items[1:]:
        t1 = parse_timestamp(current["timestamp"])
        t2 = parse_timestamp(nxt["timestamp"])

        if abs((t2 - t1).total_seconds()) <= window_seconds:
            merged = dict(current)
            merged["doc"] = current["doc"] + "\n" + nxt["doc"]
            merged["importance"] = max(current["importance"], nxt["importance"])
            current = merged
        else:
            fused.append(current)
            current = nxt

    fused.append(current)
    return fused


# ------------------------------------------------------------
# Semantic Memory Placeholder
# ------------------------------------------------------------
def get_semantic_hits(semantic_coll, query, topk):
    if semantic_coll is None:
        return {"documents": [[]], "metadatas": [[]], "distances": [[]]}
    return semantic_coll.query(
        query_texts=[query],
        n_results=topk,
        include=["documents", "metadatas", "distances"],
    )


# ------------------------------------------------------------
# Unified Deterministic Recall
# ------------------------------------------------------------
def get_relevant_ltm(
    query,
    persona_coll,
    episodic_coll,
    semantic_coll=None,
    topk_persona=5,
    topk_episodic=10,
    topk_semantic=5,
    importance_threshold=0.6,
    return_debug=False,
):
    cfg = get_config().get("debug", {})

    persona_hits = persona_coll.query(
        query_texts=[query],
        n_results=topk_persona,
        include=["documents", "metadatas", "distances"],
    )
    episodic_hits = episodic_coll.query(
        query_texts=[query],
        n_results=topk_episodic,
        include=["documents", "metadatas", "distances"],
    )
    semantic_hits = get_semantic_hits(semantic_coll, query, topk_semantic)

    persona_norm = normalize_hits(persona_hits)
    episodic_norm = normalize_hits(episodic_hits)
    semantic_norm = normalize_hits(semantic_hits)

    persona_sorted = deterministic_sort(persona_norm)
    episodic_sorted = deterministic_sort(episodic_norm)
    semantic_sorted = deterministic_sort(semantic_norm)

    persona_filt = filter_items(persona_sorted, importance_threshold)
    episodic_filt = filter_items(episodic_sorted, importance_threshold)
    semantic_filt = filter_items(semantic_sorted, importance_threshold)

    # =======================================================
    # CNS FUSION V3 — Rigidity-Controlled Scoring
    # =======================================================

    cfg = get_config()
    rigidity = cfg.get("persona", {}).get("rigidity", 0.5)

    def score_item(item, weight_similarity=0.7, weight_importance=0.3):
        """Base scoring formula — modified by rigidity later."""
        return (item["similarity"] * weight_similarity) + (
            item["importance"] * weight_importance
        )

    def apply_rigidity_scaling(persona_items, episodic_items, semantic_items, rigidity):
        """Scale memory scores based on persona rigidity."""

        persona_scale = rigidity  # persona gets stronger as rigidity increases
        flex_scale = (
            1.0 - rigidity
        )  # episodic + semantic get stronger as rigidity decreases

        for item in persona_items:
            item["score"] *= persona_scale

        for item in episodic_items:
            item["score"] *= flex_scale

        for item in semantic_items:
            item["score"] *= flex_scale

        return persona_items, episodic_items, semantic_items

    # Score items using base formula
    persona_scored = [dict(x, score=score_item(x)) for x in persona_filt]
    episodic_scored = [dict(x, score=score_item(x)) for x in episodic_filt]
    semantic_scored = [dict(x, score=score_item(x)) for x in semantic_filt]

    # Apply rigidity scaling
    persona_scaled, episodic_scaled, semantic_scaled = apply_rigidity_scaling(
        persona_scored,
        episodic_scored,
        semantic_scored,
        rigidity,
    )

    # Rank results
    persona_rank = sorted(persona_scaled, key=lambda x: -x["score"])
    episodic_rank = sorted(episodic_scaled, key=lambda x: -x["score"])
    semantic_rank = sorted(semantic_scaled, key=lambda x: -x["score"])

    # Fuse episodic into coherent scenes
    episodic_rank = fuse_chunks(episodic_rank)

    if cfg.get("enabled") and cfg.get("show_recall"):
        debug_ltm_event(
            "PHASE_2+3_RECALL",
            query=query,
            persona_results=len(persona_rank),
            episodic_results=len(episodic_rank),
            semantic_results=len(semantic_rank),
        )

    # Persona ? Semantic ? Episodic
    lines = []
    lines.extend(f"[PERSONA] {x['doc']}" for x in persona_rank)
    lines.extend(f"[SEMANTIC] {x['doc']}" for x in semantic_rank)
    lines.extend(f"[EPISODIC] {x['doc']}" for x in episodic_rank)

    final = "\n".join(lines).strip()

    if return_debug:
        return final, {
            "persona": persona_rank,
            "semantic": semantic_rank,
            "episodic": episodic_rank,
        }

    return final
