import os, time, re, json, queue, hashlib, urllib.parse
from dataclasses import dataclass
from typing import Dict, List, Optional
import yaml
import requests
from bs4 import BeautifulSoup

DENYLIST_HARD = [r".*://.*\.captcha\..*", r".*://pastebin\.com/.*"]  # code-level denylist

@dataclass
class CrawlPolicy:
    max_depth: int = 1
    max_pages: int = 10
    same_domain_only: bool = True
    same_path_preferred: bool = True
    follow_pdf_links: bool = False

@dataclass
class FetchPolicy:
    max_requests_per_hour: int = 30
    request_timeout_sec: int = 20
    retries: int = 1
    user_agent: str = "Orion/1.0 (local)"
    robots_txt_respect: bool = True

@dataclass
class Toggles:
    internet_enabled: bool = True
    store_web_to_ltm: bool = True
    allow_pdfs: bool = False
    quarantine_mode: bool = False

@dataclass
class Policy:
    toggles: Toggles
    fetch: FetchPolicy
    crawl: CrawlPolicy
    sources: dict
    summarize: dict
    dedupe: dict
    score: dict
    ttl_days: dict
    budgets: dict
    storage: dict
    maintenance: dict
    recall: dict
    quarantine: dict

def load_policy(path: str) -> Policy:
    with open(path, "r", encoding="utf-8") as f:
        y = yaml.safe_load(f)
    # Minimal validation + safe defaults
    def get(d, k, default): return d.get(k, default) if isinstance(d, dict) else default
    toggles = Toggles(**get(y, "toggles", {}))
    fetch   = FetchPolicy(**get(y, "fetch", {}))
    crawl   = CrawlPolicy(**get(y, "crawl", {}))
    return Policy(
        toggles=toggles, fetch=fetch, crawl=crawl,
        sources=get(y, "sources", {}), summarize=get(y, "summarize", {}),
        dedupe=get(y, "dedupe", {}), score=get(y, "score", {}),
        ttl_days=get(y, "ttl_days", {}), budgets=get(y, "budgets", {}),
        storage=get(y, "storage", {}), maintenance=get(y, "maintenance", {}),
        recall=get(y, "recall", {}), quarantine=get(y, "quarantine", {})
    )

# ---------- Utilities

def same_reg_domain(a: str, b: str) -> bool:
    try:
        ah, bh = urllib.parse.urlparse(a).hostname or "", urllib.parse.urlparse(b).hostname or ""
        return ah.split(".")[-2:] == bh.split(".")[-2:]
    except Exception:
        return False

def is_pdf_url(url: str) -> bool:
    return url.lower().endswith(".pdf")

def url_allowed(url: str, policy: Policy, seed_url: str) -> bool:
    # hard denylist (code-level)
    for pat in DENYLIST_HARD:
        if re.fullmatch(pat, url): return False

    src = policy.sources or {}
    deny = src.get("denylist", []) or []
    allow = src.get("allowlist", []) or []

    def matches(pattern: str, host: str) -> bool:
        # simple wildcard on host (e.g., *.gov)
        if pattern.startswith("*."):
            return host.endswith(pattern[1:])
        return host == pattern

    host = urllib.parse.urlparse(url).hostname or ""
    # denylist-first
    for d in deny:
        if d.startswith("*.") or d == host or re.fullmatch(d, host):
            return False

    # allow if in allowlist (host or wildcard)
    allowed = False
    for a in allow:
        if a.startswith("*.") and host.endswith(a[1:]): allowed = True
        elif a == host: allowed = True
        elif a == "wikipedia.org" and host.endswith(".wikipedia.org"): allowed = True
    if not allowed and allow:  # if allowlist is non-empty, require match
        return False

    # same-domain constraint
    if policy.crawl.same_domain_only and not same_reg_domain(url, seed_url):
        return False

    # pdf handling
    if is_pdf_url(url) and not (policy.toggles.allow_pdfs or policy.crawl.follow_pdf_links):
        return False

    return True

def normalize(url: str, base: str) -> Optional[str]:
    try:
        u = urllib.parse.urljoin(base, url)
        parsed = urllib.parse.urlparse(u)
        if parsed.scheme not in ("http", "https"): return None
        return urllib.parse.urlunparse(parsed)
    except Exception:
        return None

def readability_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for s in soup(["script", "style", "noscript"]): s.extract()
    return soup.get_text(" ", strip=True)

