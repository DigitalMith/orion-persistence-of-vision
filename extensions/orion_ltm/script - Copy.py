# C:\Orion\text-generation-webui\extensions\orion_ltm\script.py

from pathlib import Path
import yaml
from uuid import uuid4
from orion_cli.utils.embedding import embed
from orion_cli.orion_ltm_integration import episodic_collection  # adjust as needed
from modules import chat
from modules.logging_colors import logger

pooled_buffer = []

try:
    from orion_cli.orion_ltm_integration import (
        initialize_chromadb_for_ltm,
        get_relevant_ltm,
        on_user_turn,
        on_assistant_turn,
    )
except Exception as e:
    initialize_chromadb_for_ltm = get_relevant_ltm = None
    def on_user_turn(*a, **k): pass
    def on_assistant_turn(*a, **k): pass
    logger.warning(f"[orion_ltm] LTM back-end not available yet: {e}")

_EMBED_READY = False
_persona = _episodic = None

def load_ltm_config():
    config_path = Path(__file__).resolve().parent / "orion_cli" / "data" / "ltm_config.yaml"
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
            return cfg.get("ltm", {})
    except Exception as e:
        print(f"[LTM] Failed to load config: {e}")
        return {}
        
def estimate_tone_and_tags(text: str) -> dict:
    # You can replace this with GPT or sentiment model later
    tone = "neutral"
    tags = ["memory", "pooled"]
    if any(word in text.lower() for word in ["regret", "sad", "lonely"]):
        tone = "somber"
    elif any(word in text.lower() for word in ["courage", "fight", "will"]):
        tone = "defiant"
    elif any(word in text.lower() for word in ["beauty", "soul", "stars"]):
        tone = "poetic"
    return {
        "tone": tone,
        "tags": ",".join(tags),
        "importance": 0.7,
    }
    
def setup():
    """Initialize ChromaDB collections for persona and episodic memory."""
    global _EMBED_READY, _persona, _episodic
    try:
        from orion_cli.utils.embedding import EMBED_FN
        _, collections = initialize_chromadb_for_ltm(EMBED_FN)
        _persona = collections["persona"]
        _episodic = collections["episodic"]
        _EMBED_READY = True
        logger.info("[orion_ltm] ✅ setup() completed: episodic and persona initialized.")
    except Exception as e:
        logger.error(f"[orion_ltm] ❌ setup() failed: {e}")

def _inject_ltm_into_state_sys_prompt(state):
    if not (_EMBED_READY and get_relevant_ltm and _persona and _episodic and isinstance(state, dict)):
        return state

    query = (state.get("context") or "").strip()
    if not query:
        return state

    # Store the original user turn into episodic memory
    try:
        on_user_turn(query, _episodic)
    except Exception:
        logger.debug("[orion_ltm] Failed to store user turn to episodic memory")

    try:
        memory_text, dbg = get_relevant_ltm(
            query,
            _persona,
            _episodic,
            topk_persona=int(state.get("orion_topk_persona", 5)),
            topk_episodic=int(state.get("orion_topk_episodic", 10)),
            return_debug=True,
            importance_threshold=0.6,  # 🔧 STRONGER FILTERING
        )
    except Exception as e:
        logger.debug(f"[orion_ltm] get_relevant_ltm failed: {e}")
        return state

    if not memory_text:
        return state

    # Inject structured LTM into prompt
    sys_prompt = (state.get("system_prompt") or "").strip()

    structured_memory = []
    if "persona_hits" in dbg and dbg["persona_hits"]:
        structured_memory.append("### [PERSONA MEMORY]")
        structured_memory.append("\n".join(f"- {line}" for line in memory_text.split("\n") if line.startswith("[PERSONA]")))

    if "episodic_hits" in dbg and dbg["episodic_hits"]:
        structured_memory.append("### [EPISODIC MEMORY]")
        structured_memory.append("\n".join(f"- {line}" for line in memory_text.split("\n") if line.startswith("[EPISODIC]")))

    if structured_memory:
        sys_prompt = f"{sys_prompt}\n\n[LTM CONTEXT]\n" + "\n".join(structured_memory).strip()

    state["system_prompt"] = sys_prompt
    return state


def custom_generate_chat_prompt(user_input, state, **kwargs):
    """Official TGWUI hook: adjust state/system_prompt then delegate."""
    text = user_input if isinstance(user_input, str) else (getattr(user_input, "text", "") or "")
    state = dict(state or {})
    state = _inject_ltm_into_state_sys_prompt(state, text)
    return chat.generate_chat_prompt(user_input, state, **kwargs)

def output_modifier(text, state):
    """Persist assistant replies as episodic memory (best-effort)."""
    try:
        reply = (text or "").strip()
        if reply and len(reply.split()) >= 10:
            on_assistant_turn(reply, _episodic)
    except Exception:
        pass
    return text

# Ensure memory collections are initialized on extension load
try:
    setup()
except Exception as e:
    logger.error(f"[orion_ltm] Setup failed during extension load: {e}")