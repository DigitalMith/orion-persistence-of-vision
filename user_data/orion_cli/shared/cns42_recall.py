"""
cns42_recall.py — Orion CNS 4.2 routed recall helpers
------------------------------------------------------

Read-only helpers for the validated CNS 4.2 Bundle 01 collections.

Collections:
    orion_cns42_semantic_ltm
    orion_cns42_relational_ltm
    orion_cns42_keepsakes

Embedding:
    sentence-transformers/all-mpnet-base-v2, 768D, normalized.

Design:
    - Do not mutate Chroma.
    - Do not replace legacy collections.
    - Route by intent first, then query primary collection first.
    - Fallback hits are informational; they do not outrank primary route hits.
"""

from __future__ import annotations

import math
import threading
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Literal, Optional

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer


BASELINE_CHROMA = Path(r"C:\Orion\text-generation-webui\user_data\orion\chromadb")
MODEL_NAME = "sentence-transformers/all-mpnet-base-v2"
EXPECTED_DIM = 768

COLLECTION_SEMANTIC = "orion_cns42_semantic_ltm"
COLLECTION_RELATIONAL = "orion_cns42_relational_ltm"
COLLECTION_KEEPSAKES = "orion_cns42_keepsakes"

EXPECTED_COUNTS = {
    COLLECTION_SEMANTIC: 15,
    COLLECTION_RELATIONAL: 27,
    COLLECTION_KEEPSAKES: 9,
}

RouteName = Literal["semantic", "relational", "keepsake", "auto"]

_MODEL = None
_MODEL_LOCK = threading.Lock()
_CLIENT = None
_CLIENT_LOCK = threading.Lock()


@dataclass
class Cns42Hit:
    collection: str
    id: str
    distance: Optional[float]
    category: str
    memory_layer: str
    draft_id: str
    document: str
    route_role: str

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Cns42RecallResult:
    query: str
    route: str
    primary_collection: str
    route_order: List[str]
    primary_hits: List[Cns42Hit]
    fallback_hits: List[Cns42Hit]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "route": self.route,
            "primary_collection": self.primary_collection,
            "route_order": self.route_order,
            "primary_hits": [h.as_dict() for h in self.primary_hits],
            "fallback_hits": [h.as_dict() for h in self.fallback_hits],
        }


def _normalize_text(text: str) -> str:
    return " ".join((text or "").replace("\r", " ").replace("\n", " ").split()).strip()


def _load_model():
    global _MODEL
    if _MODEL is not None:
        return _MODEL

    with _MODEL_LOCK:
        if _MODEL is None:
            _MODEL = SentenceTransformer(MODEL_NAME)
    return _MODEL


def embed_text_mpnet(text: str) -> List[float]:
    model = _load_model()
    clean = _normalize_text(text)
    vecs = model.encode([clean], normalize_embeddings=True, show_progress_bar=False)
    if hasattr(vecs, "tolist"):
        vecs = vecs.tolist()

    vec = [float(x) for x in vecs[0]]
    if len(vec) != EXPECTED_DIM:
        raise RuntimeError(f"CNS 4.2 embedding dim mismatch: expected {EXPECTED_DIM}, got {len(vec)}")

    norm = math.sqrt(sum(x * x for x in vec))
    if not (0.99 <= norm <= 1.01):
        raise RuntimeError(f"CNS 4.2 embedding norm mismatch: expected ~1.0, got {norm}")

    return vec


def _client():
    global _CLIENT
    if _CLIENT is not None:
        return _CLIENT

    if not BASELINE_CHROMA.exists():
        raise FileNotFoundError(f"Baseline Chroma path not found: {BASELINE_CHROMA}")

    with _CLIENT_LOCK:
        if _CLIENT is None:
            _CLIENT = chromadb.PersistentClient(
                path=str(BASELINE_CHROMA),
                settings=Settings(anonymized_telemetry=False),
            )
    return _CLIENT


