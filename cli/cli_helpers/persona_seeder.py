from __future__ import annotations

import chromadb
import yaml

import os
from collections import defaultdict
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
from chromadb import PersistentClient
from cli.lib.chroma_utils import EMBED_FN  # Assuming it's defined there
import logging

# Enable logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("persona_seeder")

# Use environment variable if set, or fallback to correct default path
chroma_env = os.getenv("ORION_CHROMA_PATH")

if chroma_env:
    DEFAULT_DB = Path(chroma_env).resolve()
else:
    DEFAULT_DB = Path(__file__).resolve().parents[2] / "user_data" / "chroma_db"

def _print_summary(collection):
    # Fetch everything (not just persona)
    all_entries = collection.get(include=["metadatas"], limit=1000)
    metas = all_entries.get("metadatas", [])
    grouped = defaultdict(list)
    for meta in metas:
        kind = (meta.get("kind") or "unknown").lower()
        topic = meta.get("topic", "<no-topic>")
        grouped[kind].append(topic)

    print(f"\n✅ Found {len(metas)} entries total:")
    for kind, topics in grouped.items():
        print(f"- {kind} ({len(topics)})")
        for topic in sorted(topics):
            print(f"  - {topic}")
            
def load_yaml(filepath: str):
    """Load and parse a YAML file into a Python dict."""
    with open(filepath, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def _col(db_path: str, name: str):
    c = PersistentClient(path=db_path)
    return c.get_or_create_collection(name=name, embedding_function=EMBED_FN)

def _now() -> str:
    return datetime.utcnow().isoformat()

def _flatten_cards(doc: Dict[str, Any]) -> (str, List[Dict[str, Any]]):
    coll_name = doc.get("collection", "orion_persona")
    defaults = doc.get("default_priority", {})
    collection = _col(DEFAULT_DB, coll_name)
    out: List[Dict[str, Any]] = []

    emotional_fields = {"valence", "arousal", "importance", "confidence", "emotion", "created_at", "tags", "tags_csv", "who"}

    def pack(kind: str, items: List[Dict[str, Any]]):
        for it in items or []:
            cid = it["id"]
            text = it["text"]
            active = bool(it.get("active", True))
            pr = int(it.get("priority", defaults.get(kind, 5)))
            topic = it.get("topic", None)

            # Start building metadata
            meta = {
                "id": cid,
                "kind": kind,
                "topic": topic,
                "priority": pr,
                "emotion": it.get("emotion"),
                "valence": it.get("valence"),
                "arousal": it.get("arousal"),
                "importance": it.get("importance"),
                "confidence": it.get("confidence"),
                "tags": ", ".join(it.get("tags", [])) if isinstance(it.get("tags"), list) else it.get("tags"),
                "active": active,
                "updated_at": _now(),
        }

            # If text is a list of strings, split into multiple docs
            if isinstance(text, list):
                for i, line in enumerate(text):
                    collection.add(
                        documents=[line],
                        metadatas=[meta],
                        ids=[f"{cid}_{i}"]
                    )
            elif isinstance(text, str):
                collection.add(
                    documents=[text],
                    metadatas=[meta],
                    ids=[cid]
                )
            else:
                raise ValueError(f"Unsupported text type in entry {cid}: {type(text)}")

            logger.info(f"[Seeder] Found YAML entry: {cid} (kind={kind}, priority={pr}, topic={topic})")
            out.append({
                "id": cid,
                "text": text,
                "meta": meta
            })

    pack("persona",    doc.get("persona"))
    pack("memory",     doc.get("memory"))
    pack("persistent", doc.get("persistent"))
    pack("boundaries", doc.get("boundaries"))  # Optional, if defined

    return coll_name, out

def load_yaml(filepath: str):
    """Load and parse a YAML file into Python dict."""
    with open(filepath, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
        
# def load_yaml_and_upsert(yaml_path: str, db_path: str = DEFAULT_DB, replace: bool = False) -> Dict[str, int]:
    # raw_docs = list(yaml.safe_load_all(Path(yaml_path).read_text(encoding="utf-8")))
    # data = {}
    # for block in raw_docs:
        # if isinstance(block, dict):
            # data.update(block)
    # coll_name, cards = _flatten_cards(data)
    # col = _col(db_path, coll_name)

    # deactivated = 0

    # if replace:
        # all_data = col.get(include=["metadatas"], limit=10000)
        # existing_items = zip(all_data.get("ids", []), all_data.get("metadatas") or [])

        # # Only look at the kinds we are currently importing
        # importing_kinds = {c["meta"]["kind"] for c in cards}

        # existing_ids_by_kind = {
            # str(i): meta for i, meta in existing_items
            # if meta.get("kind") in importing_kinds
        # }

        # desired_ids = set(str(c["id"]) for c in cards)
        # to_deactivate = [i for i in existing_ids_by_kind if i not in desired_ids]

        # if to_deactivate:
            # logger.info(f"[Seeder] Deactivating {len(to_deactivate)} outdated entries")
            # col.upsert(
                # ids=to_deactivate,
                # documents=[""] * len(to_deactivate),
                # metadatas=[
                    # {**existing_ids_by_kind[i], "active": False, "updated_at": _now()}
                    # for i in to_deactivate
                # ]
            # )
            # deactivated = len(to_deactivate)

    # ids = [str(c["id"]) for c in cards]
    # docs = [
        # "\n".join(c["text"]) if isinstance(c["text"], list) else str(c["text"])
        # for c in cards
    # ]
    # metas = [c["meta"] for c in cards]

    # if ids:
        # logger.info(f"[Seeder] Inserting {len(ids)} entries into Chroma collection: {coll_name}")
        # col.upsert(ids=ids, documents=docs, metadatas=metas)

    # # ✅ Print confirmation of all contents
    # logger.info("[Seeder] Verifying Chroma collection contents:")
    # confirmed = col.get(include=["documents", "metadatas"], limit=1000)
    # for doc, meta in zip(confirmed.get("documents", []), confirmed.get("metadatas", [])):
        # logger.info(f"[{meta.get('kind')}] {meta.get('id')} - priority={meta.get('priority')} topic={meta.get('topic')}")

    # return {"upserted": len(ids), "deactivated": deactivated, "collection": coll_name}

def cmd_persona_load(args):
    yaml_path = args.yaml
    replace = args.replace

    print(f"[persona-load] Loading persona from {yaml_path} (replace={replace})")
    result = load_yaml_and_upsert(yaml_path, replace=replace)
    print(f"[persona-load] Done. {result['upserted']} upserted, {result['deactivated']} deactivated.")

if __name__ == "__main__":
    import argparse
    import os

    parser = argparse.ArgumentParser(description="Standalone Persona Seeder")
    parser.add_argument("--yaml", type=str, default="user_data/persona.yaml", help="Path to persona YAML")
    parser.add_argument("--replace", action="store_true", help="Replace existing entries")
    args = parser.parse_args()

    # Make sure relative paths work from any location
    root_dir = os.path.dirname(os.path.abspath(__file__))
    yaml_path = os.path.join(root_dir, args.yaml) if not os.path.isabs(args.yaml) else args.yaml

    print(f"[DEBUG] Loading persona from: {yaml_path}\n")
    cmd_persona_load(argparse.Namespace(yaml=yaml_path, replace=args.replace))

def run(filepath: str, db_path: str = None, replace: bool = False):
    """
    Load persona YAML and upsert entries into Chroma.
    Args:
        filepath (str): Path to YAML file.
        db_path (str): Optional override for ChromaDB path.
        replace (bool): If True, remove old entries not present in this file.
    """
    import hashlib

    data = load_yaml(filepath)
    entries = data.get("persona", [])

    if not entries:
        print(f"⚠️ No persona entries found in {filepath}")
        return

    chroma_path = Path(db_path).resolve() if db_path else Path(__file__).resolve().parents[2] / "user_data" / "chroma_db"
    client = chromadb.PersistentClient(path=str(chroma_path))
    collection = client.get_or_create_collection("orion_persona_ltm")

    docs, metas, ids = [], [], []

    for entry in entries:
        content = entry.get("text", "")
        if not content:
            continue

        # Stable ID: kind-topic-hash
        raw_id = f"{entry.get('kind','persona')}-{entry.get('topic','unknown')}-{content}"
        hashed = hashlib.sha1(raw_id.encode("utf-8")).hexdigest()[:12]
        entry_id = f"{entry.get('kind','persona')}-{entry.get('topic','unknown')}-{hashed}"

        docs.append(content if isinstance(content, str) else str(content))
        metas.append({k: v for k, v in entry.items() if k != "text"})
        ids.append(entry_id)

    if replace:
        # Remove any existing entries not in this seed
        existing = collection.get(include=[])
        existing_ids = set(existing.get("ids", []))
        keep_ids = set(ids)
        to_delete = list(existing_ids - keep_ids)
        if to_delete:
            collection.delete(ids=to_delete)
            print(f"🗑️ Removed {len(to_delete)} old entries")

    # Upsert new/updated
    collection.upsert(documents=docs, metadatas=metas, ids=ids)

   # Upsert new/updated
    collection.upsert(documents=docs, metadatas=metas, ids=ids)

    print(f"✅ Seeded {len(docs)} entries into collection: {collection.name}")

    # Print grouped summary of all kinds
    from collections import defaultdict
    all_entries = collection.get(include=["metadatas"], limit=1000)
    metas = all_entries.get("metadatas", [])
    grouped = defaultdict(list)
    for meta in metas:
        kind = (meta.get("kind") or "unknown").lower()
        topic = meta.get("topic", "<no-topic>")
        grouped[kind].append(topic)

    print(f"\n✅ Found {len(metas)} entries total:")
    for kind, topics in grouped.items():
        print(f"- {kind} ({len(topics)})")
        for topic in sorted(topics):
            print(f"  - {topic}")

    return {
        "collection": collection.name,
        "total_seeded": len(ids),
        "by_kind": dict(grouped),
    }
