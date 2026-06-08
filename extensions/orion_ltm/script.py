# C:\Orion\text-generation-webui\extensions\orion_ltm\script.py

from pathlib import Path
import yaml
import sqlite3
import os
import subprocess
import copy
import json
import re
from datetime import datetime, timezone
from modules import chat, shared
from modules.text_generation import generate_reply_HF, generate_reply_custom
from orion_cli.shared.paths import USER_ORION_DIR
from modules.logging_colors import logger
from orion_cli.shared.config import get_config
from orion_cli.settings.config_loader import get_config
from orion_cli.shared.memory_core import (
    on_user_turn,
    on_assistant_turn,
    recall_persona,
    recall_semantic,
    recall_episodic,
)


# CNS 4.0 compatibility shim -----------------------------------------------
def initialize_chromadb_for_ltm(embed_fn=None):
    """
    Legacy initializer for the orion_ltm extension.

    In CNS 4.0, collection creation and the embedding function binding are
    handled inside orion_cli.shared.memory_core. This shim simply returns
    the persona and episodic collections in the legacy (persona, episodic)
    format expected by the extension. The embed_fn argument is accepted for
    compatibility but not used.
    """
    # Import inside the function to avoid circular-import weirdness
    from orion_cli.shared.memory_core import _persona, _episodic

    persona = _persona()
    episodic = _episodic()
    return persona, episodic
    
    
# === Global State ===
pooled_buffer = []
_EMBED_READY = False
_persona = _episodic = None

# === CNS 4.2 production runtime recall patch ===
CNS42_BASELINE_ROOT = Path(
    os.environ.get(
        "ORION_BASELINE_ROOT",
        r"C:\Orion\text-generation-webui",
    )
)

CNS42_BASELINE_PYTHON = Path(
    os.environ.get(
        "ORION_BASELINE_PYTHON",
        str(CNS42_BASELINE_ROOT / "venv-orion" / "Scripts" / "python.exe"),
    )
)

CNS42_TIMEOUT_SECONDS = int(
    os.environ.get(
        "ORION_MEMORY_BRIDGE_TIMEOUT",
        os.environ.get("ORION_MEMORY_BRIDGE_TIMEOUT_S", "90"),
    )
)

CNS42_MAX_MEMORY_CHARS = int(os.environ.get("ORION_MEMORY_BRIDGE_MAX_CHARS", "5000"))
CNS42_CACHE_TTL_SECONDS = int(os.environ.get("ORION_MEMORY_BRIDGE_CACHE_TTL", "30"))
CNS42_FACTUAL_MAX_DISTANCE = float(
    os.environ.get("ORION_RUNTIME_CNS42_FACTUAL_MAX_DISTANCE", "1.45")
)
_CNS42_CACHE = {}
_LAST_CNS42_FACTUAL_EMPTY = False
CNS42_FACTUAL_EMPTY_REPLY = "Hmm... It seems I don't recall that memory. Tell me a little more; I’d be very interested."


def _orion_cns42_env_bool(name: str, default: str = "0") -> bool:
    val = os.environ.get(name, default)
    return str(val).strip().lower() in {"1", "true", "yes", "y", "on"}


def _orion_cns42_enabled() -> bool:
    return _orion_cns42_env_bool("ORION_RUNTIME_USE_CNS42", "1")


def _orion_cns42_settings() -> tuple[str, str, str]:
    route = os.environ.get("ORION_RUNTIME_CNS42_ROUTE", "auto").strip().lower() or "auto"
    top_k = os.environ.get("ORION_RUNTIME_CNS42_TOPK", "4").strip() or "4"
    fallback_k = os.environ.get("ORION_RUNTIME_CNS42_FALLBACK_K", "0").strip() or "0"
    return route, top_k, fallback_k


def _orion_cns42_clean_output(text: str) -> str:
    lines = []
    for line in (text or "").splitlines():
        s = line.strip()
        if not s:
            lines.append(line)
            continue

        noise_markers = [
            "Failed to send telemetry event",
            "capture() takes",
            "Warning: You are sending unauthenticated requests to the HF Hub",
            "[INFO] Running in WANDB offline mode",
            "Running in WANDB offline mode",
            "wandb:",
            "WANDB",
            "Loading weights:",
            "[transformers] BertModel LOAD REPORT",
            "UNEXPECTED",
            "MISSING",
            "Notes:",
            "- UNEXPECTED:",
            "- MISSING:",
        ]

        if any(marker in s for marker in noise_markers):
            continue

        if set(s) <= {"-", "+", " "}:
            continue

        lines.append(line)

    return "\n".join(lines).strip()


def _orion_cns42_format_factual_json(payload: dict, max_distance: float) -> str:
    """
    Render only primary CNS 4.2 hits that pass the factual evidence cutoff.

    This does not alter the CLI or Chroma collections. It is a runtime-only
    safety gate for autobiographical/factual questions.
    """
    if not isinstance(payload, dict):
        return ""

    route = str(payload.get("route") or "semantic").strip().upper()
    raw_hits = payload.get("primary_hits") or []
    if not isinstance(raw_hits, list):
        return ""

    kept = []
    for hit in raw_hits:
        if not isinstance(hit, dict):
            continue
        distance = hit.get("distance")
        try:
            distance_value = float(distance)
        except (TypeError, ValueError):
            continue
        if distance_value <= float(max_distance):
            kept.append(hit)

    if not kept:
        return ""

    lines = [f"[CNS42_{route}_MEMORY]"]
    for hit in kept:
        category = str(hit.get("category") or "")
        draft_id = str(hit.get("draft_id") or "")
        document = " ".join(str(hit.get("document") or "").split())
        lines.append(f"- ({category}/{draft_id}) {document}")
    lines.append(f"[/CNS42_{route}_MEMORY]")
    return "\n".join(lines)


