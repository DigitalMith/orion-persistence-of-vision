"""
config.py — Orion CNS 4.0 core config

Single source of truth for all Orion configuration.
If a required value is missing or malformed, raise ConfigError.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

import yaml


class ConfigError(RuntimeError):
    """Raised when Orion configuration is missing or invalid."""


# Paths are resolved relative to the orion_cli package root
_ORION_CLI_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = _ORION_CLI_ROOT / "data" / "config.yaml"
LTM_CONFIG_PATH = _ORION_CLI_ROOT / "data" / "ltm_config.yaml"


@dataclass
class PersonaConfig:
    rigidity: float = 0.5  # 0.0–1.0


@dataclass
class LTMConfig:
    persona_collection: str
    episodic_collection: str


@dataclass
class OrionConfig:
    embed_model: str
    persona: PersonaConfig
    ltm: LTMConfig
    raw: Dict[str, Any]  # keep full dict around for advanced use


_CONFIG: OrionConfig | None = None


def _load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise ConfigError(f"Missing config file: {path}")
    try:
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception as exc:  # noqa: BLE001
        raise ConfigError(f"Failed to parse YAML config: {path}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"Config file must contain a mapping at top level: {path}")
    return data


def _merge_ltm(main_cfg: Dict[str, Any], ltm_cfg: Dict[str, Any]) -> None:
    """
    Optional: merge values from ltm_config.yaml into main config under 'ltm'.
    ltm_cfg wins for the 'ltm' section only.
    """
    if "ltm" not in main_cfg or not isinstance(main_cfg["ltm"], dict):
        main_cfg["ltm"] = {}
    ltm_section = main_cfg["ltm"]
    for key, value in ltm_cfg.get("ltm", {}).items():
        ltm_section[key] = value


def _build_config_dict() -> Dict[str, Any]:
    cfg = _load_yaml(CONFIG_PATH)

    # Optionally merge ltm_config.yaml if present
    if LTM_CONFIG_PATH.exists():
        ltm_cfg = _load_yaml(LTM_CONFIG_PATH)
        _merge_ltm(cfg, ltm_cfg)

    # Defaults & validation
    cfg.setdefault("embed_model", "intfloat/e5-large-v2")

    ltm = cfg.setdefault("ltm", {})
    ltm.setdefault("persona_collection", "persona")
    ltm.setdefault("episodic_collection", "orion_episodic_sent_ltm")

    persona = cfg.setdefault("persona", {})
    rigidity = float(persona.get("rigidity", 0.5))
    if not 0.0 <= rigidity <= 1.0:
        raise ConfigError(f"persona.rigidity must be between 0.0 and 1.0, got {rigidity}")
    persona["rigidity"] = rigidity

    return cfg


def _build_config() -> OrionConfig:
    cfg = _build_config_dict()

    persona_cfg = PersonaConfig(rigidity=cfg["persona"]["rigidity"])
    ltm_cfg = LTMConfig(
        persona_collection=cfg["ltm"]["persona_collection"],
        episodic_collection=cfg["ltm"]["episodic_collection"],
    )

    return OrionConfig(
        embed_model=cfg["embed_model"],
        persona=persona_cfg,
        ltm=ltm_cfg,
        raw=cfg,
    )


def get_config() -> OrionConfig:
    """Return the singleton Orion CNS 4.0 configuration."""
    global _CONFIG  # noqa: PLW0603
    if _CONFIG is None:
        _CONFIG = _build_config()
    return _CONFIG
