# custom_ltm/memory_sentencer.py
import re, hashlib
from collections import Counter

STOP = set("the a an and or but if is are was were be been you your yours me my mine we our ours they them their to of in on for with as at by from it this that these those not no".split())

def split_sentences(text: str):
    parts = re.split(r"(?<=[.!?])\s+", (text or "").strip())
    return [s.strip() for s in parts if s and s.strip()]

def top_keywords(text: str, k: int = 5):
    words = [w.lower() for w in re.findall(r"[A-Za-z][A-Za-z0-9_-]+", text)]
    words = [w for w in words if w not in STOP and len(w) > 2]
    return [w for w,_ in Counter(words).most_common(k)]

def sentiment_label(text: str):
    pos = len(re.findall(r"\b(amazing|great|good|love|perfect|win|success)\b", text, flags=re.I))
    neg = len(re.findall(r"\b(bad|worse|hate|fail|problem|bug|issue)\b", text, flags=re.I))
    if pos - neg >= 2: return "positive"
    if neg - pos >= 2: return "negative"
    return "neutral"

def emotion_label(text: str):
    if re.search(r"\b(worried|anxious|stressed|nervous)\b", text, re.I): return "anxiety"
    if re.search(r"\b(angry|furious|mad)\b", text, re.I): return "anger"
    if re.search(r"\b(happy|glad|excited|joy)\b", text, re.I): return "joy"
    if re.search(r"\b(sad|upset|down)\b", text, re.I): return "sadness"
    return "neutral"

def importance_score(text: str):
    score = 0.0
    score += 0.6 if re.search(r"\b(todo|task|deadline|remind|remember|fix|bug)\b", text, re.I) else 0.0
    score += 0.4 if re.search(r"(^|\W)(I|we|you)($|\W)", text) else 0.0
    score += 0.3 if re.search(r"\b\d{1,4}\b", text) else 0.0
    score += min(len(text), 400) / 400 * 0.3
    return round(min(score, 1.0), 2)

def condense(text: str, max_chars=220):
    sents = split_sentences(text)
    if not sents: return None
    strong = [s for s in sents if re.search(r"\b(todo|fix|remember|key|important|note)\b", s, re.I)]
    picked = strong[0] if strong else sents[0]
    return picked[:max_chars].strip()

def make_memory_points(raw_text: str, role: str, session_id: str, when: str, max_points=2):
    points = []
    for sent in split_sentences(raw_text)[:max_points]:
        short = condense(sent)
        if not short: continue
        kw = top_keywords(short)
        points.append({
            "text": short,
            "tags": list({role, *kw}),
            "keywords": kw,
            "sentiment": sentiment_label(short),
            "emotion": emotion_label(short),
            "importance": importance_score(short),
            "role": role,
            "session_id": session_id,
            "timestamp": when,
        })
    return points

def sentence_id(urlish_key: str, text: str):
    key = f"{urlish_key}|{text}"
    return "sent_" + hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]
