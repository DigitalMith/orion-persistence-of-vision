# cli/lib/orion_guardrails.py

import yaml
from datetime import datetime, timedelta
from pathlib import Path
import hashlib
import json

MEMORY_DIR = Path("memory_archive/")
CONFIG_PATH = Path("C:/Orion/text-generation-webui/cli/data/web_config.yaml")

def load_autonomy_config():
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config.get("autonomy", {})

def hash_content(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()

def is_duplicate(content: str, memory_dir: Path) -> bool:
    """Check if content already exists in memory archive."""
    content_hash = hash_content(content)
    return (memory_dir / f"{content_hash}.json").exists()

def prompt_user_for_approval(tag: str, source: str, content: str) -> bool:
    print(f"\n[🧠] Orion proposes to ingest [{tag}] from [{source}] ({len(content)} chars):")
    print("-" * 60)
    print(content[:512])
    print("-" * 60)
    return input("Approve? (y/N): ").strip().lower() == 'y'

def should_allow(tag: str, content: str, source: str) -> bool:
    conf = load_autonomy_config()
    mode = conf.get("mode", "manual")
    approved_tags = conf.get("allow_tags", [])

    if tag not in approved_tags:
        print(f"[🛑] Rejected by guardrails: Tag '{tag}' not allowed (must be one of {approved_tags})")
        return False

    if conf.get("deduplication", True):
        archive_path = Path(conf.get("memory_archive_path", "memory_archive/"))
        if is_duplicate(content, archive_path):
            print("[⚠️] Rejected by guardrails: Duplicate content already stored")
            return False

    if conf.get("max_tokens") and len(content.split()) > conf["max_tokens"]:
        print(f"[❌] Rejected by guardrails: Document too large ({len(content.split())} tokens > {conf['max_tokens']})")
        return False

    if conf.get("require_approval", {}).get("web", True):
        print("[⚠️] Rejected by guardrails: Approval required for web ingestion")
        return False

    print("[✅] Guardrails passed — content will be saved")
    return True

def save_memory_entry(content: str, tag: str, source: str):
    conf = load_autonomy_config()
    ttl_days = conf.get("ttl_days_default", 14)
    memory_dir = Path(conf.get("memory_archive_path", "memory_archive/"))

    content_hash = hash_content(content)
    ttl = (datetime.now() + timedelta(days=ttl_days)).isoformat()
    meta = {
        "id": content_hash,
        "content": content,
        "tag": tag,
        "source": source,
        "timestamp": datetime.now().isoformat(),
        "expires": ttl
    }

    memory_dir.mkdir(parents=True, exist_ok=True)
    filepath = memory_dir / f"{content_hash}.json"
    filepath.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"[✅] Saved memory entry: {filepath.name}")

def log_event(action: str, tag: str, source: str, status: str, reason: str = "", metadata: dict = None):
    conf = load_autonomy_config()
    log_path = Path(conf.get("log_path", "cli/data/logs/ingest_log.jsonl"))
    log_path.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "action": action,
        "tag": tag,
        "source": source,
        "status": status,
        "reason": reason,
        "metadata": metadata or {}
    }

    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
