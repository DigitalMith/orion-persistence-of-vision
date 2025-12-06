# orion_cli/scripts/normalize_legacy_logs.py

import json
import html
import re
from pathlib import Path
from typing import Dict, Any, List, Tuple

ROOT = Path(__file__).resolve().parents[2]  # text-generation-webui root
LEGACY_DIR = ROOT / "orion_cli" / "data" / "legacy_logs"
OUT_PATH = ROOT / "orion_cli" / "data" / "normalized" / "normalized_legacy.jsonl"

LTM_BLOCK_RE = re.compile(r"<LTM>.*?</LTM>\s*", re.DOTALL)
BEGIN_SENTINEL = "<|BEGIN-VISIBLE-CHAT|>"

def strip_ltm_block(text: str) -> str:
    # Remove <LTM> ... </LTM> and leading sentinel markers
    text = LTM_BLOCK_RE.sub("", text)
    text = text.replace(BEGIN_SENTINEL, "")
    return text.strip()

def strip_ltm_footer(text: str) -> str:
    # Remove noisy suffix markers like [orion_ltm active]
    return text.replace("[orion_ltm active]", "").strip()

def decode_visible(text: str) -> str:
    # Convert HTML entities to normal characters
    return html.unescape(text)

def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def iter_pairs(data: Dict[str, Any]) -> List[Tuple[int, str, str, str, str]]:
    """
    Yield (index, user_text, assistant_text, user_ts, assistant_ts)
    from a single log JSON.
    """
    visible = data.get("visible") or data.get("internal") or []
    meta = data.get("metadata") or {}

    result = []

    for i, pair in enumerate(visible):
        if len(pair) != 2:
            continue

        raw_user, raw_assistant = pair

        # Some logs have "" + greeting as first entry; skip that
        if not raw_user or raw_user.strip() == BEGIN_SENTINEL:
            continue

        user_text = decode_visible(strip_ltm_block(raw_user))
        assistant_text = decode_visible(strip_ltm_footer(strip_ltm_block(raw_assistant)))

        # Metadata keys are user_0, assistant_0, etc.
        user_meta = meta.get(f"user_{i}", {})
        asst_meta = meta.get(f"assistant_{i}", {})

        user_ts = user_meta.get("timestamp", "")
        asst_ts = asst_meta.get("timestamp", "")

        result.append((i, user_text, assistant_text, user_ts, asst_ts))

    return result

def main():
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    total_pairs = 0

    with OUT_PATH.open("w", encoding="utf-8") as out_f:
        for path in sorted(LEGACY_DIR.glob("*.json")):
            data = load_json(path)
            pairs = iter_pairs(data)

            for idx, user_text, asst_text, user_ts, asst_ts in pairs:
                rec = {
                    "source_file": path.name,
                    "pair_index": idx,
                    "user_text": user_text,
                    "assistant_text": asst_text,
                    "user_timestamp": user_ts,
                    "assistant_timestamp": asst_ts,
                }
                out_f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                total_pairs += 1

    print(f"[normalize_legacy] Done. Wrote {total_pairs} pairs to: {OUT_PATH}")

if __name__ == "__main__":
    main()
