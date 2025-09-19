import chromadb
from chromadb.config import Settings

def cmd_ltm_peek(args):
    print(f"[ltm-peek] Connecting to ChromaDB at: {args.db}")
    client = chromadb.PersistentClient(path=args.db, settings=Settings(anonymized_telemetry=False))

    try:
        collection = client.get_collection(name=args.collection)
    except Exception as e:
        print(f"[ltm-peek] Error: {e}")
        return

    results = collection.get(include=["documents", "metadatas"])
    docs = results.get("documents", [])
    metas = results.get("metadatas", [])

    shown = 0
    print(f"[ltm-peek] Retrieved {len(docs)} documents from collection: {args.collection}")
    for i, (doc, meta) in enumerate(zip(docs, metas)):
        if shown >= args.n:
            break
        if args.kind != "all" and meta.get("kind") != args.kind:
            continue
        if args.topic and meta.get("topic") != args.topic:
            continue
        shown += 1
        print("="*60)
        print(f"Entry #{shown}")
        print(f"ID: {meta.get('id')}")
        print(f"Kind: {meta.get('kind')}")
        print(f"Topic: {meta.get('topic')}")
        if args.raw:
            print(f"Text: {doc}")
        else:
            preview = doc[:300].replace("\n", " ")
            print(f"Preview: {preview}...")

    if shown == 0:
        print("[ltm-peek] No entries matched the provided filters.")