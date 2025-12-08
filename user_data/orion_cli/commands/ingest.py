"""
ingest.py — Typer Commands for Persona & Episodic Ingestion
-----------------------------------------------------------

These commands allow users to add persona entries and episodic memories
into Orion's long-term memory store.

All ingestion logic lives in:
    orion_cli.shared.memory_core
"""

from __future__ import annotations

import typer
from pathlib import Path

from orion_cli.shared.memory_core import (
    add_persona_entry,
    add_episodic_entry,
)


app = typer.Typer(help="Ingest persona and episodic memory into Orion.")


# -------------------------------------------------------------
# Helpers
# -------------------------------------------------------------

def _load_text_source(source: str, is_file: bool) -> str:
    """
    Load text either from a string literal or from a file.
    """
    if is_file:
        path = Path(source)
        if not path.exists():
            raise typer.BadParameter(f"File not found: {source}")

        return path.read_text(encoding="utf-8")

    return source


# -------------------------------------------------------------
# Persona ingestion
# -------------------------------------------------------------

@app.command("persona")
def ingest_persona(
    source: str = typer.Argument(
        ...,
        help="Text to ingest or path to a file containing persona data."
    ),
    file: bool = typer.Option(
        False,
        "--file",
        "-f",
        help="Interpret <source> as a file path.",
    ),
):
    """
    Add a persona memory entry (or entries) to Orion.
    """
    text = _load_text_source(source, file)

    lines = [line.strip() for line in text.split("\n") if line.strip()]
    count = 0

    for line in lines:
        new_id = add_persona_entry(line)
        if new_id:
            typer.echo(f"Added persona entry: {new_id}")
            count += 1

    typer.echo(f"Completed. {count} persona entries added.")


# -------------------------------------------------------------
# Episodic ingestion
# -------------------------------------------------------------

@app.command("episodic")
def ingest_episodic(
    source: str = typer.Argument(
        ...,
        help="Text or file containing an episodic memory entry."
    ),
    file: bool = typer.Option(
        False,
        "--file",
        "-f",
        help="Interpret <source> as a file path.",
    ),
    min_length: int = typer.Option(
        10,
        "--min-length",
        "-m",
        help="Minimum word count required for ingestion (default: 10).",
    ),
):
    """
    Add an episodic memory entry to Orion.
    """
    text = _load_text_source(source, file)

    new_id = add_episodic_entry(
        text,
        metadata={"ingest_source": "cli"},
        min_length=min_length,
    )

    if new_id:
        typer.echo(f"Added episodic entry: {new_id}")
    else:
        typer.echo("Episodic entry too short or duplicate. Not added.")


__all__ = ["app"]
