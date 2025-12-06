# state_manager.py — FINAL NON-RECURSIVE VERSION

import os
import json
from pathlib import Path

STATE_DIR = Path(__file__).resolve().parent / "state"
STATE_FILE = STATE_DIR / "self_state.json"

DEFAULT_STATE = {
    "valence": 0.0,
    "arousal": 0.0,
    "closeness": 0.0,
    "trust": 0.0,
    "trajectory": "stable",
}


def _ensure_state_file():
    """
    Ensures the directory and state file exist.
    DOES NOT call save_state() to avoid recursion.
    """
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)

        if not STATE_FILE.exists():
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_STATE, f, indent=2)

    except Exception as e:
        raise RuntimeError(
            f"[Orion-State] Failed to initialize state file: {e}"
        )


def save_state(state: dict):
    """
    Saves current state to disk.
    DOES NOT call _ensure_state_file() to avoid recursion.
    """
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        raise RuntimeError(f"[Orion-State] Failed to save state: {e}")


def load_state() -> dict:
    """
    Loads state from disk. Recreates cleanly if corrupted.
    """
    _ensure_state_file()

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        save_state(DEFAULT_STATE)
        return DEFAULT_STATE


def get_state_summary() -> str:
    """
    Returns a formatted human-readable summary of Orion's self-state.
    Used inside identity_system_prompt.
    """
    state = load_state()

    return (
        f"Valence: {state['valence']}\n"
        f"Arousal: {state['arousal']}\n"
        f"Closeness: {state['closeness']}\n"
        f"Trust: {state['trust']}\n"
        f"Trajectory: {state['trajectory']}"
    )
