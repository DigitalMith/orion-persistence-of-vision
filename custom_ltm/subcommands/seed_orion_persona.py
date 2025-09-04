import os, hashlib
import chromadb
from chromadb.utils import embedding_functions
from chromadb.config import Settings

# --- Config ---
SCRIPT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))

CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", os.path.join(PROJECT_ROOT, "user_data", "chroma_db"))
PERSONA_COLLECTION_NAME = os.getenv("ORION_PERSONA_COLLECTION", "orion_persona_ltm")
ORION_DATA_FILE = os.getenv("ORION_PERSONA_FILE", r"C:\Orion\memory\Orion_Data.txt")
SOURCE_TAG = "Orion_Data.txt"  # we'll only replace docs from this source

EMBED_FN = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

def load_orion_persona(file_path):
    persona_statements = []
    if not os.path.exists(file_path):
        print(f"ERROR: Persona file not found at {file_path}")
        return []
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Extract sections simply: keep non-empty lines not starting with '[' headers
    blocks = []
    # you can keep your original parsing logic; here we just keep it robust
    for line in content.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        # Skip section headers like [IDENTITY] but keep their content
        if s.startswith("[") and s.endswith("]"):
            continue
        # Normalize bullet formatting
        if s.startswith("-"):
            s = s[1:].strip()
        if len(s) > 10:
            blocks.append(s)

    # dedupe while preserving order
    seen = set(); out = []
    for b in blocks:
        if b not in seen:
            seen.add(b); out.append(b)
    return out

def stable_id(prefix: str, text: str) -> str:
    h = hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{h}"

def main():
    print(f"Chroma path: {CHROMA_DB_PATH}")
    print(f"Persona file: {ORION_DATA_FILE}")

    client = chromadb.PersistentClient(
        path=CHROMA_DB_PATH,
        settings=Settings(anonymized_telemetry=False)
    )

    # Get or create collection (NO DELETE)
    try:
        persona = client.get_collection(PERSONA_COLLECTION_NAME, embedding_function=EMBED_FN)
    except Exception:
        persona = client.create_collection(PERSONA_COLLECTION_NAME, embedding_function=EMBED_FN)

    # Load existing docs (metas + ids)
    existing = persona.get(include=["metadatas", "documents"])
    existing_ids = existing.get("ids", []) or []
    existing_metas = existing.get("metadatas", []) or []

    # Remove ONLY old persona docs from same source (fresh replace)
    to_delete = [doc_id for doc_id, meta in zip(existing_ids, existing_metas)
                 if isinstance(meta, dict) and meta.get("source") == SOURCE_TAG]
    if to_delete:
        persona.delete(ids=to_delete)
        print(f"Removed {len(to_delete)} old persona lines from source={SOURCE_TAG}")

    # Prepare new persona docs with stable IDs
    persona_docs = load_orion_persona(ORION_DATA_FILE)
    if not persona_docs:
        print(f"Warning: No persona statements loaded from {ORION_DATA_FILE}.")
        return

    new_ids = [stable_id("persona", d) for d in persona_docs]
    new_metas = [{"type": "persona", "source": SOURCE_TAG} for _ in persona_docs]

    # Add (idempotent-ish: re-run yields same IDs)
    persona.add(documents=persona_docs, metadatas=new_metas, ids=new_ids)

    print(f"Added {len(persona_docs)} persona statements.")
    try:
        print(f"Collection count now: {persona.count()}")
    except Exception:
        pass

if __name__ == "__main__":
    main()
