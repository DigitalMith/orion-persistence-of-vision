# orion_cli/utils/config.py

import os
import yaml
from pathlib import Path

# === Default config values ===
_CONFIG_LOADED = False
_cached_cfg = None
_DEFAULTS = {
    "embed_model": "intfloat/e5-large-v2",
    "ltm": {
        "persona_collection": "persona",
        "episodic_collection": "orion_episodic_ltm",
    },
}

CONFIG_PATH = Path("orion_cli/data/config.yaml")
LTM_CONFIG_PATH = Path("orion_cli/data/ltm_config.yaml")


def _load_yaml(path: Path):
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _merge(base: dict, override: dict):
    result = base.copy()
    for k, v in override.items():
        if isinstance(v, dict) and k in result:
            result[k] = _merge(result[k], v)
        else:
            result[k] = v
    return result


def get_config():
    global _CONFIG_LOADED, _cached_cfg

    # ✅ Return cached config if already loaded
    if _CONFIG_LOADED and _cached_cfg:
        return _cached_cfg

    base = _DEFAULTS.copy()
    user_cfg = _load_yaml(CONFIG_PATH)
    ltm_cfg = _load_yaml(LTM_CONFIG_PATH)

    # Optional environment override
    model_env = os.getenv("ORION_EMBED_MODEL")
    if model_env:
        base["embed_model"] = model_env

    base = _merge(base, user_cfg)
    base["ltm"] = _merge(base.get("ltm", {}), ltm_cfg.get("ltm", {}))

    # ✅ Mark as cached
    _CONFIG_LOADED = True
    _cached_cfg = base

    print("[CONFIG] get_config() loaded successfully")
    return base
