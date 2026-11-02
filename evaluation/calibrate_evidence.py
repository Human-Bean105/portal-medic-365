"""Calibrates the evidence-sufficiency levels against the retrieval benchmark.

For each query, the evidence status comes from the reranker's best grade among the passages shown to the model
(see medi/rag/evidence.py). A status is useful only if it predicts whether the passages really cover the question,
so this reports, per status, how often a labeled primary topic is among the top 5 passages. For comparison it does the
same for v1's raw cosine-similarity score, bucketed.

Usage (from the doctor/ folder, after retrieval_ablation.py):  python evaluation/calibrate_evidence.py
Writes evaluation/reports/evidence_calibration.md.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
from evaluation import metrics  # noqa: E402
from medi.rag.evidence import status_from_grades  # noqa: E402


def main():
    report = json.loads((HERE / "reports" / "retrieval_ablation.json").read_text(encoding="utf-8"))
    all_rows = report["results"]["analyzer + rerank 15x450"]["per_query"]
    rows = [r for r in all_rows if r["primary"]]
    oos = [r for r in all_rows if not r["primary"]]
    lines = ["# Evidence sufficiency calibration", "",
             "Answerable queries: per evidence status, the number of queries and the share whose top 5 passages include "
             "a labeled primary topic (hit@5) or any relevant topic. Out-of-scope queries (nothing relevant exists in the "
             "knowledge base) are counted separately: ideally they are never rated sufficient.", "",
             "| Status (from reranker grades) | Answerable queries | Hit@5 (primary) | Any relevant topic in top 5 | Out-of-scope queries |",
             "|---|---|---|---|---|"]
    for status in ("sufficient", "partial", "insufficient", "none"):
        sub = [r for r in rows if status_from_grades(r["grades"][:5]) == status]
        hit = metrics.mean([metrics.hit_at_k(r["titles"], r["primary"], 5) for r in sub])
        rel = metrics.mean([int(any(t in r["relevant"] for t in r["titles"][:5])) for r in sub])
        n_oos = sum(status_from_grades(r["grades"][:5]) == status for r in oos)
        lines.append(f"| {status} | {len(sub)} | {hit} | {rel} | {n_oos} |")
    lines += ["", "Out-of-scope queries and their status: " + ", ".join(
        f"{r['qid']}={status_from_grades(r['grades'][:5])}" for r in oos)]
    lines += ["", "For comparison, v1's signal: the top passage's cosine similarity (same queries, before reranking).", "",
              "| Top cosine | Queries | Hit@5 (primary) |", "|---|---|---|"]
    for lo, hi in ((0.0, 0.4), (0.4, 0.5), (0.5, 0.6), (0.6, 1.01)):
        sub = [r for r in rows if lo <= (r["top_cosine"] or 0) < hi]
        lines.append(f"| {lo:.1f}-{min(hi, 1.0):.1f} | {len(sub)} | {metrics.mean([metrics.hit_at_k(r['titles'], r['primary'], 5) for r in sub])} |")
    misses = [r for r in rows if status_from_grades(r["grades"][:5]) == "sufficient" and not metrics.hit_at_k(r["titles"], r["primary"], 5)]
    lines += ["", f"Queries rated sufficient without a primary topic in the top 5: {[r['qid'] for r in misses]}"]
    text = "\n".join(lines) + "\n"
    (HERE / "reports" / "evidence_calibration.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
