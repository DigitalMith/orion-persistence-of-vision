from __future__ import annotations

import os
from pathlib import Path

"""
Centralized path definitions for Orion CLI.

Rule of truth:
- Prefer user-owned YAML under:   <USER_ORION_DIR>/data/
- If missing, fall back to CLI templates in: <PACKAGE_ROOT>/data/

Notes:
- PACKAGE_ROOT: static CLI package (code + templates)
- USER_ORION_DIR: dynamic Orion user data root (config, memory, embeddings, cache)
  - Default: <PACKAGE_ROOT parent>/orion
  - Override via ORION_USER_DIR
"""


# -------------------------------------------------------------------
# Small helpers (prevent mkdir boilerplate and keep intent readable)
# -------------------------------------------------------------------
def _ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


def prefer_user_else_template(user_path: Path, template_path: Path) -> Path:
    """
    Resolve a YAML/config path with this rule:
      - If user_path exists, use it.
      - Else fall back to template_path.
    """
    return user_path if user_path.exists() else template_path


# -------------------------------------------------------------------
# Orion CLI Package Root (static code + templates)
# Example:
#   C:/Orion/text-generation-webui/user_data/orion_cli
# -------------------------------------------------------------------
PACKAGE_ROOT = Path(__file__).resolve().parent.parent


# -------------------------------------------------------------------
# Orion User Data Root (dynamic state, embeddings, memory, persona)
#
# Default:
#   C:/Orion/text-generation-webui/user_data/orion
#
# Can be overridden by env var ORION_USER_DIR
# -------------------------------------------------------------------
DEFAULT_USER_ORION_DIR = PACKAGE_ROOT.parent / "orion"
USER_ORION_DIR = _ensure_dir(
    Path(os.getenv("ORION_USER_DIR", str(DEFAULT_USER_ORION_DIR)))
)


# -------------------------------------------------------------------
# User Config + Persona + Identity + Semantic + Agent tools policy
#
#   <USER_ORION_DIR>/data/
# -------------------------------------------------------------------
USER_DATA_DIR = _ensure_dir(USER_ORION_DIR / "data")

USER_CONFIG_PATH = USER_DATA_DIR / "config.yaml"
USER_PERSONA_PATH = USER_DATA_DIR / "persona.yaml"
USER_IDENTITY_PATH = USER_DATA_DIR / "identity.yaml"
USER_SEMANTIC_PATH = USER_DATA_DIR / "semantic.yaml"
USER_AGENT_TOOLS_PATH = USER_DATA_DIR / "agent_tools.yaml"


# -------------------------------------------------------------------
# Agent / Runtime State
#
#   <USER_ORION_DIR>/state/
# -------------------------------------------------------------------
USER_STATE_DIR = _ensure_dir(USER_ORION_DIR / "state")
AGENT_STATE_PATH = USER_STATE_DIR / "agent_state.yaml"


# -------------------------------------------------------------------
# ChromaDB persistent memory store
#
#   <USER_ORION_DIR>/chromadb/
# -------------------------------------------------------------------
CHROMA_DIR = _ensure_dir(USER_ORION_DIR / "chromadb")

# Backwards-compat alias for older code
DEFAULT_CHROMA_PATH = CHROMA_DIR


# -------------------------------------------------------------------
# Embedding Model Downloads (pinned / curated)
#
#   <USER_ORION_DIR>/embeddings/
# -------------------------------------------------------------------
EMBEDDING_MODEL_DIR = _ensure_dir(USER_ORION_DIR / "embeddings")


# -------------------------------------------------------------------
# HuggingFace Cache
#
#   <USER_ORION_DIR>/hf_cache/
#
# HF_HOME is only set here if the user has not already chosen a value.
# -------------------------------------------------------------------
HF_CACHE_DIR = _ensure_dir(USER_ORION_DIR / "hf_cache")
DEFAULT_HF_CACHE_PATH = HF_CACHE_DIR

if "HF_HOME" not in os.environ:
    os.environ["HF_HOME"] = str(HF_CACHE_DIR)