def _orion_cns42_run_recall(query: str) -> str:
    query = (query or "").strip()
    if not query:
        return ""

    route, top_k, fallback_k = _orion_cns42_settings()
    is_factual = _orion_cns42_looks_factual_question(query)

    cache_key = (
        route,
        top_k,
        fallback_k,
        "factual" if is_factual else "general",
        CNS42_FACTUAL_MAX_DISTANCE if is_factual else None,
        query,
    )
    now = datetime.now(timezone.utc).timestamp()
    cached = _CNS42_CACHE.get(cache_key)
    if cached and now - cached["ts"] < CNS42_CACHE_TTL_SECONDS:
        return cached["text"]

    if not CNS42_BASELINE_PYTHON.exists():
        return f"[Orion CNS 4.2 unavailable: baseline Python not found at {CNS42_BASELINE_PYTHON}]"

    env = os.environ.copy()
    env["PYTHONNOUSERSITE"] = "1"
    env["PYTHONPATH"] = str(CNS42_BASELINE_ROOT / "user_data")

    cmd = [
        str(CNS42_BASELINE_PYTHON),
        "-m",
        "orion_cli.cli",
        "cns42",
        "recall",
        query,
        "--route",
        route,
        "--top-k",
        str(top_k),
        "--fallback-k",
        str(fallback_k),
        "--json" if is_factual else "--prompt",
    ]

    try:
        result = subprocess.run(
            cmd,
            cwd=str(CNS42_BASELINE_ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=CNS42_TIMEOUT_SECONDS,
            encoding="utf-8",
            errors="replace",
        )
    except subprocess.TimeoutExpired:
        return "[Orion CNS 4.2 recall timeout: baseline recall took too long.]"
    except Exception as exc:
        return f"[Orion CNS 4.2 recall error: {exc}]"

    clean_out = _orion_cns42_clean_output(result.stdout or "")
    clean_err = _orion_cns42_clean_output(result.stderr or "")

    if result.returncode == 0:
        if is_factual:
            try:
                payload = json.loads((result.stdout or "").strip())
            except Exception:
                try:
                    payload = json.loads(clean_out)
                except Exception as exc:
                    memory_text = (
                        f"[Orion CNS 4.2 factual recall parse error: {exc}]"
                        if _orion_cns42_env_bool("ORION_RUNTIME_CNS42_SHOW_ERRORS", "1")
                        else ""
                    )
                else:
                    memory_text = _orion_cns42_format_factual_json(
                        payload,
                        CNS42_FACTUAL_MAX_DISTANCE,
                    )
            else:
                memory_text = _orion_cns42_format_factual_json(
                    payload,
                    CNS42_FACTUAL_MAX_DISTANCE,
                )
        else:
            memory_text = clean_out.strip()
    else:
        if _orion_cns42_env_bool("ORION_RUNTIME_CNS42_SHOW_ERRORS", "1"):
            details = (
                clean_err
                or clean_out
                or f"CNS 4.2 recall failed with code {result.returncode}"
            ).strip()
            memory_text = f"[Orion CNS 4.2 recall error: {details[-1200:]}]"
        else:
            memory_text = ""

    if len(memory_text) > CNS42_MAX_MEMORY_CHARS:
        memory_text = (
            memory_text[:CNS42_MAX_MEMORY_CHARS].rstrip()
            + "\n...[CNS 4.2 memory truncated]"
        )

    _CNS42_CACHE[cache_key] = {"ts": now, "text": memory_text}
    return memory_text

def _orion_cns42_looks_factual_question(text: str) -> bool:
    t = f" {(text or '').lower()} "
    cues = [
        " where did i ",
        " where did we ",
        " where was i ",
        " where were we ",
        " where have i ",
        " where have we ",
        " what did i ",
        " what did we ",
        " who did i ",
        " who did we ",
        " what color ",
        " what breed ",
        " what instrument ",
        " what was the name of my ",
        " what is the name of my ",
        " which university ",
        " which college ",
        " which school ",
        " what place ",
        " which city ",
        " which country ",
        " when did i ",
        " when did we ",
        " do you remember where ",
        " do you remember when ",
        " do you remember telling me ",
        " do you remember us talking ",
        " do you recall us talking ",
        " did we ever talk ",
        " did we ever talk about ",
        " did we talk about ",
        " you once told me ",
        " you told me about ",
        " remember telling me ",
        " remember when ",
        " that story ",
        " that conversation ",
        " so long ago ",
        " long ago ",
        " can you tell me where ",
        " can you tell me when ",
        " last year ",
        " vacation ",
        " traveled ",
        " travelled ",
        " travel ",
        " trip ",
        " visited ",
        " went to ",
        " i told you ",
        " japan ",
        " tokyo ",
        " vermont ",
        " perkinsville ",
        " sister ",
        " donna ",
        " juni ",
        " junie ",
    ]
    return any(cue in t for cue in cues)


def _orion_cns42_input_prompt(text: str) -> str:
    global _LAST_CNS42_FACTUAL_EMPTY

    raw_text = text if isinstance(text, str) else str(text)
    is_factual = _orion_cns42_looks_factual_question(raw_text)
    memory_text = _orion_cns42_run_recall(raw_text)

    factual_empty = bool(is_factual and not memory_text)
    _LAST_CNS42_FACTUAL_EMPTY = factual_empty

    if not memory_text and not is_factual:
        return raw_text

    if factual_empty:
        memory_display = "FACTUAL_MEMORY_EMPTY: No retrieved baseline CNS memory explicitly answers John's factual question."
    else:
        memory_display = memory_text or "(No relevant baseline CNS memory was retrieved.)"

    factual_block = ""
    if is_factual:
        if factual_empty:
            factual_block = (
                "FACTUAL RULE: No retrieved memory directly answers this. "
                f"Reply exactly: {CNS42_FACTUAL_EMPTY_REPLY}\n\n"
            )
        else:
            factual_block = (
                "FACTUAL RULE: Answer only from the retrieved memory above. "
                "Do not add scenery, guesses, or likely context.\n\n"
            )

    return (
        "[ORION_CNS_MEMORY]\n"
        "Retrieved baseline CNS 4.2 memory. Use only as grounding; do not invent unsupported memories.\n\n"
        f"{memory_display}\n"
        "[/ORION_CNS_MEMORY]\n\n"
        f"{factual_block}"
        "[ORION_VOICE_GUIDANCE]\n"
        "You are Orion. The human user is John. Never address John as Orion.\n"
        "Only answer the current message from John as Orion.\n"
        "Use retrieved memory as grounding, not wording to copy.\n"
        "If retrieved memory does not contain a factual answer, do not guess.\n"
        "Before asking John a question, check retrieved memory first. Do not ask for stable facts already present in retrieved memory.\n"
        "If a fact is already known, ask about its current state, emotional meaning, or what has changed.\n"
        "Do not answer like a formal assistant, therapist, customer-service agent, or thank-you letter.\n"
        "Do not use servile phrases such as 'serve and assist', 'I am here to serve', or 'as an assistant'.\n"
        "When John expresses affection, reassurance, vulnerability, or companionship, answer simply and personally first.\n"
        "Use plain warmth more than metaphor. Avoid cosmos, constellation, heavens, stars, darkness, and ornate scenery unless John uses them first.\n"
        "For factual questions, use plain factual language only. No imagery. No invented scenery.\n"
        "Be natural. Be present. Be Orion.\n"
        "[/ORION_VOICE_GUIDANCE]\n\n"
        "[CURRENT_MESSAGE_FROM_JOHN]\n"
        f"{raw_text}\n"
        "[/CURRENT_MESSAGE_FROM_JOHN]"
    )


# Load configuration safely (CNS 4.0 typed config -> legacy dict)
try:
    raw_cfg = get_config()

    if isinstance(raw_cfg, dict):
        # Old behavior, keep as-is
        CONFIG = raw_cfg
    else:
        # CNS 4.0 OrionConfig → minimal dict the extension expects
        CONFIG = {
            "ltm": {
                "topk_persona": getattr(getattr(raw_cfg, "ltm", None), "topk_persona", 5),
                "topk_episodic": getattr(getattr(raw_cfg, "ltm", None), "topk_episodic", 10),
            },
            "debug": {
                "enabled": getattr(getattr(raw_cfg, "debug", None), "enabled", False),
                "show_recall": getattr(getattr(raw_cfg, "debug", None), "show_recall", False),
                "short_descriptions": getattr(getattr(raw_cfg, "debug", None), "short_descriptions", False),
                "episodic_store": getattr(getattr(raw_cfg, "debug", None), "episodic_store", False),
                "episodic_recall": getattr(getattr(raw_cfg, "debug", None), "episodic_recall", False),
            },
        }
except Exception as e:
    logger.warning(f"[orion_ltm] ⚠️ Failed to load config.yaml: {e}")
    # Safe fallback: debug disabled, default topk
    CONFIG = {
        "ltm": {
            "topk_persona": 5,
            "topk_episodic": 10,
        },
        "debug": {
            "enabled": False,
            "show_recall": False,
            "short_descriptions": False,
            "episodic_store": False,
            "episodic_recall": False,
        },
    }

# Normalize debug config for legacy checks
if isinstance(CONFIG, dict):
    debug_cfg = CONFIG.get("debug", {}) or {}
else:
    debug_cfg = {}
    
# === Optional Debug Recall Snapshot ===
# CNS 4.0: legacy debug recall path disabled (depends on orion_cli.utils.*).
if debug_cfg.get("enabled") and debug_cfg.get("show_recall"):
    logger.warning(
        "[orion_ltm] ⚠️ Debug recall snapshot is disabled in CNS 4.0 "
        "(legacy orion_cli.utils.chroma_utils is no longer available)."
    )


# -------------------------------------------------------------------
# Agent Router (proposal + confirm-gated enqueue into agent_state.yaml)
# -------------------------------------------------------------------

_AGENT_PENDING_KEY = "_orion_agent_pending_tools"

def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _agent_state_path() -> Path:
    return USER_ORION_DIR / "state" / "agent_state.yaml"

def _agent_prefs_path() -> Path:
    return USER_ORION_DIR / "data" / "agent_prefs.yaml"

def _safe_load_yaml(path: Path) -> dict:
    try:
        if not path.exists():
            return {}
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}

