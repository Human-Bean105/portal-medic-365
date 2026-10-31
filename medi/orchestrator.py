"""Runs one consultation turn through Medi's pipeline:

    intake -> safety pre-check -> (emergency alert sent now) -> retrieval -> generation -> output checks -> result

Each stage is a separate module; this file only decides the order and records a trace. The safety pre-check is
deterministic and runs first, and its alerts reach the person before any slower stage starts."""
import json

from . import config, language, llm, prompts
from .conversation import last_user_text, profile_note
from .intake import Turn
from .rag.citations import cited_sources, reference_note
from .rag.retrieval import find_references
from .safety import escalation, output_checks
from .safety.input_checks import screen_message
from .trace import Trace

GENERATION_TIMEOUT = 45


def sse(event):
    return f"data: {json.dumps(event)}\n\n".encode()


def safety_precheck(turn, trace):
    said = last_user_text(turn.messages)
    with trace.stage("safety_precheck") as s:
        flags = screen_message(said, turn.lang, usage=trace.usage) if said else []
        s["alerts"] = [f["label"] for f in flags]
    return flags


def retrieve(turn, flags, cfg, trace):
    if not cfg.rag or not last_user_text(turn.messages):
        return []
    with trace.stage("retrieval") as s:
        passages = find_references(turn.messages, turn.mode, lang=turn.lang, cfg=cfg, usage=trace.usage,
                                   alerts=[f["label"] for f in flags], info=s)
        s["passages"] = [{"title": p["t"], "score": p.get("score")} for p in passages]
    return passages


def build_payload(turn, flags, passages):
    wellbeing = turn.mode == "wellbeing"
    system = ((prompts.WELLBEING_PROMPT if wellbeing else prompts.SYSTEM_PROMPT) + "\n\n" + profile_note(turn.profile, turn.patient)
              + "\n\n" + language.language_note(turn.lang))
    if passages:
        system += "\n\n" + reference_note(passages)
    if flags:
        system += "\n\n" + escalation.alert_note(flags, wellbeing)
    return {
        "model": config.MODEL,
        "temperature": 0.5 if wellbeing else 0.3,
        "messages": [{"role": "system", "content": system}] + turn.messages[-config.MAX_MESSAGES:],
        "response_format": {"type": "json_schema", "json_schema": prompts.WELLBEING_SCHEMA if wellbeing else prompts.RESPONSE_SCHEMA},
    }


def finish(result, flags, passages, turn, trace):
    with trace.stage("output_validation") as s:
        result, checks = output_checks.validate(result, flags, passages, turn.mode, turn.lang)
        s["checks"] = checks
        s["failed"] = [c["check"] for c in checks if not c["passed"]]
    result["safety_alerts"] = flags
    result["sources"] = cited_sources(result, passages)
    trace.info["level"] = result.get("triage", {}).get("level") or result.get("risk", {}).get("level")
    return result


def consult(turn: Turn, cfg=config.DEFAULT, trace=None):
    """One turn, all at once. The returned result includes "retrieved" (the passages shown to the model) for evaluation."""
    trace = trace or Trace("consult")
    flags = safety_precheck(turn, trace)
    passages = retrieve(turn, flags, cfg, trace)
    with trace.stage("generation") as s:
        s["model"] = config.MODEL
        raw = llm.chat_text(build_payload(turn, flags, passages), timeout=GENERATION_TIMEOUT, usage=trace.usage)
    result = finish(json.loads(raw), flags, passages, turn, trace)
    result["retrieved"] = passages
    return result


def consult_stream(turn: Turn, cfg=config.DEFAULT, trace=None, include_trace=False):
    """Same as consult, but as server-sent events: safety alerts first (before retrieval starts), then the raw JSON
    as the model writes it (the reply field comes first, so the browser can show it word by word), then the result."""
    trace = trace or Trace("stream")
    try:
        flags = safety_precheck(turn, trace)
        yield sse({"type": "alerts", "alerts": flags})
        passages = retrieve(turn, flags, cfg, trace)
        text = ""
        with trace.stage("generation") as s:
            s["model"] = config.MODEL
            for delta in llm.chat_stream(build_payload(turn, flags, passages), timeout=GENERATION_TIMEOUT, usage=trace.usage):
                text += delta
                yield sse({"type": "delta", "text": delta})
        result = finish(json.loads(text), flags, passages, turn, trace)
        if include_trace:
            result["trace"] = trace.summary()
        yield sse({"type": "done", "result": result})
    except llm.OpenAIError as e:
        trace.info["error"] = f"openai_{e.status}"
        yield sse({"type": "error", "error": str(e)})
    except Exception as e:
        trace.info["error"] = type(e).__name__
        yield sse({"type": "error", "error": "Medi couldn't finish that answer. Please try again."})
