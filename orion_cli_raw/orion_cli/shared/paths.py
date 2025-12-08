"""
Shared Paths
------------
Defines absolute paths for TGWUI root, Orion CLI root,
ChromaDB, logs, and future paths from config.
"""

from pathlib import Path
from .config import config

# TGWUI ROOT (user override or fallback to working dir)
TGWUI_ROOT = Path(config.get("paths", {}).get("tgwui_root", ".")).resolve()

# ORION CLI ROOT
ORION_CLI_ROOT = TGWUI_ROOT / "orion_cli"

# CHROMA DIRECTORY
CHROMA_DIR = Path(
    config.get("paths", {}).get("chroma_dir", TGWUI_ROOT / "user_data/Chroma-DB")
).resolve()

CHROMA_DB_PATH = CHROMA_DIR / "chroma.sqlite3"

# GLOBAL CONFIG PATH
CONFIG_PATH = ORION_CLI_ROOT / "data" / "config.yaml"

# LOG PATHS (future)
LOG_DIR = ORION_CLI_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)
