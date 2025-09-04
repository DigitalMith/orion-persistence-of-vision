from __future__ import annotations
import re, hashlib
import json
from pathlib import Path
from typing import List, Dict, Any
from chromadb import PersistentClient
from sentence_transformers import SentenceTransformer
from cli_helpers.utils import normalize_topic

DEFAULT_DB_PATH = "user_data/chroma_db"
DEFAULT_COLLECTION = "orion_episodic_sent_ltm"

def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    items = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except Exception:
                # Skip bad lines but do not crash
                continue
    return items

def _ensure_lists(xs, name: str):
    if not isinstance(xs, list):
        raise ValueError(f"{name} must be a list (got {type(xs)})")

def run(
    staged_path: str = "LTM_Staged/summaries.jsonl",
    persist_dir: str = "chroma",
    collection_name: str = "orion_episodic_sent_ltm",
    batch_size: int = 256,
):
    try:
        import chromadb
    except Exception as e:
        print(f"[ERROR] ChromaDB not installed: {e}")
        return

    try:
        from sentence_transformers import SentenceTransformer
    except Exception as e:
        print(f"[ERROR] sentence-transformers not installed: {e}")
        print("       pip install sentence-transformers")
        return

    staged = Path(staged_path)
    if not staged.exists():
        print(f"[ERROR] Staged file not found: {staged}")
        return

    items = _load_jsonl(staged)
    if not items:
        print(f"[INFO] Nothing to ingest in {staged}")
        return

    # prepare client & collection
    client = chromadb.PersistentClient(path=persist_dir)
    coll = client.get_or_create_collection(name=collection_name)

    # build arrays
    ids, docs, metas = [], [], []
    for it in items:
        _id = it.get("id") or f"row_{len(ids)}"
        text = (it.get("text") or "").strip()
        if not text:
            continue
        meta = {
            "topic": it.get("topic", "general"),
            "tags": it.get("tags", []),
            **(it.get("metadata") or {}),
        }
        # flatten tags for easier SQL filters; Chroma stores JSON fine but simple is ok
        if isinstance(meta.get("tags"), list):
            meta["tags_csv"] = ",".join(str(t) for t in meta["tags"])
        ids.append(str(_id))
        docs.append(text)
        metas.append(meta)

    if not ids:
        print("[INFO] No valid rows to ingest (empty texts).")
        return

    # embed & add in batches
    model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")
    added = 0
    for start in range(0, len(docs), batch_size):
        end = min(start + batch_size, len(docs))
        batch_docs = docs[start:end]
        batch_ids = ids[start:end]
        batch_metas = metas[start:end]
        vecs = model.encode(batch_docs, show_progress_bar=False, convert_to_numpy=True)
        # Ensure lengths align
        _ensure_lists(batch_ids, "ids")
        _ensure_lists(batch_docs, "documents")
        _ensure_lists(batch_metas, "metadatas")

        coll.add(ids=batch_ids, documents=batch_docs, metadatas=batch_metas, embeddings=vecs.tolist())
        added += len(batch_ids)

    print(f"✅ Ingested {added} items into Chroma → collection='{collection_name}' (persist='{persist_dir}')")

def _chunks_from_text(text: str):
    """Split text into manageable chunks (paragraphs/sentences)."""
    paras = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]
    chunks = []
    for p in paras:
        if len(p) > 2000:  # break down huge paragraphs
            parts = re.split(r'(?<=[\.\!\?])\s+', p)
            buf = ""
            for s in parts:
                if len(buf) + len(s) + 1 > 1200:
                    chunks.append(buf.strip())
                    buf = s
                else:
                    buf = (buf + " " + s).strip()
            if buf:
                chunks.append(buf)
        else:
            chunks.append(p)
    return [c for c in chunks if c]

def ingest_txt_direct(
    file_path: str,
    topic: str,
    tags: list[str] | None = None,
    persist_dir: str = DEFAULT_DB_PATH,
    collection_name: str = DEFAULT_COLLECTION,
    add_full_doc: bool = True,
    batch_size: int = 128,
) -> int:
    """Directly ingest a .txt file: chunked + optional full-doc record."""
    tags = tags or []
    p = Path(file_path)
    text = p.read_text(encoding="utf-8", errors="ignore")

    # --- normalize + prepare ---
    topic_norm = normalize_topic(topic)
    tags_csv = ",".join(tags) if tags else ""

    chunks = _chunks_from_text(text)
    client = PersistentClient(path=persist_dir)
    coll = client.get_or_create_collection(name=collection_name)
    model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")

    docs, metas, ids = [], [], []
    base_id = hashlib.sha1((str(p.resolve()) + str(p.stat().st_mtime)).encode("utf-8")).hexdigest()

    # chunk records (skip empties)
    for i, c in enumerate(chunks):
        c = (c or "").strip()
        if not c:
            continue
        docs.append(c)
        metas.append({
            "topic": topic_norm,
            "topic_raw": topic,
            "source": "txt",
            "file": p.name,
            "tags": tags_csv,
            "chunk": i
        })
        ids.append(f"{base_id}_c{i}")

    # optional full-doc record (only if non-empty)
    full_doc = (text or "").strip()
    if add_full_doc and full_doc:
        docs.append(full_doc[:20000])  # safety cap
        metas.append({
            "topic": topic_norm,
            "topic_raw": topic,
            "source": "txt",
            "file": p.name,
            "tags": tags_csv,
            "chunk": "full"
        })
        ids.append(f"{base_id}_full")

    # --- final sanity: keep arrays perfectly aligned ---
    n = min(len(docs), len(metas), len(ids))
    docs, metas, ids = docs[:n], metas[:n], ids[:n]

    if n == 0:
        return 0

    # embed + UPSERT in batches (so re-ingest updates metadata)
    total = 0
    for i in range(0, n, batch_size):
        D = docs[i:i+batch_size]
        M = metas[i:i+batch_size]
        I = ids[i:i+batch_size]
        E = model.encode(D, convert_to_numpy=True, normalize_embeddings=True).tolist()
        # lengths must match exactly
        assert len(D) == len(M) == len(I) == len(E), f"batch mismatch: {len(D)}, {len(M)}, {len(I)}, {len(E)}"
        coll.upsert(documents=D, metadatas=M, ids=I, embeddings=E)
        total += len(D)

    return total
