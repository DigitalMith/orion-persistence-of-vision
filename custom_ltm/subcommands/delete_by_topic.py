# delete_by_topic.py
import sys
from orion_memory import OrionMemory

if len(sys.argv) != 2:
    print("Usage: python delete_by_topic.py <topic>")
    sys.exit(1)

topic = sys.argv[1]
mem = OrionMemory(path=r"C:\Orion\text-generation-webui\user_data\chroma_db")

for collection in [mem._col_web, mem._col_epi]:
    results = collection.get(include=["metadatas"])
    ids_to_delete = [
        doc_id for doc_id, meta in zip(results["ids"], results["metadatas"])
        if meta.get("tags") and topic.lower() in meta["tags"].lower()
    ]
    if ids_to_delete:
        collection.delete(ids=ids_to_delete)
        print(f"Deleted {len(ids_to_delete)} docs from {collection.name}")
    else:
        print(f"No docs found for {topic} in {collection.name}")
