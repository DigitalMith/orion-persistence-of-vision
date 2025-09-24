# cli/scripts/prepare_lora_jsonl.py

import os, json
import nltk
from transformers import AutoTokenizer

# make sure punkt is downloaded (only needs to happen once)
nltk.download("punkt", quiet=True)

tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")

def sentence_chunk(text: str, max_tokens: int = 400):
    """Split text into sentence-based chunks capped at max_tokens."""
    sentences = nltk.sent_tokenize(text)
    chunks, current, count = [], [], 0
    for sent in sentences:
        tokens = tokenizer.encode(sent, add_special_tokens=False)
        if count + len(tokens) > max_tokens and current:
            chunks.append(" ".join(current))
            current, count = [], 0
        current.append(sent)
        count += len(tokens)
    if current:
        chunks.append(" ".join(current))
    return chunks

def process_directory(input_dir: str, label: str):
    """Yield JSONL-ready records from a directory of .txt files."""
    if not os.path.isdir(input_dir):
        print(f"⚠️ Directory not found: {input_dir}")
        return

    for fname in os.listdir(input_dir):
        if not fname.endswith(".txt"):
            continue
        path = os.path.join(input_dir, fname)
        print(f"🔍 Processing {path} ...")
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        chunks = sentence_chunk(text)
        print(f"   → {len(chunks)} chunks created")
        for i, chunk in enumerate(chunks):
            record = {
                "prompt": f"{label} excerpt from {fname}",
                "completion": chunk.strip()
            }
            yield record

def main():
    base_dir = r"C:\Orion\train"
    voice_dir = os.path.join(base_dir, "voice")
    study_dir = os.path.join(base_dir, "study")

    output = os.path.join(base_dir, "lora_dataset.jsonl")
    written = 0

    try:
        with open(output, "w", encoding="utf-8") as out:
            for record in process_directory(voice_dir, "Mystical Voice"):
                out.write(json.dumps(record, ensure_ascii=False) + "\n")
                written += 1
            for record in process_directory(study_dir, "Mystical Study"):
                out.write(json.dumps(record, ensure_ascii=False) + "\n")
                written += 1

        if written == 0:
            print(f"⚠️ No chunks written. Check that {voice_dir} and {study_dir} contain .txt files.")
        else:
            print(f"✅ {written} chunks written to {output}")

    except Exception as e:
        print(f"💥 ERROR: {type(e).__name__}: {e}")

if __name__ == "__main__":
    main()