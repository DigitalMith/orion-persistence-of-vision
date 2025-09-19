from chromadb import PersistentClient
from chromadb.config import Settings
import os

# Set hardcoded absolute or relative-to-script paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ⛏ Source: the accidental DB created during testing
SOURCE_PATH = os.path.join(SCRIPT_DIR, "orion_cli", "cli_support", "chroma_db")

# ✅ Destination: original central ChromaDB
DEST_PATH = os.path.join(SCRIPT_DIR, "user_data", "chroma_db")

def merge_chroma_collections(source_path, dest_path):
    source_client = PersistentClient(path=source_path, settings=Settings(anonymized_telemetry=False))
    dest_client = PersistentClient(path=dest_path, settings=Settings(anonymized_telemetry=False))

    source_collections = source_client.list_collections()
    print(f"[INFO] Found collections in source: {[c.name for c in source_collections]}")

    for collection in source_collections:
        src_coll = source_client.get_collection(name=collection.name)
        dest_coll = dest_client.get_or_create_collection(name=collection.name)

        results = src_coll.get(include=["documents", "metadatas", "embeddings"])

        if not results["ids"]:
            print(f"[SKIP] No records in collection '{collection.name}'")
            continue

        print(f"[MERGE] Transferring {len(results['ids'])} items into '{collection.name}'")
        dest_coll.add(
            ids=results["ids"],
            documents=results["documents"],
            metadatas=results["metadatas"],
            embeddings=results["embeddings"]
        )

    print("\n✅ Merge complete!")

if __name__ == "__main__":
    merge_chroma_collections(SOURCE_PATH, DEST_PATH)
