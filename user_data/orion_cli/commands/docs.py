from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set
import fnmatch

import typer
import yaml

from orion_cli.shared.paths import (
    PACKAGE_ROOT,
    USER_DATA_DIR,
    USER_ORION_DIR,
    WORKSPACE_DIR,
)

app = typer.Typer(help="Documentation snapshot tools (manifest-driven).")


def _find_tgwui_root(package_root: Path) -> Path:
    p = package_root.resolve()
    while p != p.parent:
        if (p / "user_data").is_dir():
            return p
        p = p.parent
    # Fallback: best guess
    return package_root.parent.parent


TGWUI_ROOT = _find_tgwui_root(PACKAGE_ROOT)

MANIFEST_PATH = USER_DATA_DIR / "snapshots_manifest.yaml"

# Output location per your requirement
OUT_CLI_MD = WORKSPACE_DIR / "orion_cli.md"
OUT_USER_MD = WORKSPACE_DIR / "orion_user.md"


@dataclass(frozen=True)
class SnapshotDefaults:
    max_file_bytes: int = 250_000
    allowed_ext: tuple[str, ...] = (
        ".py",
        ".md",
        ".yaml",
        ".yml",
        ".json",
        ".txt",
        ".ps1",
        ".bat",
        ".sh",
        ".gitkeep",
    )
    exclude_globs: tuple[str, ...] = (
        "**/__pycache__/**",
        "**/.git/**",
        "**/*.pyc",
        "**/*.pyo",
        "**/*.pyd",
        "**/*.so",
        "**/*.dll",
        "**/*.exe",
        "**/*.bin",
        "**/*.db",
        "**/*.sqlite",
        "**/*.sqlite3",
        "**/*.gguf",
        "**/*.safetensors",
        "**/*.pt",
        "**/*.onnx",
        "**/*.zip",
        "**/*.7z",
        "**/*.tar",
        "**/*.gz",
        "**/*.png",
        "**/*.jpg",
        "**/*.jpeg",
        "**/*.webp",
    )
    NO_READ_DIRS = {
        "chromadb",
        "embeddings",
        "hf_cache",
        "logs",
        "__pycache__",
    }


