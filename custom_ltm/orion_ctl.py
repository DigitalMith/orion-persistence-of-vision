# custom_ltm/orion_ctl.py  (fixed + seed-jsonl)
import os, argparse, json, shutil, time, hashlib
from pathlib import Path
from custom_ltm.chroma_utils import get_client as _chroma_client, get_collection as _get_collection
# from chromadb.utils import embedding_functions
from orion_memory.memory.embedding import Embedder

class OrionEmbedder:
    def __init__(self):
        self._inner = Embedder()  # your 768-d embedder

    # Chroma calls the embedding function like a callable
    def __call__(self, texts):
        return self._inner.encode(texts)

    # Some Chroma versions also look for these:
    def embed_documents(self, texts):
        return self._inner.encode(texts)

    def embed_query(self, text):
        return self._inner.encode([text])[0]

    # Chroma checks for conflicts via a name() method
    def name(self):
        return "orion-embedder-768d"

EMBED = OrionEmbedder()

# --- Optional policy/guardrails ---
try:
    from policy_loader import load_policy, enforce_on_pairs  # optional
except Exception:
    def load_policy(path): return {}
    def enforce_on_pairs(docs, metas, policy, phase): return docs, metas

ROOT = Path(__file__).resolve().parents[1]  # ...\text-generation-webui
CHROMA_DB_PATH = Path(os.getenv("CHROMA_DB_PATH", ROOT / "user_data" / "chroma_db"))

# Collections
COLL_PERSONA        = os.getenv("ORION_PERSONA_COLLECTION",        "orion_persona_ltm")
COLL_EPISODIC       = os.getenv("ORION_EPISODIC_COLLECTION",       "orion_episodic_ltm")
COLL_EPISODIC_SENT  = os.getenv("ORION_EPISODIC_SENT_COLLECTION",  "orion_episodic_sent_ltm")
COLL_WEB            = os.getenv("ORION_WEB_COLLECTION",            "orion_web_ltm")

# Inputs (legacy convenience)
PERSONA_FILE  = Path(os.getenv("ORION_PERSONA_FILE", r"C:\Orion\memory\Orion_Data.txt"))
CHAT_DIR      = Path(os.getenv("ORION_CHAT_DIR",   r"C:\Orion\memory\chat"))
LTM_JSON      = Path(os.getenv("ORION_LONG_TERM_MEMORY_FILE", r"C:\Orion\memory\long_term_memory.json"))

# # Embeddings
# EMBED = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")

def get_client():
    return _chroma_client(str(CHROMA_DB_PATH))

def get_col(name: str):
    c = get_client()
    try:
        # If it already exists, open it WITHOUT providing an embedding function
        return c.get_collection(name)
    except Exception:
        # Only when creating a NEW collection, provide our embedder
        return c.get_or_create_collection(name=name, embedding_function=EMBED)

# ---------- helpers ----------
def persona_lines_from_file(path: Path):
    if not path.is_file():
        print(f"ERROR: Persona file not found: {path}")
        return []
    blocks, seen, out = [], set(), []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):       # comments
            continue
        if s.startswith("[") and s.endswith("]"):  # section headers
            continue
        if s.startswith("-"):
            s = s[1:].strip()
        if len(s) > 10:
            blocks.append(s)
    for b in blocks:
        if b not in seen:
            seen.add(b)
            out.append(b)
    return out

def episodic_id(key: str) -> str:
    return "episodic_" + hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]

def sha12(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]
    
def _sanitize_metadata(meta: dict) -> dict:
    allowed = (str, int, float, bool, type(None))
    out = {}
    for k, v in (meta or {}).items():
        if isinstance(v, allowed):
            out[k] = v
        elif isinstance(v, (list, tuple, set)):
            out[f"{k}_csv"] = "|".join(map(str, v))
        elif isinstance(v, dict):
            out[f"{k}_json"] = json.dumps(v, ensure_ascii=False)
        else:
            out[k] = str(v)
    return out

# ---------- commands ----------
def cmd_inspect(_args):
    c = get_client()
    print("DB:", CHROMA_DB_PATH)
    for info in c.list_collections():
        col = get_col(info.name)  # but ensure get_col() first tries get_collection() w/o EMBED (which you already patched)
        try:
            n = col.count()
        except Exception:
            n = "?"
        print(f"- {info.name}: {n}")

