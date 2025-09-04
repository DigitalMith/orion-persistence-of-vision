
import os
import json
import time
import datetime
from pathlib import Path
from orion_utils.memory_ops import (
    sentence_segment,
    tag_sentences,
    store_to_chroma,
    embed_sentence,
    search_similar,
)

SIM_THRESHOLD = 0.95  # similarity threshold for deduplication


def main(file_path: str, topic=None, tags=None, out=None, max_chars=800):
    if not os.path.exists(file_path):
        print(f"[✗] File not found: {file_path}")
        return

    print(f"[→] Reading from: {file_path}")
    start = time.time()

    # Resolve output path
    if not out:
        default_dir = Path("C:/Orion/logs/cli")
        default_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        out = default_dir / f"summary_{timestamp}.jsonl"
    else:
        out = Path(out)
        out.parent.mkdir(parents=True, exist_ok=True)

    # Flatten tag list to a string
    tag_str = ", ".join(tags) if tags else None

    with open(file_path, 'r', encoding='utf-8-sig') as f:
        raw_text = f.read()

    sentences = sentence_segment(raw_text)
    entries = []
    accepted = 0
    failed = 0

    for idx, sentence in enumerate(sentences):
        sentence = sentence.strip()
        if len(sentence) < 10:
            continue  # skip short

        if accepted > 0 and accepted % 25 == 0:
            print(f"[... still working] {accepted} accepted, {failed} failed...")

        emb = embed_sentence(sentence)
        dup = search_similar(emb, threshold=SIM_THRESHOLD)
        if dup:
            print(f"[→] Skipped (duplicate @ {dup['similarity']}): '{sentence}'")
            continue

        entry_tags = tag_sentences(sentence, extra_tags=tags)
        try:
            ok = store_to_chroma(
                sentence,
                tag_str,
                topic=topic,
                subtopic=None,
                source=os.path.basename(file_path),
                embedding=emb,
            )
        except Exception as e:
            print(f"[✗] Failed to store: {e}")
            failed += 1
            continue

        if not ok:
            failed += 1
            continue

        entries.append({
            "text": sentence,
            "tags": entry_tags,
            "topic": topic,
            "source": os.path.basename(file_path),
        })
        accepted += 1

    with open(out, "w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    end = time.time()
    print(f"\n📄 Summary for '{os.path.basename(file_path)}':")
    print(f"  • Lines processed:     {len(sentences)}")
    print(f"  • Entries accepted:    {accepted}")
    print(f"  • Entries failed:      {failed}")
    print(f"  • Output log:          {out}")
    print(f"  • Time elapsed:        {round(end - start, 2)} sec")
