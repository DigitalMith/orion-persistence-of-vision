import json
import time
from pathlib import Path
from datetime import datetime

from orion_cli.shared.nemo import nemo_annotate_turn


# --------------------------------------------------------------------
# CONFIGURATION
# --------------------------------------------------------------------
CHECKPOINT_EVERY = 25   # write checkpoint markers every 25 turns
SLEEP_BETWEEN_TURNS = 0.2  # small delay to avoid overwhelming GPU/CPU


# --------------------------------------------------------------------
# HELPERS
# --------------------------------------------------------------------
def count_lines(path: Path) -> int:
    """Count the number of non-empty lines in a JSONL file."""
    n = 0
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                n += 1
    return n


def load_jsonl(path: Path):
    """Stream-load a JSONL file of raw dialog turns."""
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                print(f"[WARN] Skipping malformed line: {line[:80]}...")


def resume_position(output_path: Path) -> int:
    """
    Detect how many lines were successfully written to the output file.
    Returns the number of enriched entries already completed.
    """
    if not output_path.exists():
        return 0

    done = 0
    with output_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("CHECKPOINT:"):
                # skip checkpoint markers
                continue
            if line:
                done += 1
    return done


def write_checkpoint(fh, index: int):
    """Write an internal checkpoint marker."""
    fh.write(f"CHECKPOINT:{index}\n")
    fh.flush()


# --------------------------------------------------------------------
# MAIN ANNOTATION PIPELINE
# --------------------------------------------------------------------
def annotate_file(input_path: str, output_dir: str):
    src = Path(input_path)
    if not src.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_path = out_dir / f"enriched_legacy_{timestamp}.jsonl"

    # If a partial output file already exists, resume from it.
    resume_at = resume_position(out_path)
    print(f"[INFO] Resuming annotation at turn index: {resume_at}")

    enriched_count = resume_at
    total_lines = count_lines(src)
    print(f"[INFO] Total turns to annotate: {total_lines}")
    raw_iter = load_jsonl(src)

    # Open output file in append mode.
    with out_path.open("a", encoding="utf-8") as out_f:

        for idx, raw in enumerate(raw_iter):
            # NEW: progress output
            print(f"[ANNOTATE] {idx + 1} / {total_lines}", end="\r")
    
            # Skip already-completed entries when resuming.
            if idx < resume_at:
                continue

            user_text = raw.get("user_text") or raw.get("user") or ""
            assistant_text = raw.get("assistant_text") or raw.get("assistant") or ""
            if not user_text or not assistant_text:
                print(f"[WARN] Skipping empty turn at index {idx}")
                continue

            try:
                ann = nemo_annotate_turn(user_text, assistant_text)
            except Exception as ex:
                print(f"[ERROR] Annotation failed at index {idx}: {ex}")
                print("[INFO] Retrying once in 3 seconds...")
                time.sleep(3)
                try:
                    ann = nemo_annotate_turn(user_text, assistant_text)
                except Exception as ex2:
                    print(f"[FATAL] Turn skipped due to repeated failure: {ex2}")
                    continue

            enriched = {
                "user": user_text,
                "assistant": assistant_text,
                "timestamp_user": raw.get("user_timestamp"),
                "timestamp_assistant": raw.get("assistant_timestamp"),
                "source_file": raw.get("source_file"),
                "pair_index": raw.get("pair_index"),

                # Nemo / model annotations
                "annotations": ann,
            }

            out_f.write(json.dumps(enriched, ensure_ascii=False) + "\n")
            enriched_count += 1

            # Write a checkpoint marker every N lines
            if enriched_count % CHECKPOINT_EVERY == 0:
                write_checkpoint(out_f, enriched_count)
                print(f"[CHECKPOINT] {enriched_count} entries completed.")

            # Throttle slightly to be safe on long runs
            time.sleep(SLEEP_BETWEEN_TURNS)

    print("\n[ANNOTATION COMPLETE]")
    print(f"Total enriched turns: {enriched_count}")
    print(f"Output file: {out_path}\n")

    return out_path