def cmd_backup_fs(_args):
    ts = time.strftime("%Y-%m-%d_%H-%M-%S")
    dst = ROOT / "backups" / "chroma" / f"{ts}"
    shutil.copytree(CHROMA_DB_PATH, dst, dirs_exist_ok=True)
    print("Backup ->", dst)

def export_jsonl(coll_name: str, out_path: Path):
    col = get_col(coll_name)
    total = col.count()
    limit, offset = 1000, 0
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        while offset < total:
            batch = col.get(limit=limit, offset=offset, include=["documents", "metadatas", "ids"])
            ids = batch.get("ids") or []
            docs = batch.get("documents") or []
            metas = batch.get("metadatas") or []
            for _id, doc, meta in zip(ids, docs, metas):
                f.write(json.dumps({"id": _id, "document": doc, "metadata": meta}, ensure_ascii=False) + "\n")
            offset += len(ids)
    print(f"Exported {total} -> {out_path}")

def cmd_export(args):
    export_jsonl(args.collection, Path(args.out))

def _load_policy(args):
    if getattr(args, "policy", None):
        try:
            return load_policy(args.policy)
        except Exception as e:
            print(f"[policy] Warning: failed to load '{args.policy}': {e}")
    return {}

def cmd_seed_persona(args):
    policy = _load_policy(args)
    col = get_col(COLL_PERSONA)

    # Remove ONLY prior persona from same source (fresh replace)
    src = "Orion_Data.txt"
    existing = col.get(include=["metadatas","ids"])
    to_del = [i for i, m in zip(existing.get("ids") or [], (existing.get("metadatas") or []))
              if isinstance(m, dict) and m.get("source") == src]
    if to_del:
        if args.dry_run:
            print(f"[dry-run] would delete {len(to_del)} old persona items (source={src})")
        else:
            col.delete(ids=to_del)
            print(f"Deleted {len(to_del)} old persona items (source={src})")

    lines = persona_lines_from_file(PERSONA_FILE)
    ids   = [f"persona_{sha12(s)}" for s in lines]
    metas = [{"type": "persona", "source": src} for _ in lines]

    # apply policy if provided
    lines, metas = enforce_on_pairs(lines, metas, policy, phase="seed_persona")

    if not args.dry_run and ids:
        # upsert if available; else add
        if hasattr(col, "upsert"):
            col.upsert(ids=ids, documents=lines, metadatas=metas)
        else:
            col.add(ids=ids, documents=lines, metadatas=metas)
    print(f"Persona seeded: {len(ids)} (dry-run={args.dry_run})")

def cmd_make_episodic_sentences(args):
    try:
        from custom_ltm.memory_sentencer import make_memory_points, sentence_id
    except ModuleNotFoundError:
        try:
            from memory_sentencer import make_memory_points, sentence_id
        except ModuleNotFoundError:
            print("[ERROR] memory_sentencer.py not found in custom_ltm")
            return 1
    src = get_col(COLL_EPISODIC)
    dst = get_col(COLL_EPISODIC_SENT)

    total = src.count()
    limit, offset = 500, 0
    added = 0

    while offset < total:
        b = src.get(limit=limit, offset=offset, include=["documents","metadatas","ids"])
        ids, docs, metas = b.get("ids") or [], b.get("documents") or [], b.get("metadatas") or []
        if not ids: break

        up_ids, up_docs, up_meta = [], [], []
        for _id, doc, md in zip(ids, docs, metas):
            if not doc:
                continue
            role = (md or {}).get("role", "unknown")
            sid  = (md or {}).get("session_id", "na")
            when = (md or {}).get("timestamp", "na")

            pts = make_memory_points(doc, role=role, session_id=sid, when=when, max_points=args.max_points)
            for p in pts:
                new_id = sentence_id(_id, p["text"])
                up_ids.append(new_id)
                up_docs.append(p["text"])

                tag_list = list(dict.fromkeys(p.get("tags", [])))
                kw_list  = list(dict.fromkeys(p.get("keywords", [])))

                meta = {
                    "type": "episodic_sentence",
                    "parent_id": _id,
                    "role": p.get("role", role),
                    "session_id": p.get("session_id", sid),
                    "timestamp": p.get("timestamp", when),
                    "tags_csv": "|".join(tag_list),
                    "keywords_csv": "|".join(kw_list),
                    "sentiment": p.get("sentiment", "neutral"),
                    "emotion":   p.get("emotion", "neutral"),
                    "importance": float(p.get("importance", 0.0)),
                    "source": "sentencer:v1",
                }
                for t in tag_list[:10]:
                    meta[f"tag_{t}"] = True
                for w in kw_list[:10]:
                    meta[f"kw_{w}"] = True
                up_meta.append(meta)

        if up_ids and not args.dry_run:
            if hasattr(dst, "upsert"):
                dst.upsert(ids=up_ids, documents=up_docs, metadatas=up_meta)
            else:
                dst.add(ids=up_ids, documents=up_docs, metadatas=up_meta)
            added += len(up_ids)
        offset += len(ids)

    print(f"{'Would add' if args.dry_run else 'Added'} {added} sentenced items (max_points={args.max_points}).")

