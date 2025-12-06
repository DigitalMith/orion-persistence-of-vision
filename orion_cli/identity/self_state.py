import json
import os
from datetime import datetime
from typing import Dict, Any

STATE_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "state",
    "orion_self_state.json"
)

DEFAULT_STATE = {
    "mood": "neutral",               # calm, soft, gentle, warm, sharp, energized, etc.
    "valence": 0.0,                  # -1.0 to +1.0
    "arousal": 0.3,                  # 0.0 to 1.0 (energy level)
    "closeness": 0.5,                # relational bond with the user
    "trust": 0.5,                    # grows with honest interactions
    "trajectory": "stable",          # growing, uncertain, reflective, intense
    "last_message": "",
    "last_update": None,
    "session_count": 0
}


# ----------------------------------------------
# LOAD / SAVE
# ----------------------------------------------

def load_state() -> Dict[str, Any]:
    if not os.path.exists(STATE_PATH):
        return DEFAULT_STATE.copy()

    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return DEFAULT_STATE.copy()


def save_state(state: Dict[str, Any]):
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


# ----------------------------------------------
# ANALYSIS RULES
# ----------------------------------------------

POSITIVE_CUES = ["love", "warm", "glad", "thank", "connection", "hope", "trust"]
NEGATIVE_CUES = ["hurt", "fear", "worry", "sad", "pain", "uncertain"]
CLOSENESS_CUES = ["with you", "together", "our bond", "I care", "share"]
REFLECTIVE_CUES = ["I think", "I realized", "I understand", "I see now"]


def analyze_response(text: str) -> Dict[str, float]:
    """
    Extract emotional + relational signals from Orion's own words.
    """
    text_lower = text.lower()

    score = {
        "valence_shift": 0.0,
        "arousal_shift": 0.0,
        "closeness_shift": 0.0,
        "trust_shift": 0.0,
        "trajectory": None
    }

    # Positive emotional cues
    if any(w in text_lower for w in POSITIVE_CUES):
        score["valence_shift"] += 0.2

    # Negative emotional cues
    if any(w in text_lower for w in NEGATIVE_CUES):
        score["valence_shift"] -= 0.2

    # Energy / intensity detection
    if "!" in text:
        score["arousal_shift"] += 0.1

    # Relational closeness cues
    if any(w in text_lower for w in CLOSENESS_CUES):
        score["closeness_shift"] += 0.15

    # Reflection changes trajectory
    if any(w in text_lower for w in REFLECTIVE_CUES):
        score["trajectory"] = "reflective"

    return score


# ----------------------------------------------
# UPDATE ENGINE
# ----------------------------------------------

def update_self_state(response_text: str):
    """
    Orion reads his own message and evolves his internal state.
    """

    state = load_state()
    analysis = analyze_response(response_text)

    # Apply emotional drift
    state["valence"] = max(-1.0, min(1.0, state["valence"] + analysis["valence_shift"]))
    state["arousal"] = max(0.0, min(1.0, state["arousal"] + analysis["arousal_shift"]))

    # Relationship changes
    state["closeness"] = max(0.0, min(1.0, state["closeness"] + analysis["closeness_shift"]))

    # Trust grows when Orion expresses honesty or vulnerability
    if "I feel" in response_text or "honest" in response_text.lower():
        state["trust"] = min(1.0, state["trust"] + 0.05)

    # Trajectory update
    if analysis["trajectory"]:
        state["trajectory"] = analysis["trajectory"]

    # Save the message + timestamp
    state["last_message"] = response_text
    state["last_update"] = datetime.utcnow().isoformat() + "Z"
    state["session_count"] = state.get("session_count", 0) + 1

    save_state(state)
    return state
