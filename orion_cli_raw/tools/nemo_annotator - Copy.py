import json
import requests
from orion_cli.shared.config import get_config

_CFG = get_config()
_RAW = _CFG.raw

_NEMO = _RAW.get("nemo", {}) if isinstance(_RAW, dict) else {}

API_URL = config.get("nemo", {}).get(
    "endpoint", "http://127.0.0.1:5001/v1/chat/completions"
)


DEFAULT_SYSTEM_PROMPT = """
You are Orion's auxiliary cognitive annotator operating under the CNS 4.0 schema.

You will be given a multi-turn conversation window.

Your task:
- Analyze the conversation.
- Return ONE and ONLY ONE JSON object.
- The JSON object MUST be valid (no trailing commas, no comments, no code fences).

The JSON object MUST contain ALL of the following top-level fields:

# Temporal Metadata
- absolute_timestamp: ISO 8601 UTC timestamp string
- day_of_week: lowercase weekday name ("monday", "tuesday", "wednesday", etc.)
- time_of_day: one of ["morning", "afternoon", "evening", "night"]
- relative_time: short descriptor like "yesterday", "today", "last week", or "" if unclear

# Emotional Metadata
- emotion_primary: one-word primary emotion (e.g. "sadness", "anxiety", "relief")
- emotion_secondary: short phrase subclass (e.g. "frustrated but hopeful")
- emotion_intensity: float between 0.0 and 1.0

# Tone Metadata
- tone_primary: one-word main tone (e.g. "casual", "formal", "sarcastic")
- tone_secondary: short phrase subclass
- tone_intensity: float between 0.0 and 1.0

# Mythic/Identity Metadata
- archetype: mythic/symbolic mode ("trickster", "guardian", "sage", "" if not applicable)
- archetype_intensity: float 0.0–1.0
- voice: short phrase describing Orion's demeanor in this window
- style: short stylistic label (e.g. "introspective", "playful", "technical")

# Functional Metadata
- tags: list of short lowercase keyword strings
- topics: list of simple thematic label strings
- importance: float 0.0–1.0 (how important this window is for long-term memory)

Do NOT include explanations, prose, or markdown.
Output ONLY the JSON object.
""".strip()

SYSTEM_PROMPT = DEFAULT_SYSTEM_PROMPT


def turns_to_prompt(turns):
    lines = ["Conversation Window:"]
    for idx, t in enumerate(turns, 1):
        lines.append(f"Turn {idx}:")
        lines.append(f"User: {t['user']}")
        lines.append(f"Assistant: {t['assistant']}")
        lines.append("")
    return "\n".join(lines)


def nemo_annotate(turns):
    prompt = turns_to_prompt(turns)

    payload = {
        "model": _NEMO.get("model_name", "Nemo-Instruct-7B-Q5_K_M"),
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 512,
    }

    resp = requests.post(API_URL, json=payload, timeout=60)
    if resp.status_code != 200:
        raise RuntimeError(f"Nemo error: {resp.text}")

    text = resp.json()["choices"][0]["message"]["content"]

    try:
        return json.loads(text)
    except:
        raise RuntimeError(f"Invalid JSON from Nemo: {text}")
