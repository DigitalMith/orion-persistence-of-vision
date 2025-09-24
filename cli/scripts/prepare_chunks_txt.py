# cli/scripts/prepare_chunks_txt.py
import os, nltk
from transformers import AutoTokenizer

nltk.download("punkt", quiet=True)
tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased", use_fast=True)

INPUT_DIR = r"C:\Orion\train\clean"
OUTPUT_DIR = r"C:\Orion\train\output"
MAX_TOKENS = 400

def sentence_chunk(text: str, max_tokens: int = MAX_TOKENS):
    sentences = nltk.sent_tokenize(text)
    chunks, cur, cur_count = [], [], 0
    for sent in sentences:
        tokens = tokenizer.encode(sent, add_special_tokens=False)
        if cur and (cur_count + len(tokens) > max_tokens):
            chunks.append(" ".join(cur).strip())
            cur, cur_count = [], 0
        cur.append(sent)
        cur_count += len(tokens)
    if cur:
        chunks.append(" ".join(cur).strip())
    return chunks

def process_file(in_path: str, out_dir: str):
    with open(in_path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()
    chunks = sentence_chunk(text)
    base = os.path.splitext(os.path.basename(in_path))[0]
    os.makedirs(out_dir, exist_ok=True)
    for i, ch in enumerate(chunks, start=1):
        out_path = os.path.join(out_dir, f"{base}_chunk{i:04d}.txt")
        with open(out_path, "w", encoding="utf-8") as out:
            out.write(ch)
    print(f"📝 {len(chunks)} chunks from {in_path} → {out_dir}")

def main():
    print(f"Starting: {INPUT_DIR} -> {OUTPUT_DIR}")
    total_chunks = 0
    for root, _, files in os.walk(INPUT_DIR):
        for fname in files:
            if not fname.lower().endswith(".txt"):
                continue
            in_path = os.path.join(root, fname)
            rel_dir = os.path.relpath(root, INPUT_DIR)
            out_dir = os.path.join(OUTPUT_DIR, rel_dir)
            process_file(in_path, out_dir)
            total_chunks += 1
    print(f"✅ Finished. Output in {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
