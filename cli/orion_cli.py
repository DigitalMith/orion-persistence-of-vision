#!/usr/bin/env python3
import sys
import os
import argparse
import traceback
from pathlib import Path

# CLI paths
CLI_ROOT = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CLI_ROOT, ".."))
for path in [CLI_ROOT, PROJECT_ROOT]:
    if path not in sys.path:
        sys.path.insert(0, path)

# Core CLI helpers
try:
    from cli_helpers.utils import normalize_topic, init_collection
    from cli_helpers import persona_seeder
    from cli_helpers.delete_topic import delete_by_topic, preview_topic, count_by_topic
    from cli_helpers.ingest_ltm import ingest_staged_with_timestamps
    from cli_helpers.ltm_helpers import embed_and_store
    from cli_helpers import (
        summary_helper,
        encoding_scan,
        health_report,
        ltm_query,
        persona_check,
    )
except ImportError as e:
    print(f"❌ Failed to import CLI helpers: {e}")
    traceback.print_exc()
    sys.exit(1)

# Optional: Web search modules
try:
    from cli.scripts.web_search import web_search, chunk_text, WEB_CONFIG
    from utils.web_search_hook import handle_web_search
except ImportError:
    web_search = None
    print("⚠️ Web search helpers not found. Skipping.")

# Web ingestion
try:
    from cli.cli_helpers.orion_net_ingest import OrionNetIngest, orion_store_callback_factory
except ImportError as e:
    print(f"❌ Failed to import Orion web ingest: {e}")
    traceback.print_exc()
    sys.exit(1)

# ------------------------------
# Subcommand functions
# ------------------------------
def run_persona_load(args):
    try:
        res = load_yaml_and_upsert(
            args.yaml, db_path=args.db, replace=args.replace
        )
        print(f"[✅] collection={res['collection']} upserted={res['upserted']} deactivated={res['deactivated']}")
    except Exception as e:
        print(f"❌ Persona load failed: {e}")
        traceback.print_exc()

def run_ingest_ltm(args):
    try:
        coll = init_collection(args.collection)
        ingest_staged_with_timestamps(
            staged_dir=Path(args.staged),
            logs_dir=Path(args.logs),
            episodic_coll=coll
        )
    except Exception as e:
        print(f"❌ Ingestion failed: {e}")
        traceback.print_exc()

def run_web_search(args):
    try:
        results = web_search(args.query)
        print("\n".join([f"{r['title']}\n{r['snippet']}\n{r['url']}\n" for r in results]))
        if args.save and WEB_CONFIG.get("save_to_ltm"):
            from cli.lib.orion_ltm_integration import initialize_chromadb_for_ltm, on_user_turn
            persona_coll, episodic_coll = initialize_chromadb_for_ltm()
            for r in results:
                chunks = chunk_text(r["snippet"], size=WEB_CONFIG.get("chunk_size", 150))
                for chunk in chunks:
                    on_user_turn(chunk, episodic_coll)
            print(f"✅ Saved {len(results)} search results to LTM")
    except Exception as e:
        print(f"❌ Web search failed: {e}")
        traceback.print_exc()

def run_ingest_web(args):
    try:
        policy_path = os.environ.get("ORION_POLICY", r"C:\Orion\text-generation-webui\orion_policy.yaml")
        ing = OrionNetIngest(policy_path)
        callback = orion_store_callback_factory()
        result = ing.ingest_web(
            url=args.url,
            topic=args.topic,
            crawl_depth=args.depth,
            crawl_pages_cap=args.max_pages,
            store_callback=callback,
        )
        print(result)
    except Exception as e:
        print(f"❌ Ingest-web failed: {e}")
        traceback.print_exc()

# ------------------------------
# Main CLI entry point
# ------------------------------
def main():
    parser = argparse.ArgumentParser(description="🧠 Orion CLI Assistant")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # persona-load
    p_load = subparsers.add_parser("persona-load", help="Load persona YAML into ChromaDB")
    p_load.add_argument("--yaml", required=True)
    p_load.add_argument("--db", default="user_data/chroma_db")
    p_load.add_argument("--replace", action="store_true")
    p_load.set_defaults(func=run_persona_load)

    # persona-seed
    p_seed = subparsers.add_parser("persona-seed", help="Seed persona from YAML or JSONL")
    p_seed.add_argument("--file", required=True)
    p_seed.add_argument("--replace", action="store_true")
    p_seed.add_argument("--db", default=None)
    p_seed.set_defaults(func=lambda args: persona_seeder.run(
        filepath=args.file,
        db_path=args.db,
        replace=args.replace
    ))

    # persona-check
    p_check = subparsers.add_parser("persona-check", help="Inspect active persona entries")
    p_check.add_argument("--db", default=None)
    p_check.set_defaults(func=lambda args: persona_check.run(args))

    # ingest-ltm
    p_ingest = subparsers.add_parser("ingest-ltm", help="Ingest staged logs")
    p_ingest.add_argument("--staged", default="cli/data/logs/LTM_Staged")
    p_ingest.add_argument("--logs", default="cli/data/logs")
    p_ingest.add_argument("--collection", default="orion_episodic_sent_ltm")
    p_ingest.set_defaults(func=run_ingest_ltm)

    # ltm-query
    q = subparsers.add_parser("ltm-query", help="Query LTM")
    q.add_argument("query")
    q.set_defaults(func=lambda args: ltm_query.run(args.query))

    # delete-topic
    dt = subparsers.add_parser("delete-topic", help="Delete entries by topic")
    dt.add_argument("topic")
    dt.set_defaults(func=lambda args: delete_by_topic(args.topic))

    # summary
    sm = subparsers.add_parser("summary", help="Print memory/persona summary")
    sm.set_defaults(func=lambda args: summary_helper.print_summary())

    # web-search
    if web_search:
        ws = subparsers.add_parser("web-search", help="Search the web")
        ws.add_argument("query")
        ws.add_argument("--save", action="store_true")
        ws.set_defaults(func=run_web_search)

    # ingest-web
    iw = subparsers.add_parser("ingest-web", help="Ingest a webpage into Orion's LTM")
    iw.add_argument("--url", required=True, help="URL to ingest")
    iw.add_argument("--topic", default="web-ingest")
    iw.add_argument("--depth", type=int, default=1)
    iw.add_argument("--max-pages", type=int, default=5)
    iw.set_defaults(func=run_ingest_web)

    # Parse and run
    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()

# ------------------------------
# Entry point
# ------------------------------
if __name__ == "__main__":
    main()