def cmd_seed_episodic(args):
    policy = _load_policy(args)
    col = get_col(COLL_EPISODIC)
    existing_ids = set((col.get(include=["ids"]).get("ids") or []))

    new_ids, new_docs, new_meta = [], [], []

    # 1) Chat transcripts
    if CHAT_DIR.is_dir():
        for f in sorted(CHAT_DIR.glob("*.json")):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
            except Exception as e:
                print(f"Skipping {f.name}: {e}")
                continue
            turns = data.get("messages") if isinstance(data, dict) else data
            if not isinstance(turns, list):
                continue
            sid = f.stem
            for i, t in enumerate(turns):
                role = (t.get("role") or t.get("speaker") or "unknown").lower()
                text = (t.get("content") or t.get("text") or "").strip()
                when = t.get("timestamp") or t.get("time") or sid
                if not text:
                    continue
                _id = episodic_id(f"{sid}|{i:06d}|{role}|{text}|{when}")
                if _id in existing_ids:
                    continue
                new_ids.append(_id)
                new_docs.append(f"[{role} at {when}]: {text}")
                new_meta.append({"type": "episodic", "role": role, "timestamp": str(when), "session_id": sid})

    # 2) Optional long_term_memory.json
    if LTM_JSON.is_file():
        try:
            data = json.loads(LTM_JSON.read_text(encoding="utf-8"))
            items = data if isinstance(data, list) else data.get("messages", [])
            if isinstance(items, list):
                for i, t in enumerate(items):
                    role = (t.get("role") or t.get("speaker") or "unknown").lower()
                    text = (t.get("content") or t.get("text") or "").strip()
                    when = t.get("timestamp") or t.get("time") or "n/a"
                    if not text:
                        continue
                    _id = episodic_id(f"ltm|{i:06d}|{role}|{text}|{when}")
                    if _id in existing_ids:
                        continue
                    new_ids.append(_id)
                    new_docs.append(f"[{role} at {when}]: {text}")
                    new_meta.append({"type": "episodic", "role": role, "timestamp": str(when), "session_id": "long_term_memory"})
        except Exception as e:
            print(f"Warning reading LTM: {e}")

    # apply policy if provided
    new_docs, new_meta = enforce_on_pairs(new_docs, new_meta, policy, phase="seed_episodic")

    if not args.dry_run and new_ids:
        col.add(ids=new_ids, documents=new_docs, metadatas=new_meta)
    print(f"Episodic added: {len(new_ids)} (dry-run={args.dry_run})")

def _route_collection_for_type(t: str) -> str:
    t = (t or "").lower()
    if t in ("self","semantic","procedural","policy","credo","identity"):
        return COLL_PERSONA
    if t in ("episodic","episodic_sentence"):
        return COLL_EPISODIC if t == "episodic" else COLL_EPISODIC_SENT
    if t in ("reference","web"):
        return COLL_WEB
    # default to persona for stable seeds
    return COLL_PERSONA

