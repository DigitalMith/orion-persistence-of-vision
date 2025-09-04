from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
import yaml
from chromadb import PersistentClient
import logging

# Enable logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("persona_seeder")

DEFAULT_DB = "user_data/chroma_db"

def _col(db_path: str, name: str):
    c = PersistentClient(path=db_path)
    return c.get_or_create_collection(name=name)

def _now() -> str:
    return datetime.utcnow().isoformat()

def _flatten_cards(doc: Dict[str, Any]) -> (str, List[Dict[str, Any]]):
    coll = doc.get("collection", "orion_persona")
    defaults = doc.get("default_priority", {})
    out: List[Dict[str, Any]] = []

    def pack(kind: str, items: List[Dict[str, Any]]):
        for it in items or []:
            cid = it["id"]
            text = it["text"]
            active = bool(it.get("active", True))
            pr = int(it.get("priority", defaults.get(kind, 5)))
            topic = it.get("topic", None)
            logger.info(f"[Seeder] Found YAML entry: {cid} (kind={kind}, priority={pr}, topic={topic})")
            out.append({
                "id": cid,
                "text": text,
                "meta": {
                    "id": cid,
                    "kind": kind,
                    "active": active,
                    "priority": pr,
                    "topic": topic,
                    "updated_at": _now(),
                }
            })

    pack("persona",    doc.get("persona"))
    pack("memory",     doc.get("memory"))
    pack("persistent", doc.get("persistent"))
    return coll, out

def load_yaml_and_upsert(yaml_path: str, db_path: str = DEFAULT_DB, replace: bool = False) -> Dict[str, int]:
    data = yaml.safe_load(Path(yaml_path).read_text(encoding="utf-8"))
    coll_name, cards = _flatten_cards(data)
    col = _col(db_path, coll_name)

    deactivated = 0

    if replace:
        all_data = col.get(include=["metadatas"], limit=10000)
        existing_items = zip(all_data.get("ids", []), all_data.get("metadatas") or [])

        # Only look at the kinds we are currently importing
        importing_kinds = {c["meta"]["kind"] for c in cards}

        existing_ids_by_kind = {
            str(i): meta for i, meta in existing_items
            if meta.get("kind") in importing_kinds
        }

        desired_ids = set(str(c["id"]) for c in cards)
        to_deactivate = [i for i in existing_ids_by_kind if i not in desired_ids]

        if to_deactivate:
            logger.info(f"[Seeder] Deactivating {len(to_deactivate)} outdated entries")
            col.upsert(
                ids=to_deactivate,
                documents=[""] * len(to_deactivate),
                metadatas=[
                    {**existing_ids_by_kind[i], "active": False, "updated_at": _now()}
                    for i in to_deactivate
                ]
            )
            deactivated = len(to_deactivate)

    ids = [str(c["id"]) for c in cards]
    docs = [
        "\n".join(c["text"]) if isinstance(c["text"], list) else str(c["text"])
        for c in cards
    ]
    metas = [c["meta"] for c in cards]

    if ids:
        logger.info(f"[Seeder] Inserting {len(ids)} entries into Chroma collection: {coll_name}")
        col.upsert(ids=ids, documents=docs, metadatas=metas)

    # ✅ Print confirmation of all contents
    logger.info("[Seeder] Verifying Chroma collection contents:")
    confirmed = col.get(include=["documents", "metadatas"], limit=1000)
    for doc, meta in zip(confirmed.get("documents", []), confirmed.get("metadatas", [])):
        logger.info(f"[{meta.get('kind')}] {meta.get('id')} - priority={meta.get('priority')} topic={meta.get('topic')}")

    return {"upserted": len(ids), "deactivated": deactivated, "collection": coll_name}

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
