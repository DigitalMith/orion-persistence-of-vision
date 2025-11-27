import json
import uuid
from orion_cli.utils.chroma_utils import get_client, EMBED_FN, _get_or_create

DEFAULT_IMPORTANCE = 0.7

# ---------------------------------------------------------
# LOAD FILE
# ---------------------------------------------------------


def load_mock_dialog_json(path: str):
    """
    Loads the mock dialog JSON file.
    Expected format:
    [
      {
        "user": "text",
        "orion": "text"
      },
      ...
    ]
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("Mock dialog JSON must be a list of turn-pairs.")

    for i, entry in enumerate(data):
        if not isinstance(entry, dict):
            raise ValueError(f"Entry #{i} is not a dict: {entry}")

        if "user" not in entry or "orion" not in entry:
            raise ValueError(f"Entry #{i} missing 'user' or 'orion' fields: {entry}")

    return data


# ---------------------------------------------------------
# NORMALIZE → CHROMA FORMAT
# ---------------------------------------------------------


def normalize_voice_pair(pair):
    """
    Convert user+orion text into a single block with flattened metadata.
    """
    user_line = str(pair["user"]).strip()
    orion_line = str(pair["orion"]).strip()

    if not orion_line:
        raise ValueError("Orion response is empty in a mock-dialog pair.")

    # Join pair into one document
    text_block = f"[USER] {user_line}\n" f"[ORION] {orion_line}"

    metadata = {
        "source": "voice_profile",
        "importance": DEFAULT_IMPORTANCE,
        "pair": True,
        "has_user": bool(user_line),
        "has_orion": True,
    }

    return {
        "id": str(uuid.uuid4()),
        "text": text_block,
        "metadata": metadata,
    }


# ---------------------------------------------------------
# INGESTION
# ---------------------------------------------------------


def ingest_voice_profile(path: str):
    """
    Load mock dialog JSON → normalize → ingest into voice_profile collection.
    """

    raw_pairs = load_mock_dialog_json(path)
    normalized = []

    for pair in raw_pairs:
        try:
            normalized.append(normalize_voice_pair(pair))
        except Exception as e:
            print(f"[WARN] Skipping invalid entry: {e}")

    if not normalized:
        raise RuntimeError("No valid voice_profile entries found.")

    client = get_client()
    coll = _get_or_create(client, "voice_profile", EMBED_FN)

    # Clear old data
    try:
        coll.delete()
        coll = _get_or_create(client, "voice_profile", EMBED_FN)
    except Exception as e:
        print(f"[WARN] Could not clear old voice_profile: {e}")

    ids = [x["id"] for x in normalized]
    docs = [x["text"] for x in normalized]
    metas = [x["metadata"] for x in normalized]

    coll.add(ids=ids, documents=docs, metadatas=metas)

    print("\n[VOICE PROFILE INGEST COMPLETE]")
    print(f"Loaded entries: {len(normalized)}")
    print(f"Source: {path}\n")

    # Preview first 3 entries
    for sample in normalized[:3]:
        print(f"- {sample['text'][:150]}...")
    print()

    return len(normalized)
