import logging
from pathlib import Path

def _read_text(path: Path):
    try:
        data = path.read_text(encoding="utf-8")
        return data, None
    except Exception as e:
        return None, str(e)

def run(directory: str):
    base = Path(directory)
    persona = base / "persona_header.txt"
    memory = base / "memory_header.txt"

    ok = True
    for file in [persona, memory]:
        if not file.exists():
            logging.error(f"Missing: {file}")
            ok = False
            continue
        text, err = _read_text(file)
        if err:
            logging.error(f"Read error {file}: {err}")
            ok = False
        else:
            if not text.strip():
                logging.warning(f"Empty or whitespace-only: {file}")
                ok = False
            else:
                logging.info(f"OK: {file} ({len(text)} chars)")

    if ok:
        print("✅ Persona check passed.")
    else:
        print("⚠ Persona check found issues. See logs.")
