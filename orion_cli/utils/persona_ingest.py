import yaml
import uuid
from orion_cli.utils.chroma_utils import get_client, EMBED_FN, _get_or_create

DEFAULT_IMPORTANCE = 0.7  # Option B

# -------------------------------
# FLATTEN HELPER
# -------------------------------


def flatten_metadata(block: dict):
    """Flatten all non-text fields into metadata."""
    meta = {}
    for k, v in block.items():
        if k == "text":
            continue
        if k == "metadata":
            # merge inner metadata first
            for mk, mv in v.items():
                meta[mk] = mv
        else:
            meta[k] = v
    return meta


# -------------------------------
# NORMALIZATION LOGIC
# -------------------------------


def normalize_persona_entry(raw):
    """
    Converts ANY persona block into:
    {
        "id": <uuid>,
        "text": <str>,
        "metadata": { ... flattened ... }
    }
    """

    if not isinstance(raw, dict):
        raise ValueError(f"Invalid persona entry: {raw}")

    if "text" not in raw:
        raise ValueError(f"Persona block missing 'text': {raw}")

    text = str(raw["text"]).strip()
    if not text:
        raise ValueError("Persona entry has empty text.")

    # Flatten metadata
    metadata = flatten_metadata(raw)

    # Fix importance
    importance = metadata.get("importance", None)
    if importance is None:
        metadata["importance"] = DEFAULT_IMPORTANCE
    else:
        try:
            metadata["importance"] = float(importance)
        except Exception:
            metadata["importance"] = DEFAULT_IMPORTANCE

    # Tag as persona
    metadata.setdefault("source", "persona")

    return {
        "id": str(uuid.uuid4()),
        "text": text,
        "metadata": metadata,
    }


# -------------------------------
# YAML LOADER
# -------------------------------


def load_persona_yaml(path: str):
    """
    Loads multi-document YAML.
    Returns a list of raw persona blocks.
    """
    with open(path, "r", encoding="utf-8") as f:
        docs = list(yaml.safe_load_all(f))

    out = []

    for doc in docs:
        if doc is None:
            continue

        if isinstance(doc, list):
            # Flat list of persona snippets
            for item in doc:
                if isinstance(item, dict):
                    out.append(item)
                else:
                    raise ValueError(f"List contains non-dict item: {item}")

        elif isinstance(doc, dict):
            # Single structured persona block
            out.append(doc)

        else:
            raise ValueError(f"Unexpected YAML structure: {doc}")

    return out


# -------------------------------
# INGESTION PIPELINE
# -------------------------------


def ingest_persona_yaml(path: str):
    """
    Main ingestion function.
    Loads persona blocks → normalizes → ingests into Chroma.
    """

    raw_blocks = load_persona_yaml(path)
    normalized = []

    for block in raw_blocks:
        try:
            norm = normalize_persona_entry(block)
            normalized.append(norm)
        except Exception as e:
            print(f"[WARN] Skipping persona entry due to error: {e}")

    if not normalized:
        raise RuntimeError("No valid persona entries found in YAML.")

    client = get_client()
    coll = _get_or_create(client, "persona", EMBED_FN)

    # Clear old persona to avoid duplicates
    try:
        coll.delete()
        coll = _get_or_create(client, "persona", EMBED_FN)
    except Exception as e:
        print(f"[WARN] Could not clear old persona: {e}")

    # Insert
    ids = [x["id"] for x in normalized]
    texts = [x["text"] for x in normalized]
    metas = [x["metadata"] for x in normalized]

    coll.add(ids=ids, documents=texts, metadatas=metas)

    print("\n[PERSONA INGEST COMPLETE]")
    print(f"Loaded entries: {len(normalized)}")
    print(f"Source: {path}\n")

    # Preview first 3
    for p in normalized[:3]:
        print(f"- {p['text'][:120]}...")
    print()

    return len(normalized)
