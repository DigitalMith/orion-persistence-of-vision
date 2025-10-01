# modules/chroma_validator.py

import chromadb
from modules.embedding_provider import get_vector_dim

def run_check():
    DIM = get_vector_dim()
    client = chromadb.Client()
    collection = client.get_or_create_collection("orion_episodic_sent_ltm")

    print("🔍 Checking embedding dimensions in ChromaDB...")

    try:
        results = collection.get()
        docs = results.get("documents", [])
        embeddings = results.get("embeddings", [])
        ids = results.get("ids", [])

        if not embeddings:
            print("⚠️ No embeddings found!")
            return

        total = len(embeddings)
        correct = 0
        invalid = 0

        for i, emb in enumerate(embeddings):
            if emb is None or len(emb) != DIM:
                print(f"❌ [Invalid] ID: {ids[i]} | Dim: {len(emb) if emb else 'None'}")
                invalid += 1
            else:
                correct += 1

        print("\n✅ Summary:")
        print(f"  Total entries: {total}")
        print(f"  Valid: {correct}")
        print(f"  Invalid: {invalid}")

    except Exception as e:
        print(f"💥 Check failed: {e}")
