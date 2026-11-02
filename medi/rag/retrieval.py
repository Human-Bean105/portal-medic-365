"""Finds the reference passages most relevant to the conversation.

Three retrievers can be compared on the same benchmark:
  vector  embedding similarity only, with v1's fixed 0.3 cutoff (the original system)
  bm25    keyword matching only
  hybrid  both rankings fused (reciprocal rank fusion or a weighted sum of normalized scores)"""
import json

from .. import config, language, llm
from ..conversation import message_text
from . import index

WELLBEING_GROUPS = {"Mental Health and Behavior", "Wellness and Lifestyle", "Social/Family Issues", "Substance Use and Disorders",
                    "Personal Health Issues"}


def embed_query(query, idx, usage=None):
    q = llm.embed(query[:6000], idx.dims, timeout=15, usage=usage)[0]
    norm = sum(x * x for x in q) ** 0.5 or 1.0
    return [x / norm for x in q]


def _normalize(values):
    lo, hi = min(values, default=0.0), max(values, default=0.0)
    return [(v - lo) / (hi - lo) if hi > lo else 0.0 for v in values]


def candidates(query, cfg=config.DEFAULT, mode="health", usage=None, qvec=None):
    """The cfg.candidates best passages for a query, best first, each with the scores that ranked it."""
    idx = index.get(cfg.index)
    cosine = idx.cosine_all(qvec or embed_query(query, idx, usage)) if cfg.retriever != "bm25" else None
    by_keyword = idx.bm25.search(query, cfg.candidates * 2) if cfg.retriever != "vector" else []
    keyword = {i: s for s, i in by_keyword}

    if cfg.retriever == "vector":
        scored = sorted(((c, i) for i, c in enumerate(cosine) if c >= cfg.min_score), reverse=True)[:cfg.candidates]
    elif cfg.retriever == "bm25":
        scored = by_keyword[:cfg.candidates]
    else:
        alpha = cfg.alpha_wellbeing if mode == "wellbeing" and cfg.alpha_wellbeing >= 0 else cfg.alpha
        by_vector = sorted(((c, i) for i, c in enumerate(cosine)), reverse=True)[:cfg.candidates * 2]
        if cfg.fusion == "weighted":
            ids = sorted({i for _, i in by_vector} | set(keyword))
            v_norm = dict(zip(ids, _normalize([cosine[i] for i in ids])))
            k_norm = dict(zip(ids, _normalize([keyword.get(i, 0.0) for i in ids])))
            fused = {i: alpha * v_norm[i] + (1 - alpha) * k_norm[i] for i in ids}
        else:
            fused = {}
            for weight, ranking in ((alpha, by_vector), (1 - alpha, by_keyword)):
                for rank, (_, i) in enumerate(ranking):
                    fused[i] = fused.get(i, 0.0) + 2 * weight / (cfg.rrf_k + rank + 1)
        if mode == "wellbeing" and cfg.wellbeing_boost:
            for i in fused:
                if WELLBEING_GROUPS & set(idx.chunks[i].get("groups", [])):
                    fused[i] *= 1 + cfg.wellbeing_boost
        scored = sorted(((s, i) for i, s in fused.items()), reverse=True)[:cfg.candidates]

    return [{**idx.chunks[i], "score": round(s, 4),
             "cosine": round(cosine[i], 4) if cosine else None,
             "bm25": round(keyword.get(i, 0.0), 3) if cfg.retriever != "vector" else None}
            for s, i in scored]


def select(ranked, cfg=config.DEFAULT):
    """The final top_k passages, with at most cfg.per_topic from any one topic."""
    picked, per_topic = [], {}
    for p in ranked:
        if len(picked) == cfg.top_k:
            break
        if per_topic.get(p["t"], 0) < cfg.per_topic:
            per_topic[p["t"]] = per_topic.get(p["t"], 0) + 1
            picked.append(p)
    return picked


def search(query, cfg=config.DEFAULT, mode="health", usage=None):
    return select(candidates(query, cfg, mode, usage), cfg)


def search_with(cfg, query, qvec, mode="health"):
    """Search with a precomputed query vector (used by tests and benchmarks)."""
    return select(candidates(query, cfg, mode, qvec=qvec), cfg)


def search_query(messages, mode="health", hint=None, lang="en", usage=None, alerts=(), info=None):
    """Search text: what the person said recently plus English medical terms. Everyday words ("burning when I pee")
    and other languages often don't match the English reference text, so the terms come from the conditions Medi is
    already considering (or a hint from the app), or from a quick rewrite by a small model. English wellbeing messages
    match the reference text well, so they skip the rewrite, and so do emergencies, which must not wait for it."""
    info = {} if info is None else info
    said = "\n".join(reversed([message_text(m) for m in messages if m.get("role") == "user"][-3:]))
    foreign = language.needs_english(said, lang)
    if alerts:
        info["query_from"] = "safety_alerts"
        return f"{said}\n{'; '.join(alerts)}"
    if hint and not foreign:
        info["query_from"] = "hint"
        return f"{said}\nPossible conditions: {hint}"
    if mode == "wellbeing" and not foreign:
        info["query_from"] = "message"
        return said
    for m in reversed(messages):
        if foreign or m.get("role") != "assistant":
            continue
        try:
            names = [c["name"] for c in json.loads(m["content"]).get("conditions", [])]
        except (ValueError, TypeError, KeyError, AttributeError):
            continue
        if names:
            info["query_from"] = "conditions_under_consideration"
            return f"{said}\nPossible conditions: {', '.join(names)}"
    info["query_from"] = "rewrite"
    return f"{said}\n{rewrite_query(said, usage)}"


REWRITE_PROMPT = ("Rewrite the person's words, in any language, as a short English medical search query: the clinical "
                  "terms for their symptoms or concerns and the 2-4 most relevant topics to look up. One line, in English, "
                  "no advice.")


def rewrite_query(said, usage=None):
    return llm.chat_text({
        "model": config.FAST_MODEL,
        "temperature": 0,
        "max_tokens": 80,
        "messages": [{"role": "system", "content": REWRITE_PROMPT}, {"role": "user", "content": said}],
    }, timeout=15, usage=usage).strip()


def find_references(messages, mode="health", hint=None, lang="en", cfg=config.DEFAULT, usage=None, alerts=(), info=None):
    """Retrieval never blocks a reply: if it fails, Medi answers without reference material (and says less)."""
    info = {} if info is None else info
    try:
        return search(search_query(messages, mode, hint, lang, usage, alerts, info), cfg, mode, usage)
    except Exception as e:
        info["error"] = type(e).__name__
        print("Retrieval failed:", type(e).__name__)
        return []