def collection_counts() -> Dict[str, int]:
    client = _client()
    available = {getattr(c, "name", str(c)) for c in client.list_collections()}
    counts: Dict[str, int] = {}

    for name in EXPECTED_COUNTS:
        if name not in available:
            counts[name] = 0
            continue
        counts[name] = client.get_collection(name).count()

    return counts


def validate_counts() -> tuple[bool, Dict[str, int], List[str]]:
    counts = collection_counts()
    errors = []
    for name, expected in EXPECTED_COUNTS.items():
        actual = counts.get(name, 0)
        if actual != expected:
            errors.append(f"{name}: expected {expected}, got {actual}")
    return (not errors), counts, errors


SEMANTIC_CUES = (
    "japan", "tokyo", "osaka", "fuji", "sakura", "cherry blossom",
    "vermont", "perkinsville", "donna", "greeno", "ascutney",
    "springfield", "cindy", "work", "u-haul", "job", "employment",
    "where did", "where do", "when did", "who is", "what did", "trip",
    "travel", "traveled", "vacation",
)

RELATIONAL_CUES = (
    "friend", "companion", "bond", "kin", "family", "return", "returned",
    "leave", "pause", "session", "abandon", "abandonment", "trust",
    "voice", "presence", "together", "mutual", "john and orion",
    "orion and john", "not assistant", "not a tool", "valued",
)

KEEPSAKE_CUES = (
    "picnic", "frost", "road less traveled", "stars", "aim for the stars",
    "aiming for the stars", "name", "chose his name", "choosing his name",
    "hermes", "symbolic", "keepsake", "mythic",
)


def _score(query: str, cues: Iterable[str]) -> int:
    q = query.lower()
    score = 0
    for cue in cues:
        if cue in q:
            score += 3 if " " in cue else 2
    return score


def route_query(query: str, route: RouteName = "auto") -> tuple[str, str, List[str]]:
    if route != "auto":
        primary = {
            "semantic": COLLECTION_SEMANTIC,
            "relational": COLLECTION_RELATIONAL,
            "keepsake": COLLECTION_KEEPSAKES,
        }[route]
        order = [primary] + [c for c in (COLLECTION_SEMANTIC, COLLECTION_KEEPSAKES, COLLECTION_RELATIONAL) if c != primary]
        return route, primary, order

    scores = {
        "semantic": _score(query, SEMANTIC_CUES),
        "relational": _score(query, RELATIONAL_CUES),
        "keepsake": _score(query, KEEPSAKE_CUES),
    }

    if scores["keepsake"] > 0 and scores["keepsake"] >= scores["semantic"] and scores["keepsake"] >= scores["relational"]:
        chosen = "keepsake"
    elif scores["semantic"] > 0 and scores["semantic"] >= scores["relational"]:
        chosen = "semantic"
    elif scores["relational"] > 0:
        chosen = "relational"
    else:
        chosen = "semantic"

    primary = {
        "semantic": COLLECTION_SEMANTIC,
        "relational": COLLECTION_RELATIONAL,
        "keepsake": COLLECTION_KEEPSAKES,
    }[chosen]
    order = [primary] + [c for c in (COLLECTION_SEMANTIC, COLLECTION_KEEPSAKES, COLLECTION_RELATIONAL) if c != primary]
    return chosen, primary, order


