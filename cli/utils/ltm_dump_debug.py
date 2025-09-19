import os
from datetime import datetime
from chromadb import PersistentClient

CHROMA_PATH = "user_data/chroma_db"
SHOW_LAST_N = 2  # You can increase if needed

def dump_chroma_collections(path, last_n=2):
    abs_path = os.path.abspath(path)
    print("🧭 Chroma path:", abs_path)

    client = PersistentClient(path=path)
    collections = client.list_collections()

    if not collections:
        print("⚠️ No collections found.")
        return

    print("🔍 Available Collections:\n")

    for col in collections:
        name = col.name
        collection = client.get_or_create_collection(name=name)
        results = collection.get()

        docs = results["documents"]
        metas = results["metadatas"]
        count = len(docs)

        print(f"📁 Collection: {name} ({count} documents)")

        if count == 0:
            continue

        print(f"  📝 Showing last {min(last_n, count)} entries:")

        for doc, meta in zip(docs[-last_n:], metas[-last_n:]):
            ts = meta.get("timestamp")
            try:
                ts_float = float(ts)
                ts_fmt = datetime.fromtimestamp(ts_float).strftime('%Y-%m-%d %H:%M:%S')
            except (TypeError, ValueError):
                ts_fmt = "N/A"
            
            preview = doc[:100].replace("\n", " ") + ("..." if len(doc) > 100 else "")
            print(f"    - Saved at: {ts_fmt}")
            print(f"      Text: {preview}")
            print(f"      Metadata: {meta}\n")


if __name__ == "__main__":
    dump_chroma_collections(CHROMA_PATH, SHOW_LAST_N)
