"""
Nemo Annotator (Stub)
---------------------
Optional: If annotator is disabled, returns None.
"""

from .config import get_config

_CFG = get_config()
_RAW = _CFG.raw
_LTM = _RAW.get("ltm", {}) if isinstance(_RAW, dict) else {}

ANNOTATOR_ENABLED = config.get("ltm", {}).get("annotator", "nemo") == "nemo"
ANNOTATOR_ENDPOINT = config.get("ltm", {}).get(
    "annotator_endpoint", "http://127.0.0.1:5002"
)

ANNOTATOR_ENABLED = _LTM.get("annotator", "nemo") == "nemo"
ANNOTATOR_ENDPOINT = _LTM.get("annotator_endpoint", "http://127.0.0.1:5002")

def annotate_window(turn_window):
    """
    turn_window: list of {user, assistant, timestamp}
    Returns metadata dict or None if Nemo disabled.
    """
    if not ANNOTATOR_ENABLED:
        return None

    # Will send prompt to Nemo later — for now, return placeholder metadata.
    return {"metadata": "placeholder"}
