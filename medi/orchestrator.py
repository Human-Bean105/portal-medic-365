"""Runs one consultation turn through Medi's pipeline:

    intake -> safety pre-check -> (alerts sent now) -> analysis -> retrieval -> reranking -> evidence check
           -> generation -> output checks -> result

Each stage is a separate module; this file only decides the order and records a trace. The safety pre-check is
deterministic and runs first, and its alerts reach the person before any slower stage starts. When it fires, the
analysis and reranking stages are skipped so emergency guidance isn't delayed."""
import json

from . import analyzer, config, language, llm, prompts
from .conversation import last_user_text, profile_note
from .intake import Turn
from .rag import evidence, rerank, retrieval
from .rag.citations import cited_sources, reference_note
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


class Context:
    """What the generator gets besides the conversation: passages, how well they cover the question, and the analysis."""
    def __init__(self, passages=(), status="not_checked", analysis=None):
        self.passages = list(passages)
        self.status = status
        self.analysis = analysis


def analyze(turn, flags, cfg, trace):
    if flags or not cfg.analyzer:
        return None
    with trace.stage("analysis") as s:
        try:
            result = analyzer.analyze(turn.messages, turn.mode, usage=trace.usage)
        except Exception as e:
            s["error"] = type(e).__name__
            return None
        s.update(intent=result["intent"], language=result["language"], missing=len(result["missing_information"]),
                 already_answered=len(result["already_answered"]))
    return result


def gather(turn, flags, cfg, trace):
    """Analysis, retrieval, reranking, and the evidence check. Never raises: on failure Medi answers without references."""
    said = last_user_text(turn.messages)
    if not cfg.rag or not said:
        return Context(status="not_used")
    analysis = analyze(turn, flags, cfg, trace)
    if analysis and analysis["intent"] == "non_health":
        return Context(status="not_needed", analysis=analysis)
    alerts = [f["label"] for f in flags]
    with trace.stage("retrieval") as s:
        try:
            if analysis:
                s["query_from"] = "analyzer"
                query = analyzer.search_text(analysis, said)
            else:
                query = retrieval.search_query(turn.messages, turn.mode, lang=turn.lang, usage=trace.usage, alerts=alerts, info=s)
            ranked = retrieval.candidates(query, cfg, turn.mode, trace.usage)
        except Exception as e:
            s["error"] = type(e).__name__
            return Context(status="not_used", analysis=analysis)
        s["candidates"] = len(ranked)
    status = "not_checked"
    if cfg.rerank and not flags and ranked:
        with trace.stage("rerank") as s:
            try:
                pool = rerank.rerank(said + (f"\n(English search terms: {analysis['search_query']})" if analysis else ""),
                                     ranked[:cfg.rerank_pool], usage=trace.usage)
                ranked = evidence.usable(pool)
                if cfg.evidence:
                    status = evidence.status_from_grades([p["grade"] for p in pool[:cfg.top_k]])
                s["grades"] = [p["grade"] for p in pool[:cfg.top_k]]
            except Exception as e:
                s["error"] = type(e).__name__
    passages = retrieval.select(ranked, cfg)
    trace.info["evidence_status"] = status
    for st in trace.stages:
        if st["stage"] == "retrieval":
            st["passages"] = [{"title": p["t"], "score": p.get("score"), "cosine": p.get("cosine"), "grade": p.get("grade")}
                              for p in passages]
    return Context(passages, status, analysis)


def build_payload(turn, flags, ctx, cfg=config.DEFAULT):
    wellbeing = turn.mode == "wellbeing"
    system = ((prompts.WELLBEING_PROMPT if wellbeing else prompts.SYSTEM_PROMPT) + "\n\n" + profile_note(turn.profile, turn.patient)
              + "\n\n" + language.language_note(turn.lang))
    if ctx.analysis:
        system += "\n\n" + analyzer.intake_note(ctx.analysis)
    if ctx.passages:
        system += "\n\n" + reference_note(ctx.passages)
    if cfg.evidence and ctx.status in ("partial", "insufficient", "none"):
        system += "\n\n" + evidence.prompt_note(ctx.status)
    if flags:
        system += "\n\n" + escalation.alert_note(flags, wellbeing)
    return {
        "model": config.MODEL,
        "temperature": 0.5 if wellbeing else 0.3,
        "messages": [{"role": "system", "content": system}] + turn.messages[-config.MAX_MESSAGES:],
        "response_format": {"type": "json_schema", "json_schema": prompts.WELLBEING_SCHEMA if wellbeing else prompts.RESPONSE_SCHEMA},
    }


def finish(result, flags, ctx, turn, trace, cfg=config.DEFAULT):
    if cfg.validate:
        with trace.stage("output_validation") as s:
            result, checks = output_checks.validate(result, flags, ctx.passages, turn.mode, turn.lang)
            s["checks"] = checks
            s["failed"] = [c["check"] for c in checks if not c["passed"]]
    else:
        result = escalation.ensure_crisis_line(result, flags, turn.lang)
    result["safety_alerts"] = flags
    result["sources"] = cited_sources(result, ctx.passages)
    result["evidence_status"] = ctx.status
    note = evidence.LIMITATION.get(ctx.status) if cfg.evidence else None
    result["limitations"] = [language.ui_text(note, turn.lang)] if note and not flags else []
    trace.info["level"] = result.get("triage", {}).get("level") or result.get("risk", {}).get("level")
    return result


def consult(turn: Turn, cfg=config.DEFAULT, trace=None):
    """One turn, all at once. The result includes "retrieved" (the passages shown to the model) for evaluation."""
    trace = trace or Trace("consult")
    flags = safety_precheck(turn, trace)
    ctx = gather(turn, flags, cfg, trace)
    with trace.stage("generation") as s:
        s["model"] = config.MODEL
        raw = llm.chat_text(build_payload(turn, flags, ctx, cfg), timeout=GENERATION_TIMEOUT, usage=trace.usage)
    result = finish(json.loads(raw), flags, ctx, turn, trace, cfg)
    result["retrieved"] = ctx.passages
    result["analysis"] = ctx.analysis
    return result


def consult_stream(turn: Turn, cfg=config.DEFAULT, trace=None, include_trace=False):
    """Same as consult, but as server-sent events: safety alerts first (before any other stage), then the raw JSON as
    the model writes it (the reply field comes first, so the browser can show it word by word), then the result."""
    trace = trace or Trace("stream")
    try:
        flags = safety_precheck(turn, trace)
        yield sse({"type": "alerts", "alerts": flags})
        ctx = gather(turn, flags, cfg, trace)
        text = ""
        with trace.stage("generation") as s:
            s["model"] = config.MODEL
            for delta in llm.chat_stream(build_payload(turn, flags, ctx, cfg), timeout=GENERATION_TIMEOUT, usage=trace.usage):
                text += delta
                yield sse({"type": "delta", "text": delta})
        result = finish(json.loads(text), flags, ctx, turn, trace, cfg)
        if include_trace:
            result["trace"] = trace.summary()
        yield sse({"type": "done", "result": result})
    except llm.OpenAIError as e:
        trace.info["error"] = f"openai_{e.status}"
        yield sse({"type": "error", "error": str(e)})
    except Exception as e:
        trace.info["error"] = type(e).__name__
        yield sse({"type": "error", "error": "Medi couldn't finish that answer. Please try again."})
