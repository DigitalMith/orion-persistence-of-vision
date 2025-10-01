# orion_cli.py

import argparse
from core import ingest, persona, memory

def main():
    parser = argparse.ArgumentParser(
        description="🧠 Orion CLI — Modular Memory, Persona, Ingestion Control"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # 🔹 Ingest LTM
    ingest_parser = subparsers.add_parser("ingest-ltm", help="Ingest staged logs into ChromaDB")
    ingest_parser.add_argument("--staged", required=True, help="Path to staged logs")
    ingest_parser.add_argument("--logs", required=True, help="Path to output logs")
    ingest_parser.set_defaults(func=ingest.run)

    # 🔹 Persona Check
    persona_parser = subparsers.add_parser("persona-check", help="View current persona state")
    persona_parser.set_defaults(func=persona.check)

    # 🔹 LTM Query
    query_parser = subparsers.add_parser("ltm-query", help="Query long-term memory")
    query_parser.add_argument("--query", required=True, help="Search string")
    query_parser.set_defaults(func=memory.query)

    # 🔹 Memory Summary
    summary_parser = subparsers.add_parser("summary", help="Summarize LTM topics")
    summary_parser.set_defaults(func=memory.summarize)

    # 🔹 Persona Seed
    seed_parser = subparsers.add_parser("persona-seed", help="Seed persona traits into memory")
    seed_parser.add_argument("--file", required=True, help="Path to persona.yaml")
    seed_parser.set_defaults(func=persona.seed)

    # 🔹 Persona Recall
    recall_parser = subparsers.add_parser("persona-recall", help="Recall persona traits from memory")
    recall_parser.set_defaults(func=persona.recall)

    # 🔹 LTM Restore
    restore_parser = subparsers.add_parser("ltm-restore", help="Restore memory from a JSONL archive")
    restore_parser.add_argument("--file", required=True, help="Path to .jsonl archive")
    restore_parser.set_defaults(func=memory.restore)

    # 🔹 LTM Normalize
    norm_parser = subparsers.add_parser("ltm-normalize", help="Normalize chatlogs into clean JSONL")
    norm_parser.add_argument("--input", required=True, help="Path to chatlog folder or file")
    norm_parser.add_argument("--output", required=True, help="Output JSONL path")
    norm_parser.set_defaults(func=memory.normalize)

    # 🔹 Check Embeddings
    check_parser = subparsers.add_parser("check-embed", help="Verify embeddings and dimensions in ChromaDB")
    check_parser.set_defaults(func=memory.check_embed)

    # 🔹 LTM Delete
    delete_parser = subparsers.add_parser("ltm-delete", help="Delete Chroma memory by topic")
    delete_parser.add_argument("--topic", required=True, help="Topic to delete from ChromaDB")
    delete_parser.add_argument("--filter", nargs="*", help="Optional metadata filters like trait=ego source=persona-seed")
    delete_parser.add_argument("--force", action="store_true", help="Skip confirmation prompt")
    delete_parser.set_defaults(func=memory.delete_topic)

    # 🔹 LTM Export
    export_parser = subparsers.add_parser("ltm-export", help="Export memory by topic to JSONL")
    export_parser.add_argument("--topic", required=True, help="Topic to export")
    export_parser.add_argument("--output", required=True, help="Output file (.jsonl)")
    export_parser.add_argument("--filter", nargs="*", help="Optional metadata filters (key=value)")
    export_parser.set_defaults(func=memory.export_topic)

    # 🔹 LTM Merge
    merge_parser = subparsers.add_parser("ltm-merge", help="Merge multiple JSONL memory files")
    merge_parser.add_argument("--input", nargs="+", required=True, help="List of .jsonl files to merge")
    merge_parser.add_argument("--output", required=True, help="Path to merged output file")
    merge_parser.set_defaults(func=memory.merge_jsonl)

    # 🔹 LTM Stats
    stats_parser = subparsers.add_parser("ltm-stats", help="Show Chroma memory statistics")
    stats_parser.add_argument("--by", default="topic", help="Group by metadata key (default: topic)")
    stats_parser.set_defaults(func=memory.stats)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
