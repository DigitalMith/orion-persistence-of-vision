"""
cns42.py — CLI commands for Orion CNS 4.2 routed recall
-------------------------------------------------------

Read-only commands for testing the validated CNS 4.2 promoted collections.
"""

from __future__ import annotations

import json

import typer

from orion_cli.shared.cns42_recall import (
    EXPECTED_COUNTS,
    format_hits_for_prompt,
    recall_cns42,
    route_query,
    validate_counts,
    verify_cns42_recall,
)

app = typer.Typer(help="CNS 4.2 routed recall tools.")


@app.command("stats")
def stats_command() -> None:
    """Show CNS 4.2 collection counts."""
    ok, counts, errors = validate_counts()

    typer.echo("=== Orion CNS 4.2 Collection Stats ===")
    for name, expected in EXPECTED_COUNTS.items():
        typer.echo(f"{name}: {counts.get(name, 0)} expected {expected}")

    if ok:
        typer.echo("Status: PASS")
    else:
        typer.echo("Status: REVIEW")
        for e in errors:
            typer.echo(f"[ERROR] {e}")


@app.command("route")
def route_command(query: str = typer.Argument(..., help="Query text to route.")) -> None:
    """Show how CNS 4.2 would route a query."""
    route_name, primary, order = route_query(query, "auto")
    typer.echo(f"query: {query}")
    typer.echo(f"route: {route_name}")
    typer.echo(f"primary_collection: {primary}")
    typer.echo("route_order:")
    for c in order:
        typer.echo(f"- {c}")


@app.command("recall")
def recall_command(
    query: str = typer.Argument(..., help="Query text for CNS 4.2 recall."),
    route: str = typer.Option(
        "auto",
        "--route",
        "-r",
        help="auto | semantic | relational | keepsake",
    ),
    top_k: int = typer.Option(4, "--top-k", "-k", help="Primary result count."),
    fallback_k: int = typer.Option(2, "--fallback-k", help="Fallback result count."),
    prompt: bool = typer.Option(False, "--prompt", help="Render prompt-injection block."),
    json_out: bool = typer.Option(False, "--json", help="Output JSON."),
) -> None:
    """Recall from CNS 4.2 with primary-route-first behavior."""
    allowed = {"auto", "semantic", "relational", "keepsake"}
    if route not in allowed:
        raise typer.BadParameter(f"--route must be one of: {', '.join(sorted(allowed))}")

    result = recall_cns42(
        query=query,
        route=route,  # type: ignore[arg-type]
        primary_top_k=top_k,
        fallback_top_k=fallback_k,
    )

    if json_out:
        typer.echo(json.dumps(result.as_dict(), ensure_ascii=False, indent=2))
        return

    if prompt:
        typer.echo(format_hits_for_prompt(result, include_fallback=fallback_k > 0))
        return

    typer.echo("=== CNS 4.2 Routed Recall ===")
    typer.echo(f"Query: {result.query}")
    typer.echo(f"Route: {result.route}")
    typer.echo(f"Primary: {result.primary_collection}")
    typer.echo("")

    typer.echo("-- Primary hits --")
    if not result.primary_hits:
        typer.echo("(none)")
    for i, h in enumerate(result.primary_hits, start=1):
        typer.echo(
            f"{i}. [{h.collection}] dist={h.distance} cat={h.category} "
            f"layer={h.memory_layer} draft={h.draft_id}"
        )
        typer.echo(f"   {h.document}")

    if result.fallback_hits:
        typer.echo("")
        typer.echo("-- Fallback hits, informational only --")
        for i, h in enumerate(result.fallback_hits, start=1):
            typer.echo(
                f"{i}. [{h.collection}] dist={h.distance} cat={h.category} "
                f"layer={h.memory_layer} draft={h.draft_id}"
            )
            typer.echo(f"   {h.document}")


@app.command("verify")
def verify_command(json_out: bool = typer.Option(False, "--json", help="Output JSON.")) -> None:
    """Run the CNS 4.2 10-query recall verification suite."""
    ok, reports = verify_cns42_recall()

    if json_out:
        typer.echo(json.dumps({"passed": ok, "tests": reports}, ensure_ascii=False, indent=2))
        return

    typer.echo("=== CNS 4.2 Recall Verification ===")
    passed_count = sum(1 for r in reports if r["passed"])
    typer.echo(f"Recall: {passed_count}/{len(reports)} passed")
    typer.echo(f"Status: {'PASS' if ok else 'REVIEW'}")
    typer.echo("")

    for r in reports:
        mark = "PASS" if r["passed"] else "REVIEW"
        typer.echo(f"{mark}: {r['query']}")
        typer.echo(f"  route: {r['route']}")
        typer.echo(f"  expected: {', '.join(r['expected'])}")
        typer.echo(f"  primary_categories: {', '.join(r['primary_categories'])}")
        top = r.get("top_hit")
        if top:
            typer.echo(f"  top: {top.get('category')} / {top.get('draft_id')}")
        typer.echo("")
