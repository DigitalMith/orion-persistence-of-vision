# orion_cli/utils/ltm_utils.py
import yaml
from pathlib import Path
import time
from orion_cli.utils.embedding import estimate_tone_and_tags
from orion_cli.utils.embedding import load_ltm_config

_buffer = []

CONFIG_PATH = Path(__file__).resolve().parent.parent / "data" / "ltm_config.yaml"
DEFAULTS = {
    "topk_persona": 3,
    "topk_episodic": 6,
    "importance_threshold": 0.6,
    "min_score": 0.7,
}

def load_ltm_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
            return config.get("ltm", DEFAULTS)
    except Exception as e:
        print(f"[ltm] ⚠️ Failed to load config: {e}")
        return DEFAULTS


def get_relevant_ltm(
    user_input: str,
    persona_coll,
    episodic_coll,
    *,
    return_debug: bool = False
) -> tuple[str, dict]:
    cfg = load_ltm_config()
    topk_persona = cfg["topk_persona"]
    topk_episodic = cfg["topk_episodic"]
    importance_threshold = cfg["importance_threshold"]
    min_score = cfg["min_score"]
    tone_boosts = cfg.get("boosts", {}).get("tone", {})
    tag_boosts = cfg.get("boosts", {}).get("tags", {})

    results = []

    try:
        p_res = persona_coll.query(
            query_texts=[user_input],
            n_results=topk_persona,
            include=["metadatas", "documents"]
        )
        results.extend(
            {
                "source": "persona",
                "doc": p_res["documents"][0][i],
                "meta": p_res["metadatas"][0][i],
                "score": 1.0,
            }
            for i in range(len(p_res.get("ids", [[]])[0]))
        )
    except Exception as e:
        print(f"[ltm] Persona query failed: {e}")

    try:
        e_res = episodic_coll.query(
            query_texts=[user_input],
            n_results=topk_episodic * 2,
            include=["documents", "metadatas", "distances"]
        )
        for i in range(len(e_res.get("ids", [[]])[0])):
            doc = e_res["documents"][0][i]
            meta = e_res["metadatas"][0][i]
            distance = e_res["distances"][0][i]
            similarity = 1 - distance
            importance = float(meta.get("importance", 0))

            # Boost score based on tone or tags
            tone = (meta.get("tone") or "").lower()
            tags = [t.strip().lower() for t in str(meta.get("tags", "")).split(",")]

            boost = tone_boosts.get(tone, 0.0)
            boost += sum(tag_boosts.get(tag, 0.0) for tag in tags)

            similarity = min(similarity + boost, 1.0)

            if similarity >= min_score or importance >= importance_threshold:
                results.append({
                    "source": "episodic",
                    "doc": doc,
                    "meta": meta,
                    "score": round(similarity, 4)
                })
    except Exception as e:
        print(f"[ltm] Episodic query failed: {e}")

    results = sorted(results, key=lambda r: r["score"], reverse=True)
    results = results[: max(topk_persona, topk_episodic)]

    ctx_lines = [f"[{r['source'].upper()}] {r['doc']}" for r in results]

    dbg = {
        "persona_hits": sum(1 for r in results if r["source"] == "persona"),
        "episodic_hits": sum(1 for r in results if r["source"] == "episodic"),
        "persona_top": topk_persona,
        "episodic_top": topk_episodic,
    }

    return ("\n".join(ctx_lines), dbg) if return_debug else ("\n".join(ctx_lines), {})
    
def live_pooled_store(user_input: str, assistant_reply: str, episodic_collection):
    from datetime import datetime

    config = load_ltm_config()
    if not config.get("live_pooled_ingest"):
        return

    turns = config.get("pooling_turns", 3)

    _buffer.append({"user": user_input.strip(), "assistant": assistant_reply.strip()})

    if len(_buffer) < turns:
        return  # not ready

    try:
        pooled_text = "\n".join(f"User: {p['user']}\nAssistant: {p['assistant']}" for p in _buffer)
        tone, tags = estimate_tone_and_tags(pooled_text)

        timestamp = time.time()
        episodic_collection.add(
            ids=[f"pooled-{int(timestamp)}"],
            documents=[pooled_text],
            metadatas=[{
                "timestamp": timestamp,
                "importance": 0.8,
                "source": "assistant",
                "tags": tags,
                "tone": tone,
                "pooled": True
            }]
        )
        print(f"[ltm] 🔄 Live pooled memory added: tone={tone}, tags={','.join(tags)}")
    except Exception as e:
        print(f"[ltm] Live pooled ingestion failed: {e}")
    finally:
        _buffer.clear()