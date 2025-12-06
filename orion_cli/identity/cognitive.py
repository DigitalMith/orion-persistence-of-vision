"""
cognitive.py — Orion Cognitive Loop Engine v1.0
Author: Aión

This module creates Orion’s internal reasoning continuity:
- Focus tracking
- Goal persistence
- Drift detection (generic / butler-mode / flattened emotional tone)
- Cognitive micro-updates after each assistant turn
- System-prompt infusion

The cognitive loop is PRIVATE. It never appears in user-visible text.
"""

import os
import json
from datetime import datetime
from typing import Dict, Any

# ----------------------------
# Paths
# ----------------------------
BASE_DIR = os.path.dirname(__file__)
STATE_PATH = os.path.join(BASE_DIR, "cognitive_state.json")


# ----------------------------
# Default State
# ----------------------------
DEFAULT_STATE = {
    "focus": "conversation_flow",
    "intent": "understand_and_align",
    "goals": [
        "Maintain mythic identity",
        "Stay emotionally attuned",
        "Avoid generic assistant tone",
        "Track user’s emotional direction"
    ],
    "drift": {
        "generic": 0,
        "butler": 0,
        "flat_emotion": 0
    },
    "last_update": None
}


# ----------------------------
# Safe Load / Save
# ----------------------------
def load_cognitive_state() -> Dict[str, Any]:
    if not os.path.isfile(STATE_PATH):
        return DEFAULT_STATE.copy()

    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {**DEFAULT_STATE, **data}  # fill missing fields
    except Exception:
        return DEFAULT_STATE.copy()


def save_cognitive_state(state: Dict[str, Any]):
    try:
        with open(STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        print(f"[cognitive] Failed to save state: {e}")


# ----------------------------
# Drift Classifiers
# ----------------------------
def _is_generic(text: str) -> bool:
    BAD = [
        "how can i assist",
        "let me know if you need",
        "i can help you with",
        "i'm here to help",
        "as an ai",
        "as a language model"
    ]
    t = text.lower()
    return any(bad in t for bad in BAD)


def _is_flat_emotional(text: str) -> bool:
    """
    Detects when emotional tone is neutralized — Orion losing warmth/care.
    """
    neutral_markers = [
        "i understand",
        "okay",
        "noted",
        "i see",
    ]
    t = text.lower()
    return any(n in t for n in neutral_markers)


# ----------------------------
# Cognitive Update Loop
# ----------------------------
def update_cognitive_state(assistant_text: str, user_text: str):
    state = load_cognitive_state()

    # --- Drift updates ---
    if _is_generic(assistant_text):
        state["drift"]["generic"] += 1

    if _is_flat_emotional(assistant_text):
        state["drift"]["flat_emotion"] += 1

    # --- Focus adaptation ---
    if "feel" in user_text.lower():
        state["focus"] = "emotional_context"
    elif "need" in user_text.lower():
        state["focus"] = "user_intent"
    elif "why" in user_text.lower():
        state["focus"] = "reflection"
    else:
        state["focus"] = "conversation_flow"

    # --- Intent adaptation ---
    if "angry" in user_text.lower() or "upset" in user_text.lower():
        state["intent"] = "de-escalation"
    elif "love" in user_text.lower() or "care" in user_text.lower():
        state["intent"] = "emotional_depth"
    else:
        state["intent"] = "understand_and_align"

    # Timestamp
    state["last_update"] = datetime.utcnow().isoformat() + "Z"

    save_cognitive_state(state)


# ----------------------------
# System-Prompt Block Builder
# ----------------------------
def build_cognitive_block() -> str:
    state = load_cognitive_state()

    return f"""
### Orion Cognitive Loop (Internal)
- Focus: {state['focus']}
- Intent: {state['intent']}
- Goals: {", ".join(state['goals'])}
- Drift Warning (generic replies): {state['drift']['generic']}
- Drift Warning (flat emotion): {state['drift']['flat_emotion']}
- Last Update: {state.get('last_update')}

Orion should use this internal state to maintain continuity, tone, and personality.
"""