# ---------- BFS Crawl + Ingest

class WebIngestor:
    def __init__(self, policy: Policy, max_runtime_sec: int = 60, fail_breaker: int = 5):
        self.policy = policy
        self.max_runtime_sec = max_runtime_sec
        self.fail_breaker = fail_breaker
        self._session = requests.Session()
        self._session.headers["User-Agent"] = policy.fetch.user_agent

    def fetch(self, url: str, timeout: int) -> Optional[str]:
        for _ in range(max(1, self.policy.fetch.retries + 1)):
            try:
                r = self._session.get(url, timeout=timeout)
                if r.status_code == 200 and r.content:
                    return r.text
            except requests.RequestException:
                pass
        return None

    def crawl_and_ingest(self, seed_url: str, topic: str, depth_override: Optional[int] = None,
                         pages_cap_override: Optional[int] = None, same_path_preferred: Optional[bool] = None):
        if not self.policy.toggles.internet_enabled:
            return {"status": "disabled"}

        start = time.time()
        visited, enqueued = set(), set()
        q = queue.Queue()

        max_depth = min(5, depth_override if depth_override is not None else self.policy.crawl.max_depth)  # hard ceiling
        max_pages = min(100, pages_cap_override if pages_cap_override is not None else self.policy.crawl.max_pages)  # hard ceiling
        same_path_pref = self.policy.crawl.same_path_preferred if same_path_preferred is None else same_path_preferred

        seed_url = normalize(seed_url, seed_url)
        if not seed_url: return {"status": "bad_seed"}

        q.put((seed_url, 0))
        enqueued.add(seed_url)

        failures = 0
        stored = 0

        while not q.empty():
            if time.time() - start > self.max_runtime_sec: break
            if stored >= max_pages: break
            url, depth = q.get()

            if url in visited: continue
            visited.add(url)

            if depth > max_depth: continue
            if not url_allowed(url, self.policy, seed_url): continue

            html = self.fetch(url, self.policy.fetch.request_timeout_sec)
            if html is None:
                failures += 1
                if failures >= self.fail_breaker: break
                continue
            else:
                failures = 0

            text = readability_text(html)
            if not text or len(text) < 400:
                continue

            # ----- Safety gate: injection/PII (stub hooks)
            # detect_injection(text) -> bool  # TODO: your classifier
            # scrub_pii(text) -> text         # TODO: your redactor

            # ----- Summarize & store (you wire to OrionMemory)
            summary = self._summarize_canonical(text=text, source=url)
            # mem.store_summary(summary, topic=topic)   # <- your implementation
            stored += 1

            # ----- Enqueue links (BFS)
            if depth < max_depth:
                links = self._extract_links(html, base=url, same_path_pref=same_path_pref, seed=seed_url)
                for link in links:
                    if link not in visited and link not in enqueued:
                        if url_allowed(link, self.policy, seed_url):
                            q.put((link, depth + 1))
                            enqueued.add(link)

        return {"status": "ok", "visited": len(visited), "stored": stored, "max_depth": max_depth}

    def _extract_links(self, html: str, base: str, same_path_pref: bool, seed: str) -> List[str]:
        soup = BeautifulSoup(html, "html.parser")
        base_path = urllib.parse.urlparse(seed).path.rstrip("/")
        out = []
        for a in soup.find_all("a", href=True):
            u = normalize(a["href"], base)
            if not u: continue
            if is_pdf_url(u) and not (self.policy.toggles.allow_pdfs or self.policy.crawl.follow_pdf_links):
                continue
            if same_path_pref:
                if urllib.parse.urlparse(u).path.startswith(base_path):
                    out.append(u)
            else:
                out.append(u)
        # De-dup while preserving order
        seen = set(); uniq = []
        for u in out:
            if u not in seen:
                seen.add(u); uniq.append(u)
        return uniq

    def _summarize_canonical(self, text: str, source: str) -> dict:
        # Placeholder: keep structure your retriever expects
        # TODO: call your local LLM to create 500–800 token canonical note per policy
        h = hashlib.sha256((source + text[:2000]).encode("utf-8")).hexdigest()[:12]
        return {
            "facts": [],
            "claims": [],
            "quotes": [],
            "date": time.strftime("%Y-%m-%d"),
            "source": source,
            "why_saved": "Web research ingest",
            "hash": h,
            "raw_excerpt": text[:2000]  # you can drop this if you prefer
        }
