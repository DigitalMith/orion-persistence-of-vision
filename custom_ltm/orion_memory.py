from custom_ltm.chroma_utils import get_client, get_collection, query_texts
from chromadb.utils import embedding_functions

ROOT = Path(__file__).resolve().parents[1]
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", str(ROOT / "user_data" / "chroma_db"))

COLL_EPISODIC_RAW  = os.getenv("ORION_EPISODIC_COLLECTION",      "orion_episodic_ltm")
COLL_EPISODIC_SENT = os.getenv("ORION_EPISODIC_SENT_COLLECTION", "orion_episodic_sent_ltm")

EMBED = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

def _client():
    return get_client(CHROMA_DB_PATH)

def _get(name: str):
    c = _client()
    return get_collection(c, name, embedding_function=EMBED)

def _flatten_query(res: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    ids = res.get("ids") or []
    docs = res.get("documents")
    metas = res.get("metadatas")
    dists = res.get("distances")
    for i in range(len(ids)):
        for j, _id in enumerate(ids[i]):
            out.append({
                "id": _id,
                "document": (docs[i][j] if docs else None),
                "metadata": (metas[i][j] if metas else None),
                "distance": (dists[i][j] if dists else None),
                "query_index": i,
                "rank": j,
            })
    return out

def prefer_sentenced(
    queries: Iterable[str],
    n_results: int = 8,
    importance_threshold: float = 0.5,
    fallback_to_raw: bool = True,
) -> List[Dict[str, Any]]:
    """Query sentenced memories first; optionally top-up from raw episodic."""
    sent = _get(COLL_EPISODIC_SENT)
    raw  = _get(COLL_EPISODIC_RAW)

    # 1) sentenced first with importance threshold
    sent_res = query_texts(
        sent,
        list(queries),
        top_k=n_results,
        where={"importance": {"$gte": importance_threshold}},
    )
    hits = _flatten_query(sent_res)
    seen_ids = {h.get("id") for h in hits}
    need = max(0, n_results - len(hits))

    # 2) optional fallback to raw episodic if not enough sentenced hits
    if fallback_to_raw and need > 0:
        raw_res = query_texts(
            raw,
            list(queries),
            top_k=n_results * 2,  # over-fetch, then trim
        )
        pool = [r for r in _flatten_query(raw_res) if r.get("id") not in seen_ids]
        hits.extend(pool[:need])

    # sort by query_index then distance (when present)
    hits.sort(
        key=lambda x: (
            x.get("query_index", 0),
            x.get("distance", 9e9) if x.get("distance") is not None else 9e9,
        )
    )
    return hits[:n_results]
