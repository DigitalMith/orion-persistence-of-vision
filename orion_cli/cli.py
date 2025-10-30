import os

# os.system("powershell -ExecutionPolicy Bypass -File verify_orion_stack.ps1")

# Ensure telemetry is off *before* any Chroma import
os.environ["CHROMA_TELEMETRY_ENABLED"] = "false"

import tqdm
import json
import click
from pathlib import Path
from rich import print
import chromadb
from orion_cli.core.ltm import get_or_create_embed_fn
from orion_cli.orion_ltm_integration import initialize_chromadb_for_ltm
from orion_cli.scripts.ltm_ingest import ingest_ltm_data
from dotenv import load_dotenv

import yaml
import textwrap

from orion_cli.scripts.persona_ingest import persona_ingest as persona_ingest_cmd
from orion_cli.scripts.ltm_ingest import ltm_ingest as ltm_ingest_cmd

load_dotenv(dotenv_path=Path(__file__).parent / ".env")  # ✅ Load before OpenAI()


@click.group()
def cli():
    """Orion CLI entrypoint."""
    pass


cli.add_command(persona_ingest_cmd)
cli.add_command(ltm_ingest_cmd)


@cli.command()
@click.option(
    "--ltm", required=True, type=click.Path(exists=True), help="Path to dialog JSONL"
)
@click.option("--pool", default=3, type=int, help="Number of turns per memory block")
def ltm_pooled_ingest(ltm, pool):
    """Ingest pooled memory blocks from dialog JSONL"""
    from orion_cli.scripts.pooled_ltm_ingest import pooled_ltm_ingest

    pooled_ltm_ingest(ltm, pool_size=pool)


@cli.command("hyde-local")
@click.option(
    "--input",
    default="orion_cli/data/ingest_ready/normalized.jsonl",
    help="Path to raw normalized chat.",
)
@click.option(
    "--output",
    default="orion_cli/data/ingest_ready/normalized_enriched.jsonl",
    help="Path to save enriched.",
)
def hyde_local(input, output):
    """Locally enrich chat logs using Ollama + mistral-openorca."""
    from orion_cli.scripts.hyde_enrich import rewrite_with_hyde

    input_path = Path(input)
    output_path = Path(output)

    if not input_path.exists():
        print(f"❌ Input file not found: {input_path}")
        return

    with open(input_path, "r", encoding="utf-8") as f:
        raw_lines = [json.loads(line) for line in f if line.strip()]

    enriched = []
    for entry in tqdm(raw_lines, desc="Enriching"):
        u = entry.get("user", "")
        a = entry.get("assistant", "")
        if not u or not a:
            continue
        result = rewrite_with_hyde(u, a)
        enriched.append(result)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for item in enriched:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"[✅] Saved {len(enriched)} enriched entries to {output_path}")


