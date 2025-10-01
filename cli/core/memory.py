# core/memory.py

from modules import chroma_ops, summary

def query(args):
    print(f"🔍 Querying LTM: '{args.query}'")
    results = chroma_ops.query_ltm(args.query)
    if not results:
        print("⚠️ No results found.")
    for r in results:
        print("➤", r)

def summarize(args):
    print("📚 Summarizing long-term memory...")
    summary.summarize_memory()

def restore(args):
    from modules import restore_ltm
    restore_ltm.restore_from_jsonl(args.file)

def normalize(args):
    from modules import normalize_chatlogs
    normalize_chatlogs.normalize_chatlog(args.input, args.output)

def delete_topic(args):
    from modules import chroma_ops

    filters = {}
    if args.filter:
        for f in args.filter:
            if "=" in f:
                k, v = f.split("=", 1)
                filters[k.strip()] = v.strip()

    chroma_ops.delete_by_topic(args.topic, filters=filters, confirm=not args.force)

def export_topic(args):
    from modules import chroma_ops

    filters = {}
    if args.filter:
        for f in args.filter:
            if "=" in f:
                k, v = f.split("=", 1)
                filters[k.strip()] = v.strip()

    chroma_ops.export_by_topic(args.topic, args.output, filters)

def merge_jsonl(args):
    from modules import file_utils
    file_utils.merge_jsonl_files(args.input, args.output)

def stats(args):
    from modules import chroma_stats
    chroma_stats.print_stats(group_by=args.by)