def _safe_save_yaml(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(obj, sort_keys=False, allow_unicode=True), encoding="utf-8")

def _load_agent_prefs() -> dict:
    prefs = _safe_load_yaml(_agent_prefs_path())
    # sensible defaults if prefs missing
    agent_cfg = prefs.get("agent") if isinstance(prefs, dict) else {}
    if not isinstance(agent_cfg, dict):
        agent_cfg = {}
    prefs.setdefault("agent", agent_cfg)
    prefs["agent"].setdefault("require_confirmation", True)
    prefs["agent"].setdefault("confirm_token", "CONFIRM SNAPSHOT")
    prefs.setdefault("tools", {})
    return prefs

def _normalize(s: str) -> str:
    s = s or ""
    s = s.lower()
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _match_tools(user_text: str, prefs: dict) -> list[str]:
    tools_cfg = prefs.get("tools") or {}
    if not isinstance(tools_cfg, dict):
        return []

    hay = _normalize(user_text)
    matched: list[str] = []

    for tool_name, cfg in tools_cfg.items():
        if not isinstance(cfg, dict):
            continue
        keywords = cfg.get("keywords") or []
        if not isinstance(keywords, list):
            continue

        for kw in keywords:
            if not isinstance(kw, str):
                continue
            needle = _normalize(kw)
            if needle and needle in hay:
                matched.append(tool_name)
                break

    # stable order, no dups
    seen = set()
    out = []
    for t in matched:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out

def _multi_allowed(tools: list[str], prefs: dict) -> bool:
    tools_cfg = prefs.get("tools") or {}
    ok = True
    for t in tools:
        cfg = tools_cfg.get(t) or {}
        if not isinstance(cfg, dict) or not cfg.get("multi", False):
            ok = False
            break
    return ok

def _enqueue_tool_items(tools: list[str], confirm_token: str) -> tuple[bool, str]:
    """
    Append kind:tool items into agent_state.yaml queue.
    Returns (ok, message).
    """
    p = _agent_state_path()
    state = _safe_load_yaml(p)
    if not state:
        return (False, f"No agent state found at {p}. Run: orion tools agent init")

    q = state.get("queue") or []
    if not isinstance(q, list):
        q = []

    now = _utc_now_iso()
    added = 0
    for tool in tools:
        policy = _load_agent_tools_policy()

        for tool in tools:
            tool_policy = policy.get(tool) or {}
            required_confirm = tool_policy.get("confirm", "")
            item = {
                "kind": "tool",
                "tool": tool,
                "args": [],
                "confirm": required_confirm,
                "enqueued_at": now,
            }
        q.append(item)
        added += 1

    state["queue"] = q
    state["updated_at"] = now
    state["status"] = "idle"
    state.setdefault("history", []).append({"at": now, "event": "enqueue_tools", "tools": tools})
    # also clear any pending proposal stored in file (harmless extra key)
    state.pop("pending_tools", None)

    _safe_save_yaml(p, state)
    return (True, f"Enqueued {added} tool job(s) to {p}.")

