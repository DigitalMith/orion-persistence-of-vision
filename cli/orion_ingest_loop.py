import time
import logging
from cli.cli_helpers.orion_net_ingest import OrionNetIngest, orion_store_callback_factory

# Topics Orion should always keep up-to-date on
TOPIC_QUEUE = [
    "GPT-4",
    "LLM agents",
    "vector databases",
    "AI alignment",
    "open source AI",
    # Extend with more topics
]

# Search targets per topic (for now, static URLs — can be dynamic later)
URL_MAP = {
    "GPT-4": "https://en.wikipedia.org/wiki/GPT-4",
    "LLM agents": "https://en.wikipedia.org/wiki/Software_agent",
    "vector databases": "https://en.wikipedia.org/wiki/Vector_database",
    "AI alignment": "https://en.wikipedia.org/wiki/AI_alignment",
    "open source AI": "https://en.wikipedia.org/wiki/Open-source_artificial_intelligence"
}

# Loop delay in seconds (1 hour)
SLEEP_INTERVAL = 3600

def run_loop():
    logging.basicConfig(level=logging.INFO)
    ingester = OrionNetIngest(policy_path="orion_policy.yaml")
    ingester.store_callback = orion_store_callback_factory()

    while True:
        print("[LOOP] Starting ingestion cycle...")

        for topic in TOPIC_QUEUE:
            url = URL_MAP.get(topic)
            if not url:
                logging.warning(f"No URL mapped for topic: {topic}")
                continue

            try:
                print(f"[LOOP] Ingesting topic '{topic}' from: {url}")
                result = ingester.ingest_web(
                    url=url,
                    topic=topic,
                )
                print(f"[RESULT] {result}")
            except Exception as e:
                logging.error(f"Failed to ingest {url}: {e}")

        print(f"[LOOP] Sleeping for {SLEEP_INTERVAL} seconds...\n")
        time.sleep(SLEEP_INTERVAL)

if __name__ == "__main__":
    run_loop()
