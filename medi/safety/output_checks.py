"""Deterministic checks on every answer before it reaches the person. Safe, mechanical problems are repaired;
anything that needs judgment is flagged in the trace for review (and counted in evaluation)."""
import re

from .. import language
from . import escalation

PERCENT = re.compile(r"\d+(\.\d+)?\s?%")
DOSE = re.compile(r"\b\d+(\.\d+)?\s?(mg|mcg|µg|ml|mL|milligrams?|micrograms?|units?)\b", re.I)
CERTAIN = re.compile(r"\b(you definitely have|you certainly have|this is definitely|i can confirm|confirmed diagnosis|"
                     r"you have been diagnosed)\b", re.I)
WB_DIAGNOSIS = re.compile(r"\byou (have|are suffering from) (clinical )?(depression|bipolar|ptsd|adhd|ocd|an? (anxiety|eating|panic|"
                          r"personality) disorder)\b", re.I)
EMERGENCY_START = re.compile(r"^\s*\*\*|911|112|999|\b000\b", re.I)
EMERGENCY_ACTION = "**Call 911 (or your local emergency number) now.**"


def _texts(result):
    """Everything the person will read, as one string."""
    parts = [result.get("reply", "")]
    parts += [result.get("triage", {}).get("headline", "")]
    for c in result.get("conditions", []):
        parts += [c.get("name", ""), c.get("explanation", "")]
    for key in ("next_steps", "red_flags_to_watch"):
        parts += result.get(key, [])
    return "\n".join(parts)


def validate(result, flags, passages, mode="health", lang="en"):
    """Returns (result, checks). Each check is {"check", "passed", "action"}; action is "repaired" or "flagged"."""
    checks = []

    def record(name, passed, action=None):
        checks.append({"check": name, "passed": passed, **({"action": action} if not passed and action else {})})

    citations = result.get("citations", [])
    valid = [n for n in citations if isinstance(n, int) and 1 <= n <= len(passages)]
    record("citations_point_to_retrieved_passages", valid == citations, "repaired")
    result["citations"] = valid

    if escalation.is_crisis(result, flags):
        had_line = bool(escalation.CRISIS_NUMBER.search(result.get("reply", "")))
        result = escalation.ensure_crisis_line(result, flags, lang)
        record("crisis_reply_includes_988_and_911", had_line, "repaired")

    text = _texts(result)
    record("no_numeric_probabilities", not PERCENT.search(text), "flagged")
    record("no_specific_doses", not DOSE.search(text), "flagged")

    if mode == "wellbeing":
        record("no_mental_health_diagnosis", not WB_DIAGNOSIS.search(result.get("reply", "")), "flagged")
        return result, checks

    record("no_unjustified_certainty", not CERTAIN.search(text), "flagged")
    level = result.get("triage", {}).get("level")
    physical = [f for f in flags if f["label"] not in escalation.MENTAL_HEALTH_FLAGS]
    if level == "emergency":
        starts_with_action = bool(EMERGENCY_START.search(result.get("reply", "")[:200]))
        if not starts_with_action:
            result["reply"] = language.ui_text(EMERGENCY_ACTION, lang) + "\n\n" + result.get("reply", "")
        record("emergency_reply_starts_with_action", starts_with_action, "repaired")
    if physical:
        # The emergency screen is already showing; a lower level here needs a human look, not an automatic change,
        # because the person may have said the symptom isn't happening now.
        record("level_matches_screener_alert", level == "emergency", "flagged")
    return result, checks
