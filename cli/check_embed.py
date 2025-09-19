from chromadb import PersistentClient

persist_path = "user_data/chroma_db"
collection_name = "orion_episodic_sent_ltm"

client = PersistentClient(path=persist_path)
coll = client.get_or_create_collection(name=collection_name)

batch_size = 100
offset = 0
total_checked = 0
missing_embeddings = 0

while True:
    results = coll.get(
        include=["documents", "embeddings"],
        offset=offset,
        limit=batch_size
    )
    docs = results["documents"]
    embeddings = results["embeddings"]
    ids = results["ids"]  # This is always returned

    if not docs:
        break

    for doc_id, emb in zip(ids, embeddings):
        total_checked += 1
        if emb is None or len(emb) == 0:
            missing_embeddings += 1
            print(f"⚠️ Missing embedding for doc: {doc_id}")

    offset += batch_size

print(f"✅ Checked {total_checked} documents; missing embeddings: {missing_embeddings}")
