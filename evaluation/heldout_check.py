"""Checks that retrieval settings chosen on the benchmark aren't just overfitted to it.

Splits the queries into two halves (alternating), picks the best configuration on one half by MRR@10 and Hit@5,
and reports how every configuration does on the other half, in both directions.

Usage (from the doctor/ folder):  python evaluation/heldout_check.py retrievers chunking
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
from evaluation import metrics  # noqa: E402


def score(rows):
    s = metrics.retrieval_summary(rows)
    return s["hit@5"], s["mrr@10"], s["recall@5"], s["precision@5"]


def main():
    results = {}
    for name in sys.argv[1:] or ["retrievers", "chunking"]:
        report = json.loads((HERE / "reports" / f"retrieval_{name}.json").read_text(encoding="utf-8"))
        results.update(report["results"])
    lines = []
    for tune, test in ((0, 1), (1, 0)):
        halves = {label: ([r for n, r in enumerate(v["per_query"]) if n % 2 == tune],
                          [r for n, r in enumerate(v["per_query"]) if n % 2 == test]) for label, v in results.items()}
        best = max(halves, key=lambda label: (score(halves[label][0])[1], score(halves[label][0])[0]))
        lines.append(f"Tuned on half {tune}, tested on half {test}: picked '{best}'")
        for label, (_, held) in sorted(halves.items(), key=lambda kv: -score(kv[1][1])[1]):
            hit, mrr, rec, prec = score(held)
            lines.append(f"  {'*' if label == best else ' '} {label:<50} hit@5 {hit:.3f}  mrr {mrr:.3f}  recall@5 {rec:.3f}  precision@5 {prec:.3f}")
    text = "\n".join(lines)
    (HERE / "reports" / "retrieval_heldout.txt").write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
