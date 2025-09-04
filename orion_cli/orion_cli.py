#!/usr/bin/env python3
import traceback
import argparse
import sys
import re
from chromadb import PersistentClient
from cli_helpers.utils import normalize_topic
from cli_helpers.persona_seeder import load_yaml_and_upsert
from cli_helpers.persona_seeder import cmd_persona_load

from cli_helpers import (
    summary_helper,
    delete_topic,
    encoding_scan,
    health_report,
    ltm_query,
    persona_check,
)
from cli_helpers.delete_topic import delete_by_topic, preview_topic, count_by_topic
from cli_helpers.ingest_helper import ingest_txt_direct  # <-- direct ingest

def cmd_ltm_peek(args):
    client = PersistentClient(path=args.db)
    coll = client.get_or_create_collection(name=args.collection)

    res = coll.get(where={"topic": args.topic}, include=["documents", "metadatas"], limit=args.n)
    docs = res.get("documents") or []
    metas = res.get("metadatas") or []
    ids   = res.get("ids") or []

    total = len(docs)
    print(f"[peek] topic={args.topic!r}  n={args.n}  found={total}")
    if total == 0:
        return

    for i, (doc, meta, _id) in enumerate(zip(docs, metas, ids), start=1):
        if not args.raw and doc:
            snippet = (doc or "").replace("\n", " ")
            if len(snippet) > 160:
                snippet = snippet[:160] + "…"
        else:
            snippet = doc or ""

        file = (meta or {}).get("file")
        chunk = (meta or {}).get("chunk")
        tags  = (meta or {}).get("tags_csv")
        print(f"\n[{i}] id={_id}")
        if file is not None:  print(f"    file:  {file}")
        if chunk is not None: print(f"    chunk: {chunk}")
        if tags:              print(f"    tags:  {tags.split(',')}")
        print(f"    text:  {snippet}")

def main():
    parser = argparse.ArgumentParser(
        prog="orion_cli",
        description="Orion Command Line Interface (LTM utilities & checks)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # seed-persona CLI
    sp = subparsers.add_parser("seed-persona", help="Seed persona and memory from YAML")
    sp.set_defaults(func=cmd_persona_load)

    # summary
    p_sum = subparsers.add_parser("summary", help="Summarize a .txt/.md into staged JSONL")
    p_sum.add_argument("--file", required=True, type=str, help="Path to text file")
    p_sum.add_argument("--topic", default=None, help="Topic label (optional)")
    p_sum.add_argument("--tags", nargs="*", default=None, help="Tags (space-separated)")
    p_sum.add_argument("--out", default=None, help="Output JSONL path")
    p_sum.add_argument("--max-chars", type=int, default=800, help="Target summary length (characters)")

    # delete-topic
    p_del = subparsers.add_parser("delete-topic", help="Delete all LTM entries by topic")
    p_del.add_argument("--topic", required=True, help="Exact topic name to delete")
    p_del.add_argument("--dry-run", action="store_true", help="Preview deletions without deleting")
    p_del.add_argument("--no-confirm", action="store_true", help="Skip confirmation prompt")

    # ingest-txt (direct)
    p_txt = subparsers.add_parser("ingest-txt", help="Directly ingest a .txt into Chroma (chunks + full doc)")
    p_txt.add_argument("--file", required=True, help="Path to .txt file")
    p_txt.add_argument("--topic", required=True, help="Topic label")
    p_txt.add_argument("--tags", default="", help="Comma-separated tags (e.g. 'orion,astronomy')")
    p_txt.add_argument("--db", default="user_data/chroma_db", help="Chroma persist dir")
    p_txt.add_argument("--collection", default="orion_episodic_sent_ltm", help="Collection name")
    p_txt.add_argument("--no-full", action="store_true", help="Skip storing a full-document record")

    # ltm-peek
    p_peek = subparsers.add_parser("ltm-peek", help="Preview LTM items by topic (shows N docs with small snippets)")
    p_peek.add_argument("--topic", required=True, help="Topic label to filter by")
    p_peek.add_argument("--n", type=int, default=10, help="Number of items to preview")
    p_peek.add_argument("--db", default="user_data/chroma_db", help="Chroma persist dir")
    p_peek.add_argument("--collection", default="orion_episodic_sent_ltm", help="Collection name")
    p_peek.add_argument("--raw", action="store_true", help="Print full documents (not truncated)")
    
    # persona-load
    p_load = subparsers.add_parser("persona-load", help="Load persona from a YAML file into ChromaDB")
    # p_load.add_argument("--yaml", required=True, help="Path to the persona.yaml file")
    p_load.add_argument("--db", default="user_data/chroma_db", help="Path to Chroma DB")
    p_load.add_argument("--replace", action="store_true", help="Replace existing records with same source tag")

    args = parser.parse_args()

    try:
        if args.command == "summary":
            summary_helper.main(
                file_path=args.file,
                topic=args.topic,
                tags=args.tags,
                out=args.out,
                max_chars=args.max_chars
            )

        elif args.command == "persona-load":
            import os
            script_dir = os.path.dirname(os.path.abspath(__file__))
            yaml_path = os.path.join(script_dir, "cli_support", "persona.yaml")  # 🔧 hardcoded path

            res = load_yaml_and_upsert(yaml_path, db_path=args.db, replace=args.replace)
            print(f"[OK] collection={res['collection']} upserted={res['upserted']} deactivated={res['deactivated']}")

        elif args.command == "ingest-txt":
            tags = [t.strip() for t in (args.tags or "").split(",") if t.strip()]
            n = ingest_txt_direct(
                file_path=args.file,
                topic=args.topic,
                tags=tags,
                persist_dir=args.db,
                collection_name=args.collection,
                add_full_doc=not args.no_full,
            )
            print(f"[OK] Ingested {n} records (topic={args.topic}, file={args.file})")

    except KeyboardInterrupt:
        print("\n[INFO] Aborted by user.")
        sys.exit(130)
    
    except Exception as e:
        print(f"[X] Unhandled error: {e}")
        traceback.print_exc()
        sys.exit(1)
    
if __name__ == "__main__":
    main()