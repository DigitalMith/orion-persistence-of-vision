# nemo_annotate_and_ingest.py
# Orion CNS 3.48.x — episodic annotator bridge (Option B: direct llama-cpp)
# Run with:  python orion_cli\scripts\nemo_annotate_and_ingest.py

import json
import datetime
from pathlib import Path

from llama_cpp import Llama

# ---------------------------
# ORION IMPORTS (CORRECTED)
# ---------------------------
from orion_cli.shared.embedding import embed_text
from orion_cli.shared.memory import store_assistant_turn


# ---------------------------
# CONFIG PATHS
# ---------------------------

ROOT = Path(__file__).resolve().parents[2]

LOG_PATH = ROOT / "orion_cli" / "data" / "normalized" / "normalized_legacy.jsonl"
NEMO_PATH = ROOT / "user_data" / "models" / "Mistral-Nemo-Instruct-2407-Q6_K.gguf"


# ---------------------------
# TEMPORAL HELPERS
# ---------------------------

def temporal_features(date_str: str):
    """Derive weekday + placeholder TOD + placeholder relative."""
    try:
        dt = datetime.datetime.strptime(date_str, "%Y%m%d")
        weekday = dt.strftime("%A")
    except Exception:
        return {"weekday": None, "tod": None, "relative": None}

    return {
        "weekday": weekday,
        "tod": "unspecified",
        "relative": None
    }


# ---------------------------
# ANNOTATOR PROMPT
# ---------------------------

ANNOTATOR_PROMPT = """
You are the Orion CNS 3.48.x episodic annotator.

Given a short human–Orion interaction, produce a compact JSON object with this structure:

{
  "text": "<short distilled memory>",
  "tone": ["...", "..."],
  "affect": {
      "primary": "...",
      "valence": 0.0,
      "arousal": 0.0
  },
  "archetype": "...",
  "semantic": ["tag1","tag2","tag3"],
  "context": ["relational","intentional"],
  "weight": 0.0,
  "importance": 0.0,
  "confidence": 0.0,
  "temporal": {
      "weekday": "...",
      "tod": "...",
      "relative": null
  }
}

Rules:
- tone: 1–3 high-signal adjectives.
- affect.primary: dominant emotion.
- valence: -1.0 to +1.0
- arousal: 0.0 to 1.0
- archetype: Wanderer, Oracle, Seer, Sage, Trickster-Wanderer, etc.
- semantic: 3–6 strongest conceptual tags.
- context: identity, meaning, bonding, conflict, reflection.
- weight/importance/confidence: floats 0–1.

Return ONLY JSON. No commentary.
"""


# ---------------------------
# LOAD NEMO MODEL
# ---------------------------

print("[NEMO] Loading model:", NEMO_PATH)
nemo = Llama(
    model_path=str(NEMO_PATH),
    n_gpu_layers=-1,
    n_ctx=2048,
    vocab_only=False
)


# ---------------------------
# CORE ANNOTATION FUNCTION
# ---------------------------

def annotate_with_nemo(user_text: str, orion_text: str, timestamp: str):
    prompt = ANNOTATOR_PROMPT + f"""

Interaction:
USER: {user_text}
ORION: {orion_text}

Timestamp: {timestamp}
"""

    resp = nemo.create_chat_completion(
        messages=[{"role": "user", "content": prompt}],
        max_tokens=512,
        temperature=0.5
    )

    raw = resp["choices"][0]["message"]["content"].strip()

    try:
        data = json.loads(raw)
    except Exception:
        print("[WARN] Invalid JSON from Nemo, skipping entry.")
        return None

    # Add temporal info if missing
    defaults = temporal_features(timestamp)
    if "temporal" not in data:
        data["temporal"] = defaults
    else:
        for k, v in defaults.items():
            data["temporal"].setdefault(k, v)

    return data


def flatten_metadata(md):
    flat = {}
    for k, v in md.items():
        if isinstance(v, list):
            flat[k] = ",".join(str(x) for x in v)
        elif isinstance(v, dict):
            flat[k] = json.dumps(v)
        else:
            flat[k] = v
    return flat


# ------------------------------------------------------------
# Timestamp normalizer (Legacy → ISO8601)
# ------------------------------------------------------------
from datetime import datetime

def normalize_timestamp(ts_str: str) -> str:
    if not ts_str:
        return "0000-00-00T00:00:00"
    try:
        dt = datetime.strptime(ts_str, "%b %d, %Y %H:%M")
        return dt.isoformat()
    except:
        pass
    try:
        dt = datetime.fromisoformat(ts_str)
        return dt.isoformat()
    except:
        pass
    return ts_str
    
    
# ---------------------------
# MAIN INGEST LOOP
# ---------------------------