# -------------------------------------------------------------------
# Orion Workspace Area (scratchpad / tools / files)
#
#   <USER_ORION_DIR>/workspace/
# -------------------------------------------------------------------
WORKSPACE_DIR = _ensure_dir(USER_ORION_DIR / "workspace")


# -------------------------------------------------------------------
# Static Package Data (templates, schema)
#
#   <PACKAGE_ROOT>/data/
# -------------------------------------------------------------------
DATA_DIR = PACKAGE_ROOT / "data"

# Shipped templates (used only when user YAML is missing)
CONFIG_TEMPLATE_PATH = DATA_DIR / "config_template.yaml"
IDENTITY_TEMPLATE_PATH = DATA_DIR / "identity_template.yaml"
PERSONA_TEMPLATE_PATH = DATA_DIR / "persona_template.yaml"
SEMANTIC_TEMPLATE_PATH = DATA_DIR / "semantic_template.yaml"
AGENT_TOOLS_TEMPLATE_PATH = DATA_DIR / "agent_tools_template.yaml"

# Backwards-compat: older code expects DEFAULT_CONFIG_PATH
# Prefer shipped default_config.yaml if present, else fall back to config_template.yaml
DEFAULT_CONFIG_PATH = DATA_DIR / "default_config.yaml"
if not DEFAULT_CONFIG_PATH.exists():
    DEFAULT_CONFIG_PATH = CONFIG_TEMPLATE_PATH

# Schema is always shipped from the CLI package
SCHEMA_PATH = DATA_DIR / "schema.json"

# Effective paths (what consumers should use when they "just want the right file")
EFFECTIVE_CONFIG_PATH = prefer_user_else_template(
    USER_CONFIG_PATH, CONFIG_TEMPLATE_PATH
)
EFFECTIVE_IDENTITY_PATH = prefer_user_else_template(
    USER_IDENTITY_PATH, IDENTITY_TEMPLATE_PATH
)
EFFECTIVE_PERSONA_PATH = prefer_user_else_template(
    USER_PERSONA_PATH, PERSONA_TEMPLATE_PATH
)
EFFECTIVE_SEMANTIC_PATH = prefer_user_else_template(
    USER_SEMANTIC_PATH, SEMANTIC_TEMPLATE_PATH
)
EFFECTIVE_AGENT_TOOLS_PATH = (
    USER_AGENT_TOOLS_PATH
    if USER_AGENT_TOOLS_PATH.exists()
    else AGENT_TOOLS_TEMPLATE_PATH
)


__all__ = [
    # roots
    "PACKAGE_ROOT",
    "USER_ORION_DIR",
    "USER_DATA_DIR",
    "USER_STATE_DIR",
    "WORKSPACE_DIR",
    "DATA_DIR",
    # user files
    "USER_CONFIG_PATH",
    "USER_PERSONA_PATH",
    "USER_IDENTITY_PATH",
    "USER_SEMANTIC_PATH",
    "USER_AGENT_TOOLS_PATH",
    # state
    "AGENT_STATE_PATH",
    # storage
    "CHROMA_DIR",
    "DEFAULT_CHROMA_PATH",
    "EMBEDDING_MODEL_DIR",
    "HF_CACHE_DIR",
    "DEFAULT_HF_CACHE_PATH",
    # templates + schema
    "CONFIG_TEMPLATE_PATH",
    "IDENTITY_TEMPLATE_PATH",
    "PERSONA_TEMPLATE_PATH",
    "SEMANTIC_TEMPLATE_PATH",
    "AGENT_TOOLS_TEMPLATE_PATH",
    "SCHEMA_PATH",
    "DEFAULT_CONFIG_PATH",
    # effective resolution helpers
    "prefer_user_else_template",
    "EFFECTIVE_CONFIG_PATH",
    "EFFECTIVE_IDENTITY_PATH",
    "EFFECTIVE_PERSONA_PATH",
    "EFFECTIVE_SEMANTIC_PATH",
    "EFFECTIVE_AGENT_TOOLS_PATH",
]
