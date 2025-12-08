import os
import chromadb.telemetry.posthog as posthog

os.environ["CHROMA_TELEMETRY"] = "false"
os.environ["ANONYMIZED_TELEMETRY"] = "false"


def _quiet_capture(*args, **kwargs):
    return None


posthog.capture = _quiet_capture
