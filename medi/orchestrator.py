"""Runs one consultation turn through the pipeline stages: safety pre-check, retrieval, generation, and checks."""
import json

from . import config, language, llm, prompts
from .conversation import last_user_text, profile_note
from .rag.citations import cited_sources, reference_note
from .rag.retrieval import find_references
from .safety import escalation
from .safety.input_checks import screen_message


def sse(event):
    return f"data: {json.dumps(event)}\n\n".encode()


def build_request(messages, profile, patient, mode="health", lang="en", cfg=config.DEFAULT):
    """Builds the chat request for a turn: keyword safety check, retrieval, language, and the full prompt."""
    said = last_user_text(messages)
    flags = screen_message(said, lang) if said else []
    wellbeing = mode == "wellbeing"
    passages = find_references(messages, mode, lang=lang, cfg=cfg) if cfg.rag and said else []
    system = ((prompts.WELLBEING_PROMPT if wellbeing else prompts.SYSTEM_PROMPT) + "\n\n" + profile_note(profile, patient)
              + "\n\n" + language.language_note(lang))
    if passages:
        system += "\n\n" + reference_note(passages)
    if flags:
        system += "\n\n" + escalation.alert_note(flags, wellbeing)
    payload = {
        "model": config.MODEL,
        "temperature": 0.5 if wellbeing else 0.3,
        "messages": [{"role": "system", "content": system}] + messages[-config.MAX_MESSAGES:],
        "response_format": {"type": "json_schema", "json_schema": prompts.WELLBEING_SCHEMA if wellbeing else prompts.RESPONSE_SCHEMA},
    }
    return payload, flags, passages


def finish(result, flags, passages, lang):
    result = escalation.ensure_crisis_line(result, flags, lang)
    result["safety_alerts"] = flags
    result["sources"] = cited_sources(result, passages)
    return result


def consult(messages, profile, patient, mode="health", lang="en", cfg=config.DEFAULT):
    payload, flags, passages = build_request(messages, profile, patient, mode, lang, cfg)
    result = finish(json.loads(llm.chat_text(payload)), flags, passages, lang)
    result["retrieved"] = passages
    return result


def consult_stream(messages, profile, patient, mode="health", lang="en", cfg=config.DEFAULT):
    """Same as consult, but yields server-sent events: safety alerts first, then the raw JSON as the model writes it
    (the reply field comes first, so the browser can show it word by word), then the finished result."""
    try:
        payload, flags, passages = build_request(messages, profile, patient, mode, lang, cfg)
        yield sse({"type": "alerts", "alerts": flags})
        text = ""
        for delta in llm.chat_stream(payload):
            text += delta
            yield sse({"type": "delta", "text": delta})
        yield sse({"type": "done", "result": finish(json.loads(text), flags, passages, lang)})
    except llm.OpenAIError as e:
        yield sse({"type": "error", "error": str(e)})
    except Exception as e:
        yield sse({"type": "error", "error": str(e)})
