# extensions/orion_ltm/script.py
print("[orion_ltm script.py] 🟡 Starting extension load...")
print("[orion_ltm script.py] starting")

import os
import sys
import re
import yaml
from pathlib import Path
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from cli.utils.web_search_hook import handle_web_search

# Prefer colored logger if available
try:
    from modules.logging_colors import logger
except ImportError:
    import logging
    logger = logging.getLogger("orion_ltm")

BASE = Path(r"C:\Orion\text-generation-webui\user_data\models\embeddings\all-MiniLM-L6-v2\snapshots")
latest_snapshot = max(BASE.iterdir(), key=os.path.getmtime)  # pick most recent
MODEL_PATH = str(latest_snapshot)

from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
EMBED_FN = SentenceTransformerEmbeddingFunction(model_name=MODEL_PATH)

def get_embed_fn():
    model_name = os.environ.get("ORION_EMBED_MODEL", "all-MiniLM-L6-v2")
    logger.info(f"[orion_ltm] Using embedding model: {model_name}")
    return SentenceTransformerEmbeddingFunction(model_name=model_name)

EMBED_FN = get_embed_fn()

# Debugging and constants
DEBUG = os.environ.get("ORION_LTM_DEBUG", "0") == "1"
TOPK_PERSONA = int(os.environ.get("ORION_LTM_TOPK_PERSONA", "3"))
TOPK_EPISODIC = int(os.environ.get("ORION_LTM_TOPK_EPISODIC", "5"))

# Setup sys.path to include custom CLI and LTM integrations
ROOT = Path(__file__).resolve().parents[2]
CLI_ROOT = ROOT / "cli"

logger.info(f"[orion_ltm] ROOT = {ROOT}")
logger.info(f"[orion_ltm] CLI_ROOT = {CLI_ROOT}")

if not CLI_ROOT.exists():
    logger.warning(f"[orion_ltm] CLI_ROOT path does not exist: {CLI_ROOT}")

for p in (ROOT, CLI_ROOT):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
        logger.info(f"[orion_ltm] Added to sys.path: {p}")

# Import and initialize LTM
try:
    from cli.lib.orion_ltm_integration import (
        initialize_chromadb_for_ltm,
        get_relevant_ltm,
        on_user_turn,
        on_assistant_turn,
    )
    logger.info("[orion_ltm] LTM imports OK")

    # 🛠️ Initialize ChromaDB with embedding function
    initialize_chromadb_for_ltm(EMBED_FN)
    LTM_READY = True
    logger.info("[orion_ltm] ChromaDB initialized successfully.")

except Exception as e:
    logger.error(f"[orion_ltm] import/setup failed: {e}")
    raise

# Global state for collections
persona_coll = None
episodic_coll = None
# Optional: initialization hook for TGWUI
LTM_READY = False

def setup():
    global persona_coll, episodic_coll, LTM_READY
    try:
        persona_coll, episodic_coll = initialize_chromadb_for_ltm(EMBED_FN)
        LTM_READY = True
        logger.info("[orion_ltm] Extension setup complete.")
    except Exception as e:
        logger.error(f"[orion_ltm] setup failed: {e}")

def _extract_last_user_message(text: str) -> str:
    matches = list(re.finditer(r"(?:^|\n)[<\[]?user[>\]]?:?\s*(.*)$", text, re.IGNORECASE))
    return matches[-1].group(1).strip() if matches else text[-2000:].strip()

def input_modifier(modifier, state):
    if not persona_coll or not episodic_coll:
        logger.warning("[orion_ltm] Skipping input_modifier: no memory collections loaded.")
        return modifier

    # Extract user text from state or fallback to chat history
    user_text = (state.get("user_input") if isinstance(state, dict) else None) or _extract_last_user_message(modifier)
    if not user_text:
        logger.warning("[orion_ltm] No user text extracted. Skipping modifier.")
        return modifier

    # ------------------ Web Search Hook Integration ------------------
    if handle_web_search(user_text):
        logger.info("[orion_ltm] Web search hook handled this input. Skipping LTM.")
        return ""  # Skip injection

    # ------------------ Retrieve Relevant Memory ------------------
    ltm_text, dbg = get_relevant_ltm(
        user_text,
        persona_coll,
        episodic_coll,
        topk_persona=TOPK_PERSONA,
        topk_episodic=TOPK_EPISODIC,
        return_debug=True,
    )

    if not ltm_text:
        logger.info("[orion_ltm] No relevant LTM found for this input.")
        return modifier

    # ------------------ Inject <LTM> into system prompt ------------------
    ltm_block = "<LTM>\n" + ltm_text.strip() + "\n</LTM>\n"
    new_modifier = modifier

    # Insert LTM before user input if 'system_prompt' is available
    if isinstance(modifier, dict) and "system_prompt" in modifier:
        new_modifier = modifier.copy()
        new_modifier["system_prompt"] = ltm_block + modifier["system_prompt"]

        if DEBUG:
            logger.warning("[orion_ltm] SYSTEM PROMPT INJECTION (raw):\n" +
                           new_modifier["system_prompt"][:1500])  # Log partial for readability

    else:
        # Fallback: prepend entire modifier if no dict structure
        new_modifier = ltm_block + modifier

    # ------------------ Append LTM debug summary (optional) ------------------
    from datetime import datetime  # Move this up here

    if DEBUG and dbg and isinstance(new_modifier, dict) and "system_prompt" in new_modifier:
        debug_meta = (
            f"\n[DEBUG LTM] persona={dbg.get('persona_hits', 0)} "
            f"episodic={dbg.get('episodic_hits', 0)} "
            f"p_top={dbg.get('persona_top')} e_top={dbg.get('episodic_top')}\n"
        )
        with open("logs/injected_prompt_log.txt", "a", encoding="utf-8") as f:
            f.write(f"\n\n===== TURN ({datetime.now().isoformat()}) =====\n")
            f.write(new_modifier["system_prompt"] + "\n")

        new_modifier["system_prompt"] += debug_meta

    return new_modifier

