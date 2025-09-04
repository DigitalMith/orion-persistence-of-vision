# Merge episodic seeding (no destructive delete)
import os, json, hashlib
from pathlib import Path

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = (SCRIPT_DIR / "..").resolve()

EPISODIC_COLLECTION_NAME = os.getenv("ORION_EPISODIC_COLLECTION", "orion_episodic_ltm")
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", str(PROJECT_ROOT / "user_data" / "chroma_db"))
CHAT_DIR = Path(os.getenv("ORION_CHAT_DIR", r"C:\Orion\memory\chat"))
LONG_TERM_MEMORY_FILE = Path(os.getenv("ORION_LONG_TERM_MEMORY_FILE", r"C:\Orion\memory\long_term_memory.json"))

EMBED_FN = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

def make_id(session_id, idx, role, content, when):
    key = f"{session_id}|{idx:06d}|{role}|{content}|{when}"
    return "episodic_" + hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]

def get_client():
    return chromadb.PersistentClient(path=CHROMA_DB_PATH, settings=Settings(anonymized_telemetry=False))

def iter_turns():
    # 1) Chat transcripts
    if CHAT_DIR.is_dir():
        for f in sorted(CHAT_DIR.glob("*.json")):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
            except Exception as e:
                print(f"Skipping {f.name}: {e}")
                continue
            session_id = f.stem
            turns = data.get("messages") if isinstance(data, dict) else data
            if not isinstance(turns, list):
                continue
            fallback_time = session_id
            for i, t in enumerate(turns):
                role = (t.get("role") or t.get("speaker") or "unknown").lower()
                content = (t.get("content") or t.get("text") or "").strip()
                when = t.get("timestamp") or t.get("time") or fallback_time
                if not content:
                    continue
                yield session_id, i, role, content, str(when), "normal", []
                

    # 2) Optional long_term_memory.json
    if LONG_TERM_MEMORY_FILE.is_file():
        try:
            data = json.loads(LONG_TERM_MEMORY_FILE.read_text(encoding="utf-8"))
            turns = data if isinstance(data, list) else data.get("messages", [])
            if isinstance(turns, list):
                for i, t in enumerate(turns):
                    role = (t.get("role") or t.get("speaker") or "unknown").lower()
                    content = (t.get("content") or t.get("text") or "").strip()
                    when = t.get("timestamp") or t.get("time") or "n/a"
                    if not content:
                        continue
                    yield "long_term_memory", i, role, content, str(when), t.get("importance","normal"), (t.get("tags") or [])
        except Exception as e:
            print(f"Warning reading long_term_memory.json: {e}")

def main():
    print(f"Chroma path: {CHROMA_DB_PATH}")
    print(f"Chat dir:    {CHAT_DIR}")
    print(f"LTM file:    {LONG_TERM_MEMORY_FILE}")

    client = get_client()

    # Get or create collection (NO DELETE)
    try:
        episodic = client.get_collection(EPISODIC_COLLECTION_NAME, embedding_function=EMBED_FN)
    except Exception:
        episodic = client.create_collection(EPISODIC_COLLECTION_NAME, embedding_function=EMBED_FN)

    # Gather existing IDs so we don't duplicate
    existing = episodic.get(include=["metadatas"])
    existing_ids = set(existing.get("ids", []) or [])

    new_docs, new_ids, new_metas = [], [], []
    inrun_ids = set()  # prevent duplicates in the same batch

    for session_id, idx, role, content, when, importance, tags in iter_turns():
        doc_id = make_id(session_id, idx, role, content, when)
        if doc_id in existing_ids or doc_id in inrun_ids:
            continue
        inrun_ids.add(doc_id)
        new_ids.append(doc_id)
        new_docs.append(f"[{role} at {when}]: {content}")
        new_metas.append({
            "type": "episodic", "role": role, "timestamp": when,
            "session_id": session_id, "importance": str(importance),
            "tags": ", ".join(tags or [])
        })

    if new_ids:
        episodic.add(documents=new_docs, metadatas=new_metas, ids=new_ids)

    print(f"Added {len(new_ids)} new episodic memories (skipped existing).")
    try:
        print(f"Collection count now: {episodic.count()}")
    except Exception:
        pass

if __name__ == "__main__":
    main()
