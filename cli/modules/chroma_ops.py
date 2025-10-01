# modules/chroma_ops.py

import chromadb

COLLECTION_NAME = "orion_episodic_sent_ltm"
client = chromadb.Client()
collection = client.get_or_create_collection(COLLECTION_NAME)

def query_ltm(query_text, top_k=5):
    try:
        result = collection.query(query_texts=[query_text], n_results=top_k)
        docs = result.get("documents", [[]])[0]
        return docs
    except Exception as e:
        print(f"❌ LTM Query failed: {e}")
        return []

def delete_by_topic(topic, filters=None, confirm=True):
    print(f"⚠️ Request to delete topic: '{topic}' with filters: {filters or 'None'}")

    if confirm:
        user_input = input("Are you sure? This cannot be undone (Y/n): ").strip().lower()
        if user_input != 'y':
            print("❌ Aborted.")
            return

    try:
        all_data = collection.get()
        ids_to_delete = []

        for doc_id, meta in zip(all_data["ids"], all_data["metadatas"]):
            if meta.get("topic") != topic:
                continue

            if filters:
                match = all(
                    str(meta.get(k, "")).lower() == v.lower()
                    for k, v in filters.items()
                )
                if not match:
                    continue

            ids_to_delete.append(doc_id)

        if not ids_to_delete:
            print("ℹ️ No matching entries found.")
            return

        print(f"🧨 Deleting {len(ids_to_delete)} entries...")
        collection.delete(ids=ids_to_delete)
        print("✅ Deletion complete.")

    except Exception as e:
        print(f"❌ Deletion failed: {e}")

    try:
        all_data = collection.get()
        ids_to_delete = []

        for doc_id, metadata in zip(all_data["ids"], all_data["metadatas"]):
            if metadata.get("topic") == topic:
                ids_to_delete.append(doc_id)

        if not ids_to_delete:
            print(f"ℹ️ No entries found for topic: {topic}")
            return

        print(f"🧨 Deleting {len(ids_to_delete)} entries...")
        collection.delete(ids=ids_to_delete)
        print("✅ Deletion complete.")

    except Exception as e:
        print(f"❌ Deletion failed: {e}")

def export_by_topic(topic, output_path, filters=None):
    try:
        all_data = collection.get()
        docs = all_data["documents"]
        metadatas = all_data["metadatas"]

        exported = 0
        with open(output_path, "w", encoding="utf-8") as f:
            for doc, meta in zip(docs, metadatas):
                if meta.get("topic") != topic:
                    continue

                if filters:
                    match = all(
                        str(meta.get(k, "")).lower() == v.lower()
                        for k, v in filters.items()
                    )
                    if not match:
                        continue

                line = {
                    "text": doc,
                    "metadata": meta
                }
                f.write(json.dumps(line) + "\n")
                exported += 1

        print(f"📤 Exported {exported} entries to {output_path}")

    except Exception as e:
        print(f"❌ Export failed: {e}")

