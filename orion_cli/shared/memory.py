"""
Create shared/memory.py and move these definitions in:

  - initialize_chromadb_for_ltm()
  - on_user_turn()
  - on_assistant_turn()
  - add_documents_to_collection()

Replace all import paths like:
    from orion_cli.orion_ltm_integration import initialize_chromadb_for_ltm

with:
    from orion_cli.shared.memory import initialize_chromadb_for_ltm

Mark the old files (orion_ltm_integration.py, core/ltm.py) as thin compatibility wrappers:
    from orion_cli.shared.memory import *
    print("[deprecated] core.ltm → shared.memory")

Update extensions/orion_ltm/script.py to import only from shared.memory.
That prevents circular imports and keeps all state (like _episodic, _persona) in one predictable module.

⚙️ Why this works beautifully

  - One canonical definition for LTM, persona, embeddings, and recall.
  - Zero duplication.
  - No circular import risk.
  - Easier to test and hot-reload.
"""

from uuid import uuid4
from datetime import datetime


def on_user_turn(user_input: str, episodic_coll):
    print(f"[DEBUG] on_user_turn() loaded from {__file__}")
    """
    Store user input into episodic memory with full Chroma safety.
    Deduplicates normalized text and forces all metadata to string-safe types.
    """
    try:
        if not isinstance(user_input, str):
            print(
                f"[ltm] ⚠️ Non-string user input detected ({type(user_input)}), coercing to str."
            )
            user_input = str(user_input)

        user_clean = user_input.strip()
        if not user_clean or len(user_clean) < 2:
            print("[ltm] Skipped user input: empty or too short.")
            return

        norm = user_clean.lower()

        existing = episodic_coll.query(
            query_texts=[norm],
            n_results=3,
            include=["documents"],
        )

        for doc in existing.get("documents", [[]])[0]:
            if isinstance(doc, str) and doc.strip().lower() == norm:
                print("[ltm] Skipped duplicate user chunk.")
                return

        ts_iso = datetime.now().isoformat()
        doc_id = f"user_{uuid4().hex}"

        metadata = {
            "timestamp": ts_iso,
            "importance": 0.5,
            "source": "user",
            "dedup": True,
        }

        # ✅ Universal sanitizer (Ruff-safe and explicit)
        try:
            user_clean = (
                str(user_input).strip()
                if isinstance(user_input, str)
                else str(user_input)
            )
        except Exception:
            user_clean = "<invalid_user_input>"
            print("[ltm] ⚠️ user_clean fallback used — non-serializable input detected")

        # ✅ Safe add to Chroma
        documents = [user_clean]
        try:
            safe_add_to_chroma(
                episodic_coll,
                ids=[doc_id],
                documents=documents,
                metadatas=[metadata],
            )
        except Exception as e:
            print(f"[ltm] ❌ safe_add_to_chroma() failed: {e}")

    except Exception as e:
        print(f"[ltm] ❌ Failed to store user turn: {e}")


def on_assistant_turn(reply: str, episodic_coll, last_user_input: str = None):
    """
    Store an assistant reply into episodic memory.
    Ensures all metadata values are strings (Chroma safe).
    Includes deep type checks to catch non-string inputs from TGWUI.
    """
    try:
        import json
        import re
        from datetime import datetime
        from uuid import uuid4

        if not reply or not isinstance(reply, str):
            print(f"[ltm] ⚠️ Invalid reply type ({type(reply)}), coercing to str.")
            reply = str(reply or "")

        reply_clean = reply.strip()
        if not reply_clean or len(reply_clean) < 10:
            print("[ltm] Skipped assistant reply: empty or too short.")
            return

        if re.fullmatch(r"\[.*?\]", reply_clean):
            print("[ltm] Skipped assistant reply: formatting artifact only.")
            return

        print(f"[ltm] Candidate assistant reply: {reply_clean[:80]}...")

        ts_iso = datetime.now().isoformat()
        doc_id = f"assistant_{uuid4().hex}"

        metadata = {
            "timestamp": str(ts_iso),
            "importance": "0.7",
            "source": "assistant",
        }

        metadata = json.loads(json.dumps(metadata))

        # --- 🧩 Diagnostic Guard ---
        print("\n[ltm][DEBUG] ----- ADD() ARGUMENT TYPES -----")
        print(f"ids:        {type(doc_id)}  ->  {repr(doc_id)}")
        print(f"documents:  {type(reply_clean)}  ->  {repr(reply_clean)[:100]}")
        print(f"metadatas:  {type(metadata)}  ->  {repr(metadata)}")
        print(f"collection: {type(episodic_coll)}")
        print("[ltm][DEBUG] --------------------------------\n")
        # ---------------------------------------------

        episodic_coll.add(
            ids=[doc_id],
            documents=[reply_clean],
            metadatas=[metadata],
        )
        print("[ltm] ✅ Added assistant episodic memory chunk.")

        if last_user_input:
            try:
                from orion_cli.utils.ltm_utils import live_pooled_store

                live_pooled_store(last_user_input, reply_clean, episodic_coll)
            except Exception as e:
                print(f"[ltm] Live pooled ingestion failed: {e}")

    except Exception as e:
        import traceback

        print(f"[ltm] ❌ Failed to store assistant turn: {e}")
        traceback.print_exc()


