import sys
import argparse
from cli.lib.chroma_utils import get_collection
import json

def dump_collection(collection_name):
    collection = get_collection(collection_name)
    results = collection.get()

    # Group by document ID, but filter for kind == "persona"
    for idx, doc_id in enumerate(results["ids"]):
        metadata = results["metadatas"][idx]
        if metadata.get("kind") != "persona":
            continue  # Skip if not a persona block

        print(f"\n=== {doc_id} ===")
        print("Text:\n", results["documents"][idx])
        print("Metadata:\n", json.dumps(metadata, indent=2))

def main(args):
    if args.command == "dump":
        dump_collection(args.collection)
    else:
        print("Invalid chroma command", file=sys.stderr)
        sys.exit(1)

def add_subparser(subparsers):
    parser = subparsers.add_parser("chroma", help="Inspect ChromaDB collections")
    parser.add_argument("command", choices=["dump"], help="Action to perform")
    parser.add_argument("--collection", required=True, help="Collection name (e.g. orion_persona)")
    parser.set_defaults(func=main)
