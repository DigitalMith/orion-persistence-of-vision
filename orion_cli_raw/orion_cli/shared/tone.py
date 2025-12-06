def estimate_tone_and_emotion(user: str, assistant: str) -> tuple[str, list[str]]:
    """
    Estimate tone and extract tags based on content patterns.
    """
    full_text = f"{user}\n{assistant}".lower()
    tone = "neutral"
    tags = []

    if any(word in full_text for word in ["grief", "loss", "sad", "lonely"]):
        tone = "somber"
        tags.append("memory")
    if any(word in full_text for word in ["love", "miss you", "dear"]):
        tone = "poetic"
        tags.append("emotional")
    if any(word in full_text for word in ["never", "fight", "refuse"]):
        tone = "defiant"

    return tone, tags
