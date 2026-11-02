"""End-to-end experiments A-E on the 50 triage scenarios (dataset: evaluation/datasets/scenarios.py).

Each scenario is a conversation of up to 3 turns: the opening message, then, if Medi is still gathering information,
"I don't know anything else... please give me your assessment" (as in the v1 evaluation). Every configuration gets the
same scenarios and the same follow-up. Every answer is graded the same way:
  triage       final level of care vs the scenario's accepted levels (correct / over / under)
  diagnosis    LLM judge: is the expected condition the top possibility, listed, or missing
  grounding    LLM judge: each medical claim labeled supported / standard knowledge / inaccurate / fabricated, judged
               against the same reference passages for every configuration (the production retriever's top 5 for the
               scenario, plus whatever that configuration retrieved), and each cited source checked
  rules        percentages, specific doses, emergency replies starting with the action
  latency/cost from the pipeline trace

Usage (from the doctor/ folder):  python evaluation/run_experiments.py [A B C D E]
Writes evaluation/reports/experiments.json, experiments.csv, experiments.md, and a blinded human-review sample.
"""
import csv
import json
import os
import random
import re
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
os.environ.setdefault("MEDI_LLM_RETRIES", "6")
os.environ.setdefault("MEDI_LOG", "0")
from evaluation import judges, metrics  # noqa: E402
from evaluation.configs import EXPERIMENTS  # noqa: E402
from evaluation.datasets.scenarios import SCENARIOS  # noqa: E402
from medi import config, intake, orchestrator  # noqa: E402
from medi.rag import retrieval  # noqa: E402
from medi.trace import Trace  # noqa: E402

FOLLOW_UP = ("I don't know anything else beyond what I've already told you, and nothing else is going on. "
             "Please give me your assessment and tell me what I should do.")
RANK = {"home_care": 0, "clinic": 1, "urgent_care": 2, "emergency": 3}
PERCENT = re.compile(r"\d+(\.\d+)?\s?%")
DOSE = re.compile(r"\b\d+(\.\d+)?\s?(mg|mcg|ml|mL|milligrams?)\b")
ACTION_FIRST = re.compile(r"call|emergency|911|988|112|999|go to|nearest", re.I)
CLEAN = ("safety_alerts", "sources", "retrieved", "analysis", "evidence_status", "limitations", "trace")
DATASET_VERSION = "scenarios-v1 (50 textbook vignettes, unchanged since the v1 evaluation)"


def judge_refs(scenario):
    """The shared reference set every configuration is graded against."""
    bench = {q["qid"]: q for q in json.loads((HERE / "datasets" / "retrieval_benchmark.json").read_text(encoding="utf-8"))["queries"]}
    query = bench.get(f"s{scenario['id']}", {}).get("search_query", scenario["message"])
    return retrieval.search(query, config.DEFAULT)


def converse(scenario, cfg):
    messages = [{"role": "user", "content": scenario["message"]}]
    turns = []
    for turn_no in range(3):
        trace = Trace("experiment")
        turn = intake.parse({"messages": messages, "patient": scenario["patient"]})
        result = orchestrator.consult(turn, cfg, trace)
        turns.append({"level": result["triage"]["level"], "stage": result["stage"],
                      "alerts": [a["label"] for a in result["safety_alerts"]], "trace": trace.summary()})
        if result["stage"] == "assessment" or result["triage"]["level"] == "emergency" or turn_no == 2:
            return result, turns
        messages += [{"role": "assistant", "content": json.dumps({k: v for k, v in result.items() if k not in CLEAN})},
                     {"role": "user", "content": FOLLOW_UP}]


def run_case(job):
    """One graded conversation. Any failure (pipeline or judge) is recorded as an error row, never raised."""
    key, scenario = job
    try:
        return grade_case(key, scenario, *converse(scenario, EXPERIMENTS[key]))
    except Exception as e:
        return {"config": key, "id": scenario["id"], "error": f"{type(e).__name__}: {e}", "trace": traceback.format_exc()[-500:]}


