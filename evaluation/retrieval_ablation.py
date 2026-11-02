"""Measures what the analyzer (better search terms) and the reranker add, on the retrieval benchmark.

Four combinations on the production retriever: {v1 rewrite, analyzer} x {no rerank, rerank top 15}.
Model outputs (analyzer queries, reranker grades) are cached in evaluation/cache/ so reruns are repeatable.

Usage (from the doctor/ folder):  python evaluation/retrieval_ablation.py
Writes evaluation/reports/retrieval_ablation.json and .md.
"""
import hashlib
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
from evaluation import metrics  # noqa: E402
from evaluation.retrieval_bench import BENCH, embed_queries  # noqa: E402
from medi import analyzer, config  # noqa: E402
from medi.rag import rerank, retrieval  # noqa: E402

CACHE = HERE / "cache"
RERANK_POOL = 15


def cached(name, keys, fn):
    """Runs fn(key) for keys not yet in evaluation/cache/<name>.json, in parallel, and returns the whole cache."""
    CACHE.mkdir(exist_ok=True)
    path = CACHE / f"{name}.json"
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    todo = [k for k in keys if k not in data]
    with ThreadPoolExecutor(max_workers=4) as pool:
        for k, v in zip(todo, pool.map(fn, todo)):
            data[k] = v
    path.write_text(json.dumps(data, indent=0, ensure_ascii=False), encoding="utf-8")
    return data


def main():
    bench = json.loads(BENCH.read_text(encoding="utf-8"))
    queries = bench["queries"]
    by_text = {q["text"]: q for q in queries}
    analyses = cached("analyzer", [q["text"] for q in queries],
                      lambda text: analyzer.analyze([{"role": "user", "content": text}], by_text[text]["mode"]))
    analyzer_queries = [dict(q, search_query=analyzer.search_text(analyses[q["text"]], q["text"])) for q in queries]

    cfg = config.DEFAULT.but(top_k=10, candidates=40)
    results = {}
    variants = {"v1 rewrite": [None, (RERANK_POOL, 450)], "analyzer": [None, (RERANK_POOL, 450), (10, 300)]}
    for qname, qs in (("v1 rewrite", queries), ("analyzer", analyzer_queries)):
        qvecs = embed_queries(qs)
        full = [retrieval.candidates(q["search_query"], cfg, q["mode"], qvec=v) for q, v in zip(qs, qvecs)]
        for setting in variants[qname]:
            pool_size, chars = setting or (RERANK_POOL, 450)
            pools = [c[:pool_size] for c in full]
            # The key includes the candidate ids, so a changed candidate list (embeddings vary slightly) is regraded.
            keyed = {f"{qname}|{q['qid']}|{chars}|{hashlib.sha1(''.join(p['id'] for p in pool).encode()).hexdigest()[:10]}": (q, pool)
                     for q, pool in zip(qs, pools)}

            def grade(key, chars=chars):
                q, pool = keyed[key]
                graded = rerank.rerank(q["text"], pool, chars=chars)
                return [[p["id"], p["grade"]] for p in graded]

            grades = cached("rerank", list(keyed), grade) if setting else {}
            rows = []
            for key, (q, pool) in keyed.items():
                if setting:
                    order = {pid: (n, g) for n, (pid, g) in enumerate(grades[key])}
                    ranked = sorted(pool, key=lambda p: order[p["id"]][0])
                    ranked = [{**p, "grade": order[p["id"]][1]} for p in ranked]
                else:
                    ranked = full[[x["qid"] for x in qs].index(q["qid"])]
                passages = retrieval.select(ranked, cfg)
                rows.append({"qid": q["qid"], "kind": q["kind"], "titles": [p["t"] for p in passages],
                             "top_cosine": pool[0]["cosine"] if pool else 0.0,
                             "grades": [p.get("grade") for p in passages],
                             "primary": q["primary"], "relevant": q["primary"] + q["related"]})
            label = qname + (f" + rerank {pool_size}x{chars}" if setting else "")
            summary = metrics.retrieval_summary(rows)
            for kind in sorted({r["kind"] for r in rows if r["primary"]}):
                sub = [r for r in rows if r["kind"] == kind]
                summary[f"hit@5[{kind}]"] = metrics.mean([metrics.hit_at_k(r["titles"], r["primary"], 5) for r in sub])
            results[label] = {"summary": summary, "per_query": rows}
            print("  done:", label)

    report = {"benchmark": bench["dataset"], "date": time.strftime("%Y-%m-%d"), "retriever": cfg.__dict__,
              "rerank_pool": RERANK_POOL, "results": results}
    (HERE / "reports" / "retrieval_ablation.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    keys = ["hit@5", "recall@5", "precision@5", "mrr@10", "recall@10"]
    kinds = sorted(k for k in next(iter(results.values()))["summary"] if k.startswith("hit@5["))
    lines = ["# Retrieval ablation: analyzer query and reranking", "",
             f"Production retriever ({cfg.retriever} {cfg.fusion}, alpha {cfg.alpha}), {len(queries)} queries, rerank pool {RERANK_POOL}.", "",
             "| Configuration | " + " | ".join(keys) + " | " + " | ".join(k[6:-1] for k in kinds) + " |",
             "|---" * (len(keys) + len(kinds) + 1) + "|"]
    for label, r in results.items():
        lines.append(f"| {label} | " + " | ".join(str(r["summary"][k]) for k in keys + kinds) + " |")
    (HERE / "reports" / "retrieval_ablation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
