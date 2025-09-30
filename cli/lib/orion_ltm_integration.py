# cli/lib/orion_ltm_integration.py

from typing import List, Dict, Any
import re
import time

from cli.data.web_config import WEB_CONFIG
from cli.lib.chroma_utils import (
    _get_or_create,
    get_client,
    get_collection,
    EMBED_FN,
)

# Centralized config for embedding model
MODEL_NAME = WEB_CONFIG.get("embedding_model", "sentence-transformers/all‑mpnet‑base‑v2")

from cli.lib.chroma_utils import (
    _get_or_create,
    get_client,
    get_collection,
    EMBED_FN,
)

# Constants for collection names
COLL_PERSONA = "orion_persona_ltm"
COLL_EPISODIC_RAW = "orion_episodic_raw_ltm"
COLL_EPISODIC_SENT = "orion_episodic_sent_ltm"

def initialize_chromadb_for_ltm(embed_fn=EMBED_FN):
    """
    Initialize ChromaDB collections for persona and episodic memory.
    Ensures collections exist and are bound to the embedding function.
    """
    persona = _get_or_create(COLL_PERSONA, embed_fn=embed_fn)
    episodic = _get_or_create(COLL_EPISODIC_SENT, cosine=True, embed_fn=embed_fn)

    print("[ltm] ChromaDB initialized: persona + episodic collections ready")
    return persona, episodic

def get_relevant_ltm(
    user_input: str,
    persona_coll,
    episodic_coll,
    topk_persona: int = 2,
    topk_episodic: int = 4,
    importance_threshold: float = 0.55,
    return_debug: bool = False,
):
    """
    Retrieve relevant persona + episodic memories with importance and recency bias.
    """

    results = []

    # Persona query
    try:
        p_res = persona_coll.query(
            query_texts=[user_input],
            n_results=topk_persona,
            include=["metadatas", "documents"],
        )
        results.extend(
            {
                "source": "persona",
                "doc": p_res["documents"][0][i],
                "meta": p_res["metadatas"][0][i],
                "score": 1.0,  # persona facts = high priority
            }
            for i in range(len(p_res.get("ids", [[]])[0]))
        )
    except Exception as e:
        print(f"[ltm] Persona query failed: {e}")

    # Episodic query
    try:
        e_res = episodic_coll.query(
            query_texts=[user_input],
            n_results=topk_episodic * 2,  # overfetch, then filter
            include=["metadatas", "documents"],
        )
        for i in range(len(e_res.get("ids", [[]])[0])):
            meta = e_res["metadatas"][0][i]
            doc = e_res["documents"][0][i]
            importance = float(meta.get("importance", 0.5))
            ts = float(meta.get("timestamp", 0))
            recency = 1.0 if ts == 0 else (1.0 / (1 + (time.time() - ts) / 86400))
            score = 0.5 * importance + 0.5 * recency
            if importance >= importance_threshold:
                results.append(
                    {"source": "episodic", "doc": doc, "meta": meta, "score": score}
                )
    except Exception as e:
        print(f"[ltm] Episodic query failed: {e}")

    # Sort + trim
    results = sorted(results, key=lambda r: r["score"], reverse=True)
    results = results[: max(topk_persona, topk_episodic)]

    # Build context
    ctx_lines = []
    for r in results:
        ctx_lines.append(f"[{r['source'].upper()}] {r['doc']}")

    dbg = {
        "persona_hits": sum(1 for r in results if r["source"] == "persona"),
        "episodic_hits": sum(1 for r in results if r["source"] == "episodic"),
        "persona_top": topk_persona,
        "episodic_top": topk_episodic,
    }

    print(f"[ltm] Retrieved {len(results)} memory entries:")
    for r in results:
        print(f" - [{r['source']}] score={r['score']:.2f} :: {r['doc'][:80]}")
    
    return ("\n".join(ctx_lines), dbg) if return_debug else "\n".join(ctx_lines)


# Optional hooks
def on_user_turn(user_input: str, episodic_coll):
    """
    Store user inputs into episodic memory with a timestamp.
    Skips duplicates based on normalized text.
    """
    try:
        norm = user_input.strip().lower()
        existing = episodic_coll.query(
            query_texts=[norm],
            n_results=3,
            include=["documents"],
        )

        for doc in existing.get("documents", [[]])[0]:
            if doc.strip().lower() == norm:
                print("[ltm] Skipped duplicate chunk.")
                return

        ts = time.time()
        episodic_coll.add(
            ids=[f"user-{int(ts)}"],
            documents=[user_input],
            metadatas=[{
                "timestamp": ts,
                "importance": 0.5,
                "dedup": True
            }],
        )
        print("[ltm] Added new episodic memory chunk.")

    except Exception as e:
        print(f"[ltm] Failed to store user turn: {e}")
    
def on_assistant_turn(reply: str, episodic_coll):
    try:
        reply_clean = reply.strip()
        if not reply_clean or len(reply_clean) < 10:
            print("[ltm] Skipped assistant reply: empty or too short.")
            return

        if re.fullmatch(r"\[.*?\]", reply_clean):
            print("[ltm] Skipped assistant reply: formatting artifact only.")
            return

        print(f"[ltm] Candidate assistant reply: {reply_clean[:80]}...")

        ts = time.time()
        episodic_coll.add(
            ids=[f"assistant-{int(ts)}"],
            documents=[reply_clean],
            metadatas=[{
                "timestamp": ts,
                "importance": 0.7,
                "source": "assistant"
            }],
        )
        print("[ltm] Added assistant episodic memory chunk.")
    except Exception as e:
        print(f"[ltm] Failed to store assistant turn: {e}")
