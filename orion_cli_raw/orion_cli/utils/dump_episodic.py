from orion_cli.orion_ltm_integration import initialize_chromadb_for_ltm
from orion_cli.orion_ltm_integration import COLL_EPISODIC_SENT


def dump_episodic(limit=10):
    collections, _ = initialize_chromadb_for_ltm()
    episodic = collections[COLL_EPISODIC_SENT]

    results = episodic.get(where={}, include=["documents", "metadatas"], limit=limit)
    documents = results.get("documents", [])
    metadatas = results.get("metadatas", [])

    if not documents:
        print("⚠️ No episodic memory found.")
        return

    for i, (doc, meta) in enumerate(zip(documents, metadatas), 1):
        print(f"\n[{i}] 📜 Memory:")
        print(doc)
        print("🧠 Metadata:")
        for k, v in meta.items():
            print(f"  {k}: {v}")


if __name__ == "__main__":
    dump_episodic(limit=10)
