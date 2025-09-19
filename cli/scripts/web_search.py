import os
import requests
import yaml

CONFIG_PATH = r"C:\Orion\text-generation-webui\cli\data\web_config.yaml"

# Load config
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

WEB_CONFIG = config.get("web_search", {})

API_KEY = WEB_CONFIG.get("api_key")
PROVIDER = WEB_CONFIG.get("api_provider", "serper")
MAX_RESULTS = WEB_CONFIG.get("max_results", 5)
CHUNK_SIZE = WEB_CONFIG.get("chunk_size", 150)
SUMMARIZE_SNIPPETS = WEB_CONFIG.get("summarize_snippets", True)

def web_search(query: str) -> list:
    """Returns a list of dicts: [{'title':..., 'snippet':..., 'url':...}, ...]"""
    if not API_KEY:
        raise EnvironmentError("SERPER_API_KEY not set in web_config.yaml")

    if PROVIDER != "serper":
        raise NotImplementedError(f"API provider {PROVIDER} not supported")

    url = "https://google.serper.dev/search"
    headers = {"X-API-KEY": API_KEY}
    payload = {"q": query}

    try:
        resp = requests.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        results = resp.json()

        output = []
        for r in results.get("organic", [])[:MAX_RESULTS]:
            snippet = r.get("snippet", "").strip()
            title = r.get("title", "No Title")
            link = r.get("link", "")
            if snippet:
                output.append({"title": title, "snippet": snippet, "url": link})
        return output

    except Exception as e:
        return [{"title": "Error", "snippet": str(e), "url": ""}]


def chunk_text(text: str, size: int = CHUNK_SIZE):
    """Simple chunking by max characters, keeps sentences whole if possible."""
    import re
    sentences = re.split(r'(?<=[.!?]) +', text)
    chunks = []
    current = ""
    for s in sentences:
        if len(current) + len(s) + 1 <= size:
            current += " " + s if current else s
        else:
            if current:
                chunks.append(current.strip())
            current = s
    if current:
        chunks.append(current.strip())
    return chunks
