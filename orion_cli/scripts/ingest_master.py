import argparse
import os
import sys

# Import persona + voice ingest modules
from orion_cli.utils.persona_ingest import ingest_persona_yaml
from orion_cli.utils.voice_profile_ingest import ingest_voice_profile


def file_exists(path: str) -> bool:
    """Cross-platform file existence check."""
    return os.path.isfile(path)


def resolve_path(path: str) -> str:
    """Resolve relative → absolute path safely."""
    return os.path.abspath(path)


def cmd_persona(args):
    """Persona ingestion command."""
    path = args.file

    if not path:
        print("[ERROR] --file is required for persona ingestion.")
        sys.exit(1)

    full = resolve_path(path)
    if not file_exists(full):
        print(f"[ERROR] Persona file not found: {full}")
        sys.exit(1)

    print(f"[INFO] Ingesting persona from: {full}")
    count = ingest_persona_yaml(full)
    print(f"[SUCCESS] Persona ingest complete. {count} entries loaded.")


def cmd_voice_profile(args):
    """Voice-profile ingestion command."""
    path = args.file

    if not path:
        print("[ERROR] --file is required for voice-profile ingestion.")
        sys.exit(1)

    full = resolve_path(path)
    if not file_exists(full):
        print(f"[ERROR] Voice profile file not found: {full}")
        sys.exit(1)

    print(f"[INFO] Ingesting voice-profile from: {full}")
    count = ingest_voice_profile(full)
    print(f"[SUCCESS] Voice-profile ingest complete. {count} entries loaded.")


def main():
    parser = argparse.ArgumentParser(
        description="Orion Master Ingest Tool — Persona + Voice Profile"
    )

    sub = parser.add_subparsers(dest="command", help="Commands")

    # -----------------------------
    # PERSONA
    # -----------------------------
    p = sub.add_parser("persona", help="Ingest persona YAML")
    p.add_argument(
        "--file",
        type=str,
        required=True,
        help="Path to persona YAML file.",
    )
    p.set_defaults(func=cmd_persona)

    # -----------------------------
    # VOICE PROFILE
    # -----------------------------
    vp = sub.add_parser("voice-profile", help="Ingest mock dialog / voice-profile JSON")
    vp.add_argument(
        "--file",
        type=str,
        required=True,
        help="Path to mock-dialog JSON file.",
    )
    vp.set_defaults(func=cmd_voice_profile)

    # -----------------------------
    # Parse
    # -----------------------------
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    main()
