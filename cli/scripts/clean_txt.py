# cli/scripts/clean_txt.py
import os
import re
from pathlib import Path

INPUT_DIR = r"C:\Orion\train"
OUTPUT_DIR = r"C:\Orion\train\clean"

SKIP_PHRASES = [
    "table of contents", "glossary", "index", "about this book", "copyright",
    "isbn", "issn", "all rights reserved", "table of the chapters", "contents"
]

SHORT_HEADER_MAX_WORDS = 6
MIN_LINE_WORDS_KEEP = 3  # drop lines with fewer than this (likely page headers / numbers)

re_page_number = re.compile(r"^\s*\d+\s*$")
re_scan_tag = re.compile(r"REP\d{2,}_?\d*|Page\s+\d+|Page\s*$", re.IGNORECASE)

def is_junk_line(line: str) -> bool:
    s = line.strip()
    if not s:
        return True
    low = s.lower()
    if any(p in low for p in SKIP_PHRASES):
        return True
    if re_page_number.match(s):
        return True
    if re_scan_tag.search(s):
        return True
    # ALL CAPS short headers (LETTER I, PREFACE)
    if s.isupper() and len(s.split()) <= SHORT_HEADER_MAX_WORDS:
        return True
    # very short lines likely headers/footers (like single word titles)
    if len(s.split()) < MIN_LINE_WORDS_KEEP:
        return True
    return False

def fix_hyphenation_and_whitespace(text: str) -> str:
    # Fix hyphenated line-breaks: word-\nNext -> wordNext
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)
    # Replace remaining single newlines inside paragraphs with spaces (we handle merging later)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text

def split_keep_paragraphs(lines):
    """
    Given cleaned lines (no junk), merge wrapped lines into paragraphs.
    Heuristic:
      - Buffer lines until a line ends with sentence-final punctuation (.?!:"”')
      - If a line ends with punctuation, flush buffer as a paragraph
      - Also flush if next line starts with a capitalized word and buffer length is large
    """
    merged = []
    buffer = ""
    for i, line in enumerate(lines):
        line = line.strip()
        if not buffer:
            buffer = line
        else:
            buffer += " " + line

        # If current line ends with sentence punctuation or closing quote, flush paragraph
        if re.search(r"[\.!?•…\"\”\']\s*$", line):
            merged.append(buffer.strip())
            buffer = ""
            continue

        # Flush heuristics: avoid huge buffers if punctuation missing (OCR oddities)
        if len(buffer) > 1000:
            merged.append(buffer.strip())
            buffer = ""

    if buffer:
        merged.append(buffer.strip())
    return merged

def clean_file(in_path: str, out_path: str):
    with open(in_path, "r", encoding="utf-8", errors="ignore") as f:
        raw = f.read()

    # quick scan cleanup
    raw = raw.replace("\f", "\n")
    raw = fix_hyphenation_and_whitespace(raw)

    # split into lines and filter junk
    raw_lines = [ln.strip() for ln in raw.split("\n")]
    keep_lines = [ln for ln in raw_lines if ln and not is_junk_line(ln)]

    # Merge wrapped lines into paragraphs
    paragraphs = split_keep_paragraphs(keep_lines)

    # Optional: collapse multiple spaces
    paragraphs = [re.sub(r"\s+", " ", p).strip() for p in paragraphs if p.strip()]

    # Write paragraphs separated by a single blank line
    out_dir = os.path.dirname(out_path)
    os.makedirs(out_dir, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as out:
        out.write("\n\n".join(paragraphs) + "\n")

def main():
    print(f"Starting cleaning: {INPUT_DIR} -> {OUTPUT_DIR}")
    processed = 0
    for root, _, files in os.walk(INPUT_DIR):
        rel = os.path.relpath(root, INPUT_DIR)
        for fname in files:
            if not fname.lower().endswith(".txt"):
                continue
            in_path = os.path.join(root, fname)
            out_subdir = os.path.join(OUTPUT_DIR, rel) if rel != "." else OUTPUT_DIR
            out_path = os.path.join(out_subdir, fname)
            try:
                print(f"🧹 Cleaning {in_path} -> {out_path}")
                clean_file(in_path, out_path)
                processed += 1
            except Exception as e:
                print(f"💥 Failed {in_path}: {type(e).__name__}: {e}")
    print(f"✅ Done. {processed} files cleaned and written to {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
