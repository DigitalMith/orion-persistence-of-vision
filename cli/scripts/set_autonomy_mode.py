# cli/scripts/set_autonomy_mode.py

import yaml
import sys
from pathlib import Path

CONFIG_PATH = Path("C:/Orion/text-generation-webui/cli/data/web_config.yaml")

VALID_MODES = ["manual", "limited", "trusted", "open"]

def set_mode(mode: str):
    if mode not in VALID_MODES:
        print(f"[❌] Invalid mode '{mode}'. Choose one of: {', '.join(VALID_MODES)}")
        return

    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    config.setdefault("autonomy", {})["mode"] = mode

    with CONFIG_PATH.open("w", encoding="utf-8") as f:
        yaml.safe_dump(config, f)

    print(f"[✅] Autonomy mode updated to: {mode}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: python set_autonomy_mode.py <{'|'.join(VALID_MODES)}>")
        sys.exit(1)

    set_mode(sys.argv[1].lower())
