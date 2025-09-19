import yaml
import sys
import argparse

from cli.lib.chroma_utils import reset_collection, add_to_collection


def ingest_persona_from_yaml(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        blocks = list(yaml.safe_load_all(f))

    # Reset the target collection before ingesting
    collection = None
    for block in blocks:
        for key, value in block.items():
            if key == "collection":
                collection = value
                reset_collection(collection)
                print(f"Reset collection: {collection}")
            elif key == "default_priority":
                default_priority = value
            else:
                # Handle both dict and list values
                items = value if isinstance(value, list) else [value]
                for item in items:
                    doc_id = item.get("id")
                    document = item.get("text")
                    metadata = {}
                    for k, v in item.items():
                        if k == "text":
                            continue
                        elif isinstance(v, list):
                            metadata[k] = ", ".join(map(str, v))  # Convert list to CSV string
                        elif isinstance(v, (str, int, float, bool)) or v is None:
                            metadata[k] = v
                        else:
                            metadata[k] = str(v)  # Fallback: convert complex objects to string
                    add_to_collection(collection, doc_id, document, metadata)
                    print(f"Added: {doc_id} to {collection}")

def main(args):
    if args.command == "ingest":
        ingest_persona_from_yaml(args.file)
    else:
        print("Invalid persona command", file=sys.stderr)
        sys.exit(1)

def add_subparser(subparsers):
    parser = subparsers.add_parser("persona", help="Manage persona memory blocks")
    parser.add_argument("command", choices=["ingest"], help="Action to perform")
    parser.add_argument("file", help="Path to YAML file")
    parser.set_defaults(func=main)