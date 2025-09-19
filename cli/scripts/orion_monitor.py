# cli/scripts/orion_monitor.py

import time
import sys
import re
from pathlib import Path

# Add project root (C:/Orion/text-generation-webui) to sys.path
ROOT_PATH = Path(__file__).resolve().parents[2]
if str(ROOT_PATH) not in sys.path:
    sys.path.insert(0, str(ROOT_PATH))

from cli.utils.web_search_hook import perform_web_search

# Path setup
CHAT_LOG_PATH = ROOT_PATH / "cli" / "data" / "messages.md"
SEEN_HASHES_PATH = ROOT_PATH / "cli" / "data" / "seen_questions.txt"

def hash_prompt(prompt: str):
    import hashlib
    return hashlib.sha256(prompt.encode()).hexdigest()

def load_seen_hashes():
    if SEEN_HASHES_PATH.exists():
        return set(SEEN_HASHES_PATH.read_text().splitlines())
    return set()

def save_seen_hash(prompt_hash: str):
    with SEEN_HASHES_PATH.open("a") as f:
        f.write(prompt_hash + "\n")

def extract_questions(log_text):
    pattern = re.compile(r"(.*?)(#autosearch(?:\s+(\w+))?)", re.IGNORECASE)
    questions = []

    for line in log_text.splitlines():
        line = line.strip()
        if line.lower().startswith("orion:"):
            continue

        match = pattern.search(line)
        if match:
            prompt = match.group(1).strip()
            tag = match.group(3).strip() if match.group(3) else "websearch"
            if prompt.endswith("?"):
                questions.append((prompt, tag))
            else:
                print(f"[⚠️] Skipped: line didn’t look like a question → {line}")
    return questions

def main():
    print("[🔍] Orion background monitor starting...")

    seen = load_seen_hashes()

    while True:
        if not CHAT_LOG_PATH.exists():
            print(f"[!] No chat log found at {CHAT_LOG_PATH}")
            time.sleep(30)
            continue

        content = CHAT_LOG_PATH.read_text(encoding="utf-8")
        questions = extract_questions(content)

        for prompt, tag in questions:
            qhash = hash_prompt(prompt)
            if qhash not in seen:
                print(f"\n[📡] New unresolved question (#{tag}): {prompt}")
                try:
                    success = perform_web_search(prompt, source="orion-monitor", tag="websearch")
                except Exception as e:
                    print(f"[❌] Search failed: {e}")
                    success = False

                if success:
                    print(f"[✅] Search completed and processed.")
                    save_seen_hash(qhash)
                    seen.add(qhash)
                else:
                    print(f"[⚠️] Skipping save. Search did not complete or was rejected.")
        
        time.sleep(60)

if __name__ == "__main__":
    main()