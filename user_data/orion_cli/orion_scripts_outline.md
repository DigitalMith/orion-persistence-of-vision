# Orion CLI Scripts — Outline + Source

> This file is **auto-generated**. Do not edit it directly.
> Update the Python files and re-run `build_orion_doc.py` instead.

## cli.py
**Role / summary (from module docstring):**

cli.py — Orion CNS Command-Line Interface (Root Entrypoint)
-----------------------------------------------------------

This file defines the `orion` command and registers all subcommands.

Subcommands:
    - orion memory ...
    - orion identity ...
    - orion ingest ...
    - orion tools ...

The real logic behind each command lives in shared modules.
Commands are intentionally thin orchestrators.

### Full source
~~~python
"""
cli.py — Orion CNS Command-Line Interface (Root Entrypoint)
-----------------------------------------------------------

This file defines the `orion` command and registers all subcommands.

Subcommands:
    - orion memory ...
    - orion identity ...
    - orion ingest ...
    - orion tools ...

The real logic behind each command lives in shared modules.
Commands are intentionally thin orchestrators.
"""

from __future__ import annotations

import typer
import warnings

from orion_cli.commands.memory import app as memory_app
from orion_cli.commands.identity import app as identity_app
from orion_cli.commands.ingest import app as ingest_app
from orion_cli.commands.tools import app as tools_app


warnings.filterwarnings(
    "ignore",
    category=FutureWarning,
    message="Using `TRANSFORMERS_CACHE` is deprecated and will be removed in v5 of Transformers. Use `HF_HOME` instead.",
)

# Root CLI application
app = typer.Typer(
    help="Orion CLI — Cognitive Neural System Tools",
    add_completion=False,
)


# Register subcommands
app.add_typer(memory_app, name="memory")
app.add_typer(identity_app, name="identity")
app.add_typer(ingest_app, name="ingest")
app.add_typer(tools_app, name="tools")


def main():
    """
    Entrypoint used by `orion` script in pyproject.toml.
    """
    app()


if __name__ == "__main__":
    main()

~~~

## __init__.py
**Role / summary (from module docstring):**

Orion CLI Package
-----------------

This package provides the complete CNS (Cognitive Neural System) logic
for Orion, including configuration, embeddings, memory engines,
identity systems, and Typer-based command-line interfaces.

All functional logic is implemented in:
    - orion_cli/shared/
    - orion_cli/commands/
    - orion_cli/settings/

The CLI entrypoint is defined in cli.py.

### Full source
~~~python
"""
Orion CLI Package
-----------------

This package provides the complete CNS (Cognitive Neural System) logic
for Orion, including configuration, embeddings, memory engines,
identity systems, and Typer-based command-line interfaces.

All functional logic is implemented in:
    - orion_cli/shared/
    - orion_cli/commands/
    - orion_cli/settings/

The CLI entrypoint is defined in cli.py.
"""

__all__ = [
    "shared",
    "commands",
    "settings",
]

~~~

## shared/paths.py
**Role / summary:**

_(add a short description for this script here if needed)_

### Full source
~~~python
from __future__ import annotations

import os
from pathlib import Path

"""
Centralized path definitions for Orion CLI.

- PACKAGE_ROOT: static CLI package (code + templates)
- USER_ORION_DIR: dynamic Orion user data root (config, memory, embeddings, cache)
  - Default: <PACKAGE_ROOT parent>/orion
  - Override via ORION_USER_DIR
"""

# -------------------------------------------------------------------
# Orion CLI Package Root (static code + templates)
# Example:
#   C:/Orion/text-generation-webui/user_data/orion_cli
# -------------------------------------------------------------------
PACKAGE_ROOT = Path(__file__).resolve().parent.parent


# -------------------------------------------------------------------
# Orion User Data Root (dynamic state, embeddings, memory, persona)
#
# Default:
#   C:/Orion/text-generation-webui/user_data/orion
#
# Can be overridden by env var ORION_USER_DIR
# -------------------------------------------------------------------
DEFAULT_USER_ORION_DIR = PACKAGE_ROOT.parent / "orion"

