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
from pathlib import Path
from datetime import datetime, timezone
from rich import print as rprint
from typing import Any

import json
import sys
import subprocess
import time
import os
import yaml
import typer

from orion_cli.shared.config import get_config

# from orion_cli.shared.embedding import embed_text  # Removed top-level only commands that need it.
from orion_cli.shared.paths import (
    PACKAGE_ROOT,
    DEFAULT_CONFIG_PATH,
    EMBEDDING_MODEL_DIR,
    SCHEMA_PATH,
    DEFAULT_CHROMA_PATH,
    AGENT_STATE_PATH,
    USER_ORION_DIR,
    USER_DATA_DIR,
    WORKSPACE_DIR,
    EFFECTIVE_AGENT_TOOLS_PATH,
)


app = typer.Typer(help="Developer tools and diagnostic commands.")

agent_app = typer.Typer(help="Agent-mode state utilities (init/status/tick).")
app.add_typer(agent_app, name="agent")


class _NoAliasDumper(yaml.SafeDumper):
    def ignore_aliases(self, data):
        return True


try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None  # type: ignore

# -------------------------------------------------------------
# Agent tool execution (safe allowlist)
# -------------------------------------------------------------

# Hard allowlist: tool name -> argv (no shell)
# Use sys.executable -m orion_cli.cli to avoid relying on `orion` in PATH.
_WARN = "ignore:Using `TRANSFORMERS_CACHE` is deprecated:FutureWarning"

_AGENT_TOOL_ALLOWLIST: dict[str, list[str]] = {
    # Add more explicitly as you decide they’re safe:
    "paths": [sys.executable, "-W", _WARN, "-m", "orion_cli.cli", "tools", "paths"],
    "config": [sys.executable, "-W", _WARN, "-m", "orion_cli.cli", "tools", "config"],
    # "memory_stats": [sys.executable, "-m", "orion_cli.cli", "memory", "stats"],
    "memory-stats": [
        sys.executable,
        "-W",
        _WARN,
        "-m",
        "orion_cli.cli",
        "memory",
        "stats",
    ],
    "persona-replace-default": [
        sys.executable,
        "-W",
        _WARN,
        "-m",
        "orion_cli.cli",
        "ingest",
        "persona-default",
        "--replace",
        "--confirm",
        "REPLACE_PERSONA",
    ],
}

# Tools that require an explicit confirmation token.
# tool_name -> required confirm token string
#
# Safe default: empty dict means "no tools require confirmation yet".
_AGENT_TOOL_CONFIRM_REQUIRED: dict[str, str] = {
    # "paths": "DO_IT",  # test-only example
    # Example (use for any destructive action):
    # "persona-replace-default": "REPLACE_PERSONA",
    "persona-replace-default": "REPLACE_PERSONA",
}

_AGENT_TOOL_TIMEOUT_S = int(os.environ.get("ORION_AGENT_TOOL_TIMEOUT_S", "60"))
_AGENT_TOOL_MAX_CHARS = int(os.environ.get("ORION_AGENT_TOOL_MAX_CHARS", "8000"))

# -------------------------------------------------------------
# Agent helpers + commands
# -------------------------------------------------------------


def _truncate(s: str, max_chars: int) -> str:
    if s is None:
        return ""
    if len(s) <= max_chars:
        return s
    return s[: max_chars - 12] + "\n…(truncated)"


def _run_allowed_tool(
    tool: str, args: list[str], allowlist: dict[str, list[str]]
) -> dict[str, Any]:
    if tool not in allowlist:
        return {
            "ok": False,
            "error": f"Tool not allowed: {tool!r}",
            "returncode": None,
            "stdout": "",
            "stderr": "",
            "timed_out": False,
            "duration_ms": 0,
            "argv": [],
        }

    base_argv = list(allowlist[tool])
    argv = base_argv + (args or [])

    t0 = time.time()
    timed_out = False
    try:
        cp = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=_AGENT_TOOL_TIMEOUT_S,
            shell=False,
        )
        rc = cp.returncode
        out = cp.stdout or ""
        err = cp.stderr or ""
    except subprocess.TimeoutExpired as e:
        timed_out = True
        rc = 124
        out = (e.stdout or "") if isinstance(e.stdout, str) else ""
        err = (e.stderr or "") if isinstance(e.stderr, str) else ""
        err = (err + "\n" if err else "") + f"Timed out after {_AGENT_TOOL_TIMEOUT_S}s."
    except Exception as e:
        rc = 1
        out = ""
        err = f"{type(e).__name__}: {e}"

    dt_ms = int((time.time() - t0) * 1000)
    return {
        "ok": (rc == 0) and (not timed_out),
        "returncode": rc,
        "stdout": _truncate(out, _AGENT_TOOL_MAX_CHARS),
        "stderr": _truncate(err, _AGENT_TOOL_MAX_CHARS),
        "timed_out": timed_out,
        "duration_ms": dt_ms,
        "argv": argv,
    }


