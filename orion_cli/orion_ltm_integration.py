# orion_ltm_integration.py
# Fully deprecated. All CNS/LTM logic is now located in shared/memory.py
# ruff: noqa: F403

from orion_cli.shared.memory import *
import warnings

warnings.warn(
    "orion_ltm_integration is deprecated → use shared.memory",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [name for name in globals().keys() if not name.startswith("_")]