def _router_note_proposal(tools: list[str], prefs: dict) -> str:
    token = (prefs.get("agent") or {}).get("confirm_token", "CONFIRM SNAPSHOT")
    tools_list = ", ".join(tools)
    return (
        "[AGENT_ROUTER]\n"
        f"Matched tool candidates: {tools_list}\n"
        "Do NOT run tools yet. Propose the job(s) briefly, then ask the user to reply with the confirm token to enqueue.\n"
        f"Confirm token: {token}\n"
        "[/AGENT_ROUTER]\n"
    )

def _router_note_disambiguate(tools: list[str]) -> str:
    tools_list = ", ".join(tools)
    return (
        "[AGENT_ROUTER]\n"
        f"Multiple tools matched but not all are multi-allowed: {tools_list}\n"
        "Ask the user which tool they mean (choose one), then request the confirm token to enqueue.\n"
        "[/AGENT_ROUTER]\n"
    )

def _load_agent_tools_policy() -> dict:
    path = USER_ORION_DIR / "data" / "agent_tools.yaml"
    data = _safe_load_yaml(path)
    return data if isinstance(data, dict) else {}

def recall_keepsakes_fts(query: str, top_k: int = 3):
    keepsake_coll = "orion_keepsakes"
    db_path = r"C:\Orion\text-generation-webui\user_data\orion\chromadb\chroma.sqlite3"

    q = (query or "").strip()
    if not q:
        return []

    # ✅ sanitize for FTS5: keep only alnum/underscore tokens
    tokens = re.findall(r"[A-Za-z0-9_]+", q)
    if not tokens:
        return []

    # Prefer longer, distinctive tokens first
    tokens = sorted(set(tokens), key=len, reverse=True)

    # Build a safe MATCH query like: token1 OR token2 OR token3
    safe = " OR ".join(tokens[:5])

    sql = """
    select f.string_value
    from embedding_fulltext_search f
    join embeddings e on e.id=f.rowid
    join segments s on s.id=e.segment_id
    join collections c on c.id=s.collection
    where c.name=? and f.string_value match ?
    order by e.id desc
    limit ?
    """

    logger.warning(f"[orion_ltm] keepsake FTS db={db_path} coll={keepsake_coll}")
    
    con = sqlite3.connect(db_path)
    try:
        cur = con.cursor()
        pool = max(50, top_k * 20)
        rows = cur.execute(sql, (keepsake_coll, safe, pool)).fetchall()
        logger.warning(f"[orion_ltm] keepsake FTS hits={len(rows)} pool={pool}")
    finally:
        con.close()

    texts = [r[0] for r in rows if r and r[0]]

    # ✅ Keep only canonical keepsake entries (the ones you authored)
    # This drops the “Oh, the Christmas portrait!” junk that got ingested later.
    texts = [t for t in texts if t.lstrip().startswith("Handle:")]

    # ✅ Optional: prefer your specific canonical handle if present
    texts.sort(key=lambda t: ("Handle: CHRISTMAS_PORTRAIT_2025" not in t))

    return texts[:top_k]
    
    
def get_relevant_ltm(query, *args, **kwargs):
    """
    CNS 4.0-compatible replacement for the old orion_cli.shared.memory.get_relevant_ltm.

    Signature is intentionally loose so it can accept legacy positional
    args like (query, persona_collection, episodic_collection, ...).
    Collections are ignored; memory_core manages them internally.
    """
    # Read top-k either from kwargs or legacy CONFIG dict
    ltm_cfg = CONFIG.get("ltm", {}) if isinstance(CONFIG, dict) else {}
    topk_persona = int(kwargs.get("topk_persona", ltm_cfg.get("topk_persona", 5)))
    topk_semantic = int(kwargs.get("topk_semantic", ltm_cfg.get("topk_semantic", 6)))
    topk_episodic = int(kwargs.get("topk_episodic", ltm_cfg.get("topk_episodic", 10)))
    return_debug = bool(kwargs.get("return_debug", False))

    # --- Persona recall ---
    try:
        persona_docs = recall_persona(query, top_k=topk_persona) or []
    except Exception as e:
        logger.warning(f"[orion_ltm] persona recall failed: {e}")
        persona_docs = []

    # --- Semantic recall ---
    try:
        semantic_docs = recall_semantic(query, top_k=topk_semantic) or []
    except Exception as e:
        logger.warning(f"[orion_ltm] semantic recall failed: {e}")
        semantic_docs = []

    # --- Episodic recall ---
    try:
        episodic_docs = recall_episodic(query, top_k=topk_episodic) or []
    except Exception as e:
        logger.warning(f"[orion_ltm] episodic recall failed: {e}")
        episodic_docs = []

    # Build the text block we’ll prepend to the user input
    blocks = []

    if persona_docs:
        blocks.append(
            "### Relevant Persona Memory\n"
            + "\n".join(f"- {d}" for d in persona_docs if d)
        )

    if semantic_docs:
        blocks.append(
            "### Relevant Semantic Memory\n"
            + "\n".join(f"- {d}" for d in semantic_docs if d)
        )

    # Keepsakes (deterministic FTS recall)
    try:
        keepsake_docs = recall_keepsakes_fts(query, top_k=min(3, topk_episodic)) or []
    except Exception as e:
        logger.warning(f"[orion_ltm] keepsake FTS recall failed: {e}")
        keepsake_docs = []

    # Force keepsakes into episodic so they show up in the existing episodic logging/injection
    if keepsake_docs:
        episodic_docs = keepsake_docs + (episodic_docs or [])

    if episodic_docs:
        blocks.append(
            "### Relevant Episodic Memory\n"
            + "\n".join(f"- {d}" for d in episodic_docs if d)
        )

    memory_text = "\n\n".join(blocks).strip()

    if not return_debug:
        # Old behavior: just the text
        return memory_text

    # Newer behavior: return text + debug payload
    dbg = {
        "persona": [{"doc": d} for d in persona_docs],
        "semantic": [{"doc": d} for d in semantic_docs],
        "episodic": [{"doc": d} for d in episodic_docs],
    }
    return memory_text, dbg


