from __future__ import annotations

from pathlib import Path
from textwrap import dedent

# Root where your CLI package lives
CLI_ROOT = Path(__file__).resolve().parent

# Curated list of scripts you want in the doc
# (add/remove as you go; this is the only place you maintain)
SCRIPT_FILES = [
    CLI_ROOT / "cli.py",
    CLI_ROOT / "__init__.py",
    CLI_ROOT / "shared" / "paths.py",
    CLI_ROOT / "shared" / "memory_core.py",
    CLI_ROOT / "commands" / "ingest.py",
    CLI_ROOT / "commands" / "memory.py",
    CLI_ROOT / "commands" / "identity.py",
    CLI_ROOT / "commands" / "tools.py",
    # add more as needed...
]

OUTPUT_PATH = CLI_ROOT / "orion_scripts_outline.md"


def make_header(path: Path) -> str:
    # Relative path from CLI root for readability
    rel = path.relative_to(CLI_ROOT)
    return f"## {rel.as_posix()}\n"


def extract_top_doc(path: Path) -> str:
    """
    Extremely dumb doc extractor:
    - If file starts with a triple-quoted string, use that as the "Role" block.
    - Otherwise, just leave a placeholder.
    """
    text = path.read_text(encoding="utf-8")
    stripped = text.lstrip()

    role_block = ""

    if stripped.startswith('"""') or stripped.startswith("'''"):
        quote = stripped[:3]
        end = stripped.find(quote, 3)
        if end != -1:
            doc = stripped[3:end]
            role_block = dedent(doc).strip()

    if role_block:
        return (
            "**Role / summary (from module docstring):**\n\n"
            + role_block
            + "\n\n"
        )

    return (
        "**Role / summary:**\n\n"
        "_(add a short description for this script here if needed)_\n\n"
    )


def build_document() -> str:
    parts: list[str] = []

    parts.append(
        dedent(
            """\
            # Orion CLI Scripts — Outline + Source

            > This file is **auto-generated**. Do not edit it directly.
            > Update the Python files and re-run `build_orion_doc.py` instead.

            """
        )
    )

    for path in SCRIPT_FILES:
        if not path.exists():
            continue

        header = make_header(path)
        doc = extract_top_doc(path)
        code = path.read_text(encoding="utf-8")

        section = []
        section.append(header)
        section.append(doc)
        section.append("### Full source\n")
        section.append("~~~python\n")
        section.append(code)
        section.append("\n~~~\n\n")

        parts.append("".join(section))

    return "".join(parts)


def main() -> None:
    doc = build_document()
    OUTPUT_PATH.write_text(doc, encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