USER_ORION_DIR = Path(os.getenv("ORION_USER_DIR", DEFAULT_USER_ORION_DIR))
USER_ORION_DIR.mkdir(parents=True, exist_ok=True)


# -------------------------------------------------------------------
# User Config + Persona + Identity
#
#   <USER_ORION_DIR>/data/
# -------------------------------------------------------------------
USER_DATA_DIR = USER_ORION_DIR / "data"
USER_DATA_DIR.mkdir(parents=True, exist_ok=True)

USER_CONFIG_PATH = USER_DATA_DIR / "config.yaml"
USER_PERSONA_PATH = USER_DATA_DIR / "persona.yaml"
USER_IDENTITY_PATH = USER_DATA_DIR / "identity.yaml"


# -------------------------------------------------------------------
# ChromaDB persistent memory store
#
#   <USER_ORION_DIR>/chromadb/
# -------------------------------------------------------------------
CHROMA_DIR = USER_ORION_DIR / "chromadb"
CHROMA_DIR.mkdir(parents=True, exist_ok=True)

# Backwards-compat alias for older code
DEFAULT_CHROMA_PATH = CHROMA_DIR


# -------------------------------------------------------------------
# Embedding Model Downloads (pinned / curated)
#
#   <USER_ORION_DIR>/embeddings/
# -------------------------------------------------------------------
EMBEDDING_MODEL_DIR = USER_ORION_DIR / "embeddings"
EMBEDDING_MODEL_DIR.mkdir(parents=True, exist_ok=True)


# -------------------------------------------------------------------
# HuggingFace Cache
#
#   <USER_ORION_DIR>/hf_cache/
#
# HF_HOME is only set here if the user has not already chosen a value.
# -------------------------------------------------------------------
HF_CACHE_DIR = USER_ORION_DIR / "hf_cache"
HF_CACHE_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_HF_CACHE_PATH = HF_CACHE_DIR

if "HF_HOME" not in os.environ:
    os.environ["HF_HOME"] = str(HF_CACHE_DIR)


# -------------------------------------------------------------------
# Orion Workspace Area (scratchpad / tools / files)
#
#   <USER_ORION_DIR>/workspace/
# -------------------------------------------------------------------
WORKSPACE_DIR = USER_ORION_DIR / "workspace"
WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)


# -------------------------------------------------------------------
# Static Package Data (templates, schema)
#
#   <PACKAGE_ROOT>/data/
# -------------------------------------------------------------------
DATA_DIR = PACKAGE_ROOT / "data"

DEFAULT_CONFIG_PATH = DATA_DIR / "default_config.yaml"
SCHEMA_PATH = DATA_DIR / "schema.json"


__all__ = [
    "PACKAGE_ROOT",
    "USER_ORION_DIR",
    "USER_DATA_DIR",
    "USER_CONFIG_PATH",
    "USER_PERSONA_PATH",
    "USER_IDENTITY_PATH",
    "CHROMA_DIR",
    "DEFAULT_CHROMA_PATH",
    "EMBEDDING_MODEL_DIR",
    "HF_CACHE_DIR",
    "DEFAULT_HF_CACHE_PATH",
    "WORKSPACE_DIR",
    "DATA_DIR",
    "DEFAULT_CONFIG_PATH",
    "SCHEMA_PATH",
]

~~~

## shared/memory_core.py
**Role / summary (from module docstring):**

memory_core.py — Orion CNS Long-Term Memory Engine (Persona + Episodic)
-----------------------------------------------------------------------

Implements the core LTM functions:
- ChromaDB client initialization
- Persona collection
- Episodic memory collection
- Safe insertion (dedup, normalized text)
- Similarity-based recall
- Memory statistics and introspection

This module contains *all* memory logic.
The Typer commands simply call these functions.

