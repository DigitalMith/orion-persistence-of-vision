# cli_helpers/utils.py
from pathlib import Path
import yaml, re
from typing import Dict, Any

def normalize_topic(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s

def load_yaml_sections(yaml_path: str) -> Dict[str, Any]:
    """
    Load a YAML file and return its top-level sections as a dictionary.
    """
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError("YAML root must be a dictionary")

    return data