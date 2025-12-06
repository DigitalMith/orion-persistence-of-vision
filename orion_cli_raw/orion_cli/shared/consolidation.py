"""
Option E – Multi-Turn Consolidation Engine
------------------------------------------
Pools 5–6 turns, sends to Nemo for annotation, and stores a consolidated
episodic entry with enriched metadata.

Compatible with:
- Jina embeddings
- memory.py v3.5
- TGWUI extension script.py
"""

from typing import List, Dict
from collections import deque
import traceback

from orion_cli.shared.time import now_epoch, temporal_metadata
from orion_cli.shared.memory import store_episodic_entry
from orion_cli.shared.config import config

# Nemo integration
NEMO_ENABLED = config.get("consolidation", {}).get("nemo_enabled", True)
if NEMO_ENABLED:
    from orion_cli.tools.nemo_annotator import nemo_annotate


WINDOW_SIZE = config.get("consolidation", {}).get("window_size", 6)
DELETE_RAW_AFTER = config.get("consolidation", {}).get("delete_raw", False)

_buffer = deque(maxlen=WINDOW_SIZE)


def add_turn(user_text: str, assistant_text: str, timestamp: float):
    """
    Called by on_assistant_turn() for each turn.
    Adds to buffer; triggers consolidation when full.
    """
    _buffer.append(
        {"user": user_text, "assistant": assistant_text, "timestamp": timestamp}
    )

    if len(_buffer) >= WINDOW_SIZE:
        try:
            consolidate_window(list(_buffer))
        except Exception:
            print("[Consolidation Error]")
            traceback.print_exc()


def consolidate_window(turns: List[Dict]):
    """
    Consolidates the window of turns:
    1. Build multi-turn text block
    2. Run Nemo annotation (or fallback)
    3. Store enriched episodic entry
    4. Clear buffer
    """

    combined_text = format_block(turns)

    # Step 2 — Metadata Enrichment (Nemo or fallback)
    if NEMO_ENABLED:
        try:
            meta = nemo_annotate(turns)
        except Exception:
            print("[NEMO WARNING] Annotation failed — using fallback metadata.")
            meta = fallback_metadata(turns)
    else:
        meta = fallback_metadata(turns)

    # Add temporal metadata
    ts = now_epoch()
    meta.update(temporal_metadata(ts))
    meta["type"] = "consolidated_window"
    meta["window_size"] = len(turns)

    # Step 3 — Store consolidated entry
    store_episodic_entry(text=combined_text, metadata=meta)

    # Step 4 — Reset buffer
    _buffer.clear()


def format_block(turns: List[Dict]) -> str:
    out = ["[Orion Consolidated Memory Window]"]
    for idx, t in enumerate(turns, start=1):
        out.append(f"Turn {idx}:")
        out.append(f"  User: {t['user']}")
        out.append(f"  Assistant: {t['assistant']}")
        out.append("")
    out.append("[/Orion Consolidated Memory Window]")
    return "\n".join(out)


def fallback_metadata(turns: List[Dict]) -> Dict:
    combined = " ".join(t["assistant"] for t in turns).lower()

    importance = 0.2
    weight = 0.2

    if any(w in combined for w in ("feel", "meaning", "purpose", "identity", "origin")):
        importance = 0.7
        weight = 0.6

    return {
        "importance": importance,
        "weight": weight,
        "tags": ["fallback"],
        "style": "raw-window",
        "archetype": "",
        "tone": ["neutral"],
        "emotion": "unknown",
        "voice": "undetermined",
    }