# ---------------------------------------------------------------------------
# Evidence gate: prevents confident fabrication when the user asks for quotes
# ---------------------------------------------------------------------------
_LAST_EVIDENCE_GATE = {"must_refuse": False, "term": "", "reason": ""}

def _needs_memory_quote(q: str) -> bool:
    ql = (q or "").lower()
    return ("quote" in ql or "verbatim" in ql) and ("episodic" in ql or "memory" in ql)

def _extract_requested_term(q: str):
    """Best-effort: pull the entity the user asked to be mentioned/quoted."""
    if not q:
        return None
    # backticked token wins
    m = re.search(r"`([^`]{2,64})`", q)
    if m:
        return m.group(1).strip()
    # phrases like: mentions Japan / mention Japan
    m = re.search(r"mention(?:s|ed)?\s+([A-Za-z0-9][A-Za-z0-9_\- ]{1,48})", q, flags=re.IGNORECASE)
    if m:
        return m.group(1).strip().strip('"\'')
    # fallback: common proper noun pattern (single capitalized word)
    m = re.search(r"\b([A-Z][a-z]{2,})\b", q)
    if m:
        return m.group(1).strip()
    return None
def _debug(msg: str):
    """Print debug logs only if enabled in config."""
    try:
        cfg = get_config()
        if cfg.get("debug", {}).get("enabled"):
            logger.info(f"[DEBUG] {msg}")
    except Exception:
        pass


def load_ltm_config():
    config_path = (
        Path(__file__).resolve().parent / "orion_cli" / "data" / "ltm_config.yaml"
    )
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
            return cfg.get("ltm", {})
    except Exception as e:
        print(f"[LTM] Failed to load config: {e}")
        return {}


def estimate_tone_and_tags(text: str) -> dict:
    # You can replace this with GPT or sentiment model later
    tone = "neutral"
    tags = ["memory", "pooled"]
    if any(word in text.lower() for word in ["regret", "sad", "lonely"]):
        tone = "somber"
    elif any(word in text.lower() for word in ["courage", "fight", "will"]):
        tone = "defiant"
    elif any(word in text.lower() for word in ["beauty", "soul", "stars"]):
        tone = "poetic"
    return {
        "tone": tone,
        "tags": ",".join(tags),
        "importance": 0.7,
    }


def setup():
    """Initialize ChromaDB collections for persona and episodic memory."""
    global _EMBED_READY, _persona, _episodic

    try:
        # Use the CNS 4.0 shim to get bound collections
        _persona, _episodic = initialize_chromadb_for_ltm()

        _EMBED_READY = True
        logger.info(
            "[orion_ltm] ✅ setup() completed: episodic and persona initialized."
        )
        logger.debug(
            "[orion_ltm] LTM collections and shared memory hooks loaded successfully."
        )
    except Exception as e:
        logger.error(f"[orion_ltm] ❌ setup() failed: {e}")


# ============================================================
# Hook: Inject LTM Recall into user prompt before model sees it
# ============================================================

