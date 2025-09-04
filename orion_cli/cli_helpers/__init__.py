"""
cli_helpers package
-------------------
Utility modules for Orion CLI:
 - summary_helper: ingest & dedup text into LTM
 - delete_topic: remove items from Chroma by topic
 - encoding_scan, health_report, ltm_query, persona_check
"""

from . import summary_helper
from . import ingest_helper
from . import ltm_query
from . import health_report
from . import encoding_scan
from . import persona_check
from . import delete_topic   # <-- you added this (good)

from .delete_topic import delete_by_topic, preview_topic, count_by_topic

__all__ = [
    "summary_helper",
    "ingest_helper",   # <-- add
    "delete_topic",
    "encoding_scan",
    "health_report",
    "ltm_query",
    "persona_check",
]