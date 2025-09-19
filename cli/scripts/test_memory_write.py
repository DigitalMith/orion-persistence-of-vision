from chromadb import PersistentClient

CHROMA_DIR = "user_data/chroma_db"
COLLECTION_NAME = "orion_ltm"

client = PersistentClient(path=CHROMA_DIR)
collection = client.get_or_create_collection(name=COLLECTION_NAME)

# Test memory
test_text = "Test entry written during LTM recovery. Should appear after Sept 5."
metadata = {
    "kind": "ltm",
    "timestamp": "Sep 17, 2025 22:40",
    "source": "manual-test"
}

doc_id = "test-ltm-" + str(hash(test_text))[:8]

collection.add(
    documents=[test_text],
    metadatas=[metadata],
    ids=[doc_id]
)

print(f"✅ Test memory saved with ID: {doc_id}")