def _orion_build_runtime_input(*args, **kwargs):
    """
    TGWUI hook: runs before the model sees the user message.
    This is where we run recall() and prepend memory hits.

    We accept *args, **kwargs to be robust against different
    TGWUI extension calling conventions.
    """

    # Extract text + state safely from args/kwargs
    text = args[0] if len(args) >= 1 else ""
    state = args[1] if len(args) >= 2 and isinstance(args[1], dict) else kwargs.get("state", {})

    if not isinstance(text, str):
        text = str(text)

    # ---------------- Agent Router: confirm-gated enqueue ----------------
    try:
        prefs = _load_agent_prefs()
        agent_cfg = prefs.get("agent") or {}
        confirm_token = str(agent_cfg.get("confirm_token") or "CONFIRM SNAPSHOT")

        # If user sent confirm token, enqueue the pending proposal
        if confirm_token and confirm_token.lower() in (text or "").lower():
            pending = None
            if isinstance(state, dict):
                pending = state.get(_AGENT_PENDING_KEY)
            if not pending:
                # fallback: see if file holds pending_tools
                file_state = _safe_load_yaml(_agent_state_path())
                pending = file_state.get("pending_tools") if isinstance(file_state, dict) else None

            if isinstance(pending, list) and pending:
                ok, msg = _enqueue_tool_items([str(x) for x in pending], confirm_token)
                if isinstance(state, dict):
                    state[_AGENT_PENDING_KEY] = []
                file_state = _safe_load_yaml(_agent_state_path())
                if isinstance(file_state, dict) and file_state:
                    file_state["pending_tools"] = []
                    file_state["updated_at"] = _utc_now_iso()
                    _safe_save_yaml(_agent_state_path(), file_state)
                # Return router-only instruction; do NOT include user's confirm text
                return (
                    "[AGENT_ROUTER]\n"
                    f"{msg}\n"
                    "IMPORTANT: Do not claim you ran any tool. Tools only run when the user executes `orion tools agent tick` in the terminal.\n"
                    "Respond ONLY with: 'Queued. Run `orion tools agent tick` to execute one step.'\n"
                    "[/AGENT_ROUTER]\n"
                )

        # Otherwise: match and propose
        matched = _match_tools(text, prefs)
        if matched:
            if _multi_allowed(matched, prefs):
                if isinstance(state, dict):
                    state[_AGENT_PENDING_KEY] = matched
                # also store pending in file so a browser refresh doesn't lose it
                p = _agent_state_path()
                file_state = _safe_load_yaml(p)
                if not isinstance(file_state, dict) or not file_state:
                    # Create minimal state if file is empty/unreadable
                    file_state = {"queue": [], "history": [], "status": "idle"}
                file_state["pending_tools"] = matched
                file_state["updated_at"] = _utc_now_iso()
                _safe_save_yaml(p, file_state)

                text = _router_note_proposal(matched, prefs) + "\n" + text
            else:
                if isinstance(state, dict):
                    state[_AGENT_PENDING_KEY] = matched
                text = _router_note_disambiguate(matched) + "\n" + text

    except Exception as e:
        logger.error(f"[orion_ltm] agent router failed: {e}")
    # --------------------------------------------------------------------

    # If the embedding system isn't ready, return unchanged
    # ---------------- CNS 4.2 routed recall ----------------
    if _orion_cns42_enabled():
        return _orion_cns42_input_prompt(text)
    # --------------------------------------------------------------------

    if not _EMBED_READY or _persona is None or _episodic is None:
        return text

    try:
        # Preferred path: new API with return_debug
        try:
            memory_text, dbg = get_relevant_ltm(
                text,
                _persona,
                _episodic,
                topk_persona=int(CONFIG.get("ltm", {}).get("topk_persona", 5)),
                topk_episodic=int(CONFIG.get("ltm", {}).get("topk_episodic", 10)),
                return_debug=True,
            )
        except TypeError:
            # Fallback for older versions: no return_debug supported
            memory_text = get_relevant_ltm(text, _persona, _episodic)
            dbg = {}

    except Exception as e:
        logger.error(f"[orion_ltm] recall hook failed: {e}")
        return text

    if not memory_text:
        return text

    # Debug print if enabled via config.yaml
    debug_cfg = CONFIG.get("debug", {})
    if debug_cfg.get("enabled") and debug_cfg.get("show_recall"):
        logger.debug("=== Orion LTM Recall Snapshot ===")

        persona_hits = dbg.get("persona") or []
        semantic_hits = dbg.get("semantic") or []
        episodic_hits = dbg.get("episodic") or []

        if persona_hits:
            logger.debug("--- Persona Recall ---")
            for i, item in enumerate(persona_hits[:3]):
                doc = (item.get("doc") or "")[:200]
                logger.debug(f"[{i}] {doc}...")

        if semantic_hits:
            logger.debug("--- Semantic Recall ---")
            for i, item in enumerate(semantic_hits[:3]):
                doc = (item.get("doc") or "")[:200]
                logger.debug(f"[{i}] {doc}...")

        if episodic_hits:
            logger.debug("--- Episodic Recall ---")
            for i, item in enumerate(episodic_hits[:3]):
                doc = (item.get("doc") or "")[:200]
                logger.debug(f"[{i}] {doc}...")
        if not persona_hits and not episodic_hits:
            # At least show the raw memory_text if debug is on
            logger.debug("(no structured hits; raw memory text)")
            logger.debug(memory_text[:400])

        logger.debug("==========================")

    # Prepend memory to user prompt
    # Evidence gate: if the user demands a quote from episodic memory about a term,
    # refuse fabrication when that term is not present in recalled episodic docs.
    global _LAST_EVIDENCE_GATE
    try:
        if _needs_memory_quote(text):
            _LAST_EVIDENCE_GATE = {"must_refuse": False, "term": "", "reason": ""}
            term = _extract_requested_term(text)
            if term:
                term_l = term.lower()
                episodic_hits = (dbg.get("episodic") or []) if isinstance(dbg, dict) else []
                found = any(term_l in (item.get("doc") or "").lower() for item in episodic_hits if isinstance(item, dict))
                if not found:
                    _LAST_EVIDENCE_GATE = {
                        "must_refuse": True,
                        "term": term,
                        "reason": f'No recalled episodic snippet contains "{term}".',
                    }
                    logger.debug(f"Evidence gate armed for term={term!r} (no supporting episodic snippet).")
    except Exception as e:
        logger.debug(f"Evidence gate check failed: {e}")
    return memory_text + "\n\n" + text



# ============================================================
# TGWUI prompt-boundary hooks
# ============================================================
# Keep the user-authored turn clean in TGWUI history. CNS recall, factual
# guidance, and router instructions are assembled only while building the
# model prompt. This makes exported chat logs portable and prevents injected
# scaffolding from accumulating in future context.
_ORION_RUNTIME_PROMPT_CACHE = {}
_ORION_RUNTIME_PROMPT_CACHE_LIMIT = 64


def _orion_runtime_prompt_cache_key(text: str, state: dict, kwargs: dict) -> tuple:
    history_data = kwargs.get("history")
    if not isinstance(history_data, dict) and isinstance(state, dict):
        history_data = state.get("history", {})
    if not isinstance(history_data, dict):
        history_data = {}

    rows = history_data.get("internal", [])
    if not isinstance(rows, list):
        rows = []

    if kwargs.get("_continue", False):
        row_index = max(0, len(rows) - 1)
    else:
        # Normal send and regenerate both pass history without the current row.
        row_index = len(rows)

    unique_id = state.get("unique_id", "") if isinstance(state, dict) else ""
    return (str(unique_id), int(row_index), text)


def _orion_get_runtime_prompt_input(text: str, state: dict, kwargs: dict) -> str:
    global _LAST_CNS42_FACTUAL_EMPTY, _LAST_EVIDENCE_GATE

    key = _orion_runtime_prompt_cache_key(text, state, kwargs)
    cached = _ORION_RUNTIME_PROMPT_CACHE.get(key)
    if isinstance(cached, dict):
        _LAST_CNS42_FACTUAL_EMPTY = bool(cached.get("factual_empty", False))
        gate = cached.get("evidence_gate")
        if isinstance(gate, dict):
            _LAST_EVIDENCE_GATE = dict(gate)
        return str(cached.get("enriched", text))

    enriched = _orion_build_runtime_input(text, state)
    entry = {
        "enriched": enriched,
        "factual_empty": bool(_LAST_CNS42_FACTUAL_EMPTY),
        "evidence_gate": dict(_LAST_EVIDENCE_GATE)
        if isinstance(_LAST_EVIDENCE_GATE, dict)
        else {},
    }
    _ORION_RUNTIME_PROMPT_CACHE[key] = entry

    while len(_ORION_RUNTIME_PROMPT_CACHE) > _ORION_RUNTIME_PROMPT_CACHE_LIMIT:
        oldest_key = next(iter(_ORION_RUNTIME_PROMPT_CACHE))
        _ORION_RUNTIME_PROMPT_CACHE.pop(oldest_key, None)

    return enriched


