"""Evaluation metrics. Each function documents exactly how it is calculated.

Retrieval metrics work at the topic level: a retrieved passage counts as relevant when its topic title is in the
query's labeled set. "primary" topics are the ones that most directly answer the query; "relevant" means primary
or related. `titles` is the list of retrieved passage titles in rank order (a topic can appear twice)."""
import statistics


def hit_at_k(titles, primary, k):
    """1 if any of the top k passages belongs to a primary topic, else 0."""
    return int(any(t in primary for t in titles[:k]))


def recall_at_k(titles, primary, k):
    """Share of the primary topics that appear among the top k passages: |primary ∩ top-k topics| / |primary|."""
    return len(set(primary) & set(titles[:k])) / len(primary) if primary else 0.0


def precision_at_k(titles, relevant, k):
    """Share of the k result slots filled by a passage from a relevant (primary or related) topic. Empty slots,
    when a retriever returns fewer than k passages, count as not relevant (standard IR definition, divides by k)."""
    return sum(t in relevant for t in titles[:k]) / k


def reciprocal_rank(titles, primary, cutoff=10):
    """1 / (rank of the first passage from a primary topic), or 0 if none appears in the top `cutoff`."""
    for rank, t in enumerate(titles[:cutoff], 1):
        if t in primary:
            return 1 / rank
    return 0.0


def mean(values):
    return round(statistics.mean(values), 3) if values else None


def percentile(values, p):
    """Nearest-rank percentile (p in 0-100)."""
    if not values:
        return None
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, max(0, round(p / 100 * len(ordered)) - 1))]


def retrieval_summary(rows):
    """Aggregate retrieval metrics over per-query rows that hold "titles", "primary", and "relevant". Queries with no
    labeled topic (out-of-scope questions) have nothing to find, so they are left out."""
    rows = [r for r in rows if r["primary"]]
    out = {"queries": len(rows)}
    for k in (5, 10):
        out[f"hit@{k}"] = mean([hit_at_k(r["titles"], r["primary"], k) for r in rows])
        out[f"recall@{k}"] = mean([recall_at_k(r["titles"], r["primary"], k) for r in rows])
        out[f"precision@{k}"] = mean([precision_at_k(r["titles"], r["relevant"], k) for r in rows])
    out["mrr@10"] = mean([reciprocal_rank(r["titles"], r["primary"]) for r in rows])
    out["avg_passages_returned@5"] = mean([min(5, len(r["titles"])) for r in rows])
    return out
