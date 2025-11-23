import json
from pathlib import Path
from datetime import datetime

# ---------------------------------------------------------
# Local-only normalization of chat logs (no OpenAI, no tags)
# ---------------------------------------------------------

def _timestamp_from_stem(stem: str) -> str:
    """
    Convert filenames like '20251111-05-29-01' to ISO timestamps:
    '2025-11-11T05:29:01'.
    If pattern doesn't match, fall back gracefully to just the date, or ''.
    """
    try:
        # Expected pattern: YYYYMMDD-HH-MM-SS
        dt = datetime.strptime(stem, "%Y%m%d-%H-%M-%S")
        return dt.isoformat()
    except ValueError:
        # Fallback: just try YYYYMMDD
        try:
            dt = datetime.strptime(stem.split("-")[0], "%Y%m%d")
            return dt.isoformat()
        except ValueError:
            return ""

def normalize_entries(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    messages = extract_messages(raw)
    if not messages:
        raise ValueError("Expected top-level list of messages or nested chat structure")

    # NEW: derive timestamp from filename stem
    stem = file_path.stem  # e.g. '20251111-05-29-01'
    timestamp = _timestamp_from_stem(stem)

    entries = []
    for i in range(len(messages) - 1):
        user_msg, reply_msg = messages[i], messages[i + 1]
        if user_msg.get("role") == "user" and reply_msg.get("role") in ["assistant", "Orion"]:
            entries.append(
                {
                    "user": user_msg["content"],
                    "response": reply_msg["content"],
                    "timestamp": timestamp,
                    "source_file": file_path.name,
                }
            )
    return entries
    

def load_json(path: Path):
    """Load a JSON file safely."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_messages(data):
    """
    Flexible extractor supporting:
      - list of {"role": "...", "content": "..."}
      - list of [user, assistant] pairs
      - nested dict structures
    """
    if isinstance(data, list):
        if all(isinstance(m, dict) and "role" in m and "content" in m for m in data):
            return data
        elif all(isinstance(m, list) and len(m) == 2 for m in data):
            result = []
            for user, assistant in data:
                result.append({"role": "user", "content": user})
                result.append({"role": "assistant", "content": assistant})
            return result

    if isinstance(data, dict):
        for key in data:
            extracted = extract_messages(data[key])
            if extracted:
                return extracted

    return None


def normalize_chat_file(path: Path):
    """
    Convert a raw chat log into simple normalized pairs:
      [
        {
          "user": "...",
          "response": "...",
          "timestamp": "...",
          "source_file": "..."
        },
        ...
      ]
    """
    raw = load_json(path)
    messages = extract_messages(raw)

    if not messages:
        raise ValueError("Expected messages in role/content format or pair format.")

    entries = []
    for i in range(len(messages) - 1):
        user_msg, reply_msg = messages[i], messages[i + 1]
        if user_msg.get("role") == "user" and reply_msg.get("role") in ["assistant", "Orion"]:
            entries.append(
                {
                    "user": user_msg["content"],
                    "response": reply_msg["content"],
                    "timestamp": path.stem.split("-")[0],
                    "source_file": path.name,
                    "metadata": {
                        "timestamp": datetime.utcnow().isoformat(),
                        "importance": 0.5,
                        "source": "normalized_chat"
                    }
                }
            )
    return entries


def normalize_directory(input_dir: Path):
    """Normalize all chat logs in a directory."""
    results = []
    for file in input_dir.glob("*.json"):
        try:
            results.extend(normalize_chat_file(file))
        except Exception as e:
            print(f"[normalize] ⚠️ Failed on {file.name}: {e}")
    return results
