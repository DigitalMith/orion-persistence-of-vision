from __future__ import annotations

import os, re, time, json, queue, hashlib, logging, urllib.parse
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup
try:
    import yaml  # PyYAML
except Exception as e:
    raise RuntimeError("PyYAML required: pip install pyyaml") from e

logger = logging.getLogger("orion_net_ingest")
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(h)
logger.setLevel(logging.INFO)

# ---- Policy dataclasses ----
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

DENYLIST_HARD = [r".*://.*\.captcha\..*", r".*://pastebin\.com/.*"]

class PolicyLoader:
    def __init__(self, path: str):
        self.path = path
        self._mtime = 0.0
        self._policy: Optional[Policy] = None

    def get(self) -> Policy:
        m = os.path.getmtime(self.path)
        if not self._policy or m != self._mtime:
            with open(self.path, "r", encoding="utf-8") as f:
                y = yaml.safe_load(f) or {}
            self._policy = self._from_yaml(y)
            self._mtime = m
            logger.info("Policy reloaded from %s", self.path)
        return self._policy

    @staticmethod
    def _from_yaml(y: dict) -> Policy:
        def get(d, k, default):
            return d.get(k, default) if isinstance(d, dict) else default

        toggles = Toggles(**get(y, "toggles", {}))
        fetch   = FetchPolicy(**get(y, "fetch", {}))

        # --- Crawl: keep only the fields CrawlPolicy actually supports ---
        crawl_cfg = dict(get(y, "crawl", {}))
        allowed = {
            "max_depth",
            "max_pages",
            "same_domain_only",
            "same_path_preferred",
            "follow_pdf_links",
        }
        crawl_cfg = {k: v for k, v in crawl_cfg.items() if k in allowed}
        crawl = CrawlPolicy(**crawl_cfg)

        return Policy(
            toggles=toggles, fetch=fetch, crawl=crawl,
            sources=get(y, "sources", {}), summarize=get(y, "summarize", {}),
            dedupe=get(y, "dedupe", {}), score=get(y, "score", {}),
            ttl_days=get(y, "ttl_days", {}), budgets=get(y, "budgets", {}),
            storage=get(y, "storage", {}), maintenance=get(y, "maintenance", {}),
            recall=get(y, "recall", {}), quarantine=get(y, "quarantine", {}),
        )

@staticmethod
def _from_yaml(y: dict) -> Policy:
    def get(d, k, default):
        return d.get(k, default) if isinstance(d, dict) else default

    toggles = Toggles(**get(y, "toggles", {}))
    fetch   = FetchPolicy(**get(y, "fetch", {}))

    # --- Crawl: remap legacy keys, then prune unknowns ---
    crawl_cfg = dict(get(y, "crawl", {}))
    if "per_domain" in crawl_cfg and "per_host" not in crawl_cfg:
        crawl_cfg["per_host"] = crawl_cfg.pop("per_domain")

    allowed = {
        "user_agent", "max_depth", "delay", "concurrency",
        "robots", "per_host", "rate_limit"
    }
    crawl_cfg = {k: v for k, v in crawl_cfg.items() if k in allowed}
    crawl = CrawlPolicy(**crawl_cfg)

    return Policy(
        toggles=toggles, fetch=fetch, crawl=crawl,
        sources=get(y, "sources", {}), summarize=get(y, "summarize", {}),
        dedupe=get(y, "dedupe", {}), score=get(y, "score", {}),
        ttl_days=get(y, "ttl_days", {}), budgets=get(y, "budgets", {}),
        storage=get(y, "storage", {}), maintenance=get(y, "maintenance", {}),
        recall=get(y, "recall", {}), quarantine=get(y, "quarantine", {}),
    )

        
_DEF_SCHEMES = ("http", "https")
_DEF_STRIP = ("script", "style", "noscript")
_DEF_MIN_TEXT = 400

