# delete_by_source.py
import sys
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions

if len(sys.argv) != 2:
    print("Usage: python delete_by_source.py <source_url>")
    sys.exit(1)

source_url = sys.argv[1]
path = r"C:\Orion\text-generation-webui\user_data\chroma_db"

client = chromadb.PersistentClient(
    path=path,
    settings=Settings(anonymized_telemetry=False, allow_reset=True)
)
embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

for col_name in ["orion_web_ltm", "orion_episodic_ltm"]:
    try:
        col = client.get_collection(col_name, embedding_function=embed_fn)
        # Find matching docs
        results = col.get(include=["metadatas", "documents"])
        delete_ids = [
            doc_id for doc_id, meta in zip(results["ids"], results["metadatas"])
            if meta.get("source") == source_url
        ]
        if delete_ids:
            col.delete(ids=delete_ids)
            print(f"Deleted {len(delete_ids)} docs from {col_name}")
        else:
            print(f"No docs found in {col_name} for {source_url}")
    except Exception as e:
        print(f"Error in {col_name}: {e}")