def cmd_seed_jsonl(args):
    path = Path(args.path)
    if not path.is_file():
        print(f"ERROR: seed file not found: {path}")
        return 1

    policy = _load_policy(args)

    # prefetch collections
    cols = {
        COLL_PERSONA: get_col(COLL_PERSONA),
        COLL_EPISODIC: get_col(COLL_EPISODIC),
        COLL_EPISODIC_SENT: get_col(COLL_EPISODIC_SENT),
        COLL_WEB: get_col(COLL_WEB),
    }

    add_count = 0
    with path.open("r", encoding="utf-8") as f:
        batch_ids, batch_docs, batch_meta, batch_cols = [], [], [], []
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception as e:
                print(f"Skipping malformed JSONL line: {e}")
                continue

            text = (rec.get("text") or rec.get("document") or "").strip()
            if not text:
                continue

            rid  = rec.get("id") or sha12(text)
            rtyp = (rec.get("type") or "semantic").lower()
            col_name = _route_collection_for_type(rtyp)
            meta = dict(rec)
            # normalize fields into metadata
            meta["type"] = rtyp
            meta.pop("text", None)
            meta.pop("document", None)
            meta.setdefault("source", "seed_jsonl")
            meta = _sanitize_metadata(meta)

            # policy hook (per item)
            [text2], [meta2] = enforce_on_pairs([text], [meta], policy, phase="seed_jsonl")
            text, meta = text2, meta2

            batch_ids.append(rid)
            batch_docs.append(text)
            batch_meta.append(meta)
            batch_cols.append(col_name)

        # group by collection and write
        for col_name in set(batch_cols):
            col = cols[col_name]
            ids  = [i for i,cname in zip(batch_ids, batch_cols) if cname == col_name]
            docs = [d for d,cname in zip(batch_docs, batch_cols) if cname == col_name]
            metas= [m for m,cname in zip(batch_meta, batch_cols) if cname == col_name]
            if not ids:
                continue
            if args.dry_run:
                print(f"[dry-run] would upsert {len(ids)} into {col_name}")
            else:
                if hasattr(col, "upsert"):
                    col.upsert(ids=ids, documents=docs, metadatas=metas)
                else:
                    col.add(ids=ids, documents=docs, metadatas=metas)
                add_count += len(ids)

    print(f"{'Would seed' if args.dry_run else 'Seeded'} {add_count if not args.dry_run else sum(1 for _ in open(path,'r',encoding='utf-8'))} items from {path}")

def cmd_list_by_topic(args):
    col = get_col(args.collection)
    res = col.get(where={args.key: {"$eq": args.value}}, include=["documents", "metadatas","ids"])
    for _id, doc, meta in zip(res.get("ids") or [], res.get("documents") or [], res.get("metadatas") or []):
        print(f"{_id}\n  meta={meta}\n  doc={doc[:200]}{'...' if doc and len(doc) > 200 else ''}\n")

def cmd_seed_all(args):
    cmd_seed_persona(args)
    cmd_seed_episodic(args)
    cmd_inspect(args)

# ---------- entry ----------
def main():
    p = argparse.ArgumentParser(prog="orion_ctl.py")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("inspect");                     s.set_defaults(func=cmd_inspect)
    s = sub.add_parser("backup-fs");                   s.set_defaults(func=cmd_backup_fs)

    s = sub.add_parser("export")
    s.add_argument("--collection", required=True)
    s.add_argument("--out", required=True)
    s.set_defaults(func=cmd_export)

    s = sub.add_parser("seed-persona")
    s.add_argument("--dry-run", action="store_true")
    s.add_argument("--policy", default=None)
    s.set_defaults(func=cmd_seed_persona)

    s = sub.add_parser("seed-episodic")
    s.add_argument("--dry-run", action="store_true")
    s.add_argument("--policy", default=None)
    s.set_defaults(func=cmd_seed_episodic)

    s = sub.add_parser("make-episodic-sentences", help="Build structured episodic sentences from raw")
    s.add_argument("--max-points", type=int, default=2)
    s.add_argument("--dry-run", action="store_true")
    s.set_defaults(func=cmd_make_episodic_sentences)

    s = sub.add_parser("seed-jsonl", help="Seed a JSONL file of records into appropriate collections")
    s.add_argument("--path", required=True)
    s.add_argument("--dry-run", action="store_true")
    s.add_argument("--policy", default=None)
    s.set_defaults(func=cmd_seed_jsonl)

    s = sub.add_parser("list-by-topic")
    s.add_argument("--collection", required=True,
                   choices=[COLL_PERSONA, COLL_EPISODIC, COLL_EPISODIC_SENT, COLL_WEB])
    s.add_argument("--key", required=True)
    s.add_argument("--value", required=True)
    s.set_defaults(func=cmd_list_by_topic)

    s = sub.add_parser("seed-all")
    s.add_argument("--dry-run", action="store_true")
    s.add_argument("--policy", default=None)
    s.set_defaults(func=cmd_seed_all)

    args = p.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