def _load_manifest(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Manifest not found: {path}")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _resolve_root(root_str: str) -> Path:
    """
    Resolve a manifest 'root' entry with placeholder support.

    Supported placeholders:
      - {CLI_ROOT}       -> PACKAGE_ROOT
      - {USER_ORION_DIR} -> USER_ORION_DIR

    Rules:
      - After substitution, absolute paths are used as-is.
      - Relative paths are resolved from TGWUI_ROOT.
    """
    s = str(root_str).strip()

    # Placeholder substitution (portable across environments)
    s = s.replace("{CLI_ROOT}", str(PACKAGE_ROOT))
    s = s.replace("{USER_ORION_DIR}", str(USER_ORION_DIR))

    p = Path(s)
    if p.is_absolute():
        return p.resolve()
    return (TGWUI_ROOT / p).resolve()


def _posix_rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except Exception:
        return path.name


def _matches_any(rel_posix: str, patterns: Iterable[str]) -> bool:
    # Normalize to forward slashes for fnmatch
    s = rel_posix.replace("\\", "/")
    for pat in patterns:
        if fnmatch.fnmatch(s, pat):
            return True
    return False


def _is_allowed_file(
    path: Path,
    rel_posix: str,
    defaults: SnapshotDefaults,
    extra_excludes: Iterable[str],
) -> bool:
    if not path.is_file():
        return False

    if _matches_any(rel_posix, defaults.exclude_globs) or _matches_any(
        rel_posix, extra_excludes
    ):
        return False

    if path.suffix.lower() not in defaults.allowed_ext:
        return False

    try:
        if path.stat().st_size > defaults.max_file_bytes:
            return False
    except Exception:
        return False

    return True


def _gather_files(
    root: Path,
    include_globs: List[str],
    defaults: SnapshotDefaults,
    extra_excludes: List[str],
) -> List[Path]:
    out: Set[Path] = set()
    for pat in include_globs:
        for p in root.glob(pat):
            if p.is_file():
                rel = _posix_rel(p, root)
                if _is_allowed_file(p, rel, defaults, extra_excludes):
                    out.add(p.resolve())
    return sorted(out)


def _dir_listing(
    root: Path,
    dir_rel: str,
    defaults: SnapshotDefaults,
    extra_excludes: List[str],
    max_lines: int = 600,
) -> List[str]:
    """
    Returns a directory tree listing (paths only), respecting excludes.
    Does NOT read file contents.
    """
    target = (root / dir_rel).resolve()
    if not target.exists() or not target.is_dir():
        return [f"(missing or not a directory) {dir_rel}"]

    lines: List[str] = []
    count = 0

    for p in sorted(target.rglob("*")):
        if not p.exists():
            continue

        rel = _posix_rel(p, root)

        # For listings, apply excludes, but do NOT apply extension/size rules.
        if _matches_any(rel, defaults.exclude_globs) or _matches_any(
            rel, extra_excludes
        ):
            continue

        # Skip very noisy hidden/system entries if they slip through
        if "/.git/" in rel.replace("\\", "/"):
            continue

        lines.append(rel)
        count += 1
        if count >= max_lines:
            lines.append("... (listing truncated) ...")
            break

    if not lines:
        lines.append("(empty)")
    return lines


def _make_header(title: str) -> str:
    return (
        f"# {title}\n\n"
        "> This file is **auto-generated**. Do not edit it directly.\n"
        "> Update inputs and re-run `orion docs snapshot` instead.\n\n"
    )


def _emit_file_section(root: Path, path: Path) -> str:
    rel = _posix_rel(path, root)
    text = path.read_text(encoding="utf-8", errors="replace")

    # Keep your special-case semantics for .gitkeep
    if path.name == ".gitkeep":
        return (
            f"## {rel}\n"
            "**Folder index (from .gitkeep):**\n\n"
            "### Contents\n"
            "~~~text\n"
            f"{text}\n"
            "~~~\n\n"
        )

    lang = "python" if path.suffix.lower() == ".py" else "text"
    return f"## {rel}\n" "### Full source\n" f"~~~{lang}\n" f"{text}\n" "~~~\n\n"


def _emit_dir_index_section(root: Path, dir_rel: str, listing: List[str]) -> str:
    return (
        f"## {dir_rel.rstrip('/')}/\n"
        "**Directory index (paths only):**\n\n"
        "### Contents\n"
        "~~~text\n" + "\n".join(listing) + "\n~~~\n\n"
    )


def _build_report(report: Dict[str, Any], defaults: SnapshotDefaults) -> str:
    title = str(report.get("title", "Snapshot")).strip() or "Snapshot"
    root_str = str(report.get("root", "")).strip()
    if not root_str:
        raise ValueError("Report is missing required field: root")

    root = _resolve_root(root_str)

    include_globs = report.get("include_globs", []) or []
    if not isinstance(include_globs, list):
        raise ValueError("include_globs must be a list")

    dir_index = report.get("dir_index", []) or []
    if not isinstance(dir_index, list):
        raise ValueError("dir_index must be a list")

    extra_excludes = report.get("exclude_globs", []) or []
    if not isinstance(extra_excludes, list):
        raise ValueError("exclude_globs must be a list")

    parts: List[str] = []
    parts.append(_make_header(title))

    # 1) Directory indexes (paths only)
    for d in dir_index:
        d = str(d)
        listing = _dir_listing(root, d, defaults, extra_excludes)
        parts.append(_emit_dir_index_section(root, d, listing))

    # 2) File inclusions (contents)
    files = _gather_files(root, include_globs, defaults, extra_excludes)
    for p in files:
        parts.append(_emit_file_section(root, p))

    return "\n".join(parts)


@app.command("snapshot")
def snapshot(
    manifest: str = typer.Option(
        str(MANIFEST_PATH),
        "--manifest",
        help="Path to snapshots_manifest.yaml",
        show_default=True,
    ),
    cli: bool = typer.Option(False, "--cli", help="Generate only the CLI snapshot."),
    user: bool = typer.Option(
        False, "--user", help="Generate only the User Data snapshot."
    ),
):
    """
    Build both snapshot Markdown files using the manifest:
      - Orion CLI Snapshot
      - Orion User Data Snapshot

    Outputs (fixed by policy):
      - user_data/orion/data/orion_scripts_outline.md
      - user_data/orion/data/orion_user_data.md
    """

    mpath = Path(manifest).expanduser()
    data = _load_manifest(mpath)

    reports = data.get("reports", {}) or {}
    cli_rep = reports.get("cli_snapshot")
    usr_rep = reports.get("user_data_snapshot")
    if not isinstance(cli_rep, dict) or not isinstance(usr_rep, dict):
        raise typer.Exit(code=2)

    defaults = SnapshotDefaults()

    # If neither flag is set, do both.
    do_cli = cli or (not cli and not user)
    do_user = user or (not cli and not user)

    if do_cli:
        cli_doc = _build_report(cli_rep, defaults)
        OUT_CLI_MD.write_text(cli_doc, encoding="utf-8")
        typer.echo(f"[docs] wrote: {OUT_CLI_MD}")

    if do_user:
        usr_doc = _build_report(usr_rep, defaults)
        OUT_USER_MD.write_text(usr_doc, encoding="utf-8")
        typer.echo(f"[docs] wrote: {OUT_USER_MD}")
