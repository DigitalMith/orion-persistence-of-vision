# modules/normalize_chatlogs.py

import os
import json
from datetime import datetime

def normalize_chatlog(input_path, output_path):
    logs = []

    # Handle single file or directory
    files = [input_path] if input_path.endswith(".json") else [
        os.path.join(input_path, f)
        for f in os.listdir(input_path) if f.endswith(".json")
    ]

    for file in files:
        with open(file, "r", encoding="utf-8") as f:
            try:
                session = json.load(f)
                messages = session.get("chat", session.get("messages", []))
            except Exception as e:
                print(f"❌ Error reading {file}: {e}")
                continue

        for msg in messages:
            if "role" not in msg or "content" not in msg:
                continue
            timestamp = msg.get("timestamp", datetime.utcnow().isoformat())
            role = msg["role"]
            text = msg["content"]

            logs.append({
                "timestamp": timestamp,
                "source": "normalize",
                "speaker": role,
                "text": text
            })

    print(f"🧼 Normalized {len(logs)} messages.")

    # Write to JSONL
    with open(output_path, "w", encoding="utf-8") as out:
        for line in logs:
            out.write(json.dumps(line) + "\n")

    print(f"✅ Output saved to: {output_path}")
