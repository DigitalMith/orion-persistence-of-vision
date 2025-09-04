# orion_ltm extension: inject persona + episodic LTM before the prompt.
import os, sys, re
from modules.logging_colors import logger

from modules.logging_colors import logger
logger.info("[orion_ltm] import start")

try:
    # your existing sys.path and imports…
    # from custom_ltm.orion_ltm_integration import ...
    logger.info("[orion_ltm] imports OK")
except Exception as e:
    logger.error(f"[orion_ltm] import failed: {e}")
    raise


# Add project and custom_ltm to sys.path so imports work no matter how TGWUI runs
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CUSTOM_LTM = os.path.join(PROJECT_ROOT, "custom_ltm")
for p in (PROJECT_ROOT, CUSTOM_LTM):
    if p not in sys.path:
        sys.path.insert(0, p)

from custom_ltm.orion_ltm_integration import (
    initialize_chromadb_for_ltm,
    get_relevant_ltm,
)

persona_coll = episodic_coll = None
DEBUG = os.environ.get("ORION_LTM_DEBUG", "0") == "1"
TOPK_PERSONA = int(os.environ.get("ORION_LTM_TOPK_PERSONA", "6"))
TOPK_EPISODIC = int(os.environ.get("ORION_LTM_TOPK_EPISODIC", "8"))

def setup():
    logger.info("[orion_ltm] setup() called")
    global persona_coll, episodic_coll
    persona_coll, episodic_coll = initialize_chromadb_for_ltm()
    try:
        pc = persona_coll.count()
        ec = episodic_coll.count()
    except Exception:
        pc = ec = -1
    logger.info(f"[Orion LTM] Ready. Persona={pc} Episodic={ec}")

def _extract_last_user_message(modifier: str) -> str:
    # Works with ChatML-like prompts; fallback to entire modifier if not found.
    # Looks for last occurrence of a "user" role.
    m = list(re.finditer(r"(?:^|\n)[<\[]?user[>\]]?:?\s*(.*)$", modifier, flags=re.IGNORECASE))
    if m:
        return m[-1].group(1).strip()
    return modifier[-2000:].strip()  # last 2k chars as a fallback

def input(modifier, state):
    if not persona_coll:
        return modifier

    # Prefer state["user_input"] if TGWUI provides it, else regex fallback.
    user_text = (state.get("user_input") if isinstance(state, dict) else None) or _extract_last_user_message(modifier)
    if not user_text:
        return modifier

    ctx, dbg = get_relevant_ltm(
        user_text,
        persona_coll,
        episodic_coll,
        topk_persona=TOPK_PERSONA,
        topk_episodic=TOPK_EPISODIC,
        return_debug=True,
    )
    if not ctx:
        return modifier

    ltm_block = "<LTM>\n" + ctx.strip() + "\n</LTM>\n"
    new_modifier = ltm_block + modifier

    if DEBUG and dbg:
        new_modifier += (
            "\n[DEBUG LTM] "
            f"persona={dbg.get('persona_hits', 0)} episodic={dbg.get('episodic_hits', 0)} "
            f"p_top={dbg.get('persona_top', None)} e_top={dbg.get('episodic_top', None)}\n"
        )
    return new_modifier

def output(output, state):
    # Optional: write new turns to episodic here later.
    return (output or "") + "\n\n[orion_ltm active]"
