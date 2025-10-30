import argparse
from orion_cli.core.ltm import ingest_ltm_file
from orion_cli.core.persona import ingest_persona_yaml


def run_ingest():
    parser = argparse.ArgumentParser(
        description="Orion unified ingest tool: persona and/or long-term memory (LTM) seeding"
    )
    parser.add_argument("--persona", type=str, help="Path to persona YAML file")
    parser.add_argument("--ltm", type=str, help="Path to LTM dialog JSONL file")

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--replace", action="store_true", help="Replace existing memory")
    mode.add_argument(
        "--append",
        action="store_true",
        help="Append to existing LTM (ignored for persona)",
    )

    args = parser.parse_args()

    if not args.persona and not args.ltm:
        parser.error("You must specify at least one of --persona or --ltm")

    if args.persona:
        print("[orion_cli] Ingesting persona...")
        ingest_persona_yaml(args.persona, replace=True)
        if args.append:
            print("[orion_cli] Warning: persona cannot be appended. Always replaced.")

    if args.ltm:
        print(
            f"[orion_cli] Ingesting LTM {'(append)' if args.append else '(replace)'}..."
        )
        ingest_ltm_file(args.ltm, replace=not args.append)

    print("[orion_cli] Ingest complete.")


if __name__ == "__main__":
    run_ingest()
