from __future__ import annotations

from datetime import datetime
from pathlib import Path
from textwrap import dedent
import fnmatch

# Root where your CLI package lives
CLI_ROOT = Path(__file__).resolve().parent

# Main output
OUTPUT_PATH = CLI_ROOT / "orion_cli_snapshot.md"

# Small sidecar file: useful for confirming what the snapshot included.
# This is intentionally excluded from the markdown snapshot itself.
MANIFEST_PATH = CLI_ROOT / "orion_cli_snapshot_manifest.txt"

# Keep this conservative. These are files that are normally useful in a source snapshot.
ALLOWED_EXTENSIONS = {
    ".py",
    ".md",
    ".txt",
    ".toml",
    ".yaml",
    ".yml",
    ".json",
    ".ps1",
    ".bat",
    ".sh",
}

ALLOWED_FILENAMES = {
    ".gitkeep",
}

# Directories we should never walk into for this kind of source snapshot.
EXCLUDED_DIR_NAMES = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    "env",
    "node_modules",
}

# File/path patterns to exclude from the snapshot.
# Important: exclude generated snapshots, or the output can recursively eat itself.
EXCLUDED_GLOBS = {
    "*.pyc",
    "*.pyo",
    "*.pyd",
    "*.so",
    "*.dll",
    "*.exe",
    "*.bin",
    "*.db",
    "*.sqlite",
    "*.sqlite3",
    "*.gguf",
    "*.safetensors",
    "*.pt",
    "*.onnx",
    "*.zip",
    "*.7z",
    "*.tar",
    "*.gz",
    "*.png",
    "*.jpg",
    "*.jpeg",
    "*.webp",
    "orion_cli_snapshot*.md",
    "orion_cli_snapshot_manifest.txt",
    "orion_scripts_outline*.md",
    "orion_user_data*.md",
}

# Safety valve so a giant accidental log/config dump does not flood the markdown.
MAX_FILE_BYTES = 250_000


def rel_posix(path: Path) -> str:
    """Return a readable path relative to CLI_ROOT."""
    return path.resolve().relative_to(CLI_ROOT.resolve()).as_posix()


def matches_any(rel_path: str, patterns: set[str]) -> bool:
    """Match a POSIX-style relative path against shell-style glob patterns."""
    rel_path = rel_path.replace("\\", "/")
    return any(fnmatch.fnmatch(rel_path, pattern) for pattern in patterns)


def is_in_excluded_dir(path: Path) -> bool:
    """True if any part of the path is inside a cache/env/git/noise directory."""
    try:
        rel_parts = path.resolve().relative_to(CLI_ROOT.resolve()).parts
    except ValueError:
        return True
    return any(part in EXCLUDED_DIR_NAMES for part in rel_parts)


def is_allowed_text_file(path: Path) -> bool:
    """
    Decide whether a file belongs in the snapshot.

    This uses extension/name filtering first. Then it enforces a size limit.
    The reader itself uses UTF-8 with replacement, so odd text files won't crash the run.
    """
    if not path.is_file():
        return False

    if is_in_excluded_dir(path):
        return False

    try:
        rel = rel_posix(path)
    except ValueError:
        return False

    if matches_any(rel, EXCLUDED_GLOBS):
        return False

    if path.name not in ALLOWED_FILENAMES and path.suffix.lower() not in ALLOWED_EXTENSIONS:
        return False

    try:
        if path.stat().st_size > MAX_FILE_BYTES:
            return False
    except OSError:
        return False

    return True


def discover_snapshot_files() -> list[Path]:
    """
    Discover files at runtime.

    This replaces the old hand-maintained SCRIPT_FILES list.
    Any new .py file under orion_cli/commands, shared, semantic, settings, etc.
    will be picked up automatically on the next run.
    """
    files: list[Path] = []

    for path in CLI_ROOT.rglob("*"):
        if is_allowed_text_file(path):
            files.append(path.resolve())

    return sorted(files, key=lambda p: rel_posix(p).lower())


def make_header_cli(path: Path) -> str:
    return f"## {rel_posix(path)}\n"


def read_text_safe(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def extract_top_doc(path: Path) -> str:
    """
    Simple doc extractor:
    - If a Python-ish file starts with a triple-quoted string, use that as the Role block.
    - Otherwise, leave a placeholder.
    """
    text = read_text_safe(path)
    stripped = text.lstrip()

    role_block = ""

    if stripped.startswith('\"\"\"') or stripped.startswith("'''"):
        quote = stripped[:3]
        end = stripped.find(quote, 3)
        if end != -1:
            doc = stripped[3:end]
            role_block = dedent(doc).strip()

    if role_block:
        return "**Role / summary (from module docstring):**\n\n" + role_block + "\n\n"

    return (
        "**Role / summary:**\n\n"
        "_(add a short description for this script here if needed)_\n\n"
    )


def fence_language(path: Path) -> str:
    suffix = path.suffix.lower()

    if suffix == ".py":
        return "python"
    if suffix in {".yaml", ".yml"}:
        return "yaml"
    if suffix == ".json":
        return "json"
    if suffix == ".toml":
        return "toml"
    if suffix == ".md":
        return "markdown"
    if suffix == ".ps1":
        return "powershell"
    if suffix in {".bat", ".cmd"}:
        return "batch"
    if suffix == ".sh":
        return "bash"

    return "text"


def write_manifest(files: list[Path]) -> None:
    lines = [
        "# Orion CLI Snapshot Manifest",
        f"# Generated: {datetime.now().isoformat(timespec='seconds')}",
        f"# Root: {CLI_ROOT}",
        f"# Files: {len(files)}",
        "",
    ]
    lines.extend(rel_posix(path) for path in files)
    MANIFEST_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_document(files: list[Path]) -> str:
    parts: list[str] = []

    parts.append(
        dedent(
            f"""\
            # Orion CLI Scripts — Outline + Source

            > This file is **auto-generated**. Do not edit it directly.
            > Update the source files and re-run `build_orion_cli_md.py` instead.
            >
            > Snapshot generated: {datetime.now().isoformat(timespec="seconds")}
            > Files included: {len(files)}
            >
            > This document is the authoritative structural view of the Orion CLI. ZIP archives are supplementary.

            """
        )
    )

    for path in files:
        code = read_text_safe(path)

        section = []
        section.append(make_header_cli(path))

        if path.name == ".gitkeep":
            section.append("**Folder index marker:**\n\n")
            section.append("### Contents\n")
        else:
            section.append(extract_top_doc(path))
            section.append("### Full source\n")

        section.append(f"~~~{fence_language(path)}\n")
        section.append(code)
        if not code.endswith("\n"):
            section.append("\n")
        section.append("~~~\n\n")

        parts.append("".join(section))

    return "".join(parts)


def main() -> None:
    files = discover_snapshot_files()
    write_manifest(files)

    doc = build_document(files)
    OUTPUT_PATH.write_text(doc, encoding="utf-8")

    print(f"Wrote {OUTPUT_PATH}")
    print(f"Wrote {MANIFEST_PATH}")
    print(f"Included {len(files)} files")


if __name__ == "__main__":
    main()
