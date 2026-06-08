"""
memory.py — Typer Commands for Orion CNS Memory Operations
----------------------------------------------------------

This module exposes user-facing memory commands for the Orion CLI.

All heavy logic lives in:
    orion_cli.shared.memory_core

Commands implemented here:
- recall: Retrieve persona or episodic memory
- stats: Show memory statistics

Usage examples:
    orion memory recall "tell me about yourself"
    orion memory recall --persona "identity traits"
    orion memory stats
"""

from __future__ import annotations

import typer

from orion_cli.shared.memory_core import (
    recall_persona,
    recall_episodic,
    recall_semantic,
    memory_stats,
)

app = typer.Typer(help="Inspect and query Orion's long-term memory stores.")


# -------------------------------------------------------------
# Recall command
# -------------------------------------------------------------


@app.command("recall")
def recall_command(
    query: str = typer.Argument(..., help="Query text for memory recall."),
    persona: bool = typer.Option(
        False,
        "--persona",
        "-p",
        help="Search only the persona memory collection.",
    ),
    semantic: bool = typer.Option(
        False,
        "--semantic",
        "-s",
        help="Search only the semantic memory collection.",
    ),
    episodic: bool = typer.Option(
        False,
        "--episodic",
        "-e",
        help="Search only the episodic memory collection.",
    ),
    top_k: int = typer.Option(
        5,
        "--top-k",
        "-k",
        help="Number of results to return (default: 5).",
    ),
):
    """
    Recall relevant persona, semantic, or episodic memories.
    If no memory category is selected, all three collections are searched.
    """
    any_selected = persona or semantic or episodic

    search_persona = persona or not any_selected
    search_semantic = semantic or not any_selected
    search_episodic = episodic or not any_selected

    found_any = False

    if search_persona:
        hits = recall_persona(query, top_k)
        if hits:
            found_any = True
            typer.echo("=== Persona Memory ===")
            for h in hits:
                typer.echo(f"- {h}")
            typer.echo("")

    if search_semantic:
        hits = recall_semantic(query, top_k)
        if hits:
            found_any = True
            typer.echo("=== Semantic Memory ===")
            for h in hits:
                typer.echo(f"- {h}")
            typer.echo("")

    if search_episodic:
        hits = recall_episodic(query, top_k)
        if hits:
            found_any = True
            typer.echo("=== Episodic Memory ===")
            for h in hits:
                typer.echo(f"- {h}")

    if not found_any:
        typer.echo("No relevant memories found.")


# -------------------------------------------------------------
# Stats command
# -------------------------------------------------------------


@app.command("stats")
def stats_command():
    """
    Display memory statistics for persona, episodic, semantic, and semantic candidate storage.
    """
    stats = memory_stats()

    typer.echo("=== Orion Memory Stats ===")
    typer.echo(f"Persona entries:              {stats.get('persona_entries', 0)}")
    typer.echo(f"Episodic entries:             {stats.get('episodic_entries', 0)}")
    typer.echo(f"Semantic entries:             {stats.get('semantic_entries', 0)}")
    typer.echo(f"Semantic candidate entries:   {stats.get('semantic_candidate_entries', 0)}")


__all__ = ["app"]
