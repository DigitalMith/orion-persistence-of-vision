import os
import json
from glob import glob
from datetime import datetime

# --- CONFIGURATION ---

CHAT_LOG_DIR = r"C:\Orion\text-generation-webui\user_data\logs\chat\Orion"

# Dynamically name the output file with today's date
date_str = datetime.now().strftime("%Y%m%d")
OUTPUT_FILE = fr"C:\Orion\memory\chat_2ltm-{date_str}.json"

# --- CODE ---

def parse_log_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    ltm_entries = []

    # Check for "messages" key (newer format)
    if 'messages' in data:
        session_start = data.get('metadata', {}).get('start', None)
        for msg in data.get('messages', []):
            entry = {
                'role': msg.get('role'),
                'content': msg.get('content'),
                'timestamp': msg.get('timestamp') or session_start
            }
            ltm_entries.append(entry)
    # Check for "internal" key (your format here)
    elif 'internal' in data and isinstance(data['internal'], list):
        # Assign a generic timestamp (or use None/empty string)
        session_start = data.get('metadata', {}).get('start', None)
        for pair in data['internal']:
            if len(pair) == 2:
                
                import re  # At the top of your script if not already

                # Extract timestamp from filename, e.g. '20250805-18-01-41.json'
                m = re.match(r"(\d{8})-(\d{2})-(\d{2})-(\d{2})", os.path.basename(filepath))
                if m:
                    ts = f"{m.group(1)} {m.group(2)}:{m.group(3)}:{m.group(4)}"
                else:
                    ts = session_start or ''

                ltm_entries.append({'role': 'user', 'content': pair[0], 'timestamp': ts})
                ltm_entries.append({'role': 'assistant', 'content': pair[1], 'timestamp': ts})
                
    return ltm_entries

def deduplicate_memories(memories):
    seen = set()
    deduped = []
    for mem in memories:
        key = (mem['role'], mem['content'].strip(), mem['timestamp'])
        if key not in seen:
            deduped.append(mem)
            seen.add(key)
    return deduped

def main():
    all_memories = []
    log_files = glob(os.path.join(CHAT_LOG_DIR, "*.json"))
    print(f"Found {len(log_files)} log files.")

    for log_path in log_files:
        print(f"Parsing {os.path.basename(log_path)}...")
        entries = parse_log_file(log_path)
        print(f"  Entries found: {len(entries)}")
        if entries:
            print(f"    First entry: {entries[0]}")
        else:
            # Print the first 500 chars of the raw file if empty (for debugging)
            with open(log_path, "r", encoding="utf-8") as f:
                raw = f.read()
                print("    Raw file preview (truncated):")
                print(raw[:500])
        all_memories.extend(entries)
    
    print(f"Total messages before deduplication: {len(all_memories)}")
    all_memories = deduplicate_memories(all_memories)
    print(f"Total messages after deduplication: {len(all_memories)}")

    all_memories.sort(key=lambda x: x.get('timestamp') or '')

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_memories, f, indent=2, ensure_ascii=False)
    print(f"Saved merged LTM to: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
