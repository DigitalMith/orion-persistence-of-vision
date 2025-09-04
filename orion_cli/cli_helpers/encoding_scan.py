import logging
from pathlib import Path

BOM = b"\xef\xbb\xbf"

def _is_utf8(path: Path):
    try:
        with path.open("rb") as f:
            data = f.read()
        # check BOM
        has_bom = data.startswith(BOM)
        # try decode
        data.decode("utf-8")
        return True, has_bom
    except Exception:
        return False, False

def _fix_bom(path: Path):
    raw = path.read_bytes()
    if raw.startswith(BOM):
        path.write_bytes(raw[len(BOM):])

def run(target: str, fix: bool = False):
    p = Path(target)
    if not p.exists():
        logging.error(f"Path not found: {p}")
        return

    files = [p] if p.is_file() else [f for f in p.rglob("*") if f.is_file()]
    total = 0; non_utf8 = 0; bom_count = 0
    for f in files:
        total += 1
        ok, has_bom = _is_utf8(f)
        if not ok:
            non_utf8 += 1
            logging.warning(f"[NON-UTF8] {f}")
        if has_bom:
            bom_count += 1
            logging.info(f"[BOM] {f}")
            if fix:
                _fix_bom(f)
                logging.info(f"[FIXED] Removed BOM: {f}")

    print(f"Scanned: {total} files")
    print(f"Non-UTF8: {non_utf8}")
    print(f"BOM present: {bom_count}{' (fixed)' if fix else ''}")
