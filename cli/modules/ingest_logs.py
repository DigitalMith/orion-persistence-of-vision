# modules/ingest_logs.py

import os
import json
from datetime import datetime
from modules import embed, file_utils

def ingest_staged_logs(staged_dir, log_output_dir):
    if not os.path.isdir(staged_dir):
        raise ValueError(f"Staged log directory not found: {staged_dir}")

    files = [f for f in os.listdir(staged_dir) if f.endswith("_raw.jsonl")]
    print(f"🔍 Found {len(files)} staged logs to ingest...")

    for fname in files:
        full_path = os.path.join(staged_dir, fname)
        print(f"⏳ Ingesting: {fname}")

        with open(full_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for line in lines:
            try:
                data = json.loads(line)
                text = data.get("content") or data.get("text") or ""
                metadata = {
                    "source": "cli",
                    "timestamp": data.get("timestamp", datetime.utcnow().isoformat()),
                    "file": fname
                }

                if text.strip():
                    embed.embed_and_store(text, metadata)
                else:
                    print(f"⚠️ Empty content skipped in: {fname}")
            except Exception as e:
                print(f"❌ Failed to ingest line in {fname}: {e}")

        # Optionally move processed file or log it
        file_utils.log_ingested_file(fname, log_output_dir)