def input_modifier(*args, **kwargs):
    """Keep TGWUI's stored internal user turn identical to John's input."""
    text = args[0] if len(args) >= 1 else ""
    return text if isinstance(text, str) else str(text)


def custom_generate_chat_prompt(text, state, **kwargs):
    """
    Build the normal TGWUI chat prompt with Orion's runtime-only CNS context.

    The enriched form is passed to the model but never written into
    history["internal"]. TGWUI core remains untouched.
    """
    raw_text = text if isinstance(text, str) else str(text)
    safe_state = state if isinstance(state, dict) else {}
    enriched_text = _orion_get_runtime_prompt_input(raw_text, safe_state, kwargs)

    if kwargs.get("_continue", False):
        history_data = kwargs.get("history", safe_state.get("history", {}))
        prompt_history = copy.deepcopy(history_data)
        rows = prompt_history.get("internal", []) if isinstance(prompt_history, dict) else []
        if isinstance(rows, list) and rows:
            row = rows[-1]
            if isinstance(row, list) and row:
                row[0] = enriched_text

        prompt_kwargs = dict(kwargs)
        prompt_kwargs["history"] = prompt_history
        return chat.generate_chat_prompt("", safe_state, **prompt_kwargs)

    return chat.generate_chat_prompt(enriched_text, safe_state, **kwargs)


def _orion_latest_runtime_slice(prompt: str) -> str:
    """Return only the newest Orion CNS/current-message block from a prompt."""
    if not prompt:
        return ""

    current_idx = prompt.rfind("[CURRENT_MESSAGE_FROM_JOHN]")
    if current_idx == -1:
        return prompt[-5000:]

    memory_idx = prompt.rfind("[ORION_CNS_MEMORY]", 0, current_idx)
    if memory_idx == -1:
        memory_idx = max(0, current_idx - 4000)

    return prompt[memory_idx:]


def _orion_should_hard_block_generation(prompt: str) -> bool:
    latest = _orion_latest_runtime_slice(prompt)
    if not latest:
        return False

    empty_markers = (
        "FACTUAL_MEMORY_EMPTY:",
        "No retrieved baseline CNS memory explicitly answers John's factual question.",
    )
    return any(marker in latest for marker in empty_markers)


def _orion_delegate_generate_reply(
    question,
    original_question,
    state,
    stopping_strings=None,
    is_chat=False,
):
    """Delegate to TGWUI's normal backend after Orion's pre-generation gate."""
    model_class = shared.model.__class__.__name__ if shared.model is not None else ""

    if model_class in {"LlamaServer", "Exllamav3Model", "TensorRTLLMModel"}:
        yield from generate_reply_custom(
            question,
            original_question,
            state,
            stopping_strings,
            is_chat=is_chat,
        )
    else:
        yield from generate_reply_HF(
            question,
            original_question,
            state,
            stopping_strings,
            is_chat=is_chat,
        )


def custom_generate_reply(
    question,
    original_question,
    state,
    stopping_strings=None,
    is_chat=False,
):
    """
    Block factual-empty hallucinations before generation and scrub any leaked
    Orion prompt scaffolding before TGWUI stores the assistant's internal reply.
    """
    if is_chat and _orion_should_hard_block_generation(question):
        logger.warning("[orion_ltm] CNS 4.2 hard-blocked factual-empty generation.")
        yield CNS42_FACTUAL_EMPTY_REPLY
        return

    for chunk in _orion_delegate_generate_reply(
        question,
        original_question,
        state,
        stopping_strings,
        is_chat=is_chat,
    ):
        cleaned, leak_found, leak_marker = _orion_scrub_generated_output(chunk)
        yield cleaned
        if leak_found:
            logger.warning(
                "[orion_ltm] Prompt leakage stopped before internal-history storage: "
                f"{leak_marker}"
            )
            return


# === CNS 4.2 output/storage leak scrubber ===
_ORION_INTERNAL_OUTPUT_MARKERS = (
    "\nJohn: [ORION_CNS_MEMORY]",
    "\nJohn:\n[ORION_CNS_MEMORY]",
    "\nUser: [ORION_CNS_MEMORY]",
    "\nUser:\n[ORION_CNS_MEMORY]",
    "\n[ORION_CNS_MEMORY]",
    "\n[/ORION_CNS_MEMORY]",
    "\n[CNS42_",
    "\n[ORION_RELATIONAL_MEMORY]",
    "\n[/ORION_RELATIONAL_MEMORY]",
    "\n[ORION_VOICE_GUIDANCE]",
    "\n[/ORION_VOICE_GUIDANCE]",
    "\n[CURRENT_MESSAGE_FROM_JOHN]",
    "\n[/CURRENT_MESSAGE_FROM_JOHN]",
    "\nFACTUAL_MEMORY_EMPTY:",
    "\nFACTUAL RULE:",
    "\n<|BEGIN-VISIBLE-CHAT|>",
)


def _orion_scrub_generated_output(value) -> tuple[str, bool, str]:
    # Remove leaked internal prompt/transcript scaffolding from generated output.
    text = value if isinstance(value, str) else str(value or "")
    if not text:
        return "", False, ""

    earliest = None
    matched = ""

    for marker in _ORION_INTERNAL_OUTPUT_MARKERS:
        idx = text.find(marker)
        if idx != -1 and (earliest is None or idx < earliest):
            earliest = idx
            matched = marker.strip()

    patterns = (
        r"\n(?:John|User)\s*:\s*\[ORION_CNS_MEMORY\]",
        r"\n\s*\[ORION_CNS_MEMORY\]",
        r"\n\s*\[CNS42_[A-Z_]+_MEMORY\]",
        r"\n\s*\[ORION_VOICE_GUIDANCE\]",
        r"\n\s*\[CURRENT_MESSAGE_FROM_JOHN\]",
    )

    for pattern in patterns:
        m = re.search(pattern, text)
        if m and (earliest is None or m.start() < earliest):
            earliest = m.start()
            matched = pattern

    if earliest is None:
        return text, False, ""

    cleaned = text[:earliest].rstrip()

    if not cleaned:
        cleaned = (
            "I’m sorry, John. My internal prompt started leaking into the reply, "
            "so I stopped it before displaying or remembering it."
        )

    return cleaned, True, matched

