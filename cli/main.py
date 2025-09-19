### Root: cli/main.py
import argparse
from cli.commands import persona
from cli.commands import chroma

def main():
    parser = argparse.ArgumentParser(description="CLI - Identity & Memory Shell")
    subparsers = parser.add_subparsers(dest="command")
    chroma.add_subparser(subparsers)

    persona.add_subparser(subparsers)

    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()


### cli/commands/persona.py
import argparse
import yaml
from cli.utils.chroma import reset_and_save_persona


def ingest_persona_from_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        blocks = list(yaml.safe_load_all(f))

    entries = []
    for block in blocks:
        for section, data in block.items():
            meta = data.copy()
            text = meta.pop("text", f"[{section.upper()}]")  # fallback
            entry = {
                "document": text.strip(),
                "metadata": {
                    "kind": section,
                    **meta
                }
            }
            entries.append(entry)

    reset_and_save_persona(entries)


def add_subparser(subparsers):
    p = subparsers.add_parser("persona", help="Manage persona identity blocks")
    p.set_defaults(func=main)
    p.add_argument("action", choices=["ingest"])  # Only ingest mode
    p.add_argument("file", help="Path to persona.yaml")


def main(args):
    if args.action == "ingest":
        ingest_persona_from_yaml(args.file)


# ChromaDB client
import os
from chromadb import PersistentClient


def reset_and_save_persona(entries, collection="orion_persona", persist_dir="user_data/chroma_db"):
    os.makedirs(persist_dir, exist_ok=True)
    client = PersistentClient(path=persist_dir)
    coll = client.get_or_create_collection(name=collection)

    # Wipe existing data before ingesting
    coll.delete(where={})

    for entry in entries:
        doc_id = f"{collection}_{hash(entry['document']) % (10 ** 8)}"
        coll.add(
            documents=[entry["document"]],
            metadatas=[entry["metadata"]],
            ids=[doc_id]
        )