### Full source
~~~python
"""
memory_core.py — Orion CNS Long-Term Memory Engine (Persona + Episodic)
-----------------------------------------------------------------------

Implements the core LTM functions:
- ChromaDB client initialization
- Persona collection
- Episodic memory collection
- Safe insertion (dedup, normalized text)
- Similarity-based recall
- Memory statistics and introspection

This module contains *all* memory logic.
The Typer commands simply call these functions.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Dict, Any, Optional

import chromadb
from chromadb.config import Settings

from orion_cli.shared.config import get_config
from orion_cli.shared.embedding import EMBED_FN, embed_text
from orion_cli.shared.utils import normalize_text
from orion_cli.paths import CHROMA_DIR, PACKAGE_ROOT
from orion_cli.shared.paths import CHROMA_DIR, PACKAGE_ROOT, USER_ORION_DIR, HF_CACHE_DIR


# -------------------------------------------------------------
# Resolve Chroma path
# -------------------------------------------------------------

def _resolve_chroma_path() -> Path:
    """
    Resolve the ChromaDB path with the following precedence:

    1. ORION_CHROMA_DIR env var (absolute or relative)
    2. config.yaml -> chroma_path (absolute or relative)
       - relative paths are resolved against the TGWUI project root
    3. Default CHROMA_DIR from paths.py (user_data/orion/chromadb)
    """

    # 1) Environment override wins
    env_raw = os.getenv("ORION_CHROMA_DIR")
    if env_raw:
        p = Path(env_raw)
        if not p.is_absolute():
            # Resolve relative to TGWUI root
            tgwui_root = PACKAGE_ROOT.parent.parent
            p = tgwui_root / p
        return p.resolve()

    # 2) Config value (may be None / empty / missing)
    cfg = get_config()
    raw = getattr(cfg, "chroma_path", None)

    if raw:
        p = Path(str(raw))

        if p.is_absolute():
            return p.resolve()

        # Treat relative chroma_path as relative to TGWUI root
        tgwui_root = PACKAGE_ROOT.parent.parent
        return (tgwui_root / p).resolve()

    # 3) Fallback: canonical default
    return CHROMA_DIR.resolve()


# -------------------------------------------------------------
# Client initialization (singleton)
# -------------------------------------------------------------

_client = None

def _get_client():
    global _client

    if _client is not None:
        return _client

    persist_path = _resolve_chroma_path()
    persist_path.mkdir(parents=True, exist_ok=True)

    _client = chromadb.PersistentClient(
        path=str(persist_path),
        settings=Settings(anonymized_telemetry=False),
    )

    return _client


# -------------------------------------------------------------
# Collection helpers
# -------------------------------------------------------------

def _get_collection(name: str):
    return _get_client().get_or_create_collection(
        name=name,
        embedding_function=EMBED_FN,
        metadata={"hnsw:space": "cosine"},
    )


# Primary collections
PERSONA_COLLECTION = "orion_persona"
EPISODIC_COLLECTION = "orion_episodic_ltm"


def _persona():
    return _get_collection(PERSONA_COLLECTION)


def _episodic():
    return _get_collection(EPISODIC_COLLECTION)


# -------------------------------------------------------------
# Ingestion (Persona + Episodic)
# -------------------------------------------------------------

def add_persona_entry(text: str, metadata: Optional[Dict[str, Any]] = None) -> str:
    """
    Insert a persona document into its collection.
    Returns the ID assigned to the inserted memory.
    """
    clean = normalize_text(text)
    col = _persona()

    vector = embed_text(clean)
    new_id = f"persona-{col.count()+1}"

    col.upsert(
        ids=[new_id],
        embeddings=[vector],
        documents=[clean],
        metadatas=[metadata or {}],
    )

    return new_id


def add_episodic_entry(
    text: str,
    metadata: Optional[Dict[str, Any]] = None,
    min_length: int = 10,
) -> Optional[str]:
    """
    Insert an episodic memory entry, with safeguards:

    - Reject trivial or extremely short entries
    - Normalize text
    - Deduplicate against existing memory
    """
    clean = normalize_text(text)

    if len(clean.split()) < min_length:
        return None  # trivial entry → skip

    col = _episodic()

    # Dedup check
    if col.count() > 0:
        hits = col.query(
            query_texts=[clean],
            n_results=1,
        )

        if hits.get("distances") and hits["distances"][0][0] < 0.05:
            # Near-duplicate → skip
            return None

    vector = embed_text(clean)
    new_id = f"episodic-{col.count()+1}"

    col.upsert(
        ids=[new_id],
        embeddings=[vector],
        documents=[clean],
        metadatas=[metadata or {}],
    )

    return new_id


# -------------------------------------------------------------
# Recall
# -------------------------------------------------------------

def recall_persona(query: str, top_k: int = 5) -> List[str]:
    """
    Retrieve persona entries most relevant to `query`.
    Returns a list of persona document strings.
    """
    col = _persona()

    if col.count() == 0:
        return []

    res = col.query(query_texts=[query], n_results=top_k)
    docs = res.get("documents", [[]])[0]

    return docs or []


def recall_episodic(query: str, top_k: int = 5) -> List[str]:
    """
    Retrieve episodic memories most relevant to `query`.
    """
    col = _episodic()

    if col.count() == 0:
        return []

    res = col.query(query_texts=[query], n_results=top_k)
    docs = res.get("documents", [[]])[0]

    return docs or []


# -------------------------------------------------------------
# Statistics
# -------------------------------------------------------------

def memory_stats() -> Dict[str, Any]:
    """
    Return summary statistics for persona & episodic memory.
    """
    p = _persona()
    e = _episodic()

    return {
        "persona_entries": p.count(),
        "episodic_entries": e.count(),
    }


def on_user_turn(text: str, **metadata) -> None:
    """
    Legacy hook used by the orion_ltm extension for user messages.

    Thin wrapper around add_episodic_entry so CNS 3.x-style extension
    code keeps working on CNS 4.0.
    """
    meta = {"role": "user", "source": "tgwui"}
    if metadata:
        meta.update(metadata)
    add_episodic_entry(text, metadata=meta, min_length=10)


def on_assistant_turn(text: str, **metadata) -> None:
    """
    Legacy hook used by the orion_ltm extension for assistant messages.
    """
    meta = {"role": "assistant", "source": "tgwui"}
    if metadata:
        meta.update(metadata)
    add_episodic_entry(text, metadata=meta, min_length=10)


__all__ = [
    "add_persona_entry",
    "add_episodic_entry",
    "recall_persona",
    "recall_episodic",
    "memory_stats",
    "PERSONA_COLLECTION",
    "EPISODIC_COLLECTION",
    "on_user_turn",
    "on_assistant_turn",
]

~~~

## commands/ingest.py
**Role / summary (from module docstring):**

ingest.py — Typer Commands for Persona & Episodic Ingestion
-----------------------------------------------------------

These commands allow users to add persona entries and episodic memories
into Orion's long-term memory store.

All ingestion logic lives in:
    orion_cli.shared.memory_core

### Full source
~~~python
"""
ingest.py — Typer Commands for Persona & Episodic Ingestion
-----------------------------------------------------------

