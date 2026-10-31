"""Finds the reference passages most relevant to the conversation."""
import json

from .. import config, language, llm
from ..conversation import message_text
from . import index


def vector_search(query, cfg=config.DEFAULT, usage=None):
    """The passages most similar to the query (cosine similarity), at most cfg.per_topic per topic."""
    data, vectors = index.load()
    dims = data["dims"]
    q = llm.embed(query[:6000], dims, usage=usage)[0]
    norm = sum(x * x for x in q) ** 0.5 or 1.0
    q = [x / norm for x in q]
    scored = sorted(
        ((sum(a * b for a, b in zip(q, vectors[i * dims:(i + 1) * dims])), i) for i in range(len(data["chunks"]))),
        reverse=True,
    )
    picked, per_topic = [], {}
    for score, i in scored:
        if score < cfg.min_score or len(picked) == cfg.top_k:
            break
        chunk = data["chunks"][i]
        if per_topic.get(chunk["t"], 0) < cfg.per_topic:
            per_topic[chunk["t"]] = per_topic.get(chunk["t"], 0) + 1
            picked.append({**chunk, "score": round(score, 3)})
    return picked


def search_query(messages, mode="health", hint=None, lang="en", usage=None):
    """Search text: what the person said recently plus English medical terms. Everyday words ("burning when I pee")
    and other languages often don't match the English reference text, so the terms come from the conditions Medi is
    already considering (or a hint from the app), or from a quick rewrite by a small model. English wellbeing messages
    match the reference text well, so they skip the rewrite."""
    said = "\n".join(reversed([message_text(m) for m in messages if m.get("role") == "user"][-3:]))
    foreign = language.needs_english(said, lang)
    if hint and not foreign:
        return f"{said}\nPossible conditions: {hint}"
    if mode == "wellbeing" and not foreign:
        return said
    for m in reversed(messages):
        if foreign or m.get("role") != "assistant":
            continue
        try:
            names = [c["name"] for c in json.loads(m["content"]).get("conditions", [])]
        except (ValueError, TypeError, KeyError):
            continue
        if names:
            return f"{said}\nPossible conditions: {', '.join(names)}"
    rewrite = llm.chat_text({
        "model": config.FAST_MODEL,
        "temperature": 0,
        "max_tokens": 80,
        "messages": [
            {"role": "system", "content": "Rewrite the person's words, in any language, as a short English medical search "
                                          "query: the clinical terms for their symptoms or concerns and the 2-4 most "
                                          "relevant topics to look up. One line, in English, no advice."},
            {"role": "user", "content": said},
        ],
    }, timeout=20, usage=usage)
    return f"{said}\n{rewrite.strip()}"


def find_references(messages, mode="health", hint=None, lang="en", cfg=config.DEFAULT, usage=None):
    """Retrieval never blocks a reply: if it fails, Medi answers without reference material."""
    try:
        return vector_search(search_query(messages, mode, hint, lang, usage), cfg, usage)
    except Exception as e:
        print("Retrieval failed:", e)
        return []
