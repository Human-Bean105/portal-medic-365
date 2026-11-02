"""Retrieval benchmark: runs several retrieval configurations on the same labeled queries and compares them.

Every configuration receives exactly the same stored search query and the same query embedding, so differences come
only from the index and the retrieval method.

Usage (from the doctor/ folder):
  python evaluation/retrieval_bench.py                 # retriever comparison on the production index settings
  python evaluation/retrieval_bench.py --chunking      # also compare chunk sizes (indexes in evaluation/indexes/)
Writes evaluation/reports/retrieval_<name>.json and .md.
"""
import argparse
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
from evaluation import metrics  # noqa: E402
from medi import config, llm  # noqa: E402
from medi.rag import index, retrieval  # noqa: E402

BENCH = HERE / "datasets" / "retrieval_benchmark.json"
V1 = config.DEFAULT.but(index="rag/medi_index_v1.json", retriever="vector", min_score=0.3, candidates=40, top_k=10)


def retriever_configs(idx_path):
    base = config.DEFAULT.but(index=idx_path, top_k=10)
    return {
        "B  v1: vector, old index, cutoff 0.3": V1,
        "vector, new index": base.but(retriever="vector", min_score=0.0),
        "bm25, new index": base.but(retriever="bm25"),
        "hybrid rrf a=0.5": base.but(retriever="hybrid", fusion="rrf", alpha=0.5),
        "hybrid rrf a=0.7": base.but(retriever="hybrid", fusion="rrf", alpha=0.7),
        "hybrid weighted a=0.5": base.but(retriever="hybrid", fusion="weighted", alpha=0.5),
        "hybrid weighted a=0.7": base.but(retriever="hybrid", fusion="weighted", alpha=0.7),
        "hybrid rrf a=0.5 + wellbeing boost": base.but(retriever="hybrid", fusion="rrf", alpha=0.5, wellbeing_boost=0.3),
        "hybrid weighted a=0.8": base.but(retriever="hybrid", fusion="weighted", alpha=0.8),
        "hybrid weighted a=0.7 + wellbeing boost": base.but(retriever="hybrid", fusion="weighted", alpha=0.7, wellbeing_boost=0.3),
        "hybrid weighted a=0.7, wellbeing a=0.9": base.but(retriever="hybrid", fusion="weighted", alpha=0.7, alpha_wellbeing=0.9),
        "hybrid weighted a=0.7, wellbeing a=0.9 + boost": base.but(retriever="hybrid", fusion="weighted", alpha=0.7,
                                                                   alpha_wellbeing=0.9, wellbeing_boost=0.3),
    }


def embed_queries(queries):
    vectors = []
    for start in range(0, len(queries), 100):
        vectors += llm.embed([q["search_query"] for q in queries[start:start + 100]], 256, timeout=60)
    return [[x / (sum(y * y for y in v) ** 0.5) for x in v] for v in vectors]


def run(cfg, queries, qvecs):
    rows, timings = [], []
    index.get(cfg.index).bm25  # build the keyword index before timing
    for q, qvec in zip(queries, qvecs):
        start = time.perf_counter()
        passages = retrieval.select(retrieval.candidates(q["search_query"], cfg, q["mode"], qvec=qvec), cfg)
        timings.append((time.perf_counter() - start) * 1000)
        rows.append({"qid": q["qid"], "kind": q["kind"], "titles": [p["t"] for p in passages],
                     "scores": [p["score"] for p in passages], "cosine": [p.get("cosine") for p in passages],
                     "primary": q["primary"], "relevant": q["primary"] + q["related"]})
    return rows, timings


def summarize(rows, timings):
    out = metrics.retrieval_summary(rows)
    for kind in sorted({r["kind"] for r in rows}):
        sub = [r for r in rows if r["kind"] == kind]
        out[f"hit@5[{kind}]"] = metrics.mean([metrics.hit_at_k(r["titles"], r["primary"], 5) for r in sub])
    out["search_ms_mean"] = round(sum(timings) / len(timings), 1)
    out["search_ms_p95"] = round(metrics.percentile(timings, 95), 1)
    return out


def write_report(name, results, bench):
    report = {"benchmark": bench["dataset"], "label_model": bench["label_model"], "date": time.strftime("%Y-%m-%d"),
              "queries": len(bench["queries"]), "results": results}
    (HERE / "reports").mkdir(exist_ok=True)
    (HERE / "reports" / f"retrieval_{name}.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    keys = ["hit@5", "recall@5", "precision@5", "mrr@10", "recall@10", "search_ms_mean"]
    lines = [f"# Retrieval benchmark: {name}", "",
             f"{len(bench['queries'])} synthetic queries, silver labels by {bench['label_model']} (see dataset note). "
             f"Run {report['date']}.", "",
             "| Configuration | " + " | ".join(keys) + " |", "|---" * (len(keys) + 1) + "|"]
    for label, r in results.items():
        lines.append(f"| {label} | " + " | ".join(str(r["summary"][k]) for k in keys) + " |")
    kinds = sorted(k for k in next(iter(results.values()))["summary"] if k.startswith("hit@5["))
    lines += ["", "Hit@5 by query type:", "", "| Configuration | " + " | ".join(k[6:-1] for k in kinds) + " |",
              "|---" * (len(kinds) + 1) + "|"]
    for label, r in results.items():
        lines.append(f"| {label} | " + " | ".join(str(r["summary"][k]) for k in kinds) + " |")
    (HERE / "reports" / f"retrieval_{name}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", default="evaluation/indexes/c900_o1.json")
    ap.add_argument("--chunking", action="store_true")
    ap.add_argument("--name", default="retrievers")
    args = ap.parse_args()
    bench = json.loads(BENCH.read_text(encoding="utf-8"))
    queries = bench["queries"]
    qvecs = embed_queries(queries)

    if args.chunking:
        best = config.DEFAULT.but(top_k=10)
        configs = {"B  v1: vector, old index, cutoff 0.3": V1}
        for path in sorted((HERE / "indexes").glob("c*.json")):
            configs[f"{best.retriever} {best.fusion} a={best.alpha}, {path.stem}"] = best.but(index=f"evaluation/indexes/{path.name}")
    else:
        configs = retriever_configs(args.index)

    results = {}
    for label, cfg in configs.items():
        rows, timings = run(cfg, queries, qvecs)
        results[label] = {"config": cfg.__dict__, "summary": summarize(rows, timings), "per_query": rows}
        print(f"  done: {label}")
    write_report(args.name, results, bench)


if __name__ == "__main__":
    main()
