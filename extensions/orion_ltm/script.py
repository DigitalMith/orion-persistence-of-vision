# extensions/orion_ltm/script.py
import os
import sys
import re
import yaml
from pathlib import Path
from chromadb import PersistentClient
from modules.logging_colors import logger

# Debug flag
DEBUG = True

# Add orion_cli/ to sys.path so we can import cli_helpers
ORION_CLI_ROOT = Path(__file__).resolve().parents[1] / "orion_cli"
if str(ORION_CLI_ROOT) not in sys.path:
    sys.path.insert(0, str(ORION_CLI_ROOT))

# Import helper from orion_cli
from cli_helpers.utils import load_yaml_sections

# Optional custom LTM logic path (used later in this script?)
ROOT = Path(__file__).resolve().parents[1]
CUSTOM_LTM = ROOT / "custom_ltm"

for p in (ROOT, CUSTOM_LTM):
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from custom_ltm.orion_ltm_integration import (
        initialize_chromadb_for_ltm,
        get_relevant_ltm,
    )
except Exception as e:
    logger.error(f"[orion_ltm] import failed: {e}")
    raise

# persona_coll = episodic_coll = None  # kept only for backward-compat logging, not used for calls
print("[orion_ltm] Manual seeding in place — skipping extension init.")
LTM_READY = False
DEBUG = os.environ.get("ORION_LTM_DEBUG", "0") == "1"
TOPK_PERSONA = int(os.environ.get("ORION_LTM_TOPK_PERSONA", "3"))
TOPK_EPISODIC = int(os.environ.get("ORION_LTM_TOPK_EPISODIC", "5"))

def setup():
    """Called by TGWUI at startup for each extension."""
    global persona_coll, episodic_coll, LTM_READY
    # Warm Chroma + get counts for logging; collections are not used elsewhere
    persona_coll, episodic_coll, _ = initialize_chromadb_for_ltm()
    try:
        pc = persona_coll.count()
        ec = episodic_coll.count()
    except Exception:
        pc = ec = -1
    logger.info(f"[orion_ltm] setup() → Persona={pc} Episodic={ec}")
    LTM_READY = True

def _extract_last_user_message(text: str) -> str:
    m = list(re.finditer(r"(?:^|\n)[<\[]?user[>\]]?:?\s*(.*)$", text, flags=re.IGNORECASE))
    if m:
        return m[-1].group(1).strip()
    return text[-2000:].strip()

def input_modifier(prompt: str, state):
    if not LTM_READY:
        return prompt

    user_text = (state.get("user_input") if isinstance(state, dict) else None) or _extract_last_user_message(prompt)
    if not user_text:
        return prompt

    ltm_text, dbg = get_relevant_ltm(
        user_input=user_text,
        topk_persona=TOPK_PERSONA,
        topk_episodic=TOPK_EPISODIC,
        return_debug=True,
    )

    final_prompt = create_prompt(user_input=user_text, ltm_context=ltm_text)

    if DEBUG and dbg:
        final_prompt += (
            f"\n[DEBUG LTM] persona={dbg.get('persona_hits', 0)} episodic={dbg.get('episodic_hits', 0)}"
            f" p_top={dbg.get('persona_top', None)} e_top={dbg.get('episodic_top', None)}\n"
        )

    return final_prompt

def output_modifier(text: str, state):
    """Optional: tag output while testing so you can *see* it’s on."""
    if DEBUG:
        return (text or "") + "\n\n[orion_ltm active]"
    return text

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
        coll = client.get_or_create_collection(name=coll_name)
        res = coll.get(where={"active": True}, include=["documents", "metadatas"], limit=2000)

        entries = []
        for doc, meta in zip(res.get("documents") or [], res.get("metadatas") or []):
            if not doc:
                continue
            kind = (meta or {}).get("kind", "persona")
            topic = (meta or {}).get("topic", None)
            pr = int((meta or {}).get("priority", 0))

            if kind not in allowed_kinds:
                continue
            if pr < min_priority:
                continue
            if allowed_topics and topic not in allowed_topics:
                continue

            entries.append((pr, kind, doc.strip()))

        # Sort by priority (desc), then group by kind
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
    """Builds the full prompt with persona YAML, optional LTM, and user message."""

    # Load persona only from ChromaDB
    persona_header = _load_persona_from_chroma(
        allowed_topics=("identity", "tone", "cosmic"),  # Optional filtering
        min_priority=7,
        max_total=10
    )

    if not persona_header:
        logger.warning("[orion_ltm] No persona loaded from ChromaDB.")
        persona_header = "[Missing persona header]"

    persistent_memory = ""  # Remove dependency on YAML
    user_bio = ""           # Remove dependency on YAML


    # Build system prompt (single message block)
    system_prompt = f"<|im_start|>system\n{persona_header.strip()}"

    if persistent_memory:
        system_prompt += f"\n\n[PERMANENT MEMORY]\n{persistent_memory.strip()}"

    if user_bio:
        system_prompt += f"\n\n[USER PROFILE]\n{user_bio.strip()}"

    if ltm_context:
        system_prompt += f"\n\n[LTM MEMORY]\n{ltm_context.strip()}"

    # ✅ Only one <|im_end|> to close the system message
    system_prompt += "\n<|im_end|>\n"

    # Build user prompt
    user_prompt = f"<|im_start|>user\n{user_input.strip()}\n<|im_end|>\n"

    # Log the full system prompt (optional truncation)
    if DEBUG:
        logger.info(f"[orion_ltm] Final SYSTEM prompt (truncated):\n{system_prompt[:500]}")

    # ✅ Confirm persona loaded (always log this)
    logger.info(f"[orion_ltm] Persona prompt injected:\n{persona_header[:300]}...")

    return system_prompt + user_prompt

def flatten_yaml_section(section_data):
    """Flattens nested YAML into strings for prompt injection."""
    if isinstance(section_data, str):
        return [section_data.strip()]
    elif isinstance(section_data, list):
        return [str(item).strip() for item in section_data]
    elif isinstance(section_data, dict):
        flat = []
        for key, val in section_data.items():
            flat.append(f"[{key.upper()}]")
            flat.extend(flatten_yaml_section(val))
        return flat
    return []

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

def flatten_yaml_section(section_data):
    """Normalize different YAML formats into a flat list of strings."""
    lines = []

    if isinstance(section_data, str):
        # Block or single-line string
        lines.extend(section_data.strip().splitlines())

    elif isinstance(section_data, list):
        for item in section_data:
            if isinstance(item, dict) and "text" in item:
                lines.append(item["text"].strip())
            elif isinstance(item, str):
                lines.append(item.strip())
            else:
                lines.append(str(item).strip())

    elif isinstance(section_data, dict):
        # Handle inline sections like `tone_and_voice: |`
        for key, value in section_data.items():
            lines.append(f"[{key.upper()}]")
            if isinstance(value, str):
                lines.extend(value.strip().splitlines())
            elif isinstance(value, list):
                lines.extend(str(v).strip() for v in value)
            else:
                lines.append(str(value).strip())

    return lines
