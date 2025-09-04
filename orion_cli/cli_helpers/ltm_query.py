from pathlib import Path

def run(query: str, collection: str = "orion_episodic_sent_ltm", persist_dir: str = "chroma", topk: int = 5):
    try:
        import chromadb
        client = chromadb.PersistentClient(path=persist_dir)
        coll = client.get_or_create_collection(name=collection)
    except Exception as e:
        print(f"[ERROR] Could not open Chroma at '{persist_dir}': {e}")
        return

    try:
        # text-only query (no embedding function; assumes collection has stored embeddings)
        res = coll.query(query_texts=[query], n_results=topk)
    except Exception as e:
        print(f"[ERROR] Query failed: {e}")
        return

    ids = res.get("ids", [[]])[0]
    docs = res.get("documents", [[]])[0]
    metas = res.get("metadatas", [[]])[0]

    if not ids:
        print("No results.")
        return

    print(f"Top-{len(ids)} results for: {query!r}")
    for i, (doc, meta) in enumerate(zip(docs, metas), 1):
        topic = meta.get("topic") if isinstance(meta, dict) else None
        print(f"\n[{i}] topic={topic}  meta={meta}")
        print(doc[:500] + ("..." if len(doc) > 500 else ""))