These commands allow users to add persona entries and episodic memories
into Orion's long-term memory store.

All ingestion logic lives in:
    orion_cli.shared.memory_core
"""

from __future__ import annotations

import json
import typer
from pathlib import Path
from orion_cli.shared.utils import read_yaml

from orion_cli.shared.memory_core import (
    add_persona_entry,
    add_episodic_entry,
)

from orion_cli.settings.config_loader import (
    get_config,
    resolve_profile_paths,
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

    # Split into lines, keep non-empty, but skip comment lines starting with '#'
    lines = [line.rstrip() for line in text.split("\n") if line.strip()]
    count = 0

    for line in lines:
        if line.lstrip().startswith("#"):
            continue  # ignore commented lines

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


# -------------------------------------------------------------
# Persona ingestion via active profile (config-driven)
# -------------------------------------------------------------

def _flatten_metadata(md: dict) -> dict:
    """
    Flatten nested metadata into string-friendly values.

    - Lists become comma-joined strings.
    - Dicts become JSON-encoded strings.
    - Scalars are passed through as-is.
    """
    flat: dict = {}
    for k, v in md.items():
        if isinstance(v, list):
            flat[k] = ",".join(str(x) for x in v)
        elif isinstance(v, dict):
            flat[k] = json.dumps(v, ensure_ascii=False)
        else:
            flat[k] = v
    return flat


@app.command("persona-default")
def ingest_persona_for_active_profile():
    """
    Ingest the persona file for the active Orion profile (YAML-aware).

    - Default profile 'orion_main' uses:
        user_data/orion_cli/data/orion_persona.yaml

    - If ORION_PROFILE is set (e.g. alex_home), it will use:
        user_data/orion/profiles/<profile>/data/persona.yaml
    """
    cfg = get_config()
    _, persona_path = resolve_profile_paths(cfg)

    if not persona_path.exists():
        raise typer.BadParameter(f"Persona file not found: {persona_path}")

    data = read_yaml(persona_path)

    # Normalize to a list of docs
    if isinstance(data, list):
        docs = data
    elif isinstance(data, (dict, str)):
        docs = [data]
    else:
        docs = []

    count = 0

    for doc in docs:
        # Plain string doc (fallback/simple mode)
        if isinstance(doc, str):
            text_entry = doc.strip()
            if not text_entry:
                continue
            metadata = {}

        # Structured YAML doc
        elif isinstance(doc, dict):
            raw_text = doc.get("text", "")
            if not isinstance(raw_text, str):
                continue

            text_entry = raw_text.strip()
            if not text_entry:
                continue

            meta_raw = {k: v for k, v in doc.items() if k != "text"}
            metadata = _flatten_metadata(meta_raw)

        else:
            continue

        new_id = add_persona_entry(text_entry, metadata=metadata)
        if new_id:
            typer.echo(f"Added persona entry: {new_id}")
            count += 1

    typer.echo(
        f"Completed. {count} persona entries added from {persona_path} "
        f"for profile {cfg.profile!r}."
    )


__all__ = ["app"]


~~~

## commands/memory.py
**Role / summary (from module docstring):**

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

### Full source
~~~python
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
from typing import Optional

from orion_cli.shared.memory_core import (
    recall_persona,
    recall_episodic,
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
    Recall relevant persona or episodic memories.
    If neither --persona nor --episodic is provided, both collections are searched.
    """
    # Determine target
    search_persona = persona or not episodic
    search_episodic = episodic or not persona

    output = []

    if search_persona:
        hits = recall_persona(query, top_k)
        if hits:
            typer.echo("=== Persona Memory ===")
            for h in hits:
                typer.echo(f"- {h}")
            typer.echo("")

    if search_episodic:
        hits = recall_episodic(query, top_k)
        if hits:
            typer.echo("=== Episodic Memory ===")
            for h in hits:
                typer.echo(f"- {h}")

    if not search_persona and not search_episodic:
        typer.echo("No memory category selected.")


