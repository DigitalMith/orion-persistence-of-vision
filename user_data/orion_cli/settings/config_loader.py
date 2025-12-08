"""
config_loader.py — Unified configuration system for Orion CLI (CNS 4.0)

Responsibilities:
    • Load default config from orion_cli/data/default_config.yaml
    • Load user-specific config from user_data/orion/data/config.yaml (if present)
    • Apply ORION_* environment variable overrides
    • Validate merged config against JSON schema
    • Return typed OrionConfig object
    • Cache results for entire process lifetime

Design:
    - Strict validation: malformed configs raise clear RuntimeError
    - Missing user config is allowed (defaults only)
    - Optional fields fall back to defaults automatically
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

from pydantic import BaseModel, Field, ValidationError

from orion_cli.shared.paths import (
    DEFAULT_CONFIG_PATH,
    SCHEMA_PATH,
    USER_CONFIG_PATH,
)
from orion_cli.shared.utils import (
    read_yaml,
    read_json,
    merge_dicts,
    require,
)


# -------------------------------------------------------------
# Pydantic Configuration Model
# -------------------------------------------------------------

class DebugSettings(BaseModel):
    enabled: bool = False
    logic: bool = False
    cognitive: bool = False
    show_recall: bool = False
    episodic_recall: bool = False
    episodic_store: bool = False
    short_descriptions: bool = False
    
class OrionConfig(BaseModel, extra="ignore"):
    """
    Unified configuration object for Orion CNS.
    Unknown fields in config.yaml are safely ignored.
    """

    # --- Chroma + Embeddings ---
    chroma_path: Path = Field(
        default=Path("user_data/Chroma-DB"),
        description="Directory where ChromaDB persistent data is stored."
    )

    embedding_model: str = Field(
        default="jinaai/jina-embeddings-v2-base-en",
        description="Model identifier for the embedding system."
    )

    embedding_dim: int = Field(
        default=768,
        description="Expected embedding dimension for the model."
    )

    # --- Persona settings ---
    class PersonaSettings(BaseModel):
        rigidity: float = 0.5

    persona: PersonaSettings = PersonaSettings()

    # --- LTM settings ---
    class LTMSettings(BaseModel, extra="ignore"):
        topk_persona: int = 5
        topk_episodic: int = 10
        importance_threshold: float = 0.0
        min_score: float = 0.0
        pooling_turns: int = 3
        boosts: dict = {}

    ltm: LTMSettings = LTMSettings()

    # --- Debug settings ---
    class DebugSettings(BaseModel, extra="ignore"):
        enabled: bool = False
        logic: bool = False
        cognitive: bool = False
        show_recall: bool = False
        episodic_recall: bool = False
        episodic_store: bool = False
        short_descriptions: bool = True

    debug: DebugSettings = DebugSettings()
    default_factory=DebugSettings

    """
    CNS 4.0 unified configuration object.
    Additional fields can be added here as the system evolves.
    """

    # Paths
    chroma_path: Path = Field(
        default=None,
        description="Directory where ChromaDB persistent data resides."
    )

    # Embedding system
    embedding_model: str = Field(
        default="jinaai/jina-embeddings-v2-base-en",
        description="Embedding model identifier."
    )

    embedding_dim: int = Field(
        default=768,
        description="Expected embedding vector dimension."
    )

    # Behavior options
    debug_mode: bool = Field(
        default=False,
        description="Enable verbose debug output for development."
    )

    class Config:
        extra = "forbid"  # No unknown keys allowed


# -------------------------------------------------------------
# Internal helpers
# -------------------------------------------------------------

def _load_default_config() -> Dict[str, Any]:
    """Load default_config.yaml (required)."""
    data = read_yaml(Path(DEFAULT_CONFIG_PATH))
    require(data is not None, f"Default config not found at: {DEFAULT_CONFIG_PATH}")
    return data


def _load_user_config() -> Dict[str, Any]:
    """Load user config if present; otherwise return empty dict."""
    config_path = Path(USER_CONFIG_PATH)
    if config_path.exists():
        data = read_yaml(config_path)
        require(
            isinstance(data, dict),
            f"User config exists but is invalid YAML: {config_path}"
        )
        return data
    return {}  # no user config → safe fallback


def _env_overrides() -> Dict[str, Any]:
    """
    Collect ORION_* environment variables.
    e.g., ORION_EMBEDDING_DIM=768 → {"embedding_dim": 768}
    """
    prefix = "ORION_"
    out: Dict[str, Any] = {}

    for key, value in os.environ.items():
        if key.startswith(prefix):
            field = key[len(prefix):].lower()
            out[field] = value
    return out


def _validate_schema(data: Dict[str, Any]) -> None:
    """
    Validate the merged configuration against schema.json.
    Only structural validation occurs here; Pydantic will validate types.
    """
    schema = read_json(Path(SCHEMA_PATH))
    require(
        isinstance(schema, dict),
        f"Schema file missing or invalid: {SCHEMA_PATH}"
    )

    required = schema.get("required", [])
    for key in required:
        require(
            key in data,
            f"Missing required config key: '{key}'"
        )


# -------------------------------------------------------------
# Public API
# -------------------------------------------------------------

@lru_cache(maxsize=1)
def get_config() -> OrionConfig:
    """
    Load, merge, validate, and return the unified OrionConfig object.

    Order of precedence:
        1. default_config.yaml
        2. user config (if exists)
        3. ORION_* environment overrides

    Validation:
        - Schema enforces required keys
        - Pydantic enforces types & structure
        - Missing optional fields fall back to defaults
    """

    # 1. Load base defaults (required)
    default_cfg = _load_default_config()

    # 2. Load user config if present (optional)
    user_cfg = _load_user_config()

    # 3. Environment overrides
    env_cfg = _env_overrides()

    # Merge order: defaults → user → env
    merged = merge_dicts(default_cfg, user_cfg, env_cfg)

    # Validate structure
    try:
        _validate_schema(merged)
    except Exception as e:
        raise RuntimeError(f"[config] Schema validation failed: {e}") from e

    # Validate types & assign defaults
    try:
        cfg = OrionConfig(**merged)
    except ValidationError as e:
        raise RuntimeError(f"[config] Invalid configuration: {e}") from e

    # Finalize any missing path defaults
    if cfg.chroma_path is None:
        # Supply default ChromaDB path dynamically
        from orion_cli.shared.paths import CHROMA_DIR
        cfg.chroma_path = CHROMA_DIR

    return cfg


__all__ = [
    "get_config",
    "OrionConfig",
]