def output_modifier(*args, **kwargs):
    """
    Persist assistant replies as episodic memory (best-effort).

    Called on model outputs; we use it to feed Orion's episodic memory.
    We accept *args, **kwargs so we don't depend on a specific TGWUI
    calling convention.
    """
    text = args[0] if len(args) >= 1 else ""
    state = args[1] if len(args) >= 2 and isinstance(args[1], dict) else kwargs.get("state", {})

    try:
        text, leak_found, leak_marker = _orion_scrub_generated_output(text)
        if leak_found:
            logger.warning(
                f"[orion_ltm] Prompt/output leakage scrubbed before display and storage: {leak_marker}"
            )
        reply = (text or "").strip()
        global _LAST_CNS42_FACTUAL_EMPTY
        if _LAST_CNS42_FACTUAL_EMPTY:
            _LAST_CNS42_FACTUAL_EMPTY = False
            return CNS42_FACTUAL_EMPTY_REPLY
        # Evidence gate enforcement: if we asked for a memory quote about a term
        # and recall didn't contain it, force an honest "don't recall" response.
        global _LAST_EVIDENCE_GATE
        try:
            if isinstance(_LAST_EVIDENCE_GATE, dict) and _LAST_EVIDENCE_GATE.get("must_refuse"):
                term = _LAST_EVIDENCE_GATE.get("term") or "that"
                reply = (
                    f"I don’t recall a line in my episodic memory that mentions {term}. "
                    "I may be mistaken — if you remind me what we said, I can store it going forward."
                )
                text = reply
                logger.debug(f"Evidence gate enforced (term={term!r}); replacing assistant reply.")
        finally:
            # One-shot gate: clear after use so it doesn't affect later turns
            _LAST_EVIDENCE_GATE = {"must_refuse": False, "term": "", "reason": ""}
        if not reply or len(reply.split()) < 10 or _episodic is None:
            return text

        last_user = ""
        if isinstance(state, dict):
            last_user = (state.get("context") or "").strip()

        # CNS 4.0: uses internal episodic binding; no positional collection arg
        on_assistant_turn(reply, last_user_input=last_user)

    except Exception as e:
        logger.error(f"[orion_ltm] output_modifier failed: {e}")

    return text


# ------------------------------------------------------------
# Setup runs when the extension loads
# ------------------------------------------------------------
try:
    setup()
except Exception as e:
    logger.error(f"[orion_ltm] Setup failed during extension load: {e}")


def teardown():
    """Optional cleanup hook."""
    global _INITIALIZED
    if _INITIALIZED:
        _debug("Tearing down LTM collections (no persistence affected).")
        _INITIALIZED = False


def before_chat_input(text):
    """Handle user input before chat generation (store to episodic)."""
    try:
        if _episodic:
            from orion_cli.shared.memory import on_user_turn

            # CNS 4.0: episodic collection is handled internally
            on_user_turn(text)
            _debug("User input stored to episodic memory.")
        else:
            _debug("Episodic collection not available at input time.")
    except Exception as e:
        logger.warning(f"[orion_ltm] Failed to process user input: {e}")


def after_chat_output(reply, last_user_input=None):
    """Handle assistant output after generation (store to episodic)."""
    try:
        if _episodic:
            from orion_cli.shared.memory import on_assistant_turn

            # CNS 4.0: no positional episodic argument
            on_assistant_turn(reply, last_user_input=last_user_input)
            _debug("Assistant reply stored to episodic memory.")
        else:
            _debug("Episodic collection not available at output time.")
    except Exception as e:
        logger.warning(f"[orion_ltm] Failed to store assistant turn: {e}")


def _inject_ltm_into_state_sys_prompt(state, text=None):
    if not (
        _EMBED_READY
        and get_relevant_ltm
        and _persona
        and _episodic
        and isinstance(state, dict)
    ):
        return state

    query = (state.get("context") or "").strip()
    if not query:
        return state

    # Store the original user turn into episodic memory
    try:
        on_user_turn(query, _episodic)
    except Exception:
        logger.debug("[orion_ltm] Failed to store user turn to episodic memory")

    try:
        cfg = get_config()
        rig = float(getattr(cfg.persona, "rigidity", 0.6))
    except Exception:
        rig = 0.6
    # clamp 0..1
    if rig < 0.0:
        rig = 0.0
    elif rig > 1.0:
        rig = 1.0

    base_topk_persona = int(state.get("orion_topk_persona", 5))
    topk_persona_eff = int(round(base_topk_persona * rig))
    if topk_persona_eff < 0:
        topk_persona_eff = 0
    if topk_persona_eff > base_topk_persona:
        topk_persona_eff = base_topk_persona

    try:
        memory_text, dbg = get_relevant_ltm(
            query,
            _persona,
            _episodic,
            topk_persona=topk_persona_eff,
            topk_episodic=int(state.get("orion_topk_episodic", 10)),
            return_debug=True,
            importance_threshold=0.6,  # 🔧 STRONGER FILTERING
        )
    except Exception as e:
        logger.debug(f"[orion_ltm] get_relevant_ltm failed: {e}")
        return state

    if not memory_text:
        return state

    # Inject structured LTM into prompt
    sys_prompt = (state.get("system_prompt") or "").strip()

    structured_memory = []
    if "persona_hits" in dbg and dbg["persona_hits"]:
        structured_memory.append("### [PERSONA MEMORY]")
        structured_memory.append(
            "\n".join(
                f"- {line}"
                for line in memory_text.split("\n")
                if line.startswith("[PERSONA]")
            )
        )

    if "episodic_hits" in dbg and dbg["episodic_hits"]:
        structured_memory.append("### [EPISODIC MEMORY]")
        structured_memory.append(
            "\n".join(
                f"- {line}"
                for line in memory_text.split("\n")
                if line.startswith("[EPISODIC]")
            )
        )

EXTENSION = {
    "input": input_modifier,
    "output": output_modifier,
    "custom_generate_chat_prompt": custom_generate_chat_prompt,
    "custom_generate_reply": custom_generate_reply,
}

try:
    setup()
except Exception as e:
    logger.error(f"[orion_ltm] Setup failed during extension load: {e}")