import typer
from pathlib import Path
from dotenv import load_dotenv

# Global
cli = typer.Typer(help="Orion CLI entrypoint.")
VERBOSE = False

# Load environment (e.g. ORION_EMBED_MODEL)
dotenv_path = Path(__file__).parent / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path=dotenv_path)


def print_verbose(msg: str):
    if VERBOSE:
        print(f"[orion_cli:verbose] {msg}")


@cli.callback()
def main(
    verbose: bool = typer.Option(False, "--verbose", help="Enable verbose output.")
):
    """Initialize CLI state."""
    global VERBOSE
    VERBOSE = verbose
    if VERBOSE:
        print("[orion_cli] Verbose mode is ON")


# -------------------------- Commands --------------------------


@cli.command("config-show")
def config_show():
    """Print current configuration from YAML."""
    from orion_cli.utils.config import get_config

    cfg = get_config()
    print_verbose("Config loaded successfully.")
    import json

    print(json.dumps(cfg, indent=4))


@cli.command("ltm-ingest")
def ltm_ingest(
    source: str = typer.Argument(..., help="Path to JSONL dialog data."),
    pool_size: int = typer.Option(3, help="Number of dialog turns to pool."),
    replace: bool = typer.Option(False, help="Replace existing memory entries."),
):
    """Ingest dialogs as LTM entries into ChromaDB."""
    from orion_cli.scripts.pooled_ltm_ingest import ingest_pooled

    ingest_pooled(source=source, pool_size=pool_size, replace=replace)


@cli.command("persona-ingest")
def persona_ingest(
    yaml_path: str = typer.Argument(..., help="Path to persona YAML file."),
    replace: bool = typer.Option(False, help="Replace existing persona blocks."),
):
    """Ingest persona definitions from YAML."""
    from orion_cli.scripts.persona_ingest import persona_ingest as _ingest

    _ingest(yaml_path, replace)


@cli.command("enrich-chat")
def enrich_chat(
    log_dir: str = typer.Argument(..., help="Directory of chat logs to enrich."),
    output_path: str = typer.Option(
        "./enriched.jsonl", help="Where to save enriched output."
    ),
):
    """Enrich raw chat logs using GPT-4 and save as enriched JSONL."""
    from orion_cli.utils.temporal_search import load_logs
    from orion_cli.utils.llm_tools import call_gpt4_enrichment

    print(f"[📂] Loading from: {log_dir}")
    logs = load_logs(log_dir)
    enriched = []

    for log in logs:
        user_msg = log.get("user")
        assistant_msg = log.get("assistant")
        if not user_msg or not assistant_msg:
            continue

        result = call_gpt4_enrichment(user_msg, assistant_msg)
        if result:
            enriched.append(result)

    if enriched:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        with open(output, "w", encoding="utf-8") as f:
            for item in enriched:
                import json

                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        print(f"[✅] Saved {len(enriched)} enriched entries to {output}")
    else:
        print("[❌] No enriched outputs were generated.")


# ------------------------- Entrypoint -------------------------

if __name__ == "__main__":
    cli()
