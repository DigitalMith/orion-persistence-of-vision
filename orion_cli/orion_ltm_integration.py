# cli/lib/orion_ltm_integration.py

import os

from orion_cli.utils.config import get_config
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
    # --- Disable Chroma telemetry globally ---
    try:
        import chromadb.telemetry.client as tele

        tele.capture = lambda *args, **kwargs: None
    except Exception:
        pass
    # -----------------------------------------

    # 🧠 Correct import — get_client now lives in utils.chroma_utils
    from orion_cli.utils.chroma_utils import get_client

    embed_fn = embed_fn or EMBED_FN

    client = get_client()
    persona = _get_or_create(client, name=COLL_PERSONA, embed_fn=embed_fn)
    episodic = _get_or_create(client, name=COLL_EPISODIC_SENT, embed_fn=embed_fn)

    return persona, episodic


def get_relevant_ltm(
    query,
    persona_coll,
    episodic_coll,
    topk_persona=5,
    topk_episodic=10,
    importance_threshold=0.6,
    return_debug=False,
):
    persona_hits = persona_coll.query(
        query_texts=[query], n_results=topk_persona, include=["documents", "metadatas"]
    )
    episodic_hits = episodic_coll.query(
        query_texts=[query], n_results=topk_episodic, include=["documents", "metadatas"]
    )

    # === 🧩 Debug Recall Hook (Smart Mode) ===
    cfg = get_config()
    dbg_cfg = cfg.get("debug", {})

    if dbg_cfg.get("enabled") and dbg_cfg.get("show_recall"):
        persona_docs = persona_hits.get("documents", [[]])[0]
        persona_metas = persona_hits.get("metadatas", [[]])[0]
        persona_scores = persona_hits.get("distances", [[]])[0]

        episodic_docs = episodic_hits.get("documents", [[]])[0]
        episodic_metas = episodic_hits.get("metadatas", [[]])[0]
        episodic_scores = episodic_hits.get("distances", [[]])[0]

        short_mode = dbg_cfg.get("short_descriptions", False)

        def summarize_hits(docs, metas, scores, label):
            print(f"\n[DEBUG] === {label} Recall ===")
            if not docs:
                print("No results.")
                return

            for i, (d, m, s) in enumerate(zip(docs[:3], metas[:3], scores[:3])):
                tone = m.get("tone", "")
                emotion = m.get("emotion", "")
                topic = m.get("topic", "")
                score = 1 - float(s) if isinstance(s, (int, float)) else None
                match_str = f"{score:.3f}" if score is not None else "n/a"

                if short_mode:
                    # 🍭 Compact: single-line summary
                    summary = f"[{i}] ({match_str}) {topic or 'untitled'}"
                    extras = []
                    if tone:
                        extras.append(f"tone={tone}")
                    if emotion:
                        extras.append(f"emotion={emotion}")
                    if extras:
                        summary += " [" + ", ".join(extras) + "]"
                    print(summary)
                else:
                    # 🍫 Full: verbose recall
                    print(f"[{i}] ({match_str}) {d[:140]}...")
                    meta_str = ", ".join(
                        f"{k}={v}"
                        for k, v in {
                            "tone": tone,
                            "emotion": emotion,
                            "topic": topic,
                        }.items()
                        if v
                    )
                    if meta_str:
                        print(f"     ↳ {meta_str}")

        summarize_hits(persona_docs, persona_metas, persona_scores, "Persona")
        summarize_hits(episodic_docs, episodic_metas, episodic_scores, "Episodic")
        print("\n[DEBUG] =========================\n")

    # === Filtering phase ===
    def filter_hits(hits):
        return [
            (doc, meta)
            for doc, meta in zip(
                hits.get("documents", [[]])[0], hits.get("metadatas", [[]])[0]
            )
            if meta.get("importance", 0.5) >= importance_threshold
        ]

    persona_filtered = filter_hits(persona_hits)
    episodic_filtered = filter_hits(episodic_hits)

    lines = []
    for doc, _ in persona_filtered:
        lines.append(f"[PERSONA] {doc}")
    for doc, _ in episodic_filtered:
        lines.append(f"[EPISODIC] {doc}")

    dbg = {"persona_hits": persona_filtered, "episodic_hits": episodic_filtered}

    result = "\n".join(lines).strip()
    return (result, dbg) if return_debug else result
