# modules/restore_ltm.py

import json
import os
from modules import embed, file_utils

def restore_from_jsonl(path):
    if not os.path.exists(path):
        print(f"❌ File not found: {path}")
        return

    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    print(f"📦 Restoring {len(lines)} entries from {path}...")

    count = 0
    for line in lines:
        try:
            obj = json.loads(line)
            text = obj.get("text", "")
            meta = obj.get("metadata", {})
            if not text.strip():
                continue

            doc_id = file_utils.hash_content(text)
            embed.embed_and_store(text, meta)
            count += 1
        except Exception as e:
            print(f"❌ Failed line: {e}")

    print(f"✅ Restored {count} memory entries.")