def _agent_state_path() -> Path:
    return AGENT_STATE_PATH


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load_agent_state(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _save_agent_state(path: Path, state: dict) -> None:
    settings = state.get("settings") or {}
    history_max = settings.get("history_max_events", 200)
    max_chars = settings.get("max_result_chars", 8000)

    # Cap history length
    hist = state.get("history")
    if (
        isinstance(history_max, int)
        and history_max > 0
        and isinstance(hist, list)
        and len(hist) > history_max
    ):
        state["history"] = hist[-history_max:]

    # Truncate large result fields (stdout/stderr) in history
    if isinstance(max_chars, int) and max_chars > 0:
        for ev in state.get("history") or []:
            res = ev.get("result") if isinstance(ev, dict) else None
            if isinstance(res, dict):
                for k in ("stdout", "stderr"):
                    v = res.get(k)
                    if isinstance(v, str) and len(v) > max_chars:
                        res[k] = (
                            v[:max_chars] + f"\n...[truncated to {max_chars} chars]"
                        )

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as f:
        yaml.safe_dump(state, f, sort_keys=False, allow_unicode=True)
    os.replace(tmp, path)


def _agent_tools_policy_path() -> Path:
    return EFFECTIVE_AGENT_TOOLS_PATH


def _load_agent_tool_policy() -> dict[str, Any]:
    """
    Returns dict with:
      allowlist: dict[str, list[str]]  (full argv incl sys.executable, -W, _WARN)
      confirm_required: dict[str, str]
      allow_args: dict[str, bool]
    Falls back to hardcoded defaults if file missing/invalid.
    """
    # Defaults from your current hardcoded dicts
    allowlist = {k: list(v) for k, v in _AGENT_TOOL_ALLOWLIST.items()}
    confirm_required = dict(_AGENT_TOOL_CONFIRM_REQUIRED)
    allow_args: dict[str, bool] = {}  # unspecified => True

    p = _agent_tools_policy_path()
    if not p.exists():
        return {
            "allowlist": allowlist,
            "confirm_required": confirm_required,
            "allow_args": allow_args,
        }

    try:
        import yaml

        raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        tools = raw.get("tools") or {}
        if not isinstance(tools, dict):
            raise ValueError("tools must be a mapping")

        new_allow: dict[str, list[str]] = {}
        new_confirm: dict[str, str] = {}
        new_allow_args: dict[str, bool] = {}

        for name, spec in tools.items():
            if not isinstance(name, str) or not isinstance(spec, dict):
                continue

            argv = spec.get("argv")
            if not isinstance(argv, list) or not all(isinstance(x, str) for x in argv):
                continue

            # Build full argv (no shell) with your warning filter
            full_argv = [sys.executable, "-W", _WARN] + argv
            new_allow[name.strip()] = full_argv

            c = spec.get("confirm") or ""
            if isinstance(c, str) and c.strip():
                new_confirm[name.strip()] = c.strip()

            aa = spec.get("allow_args")
            if isinstance(aa, bool):
                new_allow_args[name.strip()] = aa

        # Only override if we loaded something sane
        if new_allow:
            allowlist = new_allow
            confirm_required = new_confirm
            allow_args = new_allow_args

    except Exception:
        # Silent fallback: policy file errors should never brick the CLI
        pass

    return {
        "allowlist": allowlist,
        "confirm_required": confirm_required,
        "allow_args": allow_args,
    }


def _read_yaml(path: Path) -> dict[str, Any]:
    if not yaml:
        return {}
    obj = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return obj if isinstance(obj, dict) else {}


def _read_json(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8")) or {}
    return obj if isinstance(obj, dict) else {}


def _load_agent_prefs() -> dict[str, Any]:
    """
    Load optional user prefs (behavior knobs) + tool config.
    Templates live in user_data/orion_cli/data.
    User overrides live in user_data/orion/data.
    """

    # commands/tools.py lives under .../user_data/orion_cli/commands/
    cli_root = Path(__file__).resolve().parents[1]  # .../user_data/orion_cli
    tgwui_root = cli_root.parents[2]  # .../text-generation-webui
    templates_dir = cli_root / "data"  # .../user_data/orion_cli/data
    user_dir = tgwui_root / "user_data" / "orion" / "data"  # .../user_data/orion/data

    prefs: dict[str, Any] = {}

    # 1) General user prefs (optional)
    for p in (user_dir / "agent_prefs.yaml", user_dir / "agent_prefs.json"):
        if p.is_file():
            try:
                prefs = _read_yaml(p) if p.suffix == ".yaml" else _read_json(p)
            except Exception:
                prefs = {}
            break

    # 2) Tools config: prefer user override, fallback to template
    tools_cfg: dict[str, Any] = {}
    tool_sources = [
        user_dir / "agent_tools.yaml",
        templates_dir / "agent_tools_template.yaml",
    ]
    for p in tool_sources:
        if p.is_file():
            try:
                doc = _read_yaml(p)
                tools_cfg = (
                    doc.get("tools") if isinstance(doc.get("tools"), dict) else {}
                )
            except Exception:
                tools_cfg = {}
            break

    # If prefs doesn't already define tools, inject loaded tools config
    if not isinstance(prefs.get("tools"), dict):
        prefs["tools"] = tools_cfg

    return prefs


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
    text: str = typer.Argument(..., help="Text to embed for testing purposes.")
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


@agent_app.command("init")
def agent_init(
    objective: str = typer.Option(
        "", "--objective", help="Initial objective for the agent."
    ),
    force: bool = typer.Option(
        False, "--force", help="Overwrite existing agent_state.yaml"
    ),
):
    """
    Initialize (create) the agent state YAML.
    """
    p = _agent_state_path()
    if p.exists() and not force:
        raise typer.BadParameter(
            f"Agent state already exists: {p} (use --force to overwrite)"
        )

    now = _utc_now_iso()
    state = {
        "schema_version": 1,
        "created_at": now,
        "updated_at": now,
        "objective": objective,
        "status": "idle",
        "queue": [],
        "last_action": None,
        "history": [],
    }

    _save_agent_state(p, state)
    rprint(f"[bold green]Initialized agent state:[/bold green] {p}")


@agent_app.command("status")
def agent_status():
    p = _agent_state_path()
    state = _load_agent_state(p)
    if not state:
        rprint(
            f"[yellow]No agent state found at {p}. Run:[/yellow] orion tools agent init"
        )
        raise typer.Exit(code=1)

    rprint("[bold cyan]=== Agent Status ===[/bold cyan]")
    rprint(f"[white]State file: {p}[/white]")
    rprint(f"[white]Objective: {state.get('objective')!r}[/white]")
    rprint(f"[white]Status:    {state.get('status')!r}[/white]")
    rprint(f"[white]Queue:     {len(state.get('queue') or [])} item(s)[/white]")
    rprint(f"[white]Updated:   {state.get('updated_at')!r}[/white]")
    rprint(f"[white]Last:      {state.get('last_action')!r}[/white]")


@agent_app.command("tick")
def agent_tick():
    p = _agent_state_path()
    state = _load_agent_state(p)
    if not state:
        rprint(
            f"[yellow]No agent state found at {p}. Run:[/yellow] orion tools agent init"
        )
        raise typer.Exit(code=1)

    # NEW: load tool policy once per tick
    policy = _load_agent_tool_policy()
    allowlist = policy["allowlist"]

    confirm_map = policy.get("confirm_required") or {}
    if not isinstance(confirm_map, dict):
        confirm_map = {}

    allow_args_map = policy.get("allow_args") or {}
    if not isinstance(allow_args_map, dict):
        allow_args_map = {}

    now = _utc_now_iso()
    queue = state.get("queue") or []
    event: dict[str, Any] = {"at": now, "event": "tick"}
    action = "noop"

    if queue:
        item = queue.pop(0)

        action = "dequeued"
        last_action: dict[str, Any] = {"kind": "dequeue", "item": item, "at": now}
        event.update({"action": "dequeued", "item": item})
        state["status"] = "ran_step"

        if (
            isinstance(item, dict)
            and (item.get("kind") or "").strip().lower() == "tool"
        ):
            tool = (item.get("tool") or "").strip()
            args = item.get("args") or []
            if not isinstance(args, list) or not all(isinstance(x, str) for x in args):
                args = []

            # NEW: minimal arg policy enforcement in tick (mirrors enqueue-tool)
            if allow_args_map.get(tool) is False and args:
                queue.insert(0, item)

                action = "blocked"
                result = {
                    "ok": False,
                    "error": f"Args are not allowed for tool {tool!r}.",
                    "returncode": None,
                    "stdout": "",
                    "stderr": "",
                    "timed_out": False,
                    "duration_ms": 0,
                    "argv": [],
                }
                last_action = {
                    "kind": "tool",
                    "item": item,
                    "at": now,
                    "result": result,
                }
                event.update({"action": "blocked", "item": item, "result": result})
                state["status"] = "idle"

            else:
                # Existing confirm-gate (policy-driven)
                required = (confirm_map.get(tool) or "").strip()
                provided = (item.get("confirm") or "").strip()

                if required and provided != required:
                    queue.insert(0, item)

                    action = "blocked"
                    result = {
                        "ok": False,
                        "error": f"Confirmation required for tool {tool!r}. Re-enqueue with --confirm {required}.",
                        "returncode": None,
                        "stdout": "",
                        "stderr": "",
                        "timed_out": False,
                        "duration_ms": 0,
                        "argv": [],
                    }
                    last_action = {
                        "kind": "tool",
                        "item": item,
                        "at": now,
                        "result": result,
                    }
                    event.update({"action": "blocked", "item": item, "result": result})
                    state["status"] = "idle"
                else:
                    # tool execution now uses policy allowlist
                    result = _run_allowed_tool(tool, args, allowlist)

                    action = "tool"
                    last_action = {
                        "kind": "tool",
                        "item": item,
                        "at": now,
                        "result": result,
                    }
                    event.update({"action": "tool", "item": item, "result": result})

                    if not result.get("ok"):
                        state["status"] = "error"

        state["last_action"] = last_action

    else:
        action = "noop"
        event.update({"action": "noop"})
        state["status"] = "idle"
        state["last_action"] = {"kind": "noop", "at": now}

    state["queue"] = queue
    state["updated_at"] = now
    state.setdefault("history", []).append(event)

    _save_agent_state(p, state)

    # Prefer friendly_name from agent_prefs.yaml for tool items
    name = action
    last_action = state.get("last_action") or {}

    if isinstance(last_action, dict) and last_action.get("kind") == "tool":
        item = last_action.get("item") or {}
        tool = item.get("tool") if isinstance(item, dict) else None

        friendly = None
        try:
            prefs = _load_agent_prefs()
            tools_cfg = (prefs or {}).get("tools") or {}
            if tool and isinstance(tools_cfg, dict):
                tool_cfg = tools_cfg.get(tool) or {}
                if isinstance(tool_cfg, dict):
                    friendly = tool_cfg.get("friendly_name")
        except Exception:
            friendly = None

        name = friendly or tool or name

    elif isinstance(last_action, dict) and last_action.get("kind") == "noop":
        name = "No work (queue empty)"

    # ---- optional polish: show ok/fail and a short note ----
    suffix = ""
    note = ""
    if isinstance(last_action, dict) and last_action.get("kind") == "tool":
        res = last_action.get("result") or {}
        if isinstance(res, dict):
            ok = res.get("ok")
            if ok is True:
                suffix = " ✅"
            elif ok is False:
                suffix = " ❌"

            # Optional: include a short message if present
            # (adjust keys if your result uses different ones)
            msg = res.get("message") or res.get("error") or ""
            if isinstance(msg, str) and msg.strip():
                note = f" — {msg.strip()}"
    # -----------------------------------------------

    rprint(f"[bold green]Tick complete.[/bold green] {name}{suffix}{note}")


@agent_app.command("enqueue")
def agent_enqueue(
    task: str = typer.Argument(..., help="Task to add to the agent queue."),
    tag: str = typer.Option("", "--tag", help="Optional tag/category."),
):
    p = _agent_state_path()
    state = _load_agent_state(p)
    if not state:
        rprint(
            f"[yellow]No agent state found at {p}. Run:[/yellow] orion tools agent init"
        )
        raise typer.Exit(code=1)

    now = _utc_now_iso()
    item = {"task": task, "tag": tag, "enqueued_at": now}
    q = state.get("queue") or []
    q.append(item)

    state["queue"] = q
    state["updated_at"] = now
    state.setdefault("history", []).append(
        {"at": now, "event": "enqueue", "item": item}
    )
    _save_agent_state(p, state)

    rprint(f"[bold green]Enqueued.[/bold green] queue_size={len(q)}")


# -------------------------------------------------------------
# Agent: batch enqueue (explicit approval gate)
# -------------------------------------------------------------


def _read_yaml_file(path: Path) -> dict:
    obj = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(obj, dict):
        raise typer.BadParameter(f"YAML root must be a mapping/object: {path}")
    return obj


def _normalize_policy(policy):
    """
    Accepts either:
      - dict with 'tools' mapping (new style)
      - tuple/list: (allowlist, confirm_required, allow_args_map) (your current style)
      - dict with 'allowlist' / 'confirm' / 'allow_args' (alt style)
    Returns:
      tools_map: { tool_name: {"allow_args": bool, "confirm": str} }
    """
    # Tuple/list style: (allowlist, confirm_required, allow_args_map)
    if isinstance(policy, (tuple, list)) and len(policy) >= 3:
        allowlist, confirm_required, allow_args_map = policy[0], policy[1], policy[2]
        tools_map = {}
        for name in (allowlist or {}).keys():
            tools_map[name] = {
                "allow_args": bool((allow_args_map or {}).get(name, False)),
                "confirm": ((confirm_required or {}).get(name) or "").strip(),
            }
        return tools_map

    # Dict style
    if isinstance(policy, dict):
        if isinstance(policy.get("tools"), dict):
            return policy["tools"]

        allowlist = policy.get("allowlist") or {}
        confirm_required = policy.get("confirm") or {}
        allow_args_map = policy.get("allow_args") or {}
        if isinstance(allowlist, dict) and allowlist:
            tools_map = {}
            for name in allowlist.keys():
                tools_map[name] = {
                    "allow_args": bool(allow_args_map.get(name, False)),
                    "confirm": (confirm_required.get(name) or "").strip(),
                }
            return tools_map

    raise typer.BadParameter("Tool policy shape not recognized")


def _validate_plan_items(plan_items: list, policy: dict) -> list[dict]:
    tools = policy.get("tools") or {}
    if not isinstance(tools, dict):
        raise typer.BadParameter("Tool policy invalid: missing 'tools' mapping")

    # ✅ ADD THIS LINE
    validated: list[dict] = []

    for i, it in enumerate(plan_items):
        if not isinstance(it, dict):
            raise typer.BadParameter(f"plan.items[{i}] must be an object")

        kind = (it.get("kind") or "").strip()
        if kind != "tool":
            raise typer.BadParameter(f"plan.items[{i}].kind must be 'tool'")

        name = it.get("tool")
        if not name or not isinstance(name, str):
            raise typer.BadParameter(f"plan.items[{i}].tool must be a string")
        if name not in tools:
            raise typer.BadParameter(f"plan.items[{i}]: tool not allowlisted: {name!r}")

        args = it.get("args") or []
        if not isinstance(args, list) or any(not isinstance(x, str) for x in args):
            raise typer.BadParameter(f"plan.items[{i}].args must be list[str]")

        allow_args = bool((tools.get(name) or {}).get("allow_args", False))
        if (not allow_args) and args:
            raise typer.BadParameter(
                f"plan.items[{i}]: args not allowed for tool {name!r}"
            )

        required_confirm = ((tools.get(name) or {}).get("confirm") or "").strip()
        provided_confirm = (it.get("confirm") or "").strip()
        if required_confirm and provided_confirm != required_confirm:
            raise typer.BadParameter(
                f"plan.items[{i}]: confirm required for {name!r}: {required_confirm!r}"
            )

        validated.append(
            {
                "kind": "tool",
                "tool": name,
                "args": args,
                "confirm": provided_confirm,
                "reason": (it.get("reason") or ""),
            }
        )

    return validated


def _validate_plan_items(plan_items: list, policy: dict) -> list[dict]:
    """
    Validates plan items against the current tool policy and returns normalized
    queue items ready to append to agent_state.yaml.

    Strict by design:
    - only kind: tool
    - tool must be allowlisted
    - args must satisfy allow_args
    - confirm must match policy confirm (if required)
    """
    tools = policy.get("tools") or {}
    if not isinstance(tools, dict):
        raise typer.BadParameter("Tool policy invalid: missing 'tools' mapping")

    validated: list[dict] = []

    if not isinstance(plan_items, list) or not plan_items:
        raise typer.BadParameter("plan.items must be a non-empty list")

    for i, it in enumerate(plan_items):
        if not isinstance(it, dict):
            raise typer.BadParameter(f"plan.items[{i}] must be an object")

        kind = (it.get("kind") or "").strip()
        if kind != "tool":
            raise typer.BadParameter(f"plan.items[{i}].kind must be 'tool'")

        name = it.get("tool")
        if not name or not isinstance(name, str):
            raise typer.BadParameter(f"plan.items[{i}].tool must be a string")
        if name not in tools:
            raise typer.BadParameter(f"plan.items[{i}]: tool not allowlisted: {name!r}")

        args = it.get("args") or []
        if not isinstance(args, list) or any(not isinstance(x, str) for x in args):
            raise typer.BadParameter(f"plan.items[{i}].args must be list[str]")

        allow_args = bool((tools.get(name) or {}).get("allow_args", False))
        if (not allow_args) and args:
            raise typer.BadParameter(
                f"plan.items[{i}]: args not allowed for tool {name!r}"
            )

        required_confirm = ((tools.get(name) or {}).get("confirm") or "").strip()
        provided_confirm = (it.get("confirm") or "").strip()
        if required_confirm and provided_confirm != required_confirm:
            raise typer.BadParameter(
                f"plan.items[{i}]: confirm required for {name!r}: {required_confirm!r}"
            )

        validated.append(
            {
                "kind": "tool",
                "tool": name,
                "args": args,
                "confirm": provided_confirm,
                "reason": (it.get("reason") or ""),
            }
        )

    return validated


@agent_app.command("enqueue-batch")
def agent_enqueue_batch(
    plan: Path = typer.Option(
        ..., "--plan", exists=True, dir_okay=False, help="Path to a plan YAML file."
    ),
    confirm: str = typer.Option("", "--confirm", help="Required: ENQUEUE_BATCH"),
):
    """
    Explicit approval gate: validate a multi-item plan against agent_tools.yaml and enqueue atomically.
    Rejects the entire batch if any item fails validation.
    """
    if confirm != "ENQUEUE_BATCH":
        rprint("[red]Refusing: missing --confirm ENQUEUE_BATCH[/red]")
        raise typer.Exit(code=2)

    # Load state
    p = _agent_state_path()
    state = _load_agent_state(p)
    if not state:
        rprint(
            f"[yellow]No agent state found at {p}. Run:[/yellow] orion tools agent init"
        )
        raise typer.Exit(code=1)

    # Load plan + policy
    plan_obj = _read_yaml_file(plan)
    plan_items = plan_obj.get("items") or []
    policy_path = _agent_tools_policy_path()
    policy_raw = _read_yaml_file(policy_path)
    if (policy_raw.get("schema_version") or 0) != 1:
        raise typer.BadParameter(
            f"Unsupported agent_tools schema_version: {policy_raw.get('schema_version')!r} in {policy_path}"
        )

    validated = _validate_plan_items(plan_items, policy_raw)

    # Append
    now = _utc_now_iso()
    q = state.get("queue") or []
    for it in validated:
        it["enqueued_at"] = now
        q.append(it)

    over = plan_obj.get("state_overrides") or {}
    if over:
        if not isinstance(over, dict):
            raise typer.BadParameter("state_overrides must be a mapping/object")

        allowed = {"history_max_events", "max_result_chars"}
        unknown = set(over.keys()) - allowed
        if unknown:
            raise typer.BadParameter(
                f"state_overrides has unknown keys: {sorted(unknown)}"
            )

        # Basic type checks
        if "history_max_events" in over and not isinstance(
            over["history_max_events"], int
        ):
            raise typer.BadParameter("state_overrides.history_max_events must be int")
        if "max_result_chars" in over and not isinstance(over["max_result_chars"], int):
            raise typer.BadParameter("state_overrides.max_result_chars must be int")

        state.setdefault("settings", {})
        state["settings"].update(over)

        if over:
            state.setdefault("history", []).append(
                {
                    "at": now,
                    "event": "settings_update",
                    "source": "plan",
                    "overrides": over,
                }
            )

    state["queue"] = q
    state["updated_at"] = now
    state.setdefault("history", []).append(
        {
            "at": now,
            "event": "enqueue_batch",
            "plan_id": plan_obj.get("plan_id", ""),
            "count": len(validated),
            "tools": [x["tool"] for x in validated],
        }
    )
    _save_agent_state(p, state)

    rprint(
        f"[bold green]Enqueued batch.[/bold green] items={len(validated)} queue_size={len(q)}"
    )


@agent_app.command("enqueue-tool")
def agent_enqueue_tool(
    tool: str = typer.Argument(..., help="Allowlisted tool name (e.g. 'paths')."),
    args: list[str] = typer.Option(
        None, "--arg", help="Repeatable arg, e.g. --arg foo --arg bar"
    ),
    tag: str = typer.Option("", "--tag", help="Optional tag/category."),
    confirm: str = typer.Option(
        "", "--confirm", help="Confirmation token for confirm-gated tools."
    ),
):

    p = _agent_state_path()
    state = _load_agent_state(p)
    if not state:
        rprint(
            f"[yellow]No agent state found at {p}. Run:[/yellow] orion tools agent init"
        )
        raise typer.Exit(code=1)

    tool = tool.strip()
    tag = (tag or "").strip()
    args = [(a or "").strip() for a in (args or []) if (a or "").strip()]
    confirm = (confirm or "").strip()

    policy = _load_agent_tool_policy()
    allowlist = policy.get["allowlist"]
    allow_args_map = policy.get("allow_args") or {}

    if tool not in allowlist:
        rprint(f"[red]Tool not allowlisted:[/red] {tool!r}")
        raise typer.Exit(code=2)

    if allow_args_map.get(tool) is False and args:
        rprint(f"[red]Args are not allowed for tool:[/red] {tool!r}")
        raise typer.Exit(code=2)

    now = _utc_now_iso()
    item = {"kind": "tool", "tool": tool, "args": args, "tag": tag, "enqueued_at": now}
    if confirm:
        item["confirm"] = confirm
    q = state.get("queue") or []
    q.append(item)

    state["queue"] = q
    state["updated_at"] = now
    state.setdefault("history", []).append(
        {"at": now, "event": "enqueue_tool", "item": item}
    )
    _save_agent_state(p, state)

    rprint(f"[bold green]Enqueued tool.[/bold green] tool={tool!r} queue_size={len(q)}")


@agent_app.command("peek")
def agent_peek(
    n: int = typer.Option(1, "--n", help="How many upcoming items to show.")
):
    p = _agent_state_path()
    state = _load_agent_state(p)
    if not state:
        rprint(
            f"[yellow]No agent state found at {p}. Run:[/yellow] orion tools agent init"
        )
        raise typer.Exit(code=1)

    q = state.get("queue") or []
    n = max(1, min(int(n), 20))
    if not q:
        rprint("[bold]Queue:[/bold] (empty)")
        return

    rprint(f"[bold]Queue (next {min(n, len(q))}/{len(q)}):[/bold]")
    for i, item in enumerate(q[:n], start=1):
        rprint(f"{i:>2}. {item!r}")


@agent_app.command("drop")
def agent_drop(
    index: int = typer.Option(
        ..., "--index", "-i", help="1-based index into the queue."
    ),
):
    p = _agent_state_path()
    state = _load_agent_state(p)
    if not state:
        rprint(
            f"[yellow]No agent state found at {p}. Run:[/yellow] orion tools agent init"
        )
        raise typer.Exit(code=1)

    q = state.get("queue") or []
    if not q:
        rprint("[yellow]Queue is empty.[/yellow]")
        raise typer.Exit(code=0)

    if index < 1 or index > len(q):
        rprint(f"[red]Index out of range.[/red] index={index} queue_size={len(q)}")
        raise typer.Exit(code=2)

    removed = q.pop(index - 1)
    now = _utc_now_iso()

    state["queue"] = q
    state["updated_at"] = now
    state.setdefault("history", []).append(
        {"at": now, "event": "drop", "index": index, "item": removed}
    )
    _save_agent_state(p, state)

    rprint(
        f"[bold green]Dropped queue item.[/bold green] index={index} queue_size={len(q)}"
    )


@agent_app.command("move")
def agent_move(
    src: int = typer.Option(..., "--from", help="1-based source index in the queue."),
    dst: int = typer.Option(
        ..., "--to", help="1-based destination index in the queue."
    ),
):
    p = _agent_state_path()
    state = _load_agent_state(p)
    if not state:
        rprint(
            f"[yellow]No agent state found at {p}. Run:[/yellow] orion tools agent init"
        )
        raise typer.Exit(code=1)

    q = state.get("queue") or []
    if not q:
        rprint("[yellow]Queue is empty.[/yellow]")
        raise typer.Exit(code=0)

    n = len(q)
    if src < 1 or src > n:
        rprint(f"[red]Source index out of range.[/red] from={src} queue_size={n}")
        raise typer.Exit(code=2)
    if dst < 1 or dst > n:
        rprint(f"[red]Destination index out of range.[/red] to={dst} queue_size={n}")
        raise typer.Exit(code=2)

    if src == dst:
        rprint("[yellow]No-op.[/yellow] from == to")
        raise typer.Exit(code=0)

    item = q.pop(src - 1)
    q.insert(dst - 1, item)

    now = _utc_now_iso()
    state["queue"] = q
    state["updated_at"] = now
    state.setdefault("history", []).append(
        {"at": now, "event": "move", "from": src, "to": dst, "item": item}
    )
    _save_agent_state(p, state)

    rprint(
        f"[bold green]Moved queue item.[/bold green] from={src} to={dst} queue_size={len(q)}"
    )


@agent_app.command("clear")
def agent_clear(
    confirm: str = typer.Option(
        "",
        "--confirm",
        help="Required confirmation token. Use: --confirm CLEAR_QUEUE",
    ),
):
    p = _agent_state_path()
    state = _load_agent_state(p)
    if not state:
        rprint(
            f"[yellow]No agent state found at {p}. Run:[/yellow] orion tools agent init"
        )
        raise typer.Exit(code=1)

    token = (confirm or "").strip()
    if token != "CLEAR_QUEUE":
        rprint("[red]Refusing to clear queue.[/red] Pass: --confirm CLEAR_QUEUE")
        raise typer.Exit(code=2)

    q = state.get("queue") or []
    n = len(q)
    if n == 0:
        rprint("[yellow]Queue is already empty.[/yellow]")
        raise typer.Exit(code=0)

    now = _utc_now_iso()
    state["queue"] = []
    state["updated_at"] = now
    state.setdefault("history", []).append(
        {"at": now, "event": "clear_queue", "count": n}
    )
    _save_agent_state(p, state)

    rprint(f"[bold green]Cleared queue.[/bold green] removed={n}")


@agent_app.command("snapshot")
def agent_snapshot(
    out: str = typer.Option(
        "",
        "--out",
        help="Optional output path. If omitted, writes to <USER_ORION_DIR>/workspace/agent_snapshots/.",
    )
):
    """
    Generate a read-only Markdown snapshot of the current Orion/Agent runtime context.

    Tier: 0 (read-only)
    - No DB writes
    - No agent state writes
    - No queue changes
    - No tool execution
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")

    # Output path (default: workspace)
    snapshots_dir = WORKSPACE_DIR / "agent_snapshots"
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    out_path = (
        Path(out).expanduser() if out else (snapshots_dir / f"agent_snapshot_{now}.md")
    )

    # Load agent state (best-effort)
    state = None
    if AGENT_STATE_PATH.exists():
        try:
            state = yaml.safe_load(AGENT_STATE_PATH.read_text(encoding="utf-8")) or {}
        except Exception:
            state = {"_error": "failed_to_parse_agent_state_yaml"}
    else:
        state = {"_note": "agent_state_missing"}

    # Load tool policy (best-effort)
    tool_policy_path = USER_DATA_DIR / "agent_tools.yaml"
    tool_policy = None
    if tool_policy_path.exists():
        try:
            tool_policy = (
                yaml.safe_load(tool_policy_path.read_text(encoding="utf-8")) or {}
            )
        except Exception:
            tool_policy = {"_error": "failed_to_parse_agent_tools_yaml"}
    else:
        tool_policy = {"_note": "agent_tools_policy_missing"}

    # Config (best-effort; should be safe to read)
    cfg_dump = None
    try:
        cfg_dump = get_config().model_dump()
    except Exception:
        cfg_dump = {"_error": "failed_to_load_config"}

    # Assemble markdown (keep it plain + reviewable)
    lines: list[str] = []
    lines.append("# Orion Agent Snapshot")
    lines.append("")
    lines.append("## Timestamp (UTC)")
    lines.append(f"- {now}")
    lines.append("")
    lines.append("## Paths")
    lines.append(f"- USER_ORION_DIR: {USER_ORION_DIR}")
    lines.append(f"- USER_DATA_DIR: {USER_DATA_DIR}")
    lines.append(f"- WORKSPACE_DIR: {WORKSPACE_DIR}")
    lines.append(f"- AGENT_STATE_PATH: {AGENT_STATE_PATH}")
    lines.append(f"- DEFAULT_CHROMA_PATH: {DEFAULT_CHROMA_PATH}")
    lines.append(f"- PACKAGE_ROOT: {PACKAGE_ROOT}")
    lines.append(f"- DEFAULT_CONFIG_PATH: {DEFAULT_CONFIG_PATH}")
    lines.append(f"- EMBEDDING_MODEL_DIR: {EMBEDDING_MODEL_DIR}")
    lines.append(f"- SCHEMA_PATH: {SCHEMA_PATH}")
    lines.append("")
    lines.append("## Agent State (summary)")
    q = state.get("queue") if isinstance(state, dict) else None
    q_len = len(q) if isinstance(q, list) else 0
    lines.append(
        f"- status: {state.get('status') if isinstance(state, dict) else 'unknown'}"
    )
    lines.append(
        f"- objective: {state.get('objective') if isinstance(state, dict) else 'unknown'}"
    )
    lines.append(f"- queue_length: {q_len}")
    lines.append(
        f"- updated_at: {state.get('updated_at') if isinstance(state, dict) else 'unknown'}"
    )
    lines.append("")
    lines.append("## Tool Policy (summary)")
    tools = tool_policy.get("tools") if isinstance(tool_policy, dict) else None
    tool_names = sorted(list(tools.keys())) if isinstance(tools, dict) else []
    lines.append(f"- policy_path: {tool_policy_path}")
    lines.append(f"- tools_count: {len(tool_names)}")
    if tool_names:
        lines.append("- tools:")
        for name in tool_names:
            lines.append(f"  - {name}")
    lines.append("")
    lines.append("## Config (model_dump)")
    lines.append("```yaml")
    lines.append(yaml.safe_dump(cfg_dump, sort_keys=False).rstrip())
    lines.append("```")
    lines.append("")
    lines.append("## Notes")
    lines.append("- This report is read-only and performs no mutations.")
    lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    rprint(f"[bold green]Wrote snapshot:[/bold green] {out_path}")


__all__ = ["app"]
