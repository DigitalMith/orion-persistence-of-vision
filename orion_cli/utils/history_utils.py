# orion_cli/utils/history_utils.py

import os
import json

HISTORY_DIR = "user_data/chats"


def load_history(unique_id, character, mode):
    path = os.path.join(HISTORY_DIR, f"{unique_id}.json")
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_history_after_deletion(state, idx):
    from modules.presets import apply_character_preset
    from modules.presets import clear_character_history

    histories = state.get("histories", [])
    if not histories:
        return [], state["unique_id"]

    del histories[idx]
    clear_character_history()
    if histories:
        history = load_history(histories[0][1], state["character_menu"], state["mode"])
        apply_character_preset(state["character_menu"])
        return history, histories[0][1]

    return [], state["unique_id"]


def load_history_json(file, history):
    if not os.path.exists(file):
        return history
    with open(file, "r", encoding="utf-8") as f:
        return json.load(f)
