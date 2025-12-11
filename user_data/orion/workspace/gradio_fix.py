from __future__ import annotations

import argparse
from pathlib import Path
import re
import subprocess
import sys


# This script is meant to run in venv-orion.
# Location: C:\Orion\text-generation-webui\cli_orion\data\gradio_fix.py

# parents[0] -> ...\cli_orion\data
# parents[1] -> ...\cli_orion
# parents[2] -> ...\text-generation-webui  ✅
ROOT = Path(__file__).resolve().parents[2]
USER = ROOT / "user_data"

EXPECTED_GRADIO = "4.37.2"
EXPECTED_GRADIO_CLIENT = "0.16.1"  # adjust if your lock file says otherwise
LOADER_KEY = "LlamaCpp"


def get_version(pkg: str) -> str | None:
    try:
        mod = __import__(pkg)
        return getattr(mod, "__version__", None)
    except Exception:
        return None


def check_versions() -> None:
    g = get_version("gradio")
    gc = get_version("gradio_client")

    print(f"[check] TGWUI root:        {ROOT}")
    print(f"[check] gradio:            {g!r} (expected {EXPECTED_GRADIO})")
    print(f"[check] gradio_client:     {gc!r} (expected {EXPECTED_GRADIO_CLIENT})")


def apply_version_fix() -> None:
    """Force reinstall the expected Gradio stack in the current venv."""
    print("[fix] Applying pinned Gradio stack in current venv (venv-orion recommended).")

    cmd = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--force-reinstall",
        f"gradio=={EXPECTED_GRADIO}",
        f"gradio_client=={EXPECTED_GRADIO_CLIENT}",
        # If you want to use the exact wheel from constraints instead, swap the line above for:
        # f"gradio_client @ https://github.com/oobabooga/gradio/releases/download/4.37.2/gradio_client-{EXPECTED_GRADIO_CLIENT}-py3-none-any.whl",
    ]

    print("[fix] Running:", " ".join(cmd))
    subprocess.run(cmd, cwd=str(ROOT))


def strip_loader_flags() -> None:
    """Strip any '--loader X' fragments from TGWUI flag files."""
    paths = [
        ROOT / "CMD_FLAGS.txt",
        ROOT / "cmd_args.txt",
        USER / "cmd_args.txt",
    ]
    pattern = re.compile(r"--loader\s+\S+")

    for p in paths:
        if not p.is_file():
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except Exception:
            continue

        new = pattern.sub("", text).strip()
        if new != text:
            p.write_text(new + "\n", encoding="utf-8")
            print(f"[fix] Stripped loader flag(s) from {p}")


def normalize_settings_loader() -> None:
    """
    Ensure user_data/settings.yaml has loader: LlamaCpp.

    This keeps TGWUI's persisted config aligned with the loader that
    launch_orion.py will pass via --loader.
    """
    settings = USER / "settings.yaml"
    if not settings.is_file():
        print(f"[info] No settings.yaml at {settings} (nothing to normalize).")
        return

    try:
        lines = settings.read_text(encoding="utf-8").splitlines()
    except Exception:
        print(f"[warn] Could not read {settings}")
        return

    out: list[str] = []
    loader_line_seen = False
    before = None

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("loader:"):
            before = stripped
            out.append(f"loader: {LOADER_KEY}")
            loader_line_seen = True
        else:
            out.append(line)

    if not loader_line_seen:
        out.append(f"loader: {LOADER_KEY}")

    settings.write_text("\n".join(out) + "\n", encoding="utf-8")

    if before is None:
        print(f"[fix] Added loader: {LOADER_KEY} to {settings}")
    else:
        print(f"[fix] Normalized loader in {settings}")
        print(f"       was: {before}")
        print(f"       now: loader: {LOADER_KEY}")
        print("       why: Orion expects this loader to match the bindings/launch script.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Diagnose/fix Gradio / loader issues for TGWUI + Orion."
    )
    parser.add_argument(
        "--apply-deps",
        action="store_true",
        help="Also force reinstall expected Gradio/gradio_client versions.",
    )
    args = parser.parse_args()

    print("[info] Orion Gradio/loader fix starting…")
    check_versions()
    strip_loader_flags()
    normalize_settings_loader()

    if args.apply_deps:
        apply_version_fix()
        print("[info] Dependency fix applied. Try launching Orion again via launch_orion.py.")
    else:
        print("[info] No pip changes applied. Re-run with --apply-deps to install pinned versions.")

    print("[info] Done.")


if __name__ == "__main__":
    main()
