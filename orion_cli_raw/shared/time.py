"""
Temporal Metadata Utilities
---------------------------
Provides timestamp generation and temporal feature extraction.
"""

from datetime import datetime


def now_epoch():
    return datetime.utcnow().timestamp()


def temporal_metadata(ts: float):
    dt = datetime.utcfromtimestamp(ts)
    return {
        "date": dt.strftime("%Y-%m-%d"),
        "weekday": dt.strftime("%A"),
        "hour": dt.hour,
        "epoch": ts,
        "is_night": dt.hour < 6 or dt.hour >= 22,
        "is_weekend": dt.weekday() >= 5,
    }
