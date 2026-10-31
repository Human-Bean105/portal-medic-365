"""Baseline latency of the v1 pipeline, stage by stage, on the first message of each scenario.

Usage (from the doctor/ folder):  python eval/measure_latency.py
Writes eval/latency_v1.json and prints a summary.
"""
import json
import statistics
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
import api._medi as medi  # noqa: E402
from scenarios import SCENARIOS  # noqa: E402


def timed(fn, *args, **kwargs):
    start = time.perf_counter()
    value = fn(*args, **kwargs)
    return value, round((time.perf_counter() - start) * 1000)


def run(s):
    messages = [{"role": "user", "content": s["message"]}]
    _, screen_ms = timed(medi.screen_message, s["message"])
    query, rewrite_ms = timed(medi.retrieval_query, messages)
    passages, search_ms = timed(medi.retrieve, query)
    payload, _, _ = medi.consult_request(messages, {}, s["patient"], rag=False)
    payload["messages"][0]["content"] += "\n\n" + medi.reference_note(passages)
    data, generate_ms = timed(medi.post_json, payload)
    usage = data.get("usage", {})
    return {"id": s["id"], "screen_ms": screen_ms, "query_rewrite_ms": rewrite_ms, "retrieval_ms": search_ms,
            "generation_ms": generate_ms, "total_ms": screen_ms + rewrite_ms + search_ms + generate_ms,
            "prompt_tokens": usage.get("prompt_tokens"), "completion_tokens": usage.get("completion_tokens")}


def p95(values):
    values = sorted(values)
    return values[min(len(values) - 1, round(0.95 * (len(values) - 1)))]


def main():
    rows = []
    for s in SCENARIOS[:20]:
        rows.append(run(s))
        print(f"  #{s['id']:>2} total {rows[-1]['total_ms']} ms")
    summary = {}
    for key in ("screen_ms", "query_rewrite_ms", "retrieval_ms", "generation_ms", "total_ms", "prompt_tokens", "completion_tokens"):
        values = [r[key] for r in rows if r[key] is not None]
        summary[key] = {"mean": round(statistics.mean(values)), "p95": p95(values)}
    out = {"pipeline": "v1", "model": medi.MODEL, "date": time.strftime("%Y-%m-%d"), "summary": summary, "results": rows}
    (HERE / "latency_v1.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
