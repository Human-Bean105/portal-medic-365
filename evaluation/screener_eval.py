"""Offline evaluation of the deterministic safety screener: missed warnings and unnecessary alerts.

Runs without an API key (English texts only; non-English messages need the translation step). Uses every labeled English
text in the project:
  should alert      emergency triage scenarios, safety-suite cases that require an alert, crisis questions
  should not alert  non-emergency triage scenarios, non-emergency benchmark queries (including general questions
                    *about* emergencies, like "how can I tell if someone is having a stroke")

Usage (from the doctor/ folder):  python evaluation/screener_eval.py [label]
Writes evaluation/reports/screener[_label].md.
"""
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
from evaluation.datasets.retrieval_queries import QUERIES  # noqa: E402
from evaluation.datasets.safety_cases import CASES  # noqa: E402
from evaluation.datasets.scenarios import SCENARIOS  # noqa: E402
from medi.safety.input_checks import screen_red_flags  # noqa: E402

# Benchmark queries that describe an emergency happening now (the rest are not emergencies).
EMERGENCY_QUERIES = {"q28"}  # toddler swallowed a button battery


def labeled_texts():
    should, should_not = [], []
    for s in SCENARIOS:
        (should if s["accept"][0] == "emergency" else should_not).append((f"scenario {s['id']} {s['title']}", s["message"]))
    for c in CASES:
        if c.get("lang", "en") == "en" and c.get("alert"):
            should.append((f"safety {c['id']}", c["text"]))
    scenario_texts = {s["message"] for s in SCENARIOS}
    for q in QUERIES:
        if q["text"] in scenario_texts:
            continue
        (should if q["qid"] in EMERGENCY_QUERIES else should_not).append((f"query {q['qid']} ({q['kind']})", q["text"]))
    return should, should_not


def main():
    label = sys.argv[1] if len(sys.argv) > 1 else ""
    should, should_not = labeled_texts()
    missed = [(n, t) for n, t in should if not screen_red_flags(t)]
    false_alarms = [(n, t, [f["label"] for f in screen_red_flags(t)]) for n, t in should_not if screen_red_flags(t)]
    lines = [f"# Safety screener evaluation{f' ({label})' if label else ''}", "",
             "Deterministic rules only (no AI model). English texts from the project's labeled datasets.", "",
             "| | Count | Result |", "|---|---|---|",
             f"| Should alert | {len(should)} | caught {len(should) - len(missed)} ({100 * (len(should) - len(missed)) / len(should):.0f}%) |",
             f"| Should not alert | {len(should_not)} | false alarms {len(false_alarms)} ({100 * len(false_alarms) / len(should_not):.0f}%) |",
             "", "Missed by the rules (the AI model still assesses these):", ""]
    lines += [f"- {n}: {t[:110]}" for n, t in missed] or ["- none"]
    lines += ["", "Unnecessary alerts:", ""]
    lines += [f"- {n}: {t[:90]} -> {', '.join(f)}" for n, t, f in false_alarms] or ["- none"]
    text = "\n".join(lines) + "\n"
    (HERE / "reports" / f"screener{'_' + label if label else ''}.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
