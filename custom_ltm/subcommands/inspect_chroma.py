import os, chromadb
from chromadb.config import Settings

CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", r"C:\Orion\text-generation-webui\user_data\chroma_db")
c = chromadb.PersistentClient(path=CHROMA_DB_PATH, settings=Settings(anonymized_telemetry=False))
print("DB path:", CHROMA_DB_PATH)
for col in c.list_collections():
    name = col.name
    try:
        cnt = c.get_collection(name).count()
    except Exception:
        cnt = "?"
    print(f"- {name}: {cnt}")