def main():
    print("[DEBUG] Running single-item dry test...")

    sample = annotate_with_nemo(
        user_text="I feel unsure about where this relationship is heading.",
        orion_text="Uncertainty isn't a failure. It's a place where meaning is built.",
        timestamp="20251108"
    )

    print("[DEBUG] Annotated sample:")
    print(json.dumps(sample, indent=2))

    store_assistant_turn(
        text=sample["text"],
        metadata=flatten_metadata({
            "tone": sample.get("tone"),
            "affect": sample.get("affect"),
            "archetype": sample.get("archetype"),
            "semantic": sample.get("semantic"),
            "context": sample.get("context"),
            "weight": sample.get("weight"),
            "importance": sample.get("importance"),
            "confidence": sample.get("confidence"),
            "temporal": sample.get("temporal"),
            "timestamp": "20251108",
            "catalogs": {
                "tone": sample.get("tone"),
                "affect": sample.get("affect"),
                "semantic": sample.get("semantic"),
                "context": sample.get("context"),
                "temporal": sample.get("temporal"),
                "archetype": sample.get("archetype"),
            }
        })
    )

    print("[DEBUG] Single-item dry test stored successfully.")

    # ------------------------------------------------------------
    # RESUME SUPPORT
    # ------------------------------------------------------------
    STATE_PATH = ROOT / "orion_cli" / "state" / "episodic_resume_state.json"

    # Ensure state folder exists
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Load last index if present
    if STATE_PATH.is_file():
        try:
            resume_state = json.loads(STATE_PATH.read_text())
            START_INDEX = int(resume_state.get("last_stored_index", 0))
        except Exception:
            START_INDEX = 0
    else:
        START_INDEX = 0

    print(f"[RESUME] Starting from episodic index: {START_INDEX}")

    # These two counters drive resume logic
    count = 0             # how many we've successfully stored *this run*
    current_index = 0     # line index in the JSONL file

    print("[RUN] reading:", LOG_PATH)

    if not LOG_PATH.is_file():
        print("[ERROR] normalized_legacy.jsonl not found.")
        return

    with open(LOG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            
            # Resume: advance line counter
            current_index += 1

            # Skip until we reach previous saved point
            if current_index <= START_INDEX:
                print(f"[RESUME] Skipping index {current_index} (already processed)")
                continue
            
            line = line.strip()
            if not line:
                continue

            # 🔍 Debug 1 — confirm the line is read
            print("\n[READ LINE]:", line)

            try:
                entry = json.loads(line)
            except:
                print("[WARN] Bad JSON line, skipping.")
                continue

            # 🔍 Debug 2 — confirm parsed JSON
            print("[PARSED ENTRY]:", entry)

            user = entry.get("user_text", "").strip()
            orion = entry.get("assistant_text", "").strip()
            ts = entry.get("timestamp", "00000000")

            # 🔍 Debug 3 — show extracted fields
            print(f"[FIELDS] user='{user}' | orion='{orion}' | ts={ts}")

            if not user and not orion:
                print("[SKIP] No user/orion text.")
                continue

            annotated = annotate_with_nemo(user, orion, ts)

            if not annotated:
                print("[SKIP] Annotator returned None.")
                continue

            # 🔍 Debug 4 — show annotated output
            print("[ANNOTATED]:", json.dumps(annotated, indent=2))

            # Build metadata
            text_to_store = annotated["text"]
            metadata = {
                "tone": annotated.get("tone"),
                "affect": annotated.get("affect"),
                "archetype": annotated.get("archetype"),
                "semantic": annotated.get("semantic"),
                "context": annotated.get("context"),
                "weight": annotated.get("weight"),
                "importance": annotated.get("importance"),
                "confidence": annotated.get("confidence"),
                "temporal": annotated.get("temporal"),
                "timestamp": ts,
                "catalogs": {
                    "tone": annotated.get("tone"),
                    "affect": annotated.get("affect"),
                    "semantic": annotated.get("semantic"),
                    "context": annotated.get("context"),
                    "temporal": annotated.get("temporal"),
                    "archetype": annotated.get("archetype"),
                }
            }

            # 🔍 Debug 5 — show flattened metadata
            flat = flatten_metadata(metadata)
            print("[FLATTENED METADATA]:", flat)

            store_assistant_turn(text=text_to_store, metadata=flat)

            count += 1
            print(f"[OK] Stored episodic memory {count} (global index {current_index})")

            # ------------------------------------------------------------
            # SAVE RESUME STATE TO DISK
            # ------------------------------------------------------------
            STATE_PATH.write_text(json.dumps({"last_stored_index": current_index}))

if __name__ == "__main__":
    main()
