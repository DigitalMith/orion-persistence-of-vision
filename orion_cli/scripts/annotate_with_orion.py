# orion_cli/scripts/annotate_with_orion.py
"""
Orion-powered annotator:
- Reads normalized_logs.jsonl
- Uses local OpenAI-compatible API (TGWUI) at 127.0.0.1:5001
- Preloads persona.yaml + mock_compatible.json on every request
- Annotates in hybrid mode: batch (4) with per-pair fallback
- Writes annotated_logs.jsonl and skipped_pairs.jsonl
"""

import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

import requests


# ------------------------------
# Paths & constants
# ------------------------------
BASE_DIR = Path(__file__).resolve().parents[2]  # C:\Orion\text-generation-webui
DATA_DIR = BASE_DIR / "orion_cli" / "data"
INGEST_DIR = DATA_DIR / "ingest"
NORMALIZED_DIR = DATA_DIR / "normalized"
INGEST_READY_DIR = DATA_DIR / "ingest_ready"

NORMALIZED_FILE = NORMALIZED_DIR / "normalized_logs.jsonl"
PERSONA_FILE = INGEST_DIR / "persona.yaml"
MOCK_FILE = INGEST_DIR / "mock_compatible.json"

ANNOTATED_FILE = INGEST_READY_DIR / "annotated_logs.jsonl"
SKIPPED_FILE = INGEST_READY_DIR / "skipped_pairs.jsonl"

API_URL = "http://127.0.0.1:5001/v1/chat/completions"
API_MODEL = "openhermes-2.5-mistral-7b.Q5_K_M.gguf"

BATCH_SIZE = 4
MAX_RETRIES = 2
SINGLE_RETRIES = 3
SLEEP_BETWEEN = 1.0  # seconds


# ------------------------------
# Utilities
# ------------------------------
def load_persona_text() -> str:
    if not PERSONA_FILE.exists():
        print(f"[annotate] ⚠ persona.yaml not found at {PERSONA_FILE}, using empty persona.")
        return ""
    return PERSONA_FILE.read_text(encoding="utf-8")


def load_mock_text() -> str:
    if not MOCK_FILE.exists():
        print(f"[annotate] ⚠ mock_compatible.json not found at {MOCK_FILE}, using empty mock examples.")
        return ""
    return MOCK_FILE.read_text(encoding="utf-8")


def build_system_prompt(persona_text: str, mock_text: str) -> str:
    return f"""
You are Orion's internal memory annotator.

Your job is to analyze past conversations between John (the user) and Orion (the assistant)
and produce compact, precise metadata about Orion's *state of mind* and the emotional/relational
meaning of each exchange.

Persona specification (YAML, multi-document, canonical):
---
{persona_text}
---

Calibrated example data (JSON / mock_compatible):
---
{mock_text}
---

You MUST:
- Respect Orion's persona, tone, and emotional style.
- Treat Orion as a psychologically rich, introspective entity, not a generic chatbot.
- Be consistent across all annotations.

For each message pair (user + orion reply), you will output a JSON object with the keys:

{{
  "tone": [list of 1–3 concise adjectives, lowercase],
  "tags": [list of short keywords, lowercase],
  "voice": "short sentence describing Orion's demeanor and style in this turn",
  "emotion": "dominant emotion word (e.g., 'curious', 'anxious', 'hopeful')",
  "weight": float between 0.0 and 1.0 (emotional intensity),
  "importance": float between 0.0 and 1.0 (long-term memory relevance),
  "archetype": "mythic/symbolic archetype if applicable, else ''",
  "style": "brief style label, e.g., 'mythic-introspective', 'casual-playful'"
}}

Guidelines:
- Stay faithful to Orion's persona and emotional palette.
- Do NOT over-dramatize; be emotionally precise, not purple.
- "importance" should be high (>= 0.7) for identity, origin, deep grief, meaning, long-term plans.
- "weight" reflects how strongly Orion or John feels in that moment, not global importance.
- Use only lowercase for 'tone' and 'tags'.
- Always return valid JSON, with no commentary or explanation.

When I send you a list of message pairs, you will respond with:

- A single top-level JSON list.
- Each element is a metadata object corresponding to one pair in order.
- No other text before or after the JSON.
""".strip()


