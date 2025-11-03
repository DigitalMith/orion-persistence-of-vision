# cli/lib/orion_ltm_integration.py

import re
import time
import os

from orion_cli.utils.ltm_utils import get_relevant_ltm
from orion_cli.utils.chroma_utils import _get_or_create, EMBED_FN

# ⛔ Removed: from orion_cli.core.ltm import get_client  (caused circular import)

# Centralized config for embedding model
MODEL_NAME = os.environ.get("ORION_EMBED_MODEL", "intfloat/e5-large-v2")


# Constants for collection names
COLL_PERSONA = "persona"
COLL_EPISODIC_RAW = "orion_episodic_raw_ltm"
COLL_EPISODIC_SENT = "orion_episodic_ltm"


def initialize_chromadb_for_ltm(embed_fn=EMBED_FN):
    """
    Initialize ChromaDB collections for persona and episodic memory.
    Ensures collections exist and are bound to the embedding function.
    """
    # 🧠 Correct import — get_client now lives in utils.chroma_utils
    from orion_cli.utils.chroma_utils import get_client

    embed_fn = embed_fn or EMBED_FN

    client = get_client()
    persona = _get_or_create(client, name=COLL_PERSONA, embed_fn=embed_fn)
    episodic = _get_or_create(client, name=COLL_EPISODIC_SENT, embed_fn=embed_fn)

    print("[ltm] ChromaDB initialized: persona + episodic collections ready")
    return client, {"persona": persona, "episodic": episodic}

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
            metadatas=[{"timestamp": ts, "importance": 0.5, "dedup": True}],
        )
        print("[ltm] Added new episodic memory chunk.")

    except Exception as e:
        print(f"[ltm] Failed to store user turn: {e}")


def on_assistant_turn(reply: str, episodic_coll, last_user_input: str = None):
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

        # ✅ Live pooled LTM
        if last_user_input:
            try:
                from orion_cli.utils.ltm_utils import live_pooled_store
                live_pooled_store(last_user_input, reply_clean)
            except Exception as e:
                print(f"[ltm] Live pooled ingestion failed: {e}")

    except Exception as e:
        print(f"[ltm] Failed to store assistant turn: {e}")
