# modules/file_utils.py

import os
import hashlib
from datetime import datetime

def hash_content(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def log_ingested_file(filename, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    log_file = os.path.join(output_dir, "ingestion.log")

    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat()} | INGESTED | {filename}\n")

    print(f"📝 Logged ingestion: {filename}")

def merge_jsonl_files(input_files, output_path):
    seen_hashes = set()
    merged = []

    for file in input_files:
        if not os.path.exists(file):
            print(f"⚠️ Skipping missing file: {file}")
            continue

        with open(file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    obj = json.loads(line)
                    text = obj.get("text", "").strip()
                    if not text:
                        continue
                    hash_id = hash_content(text)
                    if hash_id in seen_hashes:
                        continue
                    seen_hashes.add(hash_id)
                    merged.append(obj)
                except Exception as e:
                    print(f"❌ Failed to parse line in {file}: {e}")

    with open(output_path, "w", encoding="utf-8") as out:
        for item in merged:
            out.write(json.dumps(item) + "\n")

    print(f"✅ Merged {len(merged)} unique entries into: {output_path}")