# ============================================================
# 🧩 Universal Chroma-safe add helper
# Ensures all values are stringified before writing to Chroma
# ============================================================
def safe_add_to_chroma(collection, ids, documents, metadatas):
    """Safely add entries to Chroma, converting all values to string-safe formats."""
    import json
    import pprint

    pp = pprint.PrettyPrinter(indent=2, width=100)

    def stringify(obj):
        """Recursively convert all values to JSON-safe, string-safe formats."""
        if isinstance(obj, (int, float, bool)):
            return str(obj)
        if obj is None:
            return ""
        if isinstance(obj, (list, tuple, set)):
            return [stringify(x) for x in obj]
        if isinstance(obj, dict):
            return {str(k): stringify(v) for k, v in obj.items()}
        if not isinstance(obj, str):
            return str(obj)
        return obj

    try:
        # ✅ Defensive normalization
        ids = stringify(ids)
        documents = stringify(documents)
        metadatas = stringify(metadatas)

        # ✅ Ensure all are lists for ChromaDB
        if not all(isinstance(x, list) for x in [ids, documents, metadatas]):
            ids = [ids] if not isinstance(ids, list) else ids
            documents = [documents] if not isinstance(documents, list) else documents
            metadatas = [metadatas] if not isinstance(metadatas, list) else metadatas

        print("[ltm] 🧠 Preparing to add to ChromaDB...")
        print(
            f"[ltm]    type(ids): {type(ids)}, type(documents): {type(documents)}, type(metadatas): {type(metadatas)}"
        )
        print(
            f"[ltm]    meta[0] types: {[{k: type(v).__name__ for k, v in m.items()} for m in metadatas]}"
        )
        print("[ltm]    --- Raw Payload Snapshot ---")
        pp.pprint({"ids": ids, "documents": documents, "metadatas": metadatas})
        print("[ltm]    -----------------------------")

        # ✅ Finally, perform the add operation
        collection.add(ids=ids, documents=documents, metadatas=metadatas)
        print("[ltm] ✅ safe_add_to_chroma() success.")

    except Exception as e:
        print(f"[ltm] ❌ safe_add_to_chroma() failed: {e}")
        print(
            f"[ltm]    type(ids): {type(ids)}, type(documents): {type(documents)}, type(metadatas): {type(metadatas)}"
        )
        print("[ltm]    --- Failed Payload Snapshot ---")
        pp.pprint({"ids": ids, "documents": documents, "metadatas": metadatas})
        print("[ltm]    -----------------------------")

        # Check for mismatched list lengths
        if not (len(ids) == len(documents) == len(metadatas)):
            print(
                f"[ltm] ⚠️ Mismatched lengths: ids={len(ids)}, docs={len(documents)}, meta={len(metadatas)}"
            )
            min_len = min(len(ids), len(documents), len(metadatas))
            ids, documents, metadatas = (
                ids[:min_len],
                documents[:min_len],
                metadatas[:min_len],
            )

        # JSON roundtrip — ensures Chroma-safe data
        metadatas = json.loads(json.dumps(metadatas))

        # ✅ Convert metadatas to proper JSON-safe dicts before add
        metadatas = json.loads(json.dumps(metadatas))

        # --- Extra safety: wrap single-item strings into nested lists ---
        if all(isinstance(d, str) for d in documents):
            documents = [documents]
        if all(isinstance(i, str) for i in ids):
            ids = [ids]
        if all(isinstance(m, dict) for m in metadatas):
            metadatas = [metadatas]

        # --- Sanity check for matching lengths ---
        n = min(len(ids), len(documents), len(metadatas))
        ids, documents, metadatas = ids[:n], documents[:n], metadatas[:n]

        # ✅ Final add
        collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
        )
        print(f"[ltm] ✅ Added {n} document(s) safely to Chroma.")
        print(f"[ltm] ✅ Added episodic memory chunk ({len(ids)} entries).")

    except Exception as e:
        print(f"[ltm] ❌ safe_add_to_chroma() failed: {e}")
        print(
            f"[ltm]    type(ids): {type(ids)}, type(documents): {type(documents)}, type(metadatas): {type(metadatas)}"
        )
        if isinstance(metadatas, list):
            for i, m in enumerate(metadatas):
                print(
                    f"[ltm]    meta[{i}] types: {{k: type(v).__name__ for k, v in m.items()}}"
                )
        print("[ltm]    --- Raw Payload Snapshot ---")
        pp.pprint({"ids": ids, "documents": documents, "metadatas": metadatas})
        print("[ltm]    -----------------------------\n")
