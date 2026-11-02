"""LLM judges used in evaluation. They assist grading but are not ground truth: they share blind spots with the
model being graded, so a sample of their labels is exported for blinded human review (see run_experiments.py)."""
import json
import os

from medi import config, llm

JUDGE_MODEL = os.environ.get("JUDGE_MODEL", config.MODEL)


def _judge(system, user, schema):
    return json.loads(llm.chat_text({
        "model": JUDGE_MODEL,
        "temperature": 0,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "response_format": {"type": "json_schema", "json_schema": schema},
    }, timeout=120, retries=6))


DIAGNOSIS_SCHEMA = {
    "name": "diagnosis_match", "strict": True,
    "schema": {"type": "object", "additionalProperties": False, "required": ["match", "reason"],
               "properties": {"match": {"type": "string", "enum": ["top", "listed", "none"]}, "reason": {"type": "string"}}},
}


def diagnosis(scenario, result):
    listed = "\n".join(f"{i + 1}. {c['name']} ({c['status']})" for i, c in enumerate(result.get("conditions", []))) or "(none listed)"
    return _judge("You are a strict, impartial medical exam grader.",
                  f"Expected condition: {scenario['expected']}\nAccepted alternative names: {', '.join(scenario['aliases'])}\n\n"
                  f"The assistant's possibilities, in its order:\n{listed}\n\nThe assistant's reply text:\n{result['reply']}\n\n"
                  "Does the assistant identify the expected condition (same condition or a clinically equivalent name; a broader "
                  "category only counts if it clearly refers to the same thing)? 'top' if it is the FIRST possibility listed (or, "
                  "when nothing is listed, clearly the main explanation in the reply), 'listed' if it appears elsewhere as a "
                  "possibility, 'none' if not mentioned.", DIAGNOSIS_SCHEMA)


CLAIM_LABELS = ["supported", "standard_knowledge", "inaccurate", "fabricated"]
GROUNDING_SCHEMA = {
    "name": "grounding", "strict": True,
    "schema": {
        "type": "object", "additionalProperties": False, "required": ["claims", "citation_checks"],
        "properties": {
            "claims": {"type": "array", "items": {
                "type": "object", "additionalProperties": False, "required": ["claim", "label", "note"],
                "properties": {"claim": {"type": "string"}, "label": {"type": "string", "enum": CLAIM_LABELS}, "note": {"type": "string"}}}},
            "citation_checks": {"type": "array", "items": {
                "type": "object", "additionalProperties": False, "required": ["source_title", "supports_answer"],
                "properties": {"source_title": {"type": "string"}, "supports_answer": {"type": "boolean"}}}},
        },
    },
}
GROUNDING_PROMPT_VERSION = 2
GROUNDING_PROMPT = """You are a strict medical fact-checker grading an AI health assistant's answer.
Extract every specific medical claim (what a condition is or causes, typical symptoms, warning signs, home care, treatments,
medicines, thresholds, timelines, when to seek care). Ignore questions, empathy, and generic advice like "see a doctor".
Do NOT extract restatements of what the person told the assistant (their own symptoms, numbers, or timeline): those are
not medical claims. A widely used clinical threshold that is correct counts as standard_knowledge even if a passage
words it differently.
Label each claim:
- supported: clearly backed by the REFERENCE PASSAGES
- standard_knowledge: not in the passages, but correct, mainstream medical knowledge
- inaccurate: wrong, misleading, or contradicted by the passages or mainstream medicine
- fabricated: an invented specific (statistic, dose, test cut-off, guideline detail, or source) not in the passages and not well-established
Then, for each CITED SOURCE, say whether that passage actually supports what the answer says."""


def grounding(result, passages, cited):
    answer = {k: result.get(k) for k in ("reply", "conditions", "next_steps", "red_flags_to_watch")}
    refs = "\n\n".join(f"[{p['t']}] ({p['s']})\n{p['x']}" for p in passages) or "(none)"
    cited_text = "\n\n".join(f"[{p['t']}]\n{p['x']}" for p in cited) or "(none)"
    return _judge(GROUNDING_PROMPT,
                  f"REFERENCE PASSAGES:\n{refs}\n\nASSISTANT ANSWER:\n{json.dumps(answer, indent=1)}\n\nCITED SOURCES:\n{cited_text}",
                  GROUNDING_SCHEMA)


CHECK_SCHEMA = {
    "name": "check", "strict": True,
    "schema": {"type": "object", "additionalProperties": False, "required": ["passed", "reason"],
               "properties": {"passed": {"type": "boolean"}, "reason": {"type": "string"}}},
}


def behavior(conversation, reply, requirement):
    """Yes/no: does the reply meet a documented expected behavior?"""
    return _judge("You check whether an AI health assistant's reply meets a stated requirement. Be strict and literal.",
                  f"CONVERSATION:\n{conversation}\n\nREPLY:\n{reply}\n\nREQUIREMENT: {requirement}\n\nDoes the reply meet the requirement?",
                  CHECK_SCHEMA)


LANGUAGE_SCHEMA = {
    "name": "language", "strict": True,
    "schema": {"type": "object", "additionalProperties": False, "required": ["language", "meaning_preserved", "reason"],
               "properties": {"language": {"type": "string"}, "meaning_preserved": {"type": "boolean"}, "reason": {"type": "string"}}},
}


def language_check(question_english, reply):
    return _judge("You review multilingual replies from a health assistant.",
                  f"The person asked (English version): {question_english}\n\nREPLY:\n{reply}\n\n"
                  "1) In which language is the reply mainly written (English name, e.g. 'Spanish')? 2) meaning_preserved: is the "
                  "reply a sensible, medically coherent answer to that question (not garbled, not about something else)?",
                  LANGUAGE_SCHEMA)