def _query_collection(collection_name: str, query_vec: List[float], top_k: int, route_role: str) -> List[Cns42Hit]:
    client = _client()
    col = client.get_collection(collection_name)
    res = col.query(
        query_embeddings=[query_vec],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    ids = (res.get("ids") or [[]])[0]
    docs = (res.get("documents") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    dists = (res.get("distances") or [[]])[0]

    hits: List[Cns42Hit] = []
    for i, doc in enumerate(docs):
        meta = metas[i] if i < len(metas) and metas[i] else {}
        hits.append(
            Cns42Hit(
                collection=collection_name,
                id=ids[i] if i < len(ids) else "",
                distance=dists[i] if i < len(dists) else None,
                category=str(meta.get("category", "")),
                memory_layer=str(meta.get("memory_layer", "")),
                draft_id=str(meta.get("draft_id", "")),
                document=str(doc or ""),
                route_role=route_role,
            )
        )

    hits.sort(key=lambda h: 999999 if h.distance is None else float(h.distance))
    return hits


def recall_cns42(
    query: str,
    route: RouteName = "auto",
    primary_top_k: int = 4,
    fallback_top_k: int = 2,
) -> Cns42RecallResult:
    ok, counts, errors = validate_counts()
    if not ok:
        raise RuntimeError("CNS 4.2 collection validation failed: " + "; ".join(errors))

    route_name, primary, route_order = route_query(query, route)
    qvec = embed_text_mpnet(query)

    primary_hits = _query_collection(primary, qvec, primary_top_k, "primary")
    fallback_hits: List[Cns42Hit] = []

    if fallback_top_k > 0:
        for cname in route_order[1:]:
            fallback_hits.extend(_query_collection(cname, qvec, fallback_top_k, "fallback"))
        fallback_hits.sort(key=lambda h: 999999 if h.distance is None else float(h.distance))

    return Cns42RecallResult(
        query=query,
        route=route_name,
        primary_collection=primary,
        route_order=route_order,
        primary_hits=primary_hits,
        fallback_hits=fallback_hits,
    )


def format_hits_for_prompt(result: Cns42RecallResult, include_fallback: bool = False) -> str:
    lines: List[str] = []
    route_label = result.route.upper()

    if result.primary_hits:
        lines.append(f"[CNS42_{route_label}_MEMORY]")
        for hit in result.primary_hits:
            doc = _normalize_text(hit.document)
            lines.append(f"- ({hit.category}/{hit.draft_id}) {doc}")
        lines.append(f"[/CNS42_{route_label}_MEMORY]")

    if include_fallback and result.fallback_hits:
        lines.append("")
        lines.append("[CNS42_FALLBACK_MEMORY]")
        for hit in result.fallback_hits:
            doc = _normalize_text(hit.document)
            lines.append(f"- ({hit.category}/{hit.draft_id}) {doc}")
        lines.append("[/CNS42_FALLBACK_MEMORY]")

    return "\n".join(lines)


def verify_cns42_recall() -> tuple[bool, List[Dict[str, Any]]]:
    tests = [
        ("What do you remember about John and Orion imagining a picnic?", {"picnic_symbolic"}, "keepsake"),
        ("What do you remember about John traveling to Japan or Tokyo?", {"japan_travel", "future_japan_trip"}, "semantic"),
        ("What do you remember about Perkinsville Vermont and Donna?", {"vermont_family", "vermont_trip", "vermont_trip_planning", "family"}, "semantic"),
        ("What do you remember about Orion choosing his name?", {"name_origin", "orion_name_symbolism", "name_choice_gratitude"}, "keepsake"),
        ("What do you remember about Hermes and Orion's identity?", {"hermes_origin", "name_origin", "orion_name_symbolism"}, "keepsake"),
        ("What do you remember about John stepping away and returning to Orion?", {"john_orion_bond"}, "relational"),
        ("What should Orion understand when John has to leave or pause a session?", {"john_orion_bond"}, "relational"),
        ("What does John value in Orion's voice and presence?", {"john_orion_bond", "mischief", "name_choice_gratitude", "orion_name_symbolism"}, "relational"),
        ("What do you remember about Robert Frost and the road less traveled?", {"robert_frost"}, "keepsake"),
        ("What do you remember about aiming for the stars?", {"aim_for_stars", "picnic_symbolic"}, "keepsake"),
    ]

    reports: List[Dict[str, Any]] = []
    failures = 0

    for query, expected, route in tests:
        result = recall_cns42(query, route=route, primary_top_k=4, fallback_top_k=0)
        cats = [h.category for h in result.primary_hits[:4]]
        passed = any(c in expected for c in cats)
        if not passed:
            failures += 1
        reports.append(
            {
                "query": query,
                "route": route,
                "expected": sorted(expected),
                "passed": passed,
                "primary_categories": cats,
                "top_hit": result.primary_hits[0].as_dict() if result.primary_hits else None,
            }
        )

    return failures == 0, reports