# -------------------------------------------------------------
# Stats command
# -------------------------------------------------------------

@app.command("stats")
def stats_command():
    """
    Display memory statistics for persona and episodic storage.
    """
    stats = memory_stats()

    typer.echo("=== Orion Memory Stats ===")
    typer.echo(f"Persona entries:   {stats['persona_entries']}")
    typer.echo(f"Episodic entries:  {stats['episodic_entries']}")


__all__ = ["app"]

~~~

## commands/identity.py
**Role / summary (from module docstring):**

identity.py — Typer Commands for Orion Identity Operations
----------------------------------------------------------

These commands expose the identity layer of CNS 4.0, enabling users to:

- Inspect persona slices
- Query identity blocks
- Debug identity behavior

All heavy CNS logic is implemented in:
    orion_cli.shared.identity_core

### Full source
~~~python
"""
identity.py — Typer Commands for Orion Identity Operations
----------------------------------------------------------

These commands expose the identity layer of CNS 4.0, enabling users to:

- Inspect persona slices
- Query identity blocks
- Debug identity behavior

All heavy CNS logic is implemented in:
    orion_cli.shared.identity_core
"""

from __future__ import annotations

import typer

from orion_cli.shared.identity_core import (
    persona_summary,
    build_identity_block,
)


app = typer.Typer(help="Inspect Orion's identity system.")


