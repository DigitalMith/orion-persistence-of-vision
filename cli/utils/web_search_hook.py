# cli/utils/web_search_hook.py

import sys
from pathlib import Path

# Add root path so 'lib' and 'cli' can be imported
ROOT_PATH = Path(__file__).resolve().parents[2]
if str(ROOT_PATH) not in sys.path:
    sys.path.insert(0, str(ROOT_PATH))

# Now it's safe to import modules using absolute paths
import os
import logging
import requests
from cli.data.web_config import WEB_CONFIG
from cli.lib.orion_guardrails import should_allow, save_memory_entry, log_event

from cli.scripts.web_search import web_search, chunk_text
from cli.lib.orion_ltm_integration import initialize_chromadb_for_ltm, on_user_turn

logger = logging.getLogger("web_search_hook")

def perform_web_search(prompt: str, source: str = "orion-web-query", tag: str = "web-search") -> bool:
    print(f"[DEBUG] perform_web_search called with tag={tag}, source={source}")

    conf = WEB_CONFIG.get("web_search", {})
    api_key = conf.get("api_key")
    provider = conf.get("provider", "serper")
    max_results = conf.get("max_results", 5)

    if provider != "serper":
        print(f"[🛑] Unsupported provider: {provider}")
        return False

    # Perform the search via Serper.dev
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
    payload = {"q": prompt, "num": max_results}
    response = requests.post("https://google.serper.dev/search", headers=headers, json=payload)

    if response.status_code != 200:
        print(f"[❌] Serper API error {response.status_code}: {response.text}")
        return False

    data = response.json()
    print(f"[DEBUG] Raw Serper response: {data}")

    # ✅ Extract results here
    results = data.get("organic", [])[:max_results]
    if not results:
        print("[❌] No search results found")
        return False

    snippets = [r.get("snippet", "") for r in results if r.get("snippet")]
    sources = [r.get("link", "") for r in results]

    combined_snippets = "\n\n".join(f"- {s}" for s in snippets if s)
    content = combined_snippets.strip() if combined_snippets else ""
    print(f"[DEBUG] Content length after search: {len(content)}")
    if content:
        print(f"[DEBUG] Preview content:\n{content[:300]}...\n")

    if not content:
        log_event("ingest_attempt", tag, source, "rejected", "Empty response")
        print("[❌] No content to save")
        return False

    allowed = should_allow(tag=tag, content=content, source=source)
    print(f"[DEBUG] should_allow returned {allowed}")

    if allowed:
        save_memory_entry(content, tag, source)
        log_event("ingest_attempt", tag, source, "saved")
        print("[✅] Saved memory entry successfully")
        return True
    else:
        log_event("ingest_attempt", tag, source, "rejected", "Guardrails")
        print("[⚠️] Guardrails rejected content")
        return False

def handle_web_search(user_input: str) -> bool:
    """
    Triggered when input contains "web search".
    - "to memory": Saves results to LTM
    - "for me": Opens in editor
    """
    if not WEB_CONFIG.get("save_to_ltm") and "to memory" in user_input.lower():
        print("[web_search_hook] LTM save disabled in config.")
        return False

    if "web search" not in user_input.lower():
        return False

    query = user_input
    for kw in ["web search", "for me", "to memory"]:
        query = query.lower().replace(kw, "")
    query = query.strip()

    if not query:
        print("⚠️ No search query found.")
        return True

    results = web_search(query)

    if not results:
        print("⚠️ No results returned.")
        return True

    # Optional: filter by allowed domains
    allowed = WEB_CONFIG.get("allowed_domains", [])
    if allowed:
        results = [r for r in results if any(domain in r["url"] for domain in allowed)]

    if not results:
        print("⚠️ No results matched allowed domains.")
        return True

    # === "for me" opens results in editor ===
    if "for me" in user_input.lower():
        from datetime import datetime
        file_path = f"web_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(file_path, "w", encoding="utf-8") as f:
            for r in results:
                f.write(f"{r['title']}\n{r['snippet']}\n{r['url']}\n\n")
        if platform.system() == "Windows":
            os.startfile(file_path)
        else:
            subprocess.call(["open", file_path])
        print(f"✅ Results written to {file_path}")
        return True

    # === "to memory" saves results to episodic LTM ===
    if "to memory" in user_input.lower():
        persona_coll, episodic_coll = initialize_chromadb_for_ltm()
        total_chunks = 0
        for r in results:
            text = r["snippet"]

            # ✳️ Optional: summarize snippet here if enabled
            if WEB_CONFIG.get("summarize_snippets", False):
                # TODO: LLM summarizer hook
                pass

            chunks = chunk_text(text, size=WEB_CONFIG.get("chunk_size", 150))
            for chunk in chunks:
                episodic_coll.add(
                    ids=[f"web-{hash(chunk)}"],
                    documents=[chunk],
                    metadatas=[{
                        "source": "web_search",
                        "url": r["url"],
                        "query": query,
                        "title": r["title"],
                        "tags": WEB_CONFIG.get("tags", []),
                        "topic": f"{WEB_CONFIG.get('topic_prefix', 'web-search')}",
                        "importance": WEB_CONFIG.get("importance_default", 0.5)
                    }]
                )
            total_chunks += len(chunks)

        print(f"✅ Saved {total_chunks} chunks from {len(results)} search results to LTM.")
        return True

    return False

def summarize_with_ollama(text: str, model="llama3") -> str:
    """Call local Ollama server to summarize web search text."""
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model,
                "prompt": f"Summarize the following information for clarity and brevity:\n\n{text}",
                "stream": False,
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("response", "").strip()
    except Exception as e:
        print(f"[❌] Summarization error: {e}")
        return ""

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m cli.utils.web_search_hook \"your question here\"")
        sys.exit(1)

    query = " ".join(sys.argv[1:])
    print(f"[CLI] Running one-off web search for: {query}")
    success = perform_web_search(query, source="cli", tag="websearch")

    if success:
        print("[CLI] ✅ Search completed and saved.")
    else:
        print("[CLI] ❌ Search failed or rejected.")
