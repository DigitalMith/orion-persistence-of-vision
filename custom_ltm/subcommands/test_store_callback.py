# ----- test_store_callback.py
import sys
sys.path.insert(0, r"C:\Orion\text-generation-webui\custom_ltm")

from orion_memory import OrionMemory
from orion_net_ingest import OrionNetIngest, orion_store_callback_factory

# Create LTM
mem = OrionMemory(path=r"C:\Orion\text-generation-webui\user_data\chroma_db")

# Hybrid: print AND save
_real_store = orion_store_callback_factory(mem)

def store_and_show(summary: dict, topic: str) -> None:
    src = (summary or {}).get("source", "")
    # Only keep English Wikipedia + Weathersfield
    if not (
        src.startswith("https://en.wikipedia.org/")
        or src.startswith("https://www.weathersfieldvt.org/")
    ):
        print(f"[SKIP] off-domain: {src}")
        return
    print(f"[STORE] topic={topic} source={src} hash={summary.get('hash')}")
    _real_store(summary, topic)

# Domain filter – only English Wikipedia + Weathersfield VT
def domain_filter(url: str) -> bool:
    return (
        url.startswith("https://en.wikipedia.org/")
        or url.startswith("https://www.weathersfieldvt.org/")
    )

# Ingest
ing = OrionNetIngest(r"C:\Orion\text-generation-webui\orion_policy.yaml")

res = ing.ingest_web(
    "https://www.weathersfieldvt.org/about/pages/our-community",
    topic="Perkinsville VT",
    crawl_depth=2,
    crawl_pages_cap=12,
    store_callback=store_and_show,
)

res = ing.ingest_web(
    "https://en.wikipedia.org/wiki/Perkinsville,_Vermont",
    topic="Perkinsville VT",
    crawl_depth=2,
    crawl_pages_cap=8,
    store_callback=store_and_show,
)

print(res)
