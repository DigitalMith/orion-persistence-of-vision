#!/usr/bin/env python3
import argparse
import logging
import sys
from pathlib import Path

# local helpers
from cli_helpers import (
    summary_helper,
    encoding_scan,
    ltm_query,
    persona_check,
    health_report,
    ingest_helper,
    delete_by_topic,
)

from cli_helpers.delete_topic import (
    delete_by_topic,
    count_by_topic,
    preview_topic,
)

def setup_logging(verbosity: int):
    level = logging.WARNING
    if verbosity == 1:
        level = logging.INFO
    elif verbosity >= 2:
        level = logging.DEBUG
    logging.basicConfig(level=level, format='[%(levelname)s] %(message)s')

def main():
    parser = argparse.ArgumentParser(
        prog="orion_cli",
        description="Orion Command Line Interface (LTM utilities & checks)",
    )
    parser.add_argument("-v", "--verbose", action="count", default=0,
                        help="Increase verbosity (-v, -vv)")

    subparsers = parser.add_subparsers(dest="command")

    # summary helper
    p_sum = subparsers.add_parser("summary", help="Summarize a .txt/.md into staged JSONL")
    p_sum.add_argument("--file", required=True, type=str, help="Path to text file")
    p_sum.add_argument("--topic", default=None, help="Topic label (optional)")
    p_sum.add_argument("--tags", nargs="*", default=None, help="Tags (space-separated)")
    p_sum.add_argument("--out", default=str(Path("LTM_Staged") / "summaries.jsonl"),
                       help="Output JSONL path")
    p_sum.add_argument("--max-chars", type=int, default=800,
                       help="Target summary length (characters)")

    # scan encoding
    p_enc = subparsers.add_parser("scan-encoding", help="Scan file/dir for UTF-8/BOM issues")
    p_enc.add_argument("target", help="File or directory")
    p_enc.add_argument("--fix", action="store_true", help="Attempt to fix in place")

    # query LTM
    p_q = subparsers.add_parser("ltm-query", help="Query Chroma LTM")
    p_q.add_argument("query", help="Search text")
    p_q.add_argument("--collection", default="orion_episodic_sent_ltm",
                     help="Chroma collection name")
    p_q.add_argument("--db", default=str(Path("chroma")), help="Chroma persist dir")
    p_q.add_argument("--topk", type=int, default=5, help="How many results to show")

    # persona validation
    p_pc = subparsers.add_parser("persona-check", help="Validate persona/memory headers")
    p_pc.add_argument("directory", help="Directory containing persona_header.txt & memory_header.txt")

    # health report
    p_hr = subparsers.add_parser("report", help="Environment & install health report")
    p_hr.add_argument("--model-path",
                      default=str(Path("user_data") / "models" / "openhermes-2.5-mistral-7b.Q5_K_M.gguf"),
                      help="Model file to verify")
    p_hr.add_argument("--chars-dir", default=str(Path("characters")),
                      help="Characters directory (expects Orion.yaml or Orion folder)")
    p_hr.add_argument("--chroma-dir", default=str(Path("chroma")),
                      help="Chroma persist directory")

    # ingest staged JSONL
    p_ing = subparsers.add_parser("ingest", help="Ingest staged JSONL into Chroma (embeddings included)")
    p_ing.add_argument("--staged", default=str(Path("LTM_Staged") / "summaries.jsonl"),
                       help="Path to staged JSONL")
    p_ing.add_argument("--db", default=str(Path("chroma")), help="Chroma persist dir")
    p_ing.add_argument("--collection", default="orion_episodic_sent_ltm", help="Collection name")
    p_ing.add_argument("--batch-size", type=int, default=256, help="Batch size for embedding/add")

    # delete-topic
    p_del = subparsers.add_parser("delete-topic", help="Delete entries by EXACT topic from Chroma LTM")
    p_del.add_argument("--topic", required=True, help="Exact topic to delete (case-sensitive)")
    p_del.add_argument("--dry-run", action="store_true", help="Show how many would be deleted, do not delete")
    p_del.add_argument("--no-confirm", action="store_true", help="Skip confirmation (dangerous)")
                   
    args = parser.parse_args()
    setup_logging(args.verbose)

    try:
        if args.command == "summary":
            summary_helper.main(args.file, topic=args.topic, tags=args.tags,
                                out_path=args.out, max_chars=args.max_chars)
        elif args.command == "scan-encoding":
            encoding_scan.run(args.target, fix=args.fix)
        elif args.command == "ltm-query":
            ltm_query.run(args.query, collection=args.collection, persist_dir=args.db, topk=args.topk)
        elif args.command == "persona-check":
            persona_check.run(args.directory)
        elif args.command == "report":
            health_report.run(model_path=args.model_path, chars_dir=args.chars_dir, chroma_dir=args.chroma_dir)
        elif args.command == "ingest":
            ingest_helper.run(staged_path=args.staged,
                              persist_dir=args.db,
                              collection_name=args.collection,
                              batch_size=args.batch_size)
        elif args.command == "delete-topic":
            topic = args.topic
            previews = preview_topic(topic, k=3)
            count = count_by_topic(topic)

            if count == 0:
                print(f"[INFO] No entries found for topic '{topic}'. Nothing to do.")
                return

            print(f"\nTopic: {topic}")
            print(f"Matches: {count}")
            if previews:
                print("Preview:")
                for line in previews:
                    print(f"  - {line}")
            else:
                print("Preview: (no sample documents found)")

            if args.dry_run:
                print(f"\n[DRY-RUN] Would delete {count} records where topic == '{topic}'.")
                return

            if not args.no_confirm:
                confirm = input(f"\nDelete ALL {count} records with topic '{topic}'? (yes/no): ").strip().lower()
                if confirm not in ("y", "yes"):
                    print("Cancelled.")
                    return

            delete_by_topic(topic)
            print(f"[✓] Deleted topic '{topic}' successfully.")

else:
    parser.print_help()
    sys.exit(1)
            
            print(f"\nTopic: {topic}")
            print(f"Matches: {count}")
            if previews:
                print("Preview:")
                for line in previews:
                    print(f"  - {line}")
            else:
                print("Preview: (no sample documents found)")

            if args.dry_run:
                print(f"\n[DRY-RUN] Would delete {count} records where topic == '{topic}'.")
                return

            if not args.no_confirm:
                confirm = input(f"\nDelete ALL {count} records with topic '{topic}'? (yes/no): ").strip().lower()
                if confirm not in ("y", "yes"):
                    print("Cancelled.")
                    return

            removed = delete_by_topic(topic, dry_run=False)
            print(f"[✓] Deleted {removed} records where topic == '{topic}'.")


            # Show preview (3 examples)
            previews = topic_preview(topic, k=3)
            print(f"\nPreview for topic: {topic}")
            if previews:
                for line in previews:
                    print(f"  - {line}")
            else:
                print("  (no preview documents found)")

            # Confirm
            if not args.dry_run:
                confirm = input(f"\nDelete ALL entries with topic '{topic}'? (yes/no): ").strip().lower()
                if confirm not in ("y", "yes"):
                    print("Cancelled.")
                    return

            count = delete_by_topic(topic, dry_run=args.dry_run)
            if args.dry_run:
                print(f"[DRY-RUN] Would delete ~{count} records where topic == '{topic}'.")
            else:
                print(f"Deleted {count} records where topic == '{topic}'.")
        
    except KeyboardInterrupt:
        print("\n[INFO] Aborted by user.")
        sys.exit(130)

