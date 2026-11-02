"""Intent classification and structured information extraction, in one small-model call per turn.

The analyzer reads the conversation and returns what the person wants (intent), what they've reported, what's still
unknown, and an English search query for retrieval. Its output is the turn's conversation state: it's rebuilt from the
conversation each turn and never stored. It's an aid, not a decision-maker: safety decisions never depend on it."""
import json

from . import config, llm
from .conversation import message_text

INTENTS = ["symptom_information", "health_education", "wellbeing_support", "emergency_concern", "follow_up",
           "visit_preparation", "non_health"]
S = {"type": "string"}
LIST = {"type": "array", "items": S}
SCHEMA = {
    "name": "turn_analysis",
    "strict": True,
    "schema": {
        "type": "object", "additionalProperties": False,
        "required": ["intent", "language", "reported_symptoms", "duration", "severity", "relevant_context",
                     "already_answered", "missing_information", "search_query", "search_topics"],
        "properties": {
            "intent": {"type": "string", "enum": INTENTS},
            "language": S,
            "reported_symptoms": LIST,
            "duration": S,
            "severity": S,
            "relevant_context": LIST,
            "already_answered": LIST,
            "missing_information": LIST,
            "search_query": S,
            "search_topics": LIST,
        },
    },
}
PROMPT = """You analyze one turn of a conversation between a person and Medi, an AI health and wellbeing assistant.
Return JSON describing the conversation so far, focused on the person's latest message. Rules:
- Use only what the person actually said. Never invent symptoms, durations, severities, or history. Use "" or [] when unknown.
- "intent" of the latest message: symptom_information (describing symptoms or an injury), health_education (a general
  question about a condition, test, medicine, or prevention), wellbeing_support (stress, mood, sleep, loneliness, coping),
  emergency_concern (they describe something that could be an emergency), follow_up (answering Medi's question or adding
  detail), visit_preparation (help preparing for or understanding a visit), non_health (unrelated to health).
- "language": the language the person writes in (e.g. English, Spanish).
- "reported_symptoms", "duration", "severity", "relevant_context" (age, conditions, medicines, pregnancy, exposures):
  in short English phrases.
- "already_answered": short English notes of details the person has already given, so Medi doesn't ask again.
- "missing_information": the 1-3 most useful details Medi still needs (empty for education or non-health questions).
- "search_query": one English line of clinical terms to look up reference material for the latest message in context.
- "search_topics": 2-4 consumer health topic names an encyclopedia like MedlinePlus would file this under, from general
  to specific (e.g. for a warfarin question: "Blood Thinners"; for itchy, watery eyes every spring: "Hay Fever").
  Use the condition or drug-class name, not a symptom list."""


def analyze(messages, mode="health", usage=None):
    turns = [f"{'Person' if m['role'] == 'user' else 'Medi'}: {_brief(m)}" for m in messages[-12:]]
    out = json.loads(llm.chat_text({
        "model": config.FAST_MODEL,
        "temperature": 0,
        "max_tokens": 500,
        "messages": [{"role": "system", "content": PROMPT + f"\n\nThe app is in {mode} mode."},
                     {"role": "user", "content": "\n".join(turns)}],
        "response_format": {"type": "json_schema", "json_schema": SCHEMA},
    }, timeout=15, usage=usage))
    return out


def _brief(message):
    """Medi's earlier turns are stored as JSON; the analyzer only needs what Medi said."""
    text = message_text(message)
    if message["role"] == "assistant":
        try:
            text = json.loads(text).get("reply", text)
        except (ValueError, AttributeError):
            pass
    return text[:1500]


def search_text(analysis, said):
    return f"{said}\n{analysis['search_query']}\n{'; '.join(analysis['search_topics'])}"


def intake_note(analysis):
    """What the generator is told about the conversation state, so it doesn't repeat questions."""
    lines = ["INTAKE NOTES (from the app's analyzer; may be incomplete, and the conversation itself always takes priority):",
             f"- Intent of the latest message: {analysis['intent'].replace('_', ' ')}"]
    if analysis["intent"] == "non_health":
        lines.append("- This message isn't about health or wellbeing. Don't carry out the request (no poems, homework, "
                     "code, trivia, etc.). Kindly say you're Medi, a health and wellbeing assistant, and offer to help "
                     "with anything health-related. Keep it to one or two sentences.")
    if analysis["already_answered"]:
        lines.append("- Already answered, don't ask again: " + "; ".join(analysis["already_answered"]))
    if analysis["missing_information"]:
        lines.append("- Still unknown and useful: " + "; ".join(analysis["missing_information"]))
    return "\n".join(lines)