def output_modifier(text: str, state):
    return (text or "") + "\n\n[orion_ltm active]" if DEBUG else text

def _load_persona_from_chroma(
    persist_dir="user_data/chroma_db",
    coll_name="orion_persona",
    allowed_kinds=("persona", "memory", "persistent"),
    allowed_topics=None,
    min_priority=5,
    max_total=20,
) -> str:
    try:
        client = PersistentClient(path=persist_dir)
        coll = client.get_or_create_collection(name=coll_name, embedding_function=EMBED_FN)
        res = coll.get(where={"active": True}, include=["documents", "metadatas"], limit=2000)

        entries = []
        for doc, meta in zip(res.get("documents") or [], res.get("metadatas") or []):
            if not doc:
                continue
            kind = meta.get("kind", "persona")
            topic = meta.get("topic")
            pr = int(meta.get("priority", 0))

            if kind not in allowed_kinds or pr < min_priority:
                continue
            if allowed_topics and topic not in allowed_topics:
                continue

            entries.append((pr, kind, doc.strip()))

        entries.sort(reverse=True)
        buckets = {"persistent": [], "persona": [], "memory": []}
        for pr, kind, text in entries[:max_total]:
            buckets.get(kind, buckets["persona"]).append(text)

        blocks = []
        if buckets["persistent"]: blocks.append("[PERMANENT]\n" + "\n".join(buckets["persistent"]))
        if buckets["persona"]:    blocks.append("[PERSONA]\n"   + "\n".join(buckets["persona"]))
        if buckets["memory"]:     blocks.append("[MEMORY]\n"    + "\n".join(buckets["memory"]))

        return "\n\n".join(blocks).strip()

    except Exception as e:
        logger.warning(f"[orion_ltm] Failed to load Chroma persona: {e}")
        return ""

def create_prompt(user_input: str, ltm_context: str = "") -> str:
    persona_header = _load_persona_from_chroma(
        allowed_topics=("identity", "tone", "cosmic"),
        min_priority=7,
        max_total=10
    )

    if not persona_header:
        logger.warning("[orion_ltm] No persona loaded from ChromaDB.")
        persona_header = "[Missing persona header]"

    system_prompt = f"<|im_start|>system\n{persona_header.strip()}"
    if ltm_context:
        system_prompt += f"\n\n[LTM MEMORY]\n{ltm_context.strip()}"
    system_prompt += "\n<|im_end|>\n"

    user_prompt = f"<|im_start|>user\n{user_input.strip()}\n<|im_end|>\n"

    if DEBUG:
        logger.info(f"[orion_ltm] Final SYSTEM prompt (truncated):\n{system_prompt[:500]}")

    logger.info(f"[orion_ltm] Persona prompt injected:\n{persona_header[:300]}...")
    return system_prompt + user_prompt

def flatten_yaml_section(section_data):
    lines = []
    if isinstance(section_data, str):
        lines.extend(section_data.strip().splitlines())
    elif isinstance(section_data, list):
        for item in section_data:
            if isinstance(item, dict) and "text" in item:
                lines.append(item["text"].strip())
            else:
                lines.append(str(item).strip())
    elif isinstance(section_data, dict):
        for key, value in section_data.items():
            lines.append(f"[{key.upper()}]")
            if isinstance(value, str):
                lines.extend(value.strip().splitlines())
            elif isinstance(value, list):
                lines.extend(str(v).strip() for v in value)
            else:
                lines.append(str(value).strip())
    return lines

def load_persona_header_from_yaml(path="user_data/persona.yaml"):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        header_lines = []
        for section in ("memory", "persona", "persistent"):
            section_data = data.get(section)
            if section_data:
                header_lines.append(f"[{section.upper()}]")
                header_lines.extend(flatten_yaml_section(section_data))

        return "\n".join(header_lines).strip()

    except Exception as e:
        logger.warning(f"[orion_ltm] Failed to load persona.yaml: {e}")
        return "[Missing persona header]"
