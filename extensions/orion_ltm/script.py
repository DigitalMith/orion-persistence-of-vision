# C:\Orion\text-generation-webui\extensions\orion_ltm\script.py

from pathlib import Path
import yaml
from modules import chat
from modules.logging_colors import logger
from orion_cli.utils.config import get_config
from orion_cli.shared.memory import on_user_turn, on_assistant_turn

# === Global State ===
pooled_buffer = []
_EMBED_READY = False
_persona = _episodic = None

# Load configuration safely
try:
    cfg = get_config()
except Exception as e:
    logger.warning(f"[orion_ltm] ⚠️ Failed to load config: {e}")
    cfg = {"debug_enabled": False, "debug_show_recall": False}

# === Optional Debug Recall Snapshot ===
# Only runs if explicitly enabled in config.yaml
if cfg.get("debug_enabled") and cfg.get("debug_show_recall"):
    try:
        print("\n[DEBUG] === Orion LTM Recall Snapshot ===")

        # Lazy import to avoid circulars
        from orion_cli.utils.chroma_utils import get_client

        client = get_client()
        persona_coll = client.get_or_create_collection("persona")
        episodic_coll = client.get_or_create_collection("orion_episodic_ltm")

        persona_docs = persona_coll.get(limit=3).get("documents", [])
        episodic_docs = episodic_coll.get(limit=3).get("documents", [])

        print("\n[DEBUG] --- Persona Recall ---")
        for i, d in enumerate(persona_docs[:3]):
            print(f"[{i}] {d[:120]}...")

        print("\n[DEBUG] --- Episodic Recall ---")
        for i, d in enumerate(episodic_docs[:3]):
            print(f"[{i}] {d[:120]}...")

        print("[DEBUG] ==========================\n")
    except Exception as e:
        logger.warning(f"[orion_ltm] ⚠️ Debug recall failed: {e}")


def _debug(msg: str):
    """Print debug logs only if enabled in config."""
    try:
        cfg = get_config()
        if cfg.get("debug", {}).get("enabled"):
            logger.info(f"[DEBUG] {msg}")
    except Exception:
        pass


def load_ltm_config():
    config_path = (
        Path(__file__).resolve().parent / "orion_cli" / "data" / "ltm_config.yaml"
    )
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
    global get_relevant_ltm, on_user_turn, on_assistant_turn  # ensure global linkage

    try:
        from orion_cli.utils.embedding import EMBED_FN
        from orion_cli.orion_ltm_integration import (
            initialize_chromadb_for_ltm,
            get_relevant_ltm,
        )
        from orion_cli.shared.memory import on_user_turn, on_assistant_turn

        # 🧠 initialize_chromadb_for_ltm returns (persona, episodic)
        _persona, _episodic = initialize_chromadb_for_ltm(EMBED_FN)

        _EMBED_READY = True
        logger.info(
            "[orion_ltm] ✅ setup() completed: episodic and persona initialized."
        )
        logger.debug(
            "[orion_ltm] LTM functions and shared memory hooks loaded successfully."
        )
    except Exception as e:
        logger.error(f"[orion_ltm] ❌ setup() failed: {e}")


def teardown():
    """Optional cleanup hook."""
    global _INITIALIZED
    if _INITIALIZED:
        _debug("Tearing down LTM collections (no persistence affected).")
        _INITIALIZED = False


def before_chat_input(text):
    """Handle user input before chat generation (store to episodic)."""
    try:
        if _episodic:
            from orion_cli.shared.memory import on_user_turn

            on_user_turn(text, _episodic)
            _debug("User input stored to episodic memory.")
        else:
            _debug("Episodic collection not available at input time.")
    except Exception as e:
        logger.warning(f"[orion_ltm] Failed to process user input: {e}")


def after_chat_output(reply, last_user_input=None):
    """Handle assistant output after generation (store to episodic)."""
    try:
        if _episodic:
            from orion_cli.shared.memory import on_assistant_turn

            on_assistant_turn(reply, _episodic, last_user_input)
            _debug("Assistant reply stored to episodic memory.")
        else:
            _debug("Episodic collection not available at output time.")
    except Exception as e:
        logger.warning(f"[orion_ltm] Failed to store assistant turn: {e}")


def _inject_ltm_into_state_sys_prompt(state, text=None):
    if not (
        _EMBED_READY
        and get_relevant_ltm
        and _persona
        and _episodic
        and isinstance(state, dict)
    ):
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
        structured_memory.append(
            "\n".join(
                f"- {line}"
                for line in memory_text.split("\n")
                if line.startswith("[PERSONA]")
            )
        )

    if "episodic_hits" in dbg and dbg["episodic_hits"]:
        structured_memory.append("### [EPISODIC MEMORY]")
        structured_memory.append(
            "\n".join(
                f"- {line}"
                for line in memory_text.split("\n")
                if line.startswith("[EPISODIC]")
            )
        )

    if structured_memory:
        sys_prompt = (
            f"{sys_prompt}\n\n[LTM CONTEXT]\n" + "\n".join(structured_memory).strip()
        )

    state["system_prompt"] = sys_prompt
    return state


def _inject_ltm_into_state_sys_prompt(state, text=None):
    # No-op fallback if not using special LTM injections
    return state


def custom_generate_chat_prompt(user_input, state, **kwargs):
    """Official TGWUI hook: adjust state/system_prompt then delegate."""
    text = (
        user_input
        if isinstance(user_input, str)
        else (getattr(user_input, "text", "") or "")
    )
    state = dict(state or {})
    state = _inject_ltm_into_state_sys_prompt(state, text)
    return chat.generate_chat_prompt(user_input, state, **kwargs)


def output_modifier(text, state):
    """Persist assistant replies as episodic memory (best-effort)."""
    try:
        reply = (text or "").strip()
        query = (state.get("context") or "").strip()

        if reply and len(reply.split()) >= 10:
            on_assistant_turn(reply, _episodic, last_user_input=query)
    except Exception as e:
        print(f"[orion_ltm] output_modifier failed: {e}")
    return text


# Ensure memory collections are initialized on extension load
try:
    setup()
except Exception as e:
    logger.error(f"[orion_ltm] Setup failed during extension load: {e}")
