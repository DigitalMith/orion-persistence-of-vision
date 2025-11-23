import json
from pathlib import Path
import typer

from orion_cli.utils.persona_ingest import ingest_yaml
from orion_cli.utils.normalize_annotate_chat import normalize_directory
from orion_cli.utils.chroma_utils import (
    get_client,
)

app = typer.Typer(add_completion=False)

# ---------------------------------------------------------
# PERSONA INGESTION
# ---------------------------------------------------------
@app.command("persona")
def persona_ingest(
    file: str = typer.Option(..., "--file", "-f", help="Path to persona YAML file"),
    replace: bool = typer.Option(
        False, "--replace", help="Replace the existing persona collection"
    ),
):
    """
    Ingest persona YAML fragments into ChromaDB.
    """
    path = Path(file)
    if not path.exists():
        typer.echo(f"❌ Persona file not found: {path}")
        raise typer.Exit(1)

    docs = ingest_yaml(path)

    client = get_client()
    collection = client.get_or_create_collection("persona")

    if replace:
        typer.echo("🧹 Clearing existing persona collection…")
        client.delete_collection("persona")
        collection = client.get_or_create_collection("persona")

    if docs:
        typer.echo(f"🧠 Ingesting {len(docs)} persona documents…")
        for chunk in docs:
            collection.add(
                documents=[chunk["text"]],
                metadatas=[chunk["metadata"]],
                ids=[chunk["id"]],
            )

    typer.echo("✅ Persona ingest complete.")


# ---------------------------------------------------------
# EPISODIC INGESTION (Normalized Logs)
# ---------------------------------------------------------
@app.command("ingest")
def episodic_ingest(
    path: str = typer.Option(
        ..., "--path", "-p", help="Directory containing normalized chat logs"
    ),
    replace: bool = typer.Option(
        False, "--replace", help="Replace episodic memory collection"
    ),
):
    """
    Ingest already-normalized logs into episodic LTM.
    """
    input_dir = Path(path)
    if not input_dir.exists():
        typer.echo(f"❌ Path not found: {input_dir}")
        raise typer.Exit(1)

    typer.echo(f"📂 Loading normalized entries from: {input_dir}")
    entries = []

    for file in input_dir.glob("*.json"):
        try:
            with file.open("r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    entries.extend(data)
                else:
                    entries.append(data)
        except Exception as e:
            typer.echo(f"⚠️ Failed to load {file.name}: {e}")

    typer.echo(f"🧠 Loaded {len(entries)} entries.")

    client = get_client()
    collection = client.get_or_create_collection("orion_episodic_ltm")

    if replace:
        typer.echo("🧹 Clearing existing episodic memory collection…")
        collection.delete()

    if entries:
        typer.echo("📥 Ingesting entries into episodic LTM…")
        ingest_batch(collection, entries)

    typer.echo("✅ Episodic ingest complete.")


# ---------------------------------------------------------
# NORMALIZE RAW CHAT LOGS (Optional)
# ---------------------------------------------------------
@app.command("chat")
def normalize_chat(
    input: str = typer.Option(
        ..., "--input", "-i", help="Directory of raw chat logs (json)"
    ),
    output: str = typer.Option(
        ..., "--output", "-o", help="Directory to write normalized logs"
    ),
):
    """
    Normalize raw chat logs into ingestion-ready structure.
    """
    input_dir = Path(input)
    output_dir = Path(output)

    if not input_dir.exists():
        typer.echo(f"❌ Input directory does not exist: {input_dir}")
        raise typer.Exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    typer.echo(f"📁 Normalizing chat logs from {input_dir}…")
    entries = normalize_directory(input_dir)

    typer.echo(f"🧠 Writing {len(entries)} normalized entries to {output_dir}…")

    for i, entry in enumerate(entries):
        out_file = output_dir / f"normalized_{i}.json"
        with out_file.open("w", encoding="utf-8") as f:
            json.dump(entry, f, ensure_ascii=False)

    typer.echo("✅ Normalization complete.")


# ---------------------------------------------------------
# MAIN ENTRY
# ---------------------------------------------------------
if __name__ == "__main__":
    app()
