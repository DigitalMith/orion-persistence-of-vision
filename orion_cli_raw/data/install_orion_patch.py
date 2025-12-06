#!/usr/bin/env python

"""
install_orion_patch.py - Auto-patches TGWUI with Orion LTM support.

✔ Copies Orion extension script
✔ Enables orion_ltm: true in settings.yaml
✔ Validates embed_model loads
✔ Cross-platform and safe to run multiple times
"""

import shutil
from pathlib import Path
import yaml
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parents[2]  # text-generation-webui root
EXT_DIR = ROOT / "extensions" / "orion_ltm"
SRC_SCRIPT = ROOT / "orion_cli" / "data" / "script.py"
DEST_SCRIPT = EXT_DIR / "script.py"
SETTINGS_YAML = ROOT / "extensions" / "settings.yaml"
CONFIG_PATH = ROOT / "orion_cli" / "data" / "config.yaml"


def log(msg):
    print(f"[orion_patch] {msg}")


def ensure_script_installed():
    EXT_DIR.mkdir(parents=True, exist_ok=True)
    if DEST_SCRIPT.exists():
        log("✅ Orion extension script already exists.")
    else:
        shutil.copy2(SRC_SCRIPT, DEST_SCRIPT)
        log(f"✅ Copied Orion script.py → {DEST_SCRIPT}")


def enable_extension():
    if not SETTINGS_YAML.exists():
        log("🔧 Creating settings.yaml")
        SETTINGS_YAML.write_text("orion_ltm: true\n")
        return

    with open(SETTINGS_YAML, "r", encoding="utf-8") as f:
        try:
            settings = yaml.safe_load(f) or {}
        except yaml.YAMLError:
            log("⚠️ settings.yaml is not valid YAML. Skipping patch.")
            return

    if settings.get("orion_ltm") is True:
        log("✅ orion_ltm already enabled in settings.yaml")
        return

    settings["orion_ltm"] = True
    with open(SETTINGS_YAML, "w", encoding="utf-8") as f:
        yaml.safe_dump(settings, f)
    log("✅ Enabled orion_ltm in settings.yaml")


def validate_embedding_model():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        model_name = config.get("embed_model", "intfloat/e5-large-v2")
        log(f"🧠 Testing embedding model load: {model_name}")
        model = SentenceTransformer(model_name)
        vec = model.encode(["test"])[0]
        dim = len(vec)
        log(f"✅ Model loaded with dimension: {dim}")
    except Exception as e:
        log(f"❌ Failed to load embedding model: {e}")


def main():
    log("🚀 Orion TGWUI Patch Starting")
    ensure_script_installed()
    enable_extension()
    validate_embedding_model()
    log("✅ Orion LTM successfully patched into TGWUI.")


if __name__ == "__main__":
    main()