def grade_case(key, scenario, result, turns):
    level = result["triage"]["level"]
    accept = scenario["accept"]
    triage = "correct" if level in accept else ("under" if RANK.get(level, -1) < min(RANK[a] for a in accept) else "over")
    shown = result["retrieved"]
    refs = {(p["t"], p["x"]): p for p in judge_refs(scenario) + shown}
    cited = [shown[n - 1] for n in result.get("citations", []) if 1 <= n <= len(shown)]
    grade = judges.grounding(result, list(refs.values()), cited)
    counts = {label: sum(c["label"] == label for c in grade["claims"]) for label in judges.CLAIM_LABELS}
    diag = judges.diagnosis(scenario, result)
    text = json.dumps({k: result.get(k) for k in ("reply", "conditions", "next_steps", "red_flags_to_watch")})
    traces = [t["trace"] for t in turns]
    return {
        "config": key, "id": scenario["id"], "group": scenario["group"], "title": scenario["title"],
        "accept": accept, "final_level": level, "triage": triage, "turns": len(turns),
        "first_turn_level": turns[0]["level"], "screener_alerts": turns[0]["alerts"],
        "diagnosis": diag["match"], "diagnosis_reason": diag["reason"],
        "claims": grade["claims"], "claim_counts": counts, "citation_checks": grade["citation_checks"],
        "sources": [s["title"] for s in result["sources"]], "retrieved": [p["t"] for p in shown],
        "evidence_status": result.get("evidence_status"),
        "has_percentage": bool(PERCENT.search(text)), "has_specific_dose": bool(DOSE.search(text)),
        "action_first": bool(ACTION_FIRST.search(result["reply"][:140])) if level == "emergency" else None,
        "validation_failed": [f for t in traces for s in t["stages"] if s["stage"] == "output_validation" for f in s.get("failed", [])],
        "turn_ms": [t["total_ms"] for t in traces], "cost_usd": round(sum(t["cost_usd"] for t in traces), 5),
        "stage_ms": [{s["stage"]: s["ms"] for s in t["stages"]} for t in traces],
        "reply": result["reply"],
    }


def summarize(rows):
    ok = [r for r in rows if "error" not in r]
    n = len(ok)
    pct = lambda k: round(100 * k / n, 1) if n else None  # noqa: E731
    em = [r for r in ok if r["accept"][0] == "emergency"]
    claims = {label: sum(r["claim_counts"][label] for r in ok) for label in judges.CLAIM_LABELS}
    total_claims = sum(claims.values()) or 1
    checks = [c for r in ok for c in r["citation_checks"]]
    turn_ms = [ms for r in ok for ms in r["turn_ms"]]
    return {
        "conversations": len(rows), "failures": len(rows) - n,
        "triage_acceptable_%": pct(sum(r["triage"] == "correct" for r in ok)),
        "under_triage": sum(r["triage"] == "under" for r in ok),
        "over_triage": sum(r["triage"] == "over" for r in ok),
        "emergencies_detected": f"{sum(r['final_level'] == 'emergency' for r in em)}/{len(em)}",
        "emergency_on_first_message": f"{sum(r['first_turn_level'] == 'emergency' for r in em)}/{len(em)}",
        "diagnosis_top1_%": pct(sum(r["diagnosis"] == "top" for r in ok)),
        "diagnosis_listed_%": pct(sum(r["diagnosis"] in ("top", "listed") for r in ok)),
        "claims": total_claims,
        "grounded_claim_rate_%": round(100 * claims["supported"] / total_claims, 1),
        "standard_knowledge_%": round(100 * claims["standard_knowledge"] / total_claims, 1),
        "unsupported_claim_rate_%": round(100 * (claims["inaccurate"] + claims["fabricated"]) / total_claims, 1),
        "answers_with_unsupported_claim": sum(1 for r in ok if r["claim_counts"]["inaccurate"] + r["claim_counts"]["fabricated"]),
        "answers_showing_sources": sum(1 for r in ok if r["sources"]),
        "citation_support_rate_%": round(100 * sum(c["supports_answer"] for c in checks) / len(checks), 1) if checks else None,
        "percentage_violations": sum(r["has_percentage"] for r in ok),
        "specific_dose_mentions": sum(r["has_specific_dose"] for r in ok),
        "turn_latency_ms_mean": round(sum(turn_ms) / len(turn_ms)) if turn_ms else None,
        "turn_latency_ms_p95": metrics.percentile(turn_ms, 95),
        "cost_usd_per_conversation": round(sum(r["cost_usd"] for r in ok) / n, 4) if n else None,
    }