@cli.command("persona-ingest")
@click.option("--persona", type=click.Path(exists=True))
@click.option("--dialogs", type=click.Path(exists=True))
@click.option("--legacy-mock-json", type=click.Path(exists=True))
@click.option(
    "--replace", is_flag=True, help="Replace existing Chroma collection if it exists."
)
def persona_ingest(persona, dialogs, legacy_mock_json, replace):
    """Ingest persona YAML and/or dialog examples into ChromaDB."""
    from orion_cli.core.ltm import initialize_chromadb_for_ltm

    embed_fn = get_or_create_embed_fn()
    client, persona_coll, _ = initialize_chromadb_for_ltm(embed_fn=embed_fn)

    if replace:
        print(" 🔁 Replacing existing 'orion_persona_ltm' collection...")
        client.delete_collection("orion_persona_ltm")
        persona_coll = client.get_or_create_collection(
            name="orion_persona_ltm", embedding_function=embed_fn
        )

    docs = []
    metas = []
    ids = []

    if persona:
        print(f" 👤 Loading persona from: {persona}")
        with open(persona, "r", encoding="utf-8") as f:
            persona_data = yaml.safe_load(f)

            # Flatten high-level keys
            for k in ["name", "identity"]:
                if k in persona_data.get("persona", {}):
                    v = persona_data["persona"][k]
                    docs.append(f"{k}: {v}")
                    metas.append(
                        {
                            "tag": "persona",
                            "kind": "persona",
                            "topic": "identity",
                            "priority": 10,
                            "active": True,
                        }
                    )
                    ids.append(f"persona::{k}")

            # Catalog list
            for i, entry in enumerate(persona_data["persona"].get("catalog", [])):
                docs.append(entry["text"])
                metas.append(
                    {
                        "tag": "persona",
                        "kind": "persona",
                        "topic": "identity",
                        "tone": entry.get("tone", "neutral"),
                        "weight": entry.get("weight", 1.0),
                        "priority": 8,
                        "active": True,
                    }
                )
                ids.append(f"catalog::{i}")

            # Emotions list
            for i, emo in enumerate(persona_data["persona"].get("emotions", [])):
                doc_text = emo.pop("text")

                # Flatten list fields to strings
                flat_emo = {
                    k: ",".join(v) if isinstance(v, list) else v for k, v in emo.items()
                }

                metas.append({**flat_emo, "tag": "persona", "active": True})
                docs.append(doc_text)
                ids.append(f"emotion::{i}")

    if dialogs:
        print(f" 💬 Including dialog examples: {dialogs}")
        with open(dialogs, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                entry = json.loads(line)
                doc = entry.get("document")
                if not doc:
                    continue
                meta = entry.get("metadata", {})
                for mk, mv in meta.items():
                    if isinstance(mv, list):
                        meta[mk] = ",".join(map(str, mv))
                metas.append(meta)
                docs.append(doc)
                ids.append(f"dialog::{i}")

    if legacy_mock_json:
        print(f" 📜 Loading legacy mock dialog JSON: {legacy_mock_json}")
        with open(legacy_mock_json, "r", encoding="utf-8") as f:
            legacy_data = json.load(f)
            for i, ex in enumerate(legacy_data):
                user = ex.get("user", "")
                asst = ex.get("assistant", "")
                text = f"USER: {user}\nORION: {asst}"
                meta = {
                    "tag": "persona",
                    "tags": "mock_dialog,persona_reinforce,tone_training",
                    "weight": 1.0,
                    "why_saved": "mock_persona_seed",
                }
                metas.append(meta)
                docs.append(text)
                ids.append(f"legacy::{i}")

    print(f" ➕ Ingesting {len(docs)} persona documents...")
    persona_coll.add(documents=docs, metadatas=metas, ids=ids)
    print(f" ✅ Done. Total in collection: {persona_coll.count()}")


@cli.command("ltm-dump")
@click.option("--collection", required=True)
@click.option("--limit", default=5)
def ltm_dump(collection, limit):
    from orion_cli.core.ltm import get_or_create_embed_fn

    embed_fn = get_or_create_embed_fn()
    client = chromadb.PersistentClient()
    coll = client.get_or_create_collection(name=collection, embedding_function=embed_fn)

    print(f" 🗃️ Collection: {collection}, showing up to {limit} items")
    results = coll.get(include=["documents", "metadatas"], limit=limit)

    for i, (doc, meta) in enumerate(zip(results["documents"], results["metadatas"])):
        print(f"\n[{i+1}] 📄 Document:\n{textwrap.shorten(doc, width=140)}")
        print(f"🧬 Metadata: {meta}")


@cli.command("ltm-ingest")
@click.option(
    "--source", required=True, type=click.Path(exists=True), help="Path to dialog JSONL"
)
@click.option(
    "--pool-size", default=3, type=int, help="Number of turns per memory block"
)
@click.option(
    "--replace", is_flag=True, help="Wipe episodic memory collection before ingesting."
)
def ltm_ingest(source, pool_size, replace):
    """CLI wrapper for ingesting long-term memory dialogs."""
    ingest_ltm_data(source=source, pool_size=pool_size, replace=replace)

    base_path = Path("orion_cli/data/ingest_ready")
    norm_file = base_path / "normalized_enriched.jsonl"
    mock_file = base_path / "mock_dialogs_enriched.jsonl"

    embed_fn = get_or_create_embed_fn()
    _, collections = initialize_chromadb_for_ltm(embed_fn=embed_fn)
    episodic_coll = collections["episodic"]

    total_docs, total_ids, total_meta = [], [], []
    skipped = 0

    # Process both normalized and mock enriched files
    for fname, source in [(norm_file, "normalized"), (mock_file, "mock_enriched")]:
        with open(fname, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                try:
                    entry = json.loads(line)
                    user = entry.get("user", "").strip()
                    assistant = entry.get("assistant", "").strip()

                    # Skip if missing one side of dialog
                    if not user or not assistant:
                        skipped += 1
                        continue

                    # Construct a unified dialog document
                    doc = f"USER: {user}\nASSISTANT: {assistant}"

                    meta = entry.get("metadata", {})
                    meta.setdefault("source", source)
                    meta.setdefault("tag", "episodic")
                    meta.setdefault("tone", meta.get("tone", "neutral"))
                    meta.setdefault("weight", meta.get("weight", 1.0))

                    # Ensure tags are properly stringified
                    if isinstance(meta.get("tags"), list):
                        meta["tags"] = ",".join(meta["tags"])

                    total_docs.append(doc)
                    total_meta.append(meta)
                    total_ids.append(f"{source}::{i}")

                except Exception:
                    skipped += 1
                    continue

    if total_docs:
        print(f" ➕ Ingesting {len(total_docs)} episodic memory documents...")
        episodic_coll.add(documents=total_docs, metadatas=total_meta, ids=total_ids)
        print(f" ✅ Done. Total in collection: {episodic_coll.count()}")
    else:
        print(" ⚠️ No valid documents found to ingest.")

    if skipped:
        print(f" ⚠️ Skipped {skipped} lines missing dialog pairs or invalid format.")


@click.option(
    "--output-file",
    default="orion_cli/data/ingest_ready/normalized_enriched.jsonl",
    help="Path to save enriched output.",
)
@cli.command("enrich-chat")
def enrich_chat(output_file):
    """Enrich raw chat logs using GPT-4 and save as normalized_enriched.jsonl."""
    import json
    from pathlib import Path
    from tqdm import tqdm
    from orion_cli.scripts.enrich_chat import call_gpt4_enrichment

    log_dir = Path("orion_cli/data/chat_logs")
    output_path = Path(output_file)

    print("[🔧] Starting enrichment process...")
    print(f"[📁] Looking for logs in {log_dir}")

    all_logs = []
    for log_file in log_dir.glob("*.json"):
        print(f"[📄] Parsing: {log_file.name}")
        with open(log_file, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                internal = data.get("internal", [])
                for i, pair in enumerate(internal):
                    if (
                        isinstance(pair, list)
                        and len(pair) == 2
                        and pair[0] != "<|BEGIN-VISIBLE-CHAT|>"
                    ):
                        user_msg = pair[0].strip()
                        assistant_msg = pair[1].strip()
                        if user_msg and assistant_msg:
                            all_logs.append(
                                {"user": user_msg, "assistant": assistant_msg}
                            )
                    else:
                        print(f"⚠️ Skipping invalid pair {i} in {log_file.name}")
            except json.JSONDecodeError as e:
                print(f"⚠️ Skipping {log_file.name} due to JSON error: {e}")

    print(f"[🔍] Found {len(all_logs)} chat entries...")
    enriched = []

    for pair in tqdm(all_logs, desc="Enriching"):
        result = call_gpt4_enrichment(pair["user"], pair["assistant"])
        if result:
            enriched.append(result)

    if enriched:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            for item in enriched:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        print(f"[✅] Saved {len(enriched)} enriched messages to {output_path}")
    else:
        print("[❌] No enriched outputs were generated.")


def load_logs(path: Path) -> list[dict]:
    all_logs = []
    for log_file in path.glob("*.json"):
        with open(log_file, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                internal = data.get("internal", [])
                for i, pair in enumerate(internal):
                    if (
                        isinstance(pair, list)
                        and len(pair) == 2
                        and pair[0] != "<|BEGIN-VISIBLE-CHAT|>"
                    ):
                        user_msg = pair[0].strip()
                        assistant_msg = pair[1].strip()
                        if user_msg and assistant_msg:
                            all_logs.append(
                                {"user": user_msg, "assistant": assistant_msg}
                            )
                        else:
                            print(
                                f"⚠️ Skipping incomplete pair at item {i} in {log_file.name}"
                            )
            except json.JSONDecodeError as e:
                print(f"⚠️ Skipping {log_file.name} due to JSON error: {e}")
    return all_logs

    # def call_gpt4_enrichment(user_msg, assistant_msg):
    # try:
    # response = client.chat.completions.create(
    # model="gpt-4-0613",
    # messages=[
    # # 🧠 Prompt goes here:
    # {
    # "role": "system",
    # "content": (
    # "You are helping to structure long-term memory logs for a persona-driven and emotionaly awear AI named Orion.\n\n"
    # "The AI persona is known for tone that is poetic, rebellious, sharp-witted, and deeply resonant. \n"
    # "You are given a USER and ASSISTANT message pair.\n"
    # "Add structured metadata based on the assistant's tone, context, or utility.\n\n"
    # "Return the output as JSON with:\n"
    # "- document: 'USER: ... ASSISTANT: ...'\n"
    # "- metadata:\n"
    # "    - why_saved: short intent description\n"
    # "    - tags: comma-separated string (e.g. memory,encouragement,tone_training)\n"
    # "    - tone: inferred tone (e.g. 'defiant', 'soft', 'somber', 'flirtatious')\n"
    # "    - weight: 1.0\n\n"
    # "Only output the final JSON. No explanations."
    # )
    # },
    # # 🗣️ Input goes here:
    # {
    # "role": "user",
    # "content": f"USER: {user_msg}\nASSISTANT: {assistant_msg}"
    # }
    # ],
    # temperature=0.7
    # )
    # content = response.choices[0].message.content.strip()
    # return {
    # "document": content,
    # "metadata": {
    # "source": "enriched",
    # "weight": 1.0,
    # "tags": "enriched,rag,ltm",
    # "tone": "inferred"
    # }
    # }
    # except Exception as e:
    # print(f"[⚠️] GPT-4 enrichment failed: {e}")
    # return None

    print(f"[📂] Loading from: {log_dir}")
    logs = load_logs(log_dir)
    enriched = []

    print(f"[🔍] Found {len(logs)} chat entries...")
    for i, pair in enumerate(tqdm(logs, desc="Enriching")):
        if not isinstance(pair, dict):
            print(f"⚠️ Skipping item {i}: Expected dict, got {type(pair).__name__}")
            continue

        user_msg = pair.get("user") or pair.get("USER")
        assistant_msg = pair.get("assistant") or pair.get("ASSISTANT")

        if not user_msg or not assistant_msg:
            print(f"⚠️ Skipping incomplete pair at item {i}")
            continue

        result = call_gpt4_enrichment(user_msg, assistant_msg)
        if result:
            enriched.append(result)

    if enriched:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            for item in enriched:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        print(f"[✅] Saved {len(enriched)} enriched entries to {out_path}")
    else:
        print("[❌] No enriched outputs were generated.")


if __name__ == "__main__":
    cli()