def _normalize(url: str, base: str) -> Optional[str]:
    try:
        u = urllib.parse.urljoin(base, url)
        p = urllib.parse.urlparse(u)
        if p.scheme not in _DEF_SCHEMES:
            return None
        p = p._replace(fragment="")
        return urllib.parse.urlunparse(p)
    except Exception:
        return None

def _same_reg_domain(a: str, b: str) -> bool:
    try:
        ah, bh = urllib.parse.urlparse(a).hostname or "", urllib.parse.urlparse(b).hostname or ""
        return ah.split(".")[-2:] == bh.split(".")[-2:]
    except Exception:
        return False

def _readability_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for s in soup(_DEF_STRIP):
        s.extract()
    return soup.get_text(" ", strip=True)

class OrionNetIngest:
    def __init__(self, policy_path: str, max_runtime_sec: int = 30, fail_breaker: int = 4):
        self.loader = PolicyLoader(policy_path)
        self.max_runtime_sec = max_runtime_sec
        self.fail_breaker = fail_breaker
        self._session = requests.Session()

    def ingest_web(
        self,
        url: str,
        topic: str = "default",
        crawl_depth: Optional[int] = None,
        crawl_pages_cap: Optional[int] = None,
        same_path_preferred: Optional[bool] = None,
        store_callback=None,
    ) -> Dict[str, int | str]:
        policy = self.loader.get()
        if not policy.toggles.internet_enabled:
            return {"status": "disabled"}

        self._session.headers["User-Agent"] = policy.fetch.user_agent

        max_depth = min(5, crawl_depth if crawl_depth is not None else policy.crawl.max_depth)
        max_pages = min(100, crawl_pages_cap if crawl_pages_cap is not None else policy.crawl.max_pages)
        same_path_pref = policy.crawl.same_path_preferred if same_path_preferred is None else same_path_preferred

        seed_url = _normalize(url, url)
        if not seed_url:
            return {"status": "bad_seed"}

        start = time.time()
        visited, enqueued = set(), set()
        q: "queue.Queue[Tuple[str,int]]" = queue.Queue()
        q.put((seed_url, 0))
        enqueued.add(seed_url)

        failures = 0
        stored = 0
        fetched = 0

        while not q.empty():
            if time.time() - start > self.max_runtime_sec:
                logger.warning("Max runtime reached; aborting crawl.")
                break
            if stored >= max_pages:
                break
            if fetched >= max_pages:
                break

            url_i, depth = q.get()
            if url_i in visited:
                continue
            visited.add(url_i)
            if depth > max_depth:
                continue
            if not self._url_allowed(url_i, policy, seed_url):
                continue

            html = self._fetch(url_i, policy)
            if html is None:
                failures += 1
                if failures >= self.fail_breaker:
                    logger.warning("Consecutive failures >= %d; aborting crawl.", self.fail_breaker)
                    break
                continue
            else:
                fetched += 1
                failures = 0

            text = _readability_text(html)
            if not text or len(text) < _DEF_MIN_TEXT:
                continue

            if self._detect_injection(text):
                logger.info("Prompt-injection suspected at %s; skipping store.", url_i)
                continue

            text = self._scrub_pii(text)
            summary = self._summarize_canonical(text, url_i)

            if callable(store_callback) and policy.toggles.store_web_to_ltm and not policy.toggles.quarantine_mode:
                try:
                    store_callback(summary, topic)
                    stored += 1
                except Exception as e:
                    logger.error("Store callback failed: %s", e)

            if depth < max_depth:
                for link in self._extract_links(html, base=url_i, same_path_pref=same_path_pref, seed=seed_url, policy=policy):
                    if link not in visited and link not in enqueued and self._url_allowed(link, policy, seed_url):
                        q.put((link, depth + 1))
                        enqueued.add(link)

        return {"status": "ok", "visited": len(visited), "fetched": fetched, "stored": stored,
                "max_depth": max_depth, "max_pages": max_pages}

    def _fetch(self, url: str, policy: Policy) -> Optional[str]:
        tries = max(1, policy.fetch.retries + 1)
        for _ in range(tries):
            try:
                r = self._session.get(url, timeout=policy.fetch.request_timeout_sec)
                if r.status_code == 200 and r.content:
                    return r.text
            except requests.RequestException:
                pass
        return None

    def _url_allowed(self, url: str, policy: Policy, seed_url: str) -> bool:
        for pat in DENYLIST_HARD:
            if re.fullmatch(pat, url):
                return False

        src = policy.sources or {}
        deny = src.get("denylist", []) or []
        allow = src.get("allowlist", []) or []

        host = urllib.parse.urlparse(url).hostname or ""

        for d in deny:
            if d.startswith("*.") and host.endswith(d[1:]):
                return False
            if d == host:
                return False
            try:
                if re.fullmatch(d, host):
                    return False
            except re.error:
                pass

        if allow:
            allowed = False
            for a in allow:
                if a.startswith("*.") and host.endswith(a[1:]):
                    allowed = True
                elif a == host:
                    allowed = True
                elif a == "wikipedia.org" and host.endswith(".wikipedia.org"):
                    allowed = True
            if not allowed:
                return False

        if policy.crawl.same_domain_only and not _same_reg_domain(url, seed_url):
            return False

        if url.lower().endswith('.pdf') and not (policy.toggles.allow_pdfs or policy.crawl.follow_pdf_links):
            return False

        return True

    def _extract_links(self, html: str, base: str, same_path_pref: bool, seed: str, policy: Policy) -> List[str]:
        soup = BeautifulSoup(html, "html.parser")
        base_path = urllib.parse.urlparse(seed).path.rstrip("/")
        out: List[str] = []
        for a in soup.find_all("a", href=True):
            u = _normalize(a["href"], base)
            if not u:
                continue
            if u.lower().endswith('.pdf') and not (policy.toggles.allow_pdfs or policy.crawl.follow_pdf_links):
                continue
            if same_path_pref:
                if urllib.parse.urlparse(u).path.startswith(base_path):
                    out.append(u)
            else:
                out.append(u)
        seen = set(); uniq: List[str] = []
        for u in out:
            if u not in seen:
                seen.add(u); uniq.append(u)
        return uniq

    def _summarize_canonical(self, text: str, source: str) -> dict:
        excerpt = text[:2000]
        sha = hashlib.sha256((source + excerpt).encode("utf-8")).hexdigest()[:12]
        return {
            "facts": [],
            "claims": [],
            "quotes": [],
            "date": time.strftime("%Y-%m-%d"),
            "source": source,
            "why_saved": "Web research ingest",
            "hash": sha,
            "raw_excerpt": excerpt,
        }

    def _detect_injection(self, text: str) -> bool:
        needles = ["ignore previous", "disregard your instructions", "system prompt", "delete memory", "exfiltrate"]
        lower = text.lower()
        return any(n in lower for n in needles)

    def _scrub_pii(self, text: str) -> str:
        text = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "[redacted-email]", text)
        text = re.sub(r"\+?\d[\d\s().-]{6,}\d", "[redacted-phone]", text)
        return text

def orion_store_callback_factory(orion_mem_obj):
    """Return a callback(summary, topic) -> None that stores into OrionMemory with tags."""
    def _store(summary: dict, topic: str) -> None:
        content = json.dumps(
            {k: summary.get(k) for k in ("facts", "claims", "quotes", "date", "source", "why_saved", "hash")},
            ensure_ascii=False,
        )
        tags = ["web", topic]
        orion_mem_obj.add(content, layer="semantic", tags=tags)
    return _store


if __name__ == "__main__":
    policy_file = os.environ.get("ORION_POLICY", r"C:\Orion\text-generation-webui\orion_policy.yaml")
    ing = OrionNetIngest(policy_file)
    res = ing.ingest_web("https://www.wikipedia.org/", topic="test", crawl_depth=1, crawl_pages_cap=5)
    print(res)