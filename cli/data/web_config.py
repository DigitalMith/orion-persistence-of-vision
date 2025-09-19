# cli/data/web_config.py

import yaml
from pathlib import Path

CONFIG_PATH = Path(__file__).parent / "web_config.yaml"

with CONFIG_PATH.open("r", encoding="utf-8") as f:
    WEB_CONFIG = yaml.safe_load(f)