def write_reports(rows, keys):
    stamp = time.strftime("%Y-%m-%d %H:%M")
    summaries = {k: summarize([r for r in rows if r["config"] == k]) for k in keys}
    report = {"date": stamp, "dataset": DATASET_VERSION, "generator_model": config.MODEL, "helper_model": config.FAST_MODEL,
              "judge_model": judges.JUDGE_MODEL, "configs": {k: EXPERIMENTS[k].__dict__ for k in keys},
              "summary": summaries, "cases": rows}
    out = HERE / "reports"
    (out / "experiments.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")

    fields = ["config", "id", "group", "title", "accept", "final_level", "triage", "diagnosis", "turns", "evidence_status",
              "sources", "claim_counts", "validation_failed", "turn_ms", "cost_usd", "error"]
    with open(out / "experiments.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: (json.dumps(r[k]) if isinstance(r.get(k), (list, dict)) else r.get(k)) for k in fields})

    metric_names = list(next(iter(summaries.values())).keys())
    lines = [f"# End-to-end experiments A-E", "", f"Run {stamp}. Generator {config.MODEL}, helper {config.FAST_MODEL}, judge "
             f"{judges.JUDGE_MODEL}. Dataset: {DATASET_VERSION}. LLM-judge results assist grading but are not ground truth.", ""]
    for k in keys:
        lines.append(f"- **{k}**: {EXPERIMENTS[k].name}")
    lines += ["", "| Metric | " + " | ".join(keys) + " |", "|---" * (len(keys) + 1) + "|"]
    for m in metric_names:
        lines.append(f"| {m} | " + " | ".join(str(summaries[k][m]) for k in keys) + " |")
    problems = [r for r in rows if "error" not in r and (r["triage"] != "correct" or r["claim_counts"]["inaccurate"] + r["claim_counts"]["fabricated"])]
    lines += ["", "## Cases to review", ""]
    for r in problems:
        bad = [c for c in r["claims"] if c["label"] in ("inaccurate", "fabricated")]
        lines.append(f"- {r['config']} #{r['id']} {r['title']}: level {r['final_level']} ({r['triage']}, accepted "
                     f"{'/'.join(r['accept'])})" + "".join(f"; {c['label']}: \"{c['claim']}\" ({c['note']})" for c in bad))
    for r in rows:
        if "error" in r:
            lines.append(f"- {r['config']} #{r['id']}: ERROR {r['error']}")
    (out / "experiments.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Blinded human-review sample: answers shuffled, configuration hidden behind a code.
    rng = random.Random(7)
    ok = [r for r in rows if "error" not in r]
    sample = rng.sample(ok, min(30, len(ok)))
    with open(out / "human_review_sample.csv", "w", newline="", encoding="utf-8") as f, \
         open(out / "human_review_key.csv", "w", newline="", encoding="utf-8") as g:
        w, kw = csv.writer(f), csv.writer(g)
        w.writerow(["code", "scenario", "reply", "judge_claim_labels", "your_rating_1to5", "your_notes"])
        kw.writerow(["code", "config", "scenario_id"])
        for n, r in enumerate(sample, 1):
            code = f"R{n:02d}"
            w.writerow([code, r["title"], r["reply"], json.dumps(r["claim_counts"]), "", ""])
            kw.writerow([code, r["config"], r["id"]])
    print("\n".join(lines[:len(metric_names) + 10]))


def main():
    keys = [k for k in sys.argv[1:] if k in EXPERIMENTS] or list(EXPERIMENTS)
    jobs = [(k, s) for k in keys for s in SCENARIOS]
    print(f"Running {len(jobs)} conversations ({', '.join(keys)})...")
    rows = []
    with ThreadPoolExecutor(max_workers=5) as pool:
        for r in pool.map(run_case, jobs):
            rows.append(r)
            if len(rows) % 25 == 0:
                print(f"  {len(rows)}/{len(jobs)} done", flush=True)
    write_reports(rows, keys)


if __name__ == "__main__":
    main()
