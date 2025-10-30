import argparse
from orion_cli.persona import ingest_persona_catalog
from orion_cli.cli import ltm_ingest


def rebuild_memory(args):
    print("\n🚀 Rebuilding Orion Memory Vaults...")

    # Persona YAML ingest only
    if args.persona_yaml:
        print(f"[🔹] Ingesting persona YAML: {args.persona_yaml}")
        ingest_persona_catalog(
            args.persona_yaml,
            collection_name=args.persona_collection,
            replace=args.replace,
            chroma_path="C:/Orion/text-generation-webui/user_data/chroma_db",
        )

    # Episodic Memory (LTM)
    if args.ltm:
        print("[🔹] Ingesting long-term episodic memory (LTM)...")
        ltm_ingest.main(["--replace"] if args.replace else [])

    print("\n✅ Memory ingest complete.")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Ingest Orion persona and/or LTM into ChromaDB."
    )
    parser.add_argument(
        "--persona-yaml",
        type=str,
        default="orion_cli/data/persona.yaml",
        help="Path to persona YAML file",
    )
    parser.add_argument(
        "--ltm",
        action="store_true",
        help="Enable LTM ingestion (normalized enriched logs)",
    )
    parser.add_argument(
        "--replace", action="store_true", help="Replace existing Chroma collections"
    )
    parser.add_argument(
        "--persona-collection",
        type=str,
        default="orion_persona_ltm",
        help="Target Chroma collection for persona",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    rebuild_memory(args)
