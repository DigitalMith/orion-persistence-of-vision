from sentence_transformers import SentenceTransformer
from datetime import datetime, timedelta

# Load only once
_temporal_embedder = SentenceTransformer("infloat/e5-large-v2")


def embed_temporal_query(text: str):
    """
    Encodes a temporal question like 'yesterday morning' to a dense vector.
    """
    instruction = "Represent this search query for retrieving relevant memories: "
    return _temporal_embedder.encode(instruction + text, normalize_embeddings=True)


def categorize_time_of_day(dt):
    hour = dt.hour
    if hour < 6:
        return "early morning"
    elif hour < 12:
        return "morning"
    elif hour < 18:
        return "afternoon"
    elif hour < 21:
        return "evening"
    else:
        return "night"


def infer_day_context(text: str) -> str | None:
    """
    Parses user text for a day reference like 'Friday', 'yesterday', or 'last weekend'
    and returns a capitalized weekday string if matched.
    """
    now = datetime.now()
    text = text.lower()

    # Exact weekday (e.g. "Friday")
    days = [
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    ]
    for i, day in enumerate(days):
        if day in text:
            return day.capitalize()

    # Relative day phrases
    if "yesterday" in text:
        return (now - timedelta(days=1)).strftime("%A")
    elif "today" in text:
        return now.strftime("%A")
    elif "tomorrow" in text:
        return (now + timedelta(days=1)).strftime("%A")
    elif "last weekend" in text:
        # fallback: assume Saturday
        return "Saturday"
    elif "this weekend" in text:
        return "Saturday"

    return None