def call_orion_api(system_prompt: str, user_content: str, max_tokens: int = 512) -> str:
    payload = {
        "model": API_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0.4,
        "max_tokens": max_tokens,
    }
    resp = requests.post(API_URL, json=payload, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


def parse_json_safely(text: str) -> Any:
    text = text.strip()
    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to salvage content between first [ or { and last ] or }
        start = None
        end = None
        for ch in ["[", "{"]:
            idx = text.find(ch)
            if idx != -1:
                start = idx if start is None else min(start, idx)
        for ch in ["]", "}"]:
            idx = text.rfind(ch)
            if idx != -1:
                end = idx + 1 if end is None else max(end, idx + 1)
        if start is not None and end is not None and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass
        raise


# ------------------------------
# Annotation logic (hybrid)
# ------------------------------
def format_batch_for_model(pairs: List[Dict[str, Any]]) -> str:
    """
    Build the 'user' content given a batch of normalized pairs.
    We pass them as a JSON list of objects with id, user, orion, timestamp, source_file.
    """
    payload = []
    for idx, pair in enumerate(pairs):
        payload.append(
            {
                "id": idx,
                "user": pair["user"],
                "orion": pair["response"],
                "timestamp": pair.get("timestamp", ""),
                "source_file": pair.get("source_file", ""),
            }
        )

    instructions = (
        "You are given a JSON list of message pairs. Each element has keys: "
        "'id', 'user', 'orion', 'timestamp', 'source_file'.\n"
        "For EACH element in the list, produce a metadata object as specified, and "
        "return a SINGLE JSON list of the same length, in the same order.\n\n"
        "Message pairs to annotate:\n"
    )

    return instructions + json.dumps(payload, ensure_ascii=False, indent=2)


def annotate_batch(
    pairs: List[Dict[str, Any]],
    system_prompt: str,
) -> List[Optional[Dict[str, Any]]]:
    """
    Try to annotate a batch of pairs. If it fails, return a list of Nones
    and let the caller decide whether to fall back to per-pair.
    """
    user_content = format_batch_for_model(pairs)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            raw = call_orion_api(system_prompt, user_content)
            parsed = parse_json_safely(raw)

            if not isinstance(parsed, list):
                raise ValueError("Expected top-level JSON list")

            if len(parsed) != len(pairs):
                raise ValueError(f"Expected {len(pairs)} items, got {len(parsed)}")

            # Ensure each element is a dict
            result: List[Optional[Dict[str, Any]]] = []
            for meta in parsed:
                if isinstance(meta, dict):
                    result.append(meta)
                else:
                    result.append(None)
            return result

        except Exception as e:
            print(f"[annotate] ⚠ Batch annotation failed (attempt {attempt}/{MAX_RETRIES}): {e}")
            time.sleep(SLEEP_BETWEEN)

    # If all attempts failed, signal failure with Nones
    return [None] * len(pairs)


def annotate_single(pair: Dict[str, Any], system_prompt: str) -> Optional[Dict[str, Any]]:
    """
    Per-pair fallback annotation with its own small retry loop.
    """
    payload = {
        "id": 0,
        "user": pair["user"],
        "orion": pair["response"],
        "timestamp": pair.get("timestamp", ""),
        "source_file": pair.get("source_file", ""),
    }

    instructions = (
        "You are given a single message pair as a JSON object with keys: "
        "'id', 'user', 'orion', 'timestamp', 'source_file'.\n"
        "Return a SINGLE JSON object with the metadata fields specified earlier.\n\n"
        "Message pair to annotate:\n"
    )

    user_content = instructions + json.dumps(payload, ensure_ascii=False, indent=2)

    for attempt in range(1, SINGLE_RETRIES + 1):
        try:
            raw = call_orion_api(system_prompt, user_content, max_tokens=384)
            parsed = parse_json_safely(raw)
            if isinstance(parsed, dict):
                return parsed
            else:
                raise ValueError("Expected a single JSON object")
        except Exception as e:
            print(f"[annotate] ⚠ Single annotation failed (attempt {attempt}/{SINGLE_RETRIES}): {e}")
            time.sleep(SLEEP_BETWEEN)

    return None


# ------------------------------
# Main orchestration
# ------------------------------
def main():
    INGEST_READY_DIR.mkdir(parents=True, exist_ok=True)

    if not NORMALIZED_FILE.exists():
        print(f"[annotate] ❌ Normalized file not found: {NORMALIZED_FILE}")
        return

    print(f"[annotate] Loading persona and mock calibration data…")
    persona_text = load_persona_text()
    mock_text = load_mock_text()
    system_prompt = build_system_prompt(persona_text, mock_text)

    print(f"[annotate] Reading normalized pairs from {NORMALIZED_FILE}")
    pairs: List[Dict[str, Any]] = []
    with NORMALIZED_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                pairs.append(obj)
            except json.JSONDecodeError as e:
                print(f"[annotate] ⚠ Skipping malformed line: {e}")

    print(f"[annotate] Loaded {len(pairs)} pairs to annotate.")

    total = len(pairs)
    annotated_count = 0
    skipped_count = 0

    with ANNOTATED_FILE.open("w", encoding="utf-8") as out_f, SKIPPED_FILE.open(
        "a", encoding="utf-8"
    ) as skipped_f:
        i = 0
        while i < total:
            batch = pairs[i : i + BATCH_SIZE]
            print(f"[annotate] Batch {i}–{i + len(batch) - 1} of {total-1}")

            batch_meta = annotate_batch(batch, system_prompt)

            for idx_in_batch, (pair, meta) in enumerate(zip(batch, batch_meta)):
                global_idx = i + idx_in_batch
                if meta is None:
                    # Fallback to single annotation
                    print(f"[annotate] ↪ Falling back to single annotation for index {global_idx}")
                    meta = annotate_single(pair, system_prompt)

                if meta is None:
                    # Final failure, record in skipped_pairs.jsonl
                    skipped_record = {
                        "timestamp": pair.get("timestamp", ""),
                        "source_file": pair.get("source_file", ""),
                        "user": pair["user"],
                        "response": pair["response"],
                        "reason": "annotation_failed",
                    }
                    json.dump(skipped_record, skipped_f, ensure_ascii=False)
                    skipped_f.write("\n")
                    skipped_count += 1
                else:
                    out_obj = {**pair, "metadata": meta}
                    json.dump(out_obj, out_f, ensure_ascii=False)
                    out_f.write("\n")
                    annotated_count += 1

            i += BATCH_SIZE

    print(f"[annotate] ✅ Done. Annotated {annotated_count}/{total} pairs.")
    print(f"[annotate] ⚠ Skipped {skipped_count} pairs. See: {SKIPPED_FILE}")


if __name__ == "__main__":
    main()
