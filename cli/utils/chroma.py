import os
from chromadb import PersistentClient

def reset_and_save_persona(entries, collection="orion_persona", persist_dir="user_data/chroma_db"):
    os.makedirs(persist_dir, exist_ok=True)
    client = PersistentClient(path=persist_dir)
    coll = client.get_or_create_collection(name=collection)

    # Clear existing data
    coll.delete(where={})

    for entry in entries:
        doc_id = f"{collection}_{hash(entry['document']) % (10 ** 8)}"
        coll.add(
            documents=[entry["document"]],
            metadatas=[entry["metadata"]],
            ids=[doc_id]
        )