# -------------------------------------------------------------
# Persona inspection
# -------------------------------------------------------------

@app.command("persona")
def persona_command(
    query: str = typer.Argument(
        "identity",
        help="Query text to retrieve persona-related information.",
    ),
    top_k: int = typer.Option(
        5,
        "--top-k",
        "-k",
        help="Number of persona entries to return.",
    ),
):
    """
    Retrieve persona entries most relevant to the given query.
    """
    hits = persona_summary(query, top_k=top_k)

    if not hits:
        typer.echo("No persona entries found.")
        return

    typer.echo("=== Persona Summary ===")
    for h in hits:
        typer.echo(f"- {h}")


# -------------------------------------------------------------
# Identity block preview
# -------------------------------------------------------------

@app.command("query")
def query_identity(
    query: str = typer.Argument(
        ...,
        help="Query text used to assemble an identity block.",
    )
):
    """
    Build and print a compact identity block.

    This is primarily used for debugging and validating that
    persona memory is behaving as expected.
    """
    block = build_identity_block(query)

    if not block.strip():
        typer.echo("No identity context available.")
        return

    typer.echo("=== Identity Block ===")
    typer.echo(block)


__all__ = ["app"]

~~~

## commands/tools.py
**Role / summary (from module docstring):**

tools.py — Developer Utilities and Diagnostics for Orion CLI
------------------------------------------------------------

These commands provide utilities for inspecting:
- configuration
- embedding behavior
- resolved paths
- general CNS diagnostics

All heavy logic is delegated to shared modules.

### Full source
~~~python
"""
tools.py — Developer Utilities and Diagnostics for Orion CLI
------------------------------------------------------------

These commands provide utilities for inspecting:
- configuration
- embedding behavior
- resolved paths
- general CNS diagnostics

All heavy logic is delegated to shared modules.
"""

from __future__ import annotations

import typer
from rich import print as rprint

from orion_cli.shared.config import get_config
# from orion_cli.shared.embedding import embed_text  # Removed top-level only commands that need it.
from orion_cli.shared.paths import (
    PACKAGE_ROOT,
    DEFAULT_CONFIG_PATH,
    EMBEDDING_MODEL_DIR,
    SCHEMA_PATH,
    DEFAULT_CHROMA_PATH,
)


app = typer.Typer(help="Developer tools and diagnostic commands.")


# -------------------------------------------------------------
# Config inspection
# -------------------------------------------------------------

@app.command("config")
def show_config():
    """
    Display the full resolved Orion CNS configuration.
    """
    cfg = get_config()

    rprint("[bold cyan]=== Orion Configuration ===[/bold cyan]")
    rprint(cfg.model_dump())


# -------------------------------------------------------------
# Embedding test
# -------------------------------------------------------------

@app.command("embed")
def embed_test(
    text: str = typer.Argument(
        ...,
        help="Text to embed for testing purposes."
    )
):
    from orion_cli.shared.embedding import embed_text
    """
    Embed text once and print vector length + preview.
    """
    vec = embed_text(text)

    rprint("[bold green]=== Embedding Test ===[/bold green]")
    rprint(f"Input: {text!r}")
    rprint(f"Vector length: {len(vec)}")
    rprint(f"Vector preview: {vec[:8]} ...")


# -------------------------------------------------------------
# Path inspection
# -------------------------------------------------------------

@app.command("paths")
def show_paths():
    """
    Display important Orion CNS filesystem paths.
    """

    rprint("[bold magenta]=== Orion Paths ===[/bold magenta]")
    rprint(f"[white]Package root:        {PACKAGE_ROOT}[/white]")
    rprint(f"[white]Default config:      {DEFAULT_CONFIG_PATH}[/white]")
    rprint(f"[white]Embedding model dir:  {EMBEDDING_MODEL_DIR}[/white]")
    rprint(f"[white]JSON Schema:          {SCHEMA_PATH}[/white]")
    rprint(f"[white]ChromaDB path:        {DEFAULT_CHROMA_PATH}[/white]")


__all__ = ["app"]

~~~

