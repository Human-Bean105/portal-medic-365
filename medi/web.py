"""HTTP layer shared by the local server and the Vercel functions: validation, rate limiting, routing, and logging."""
import hmac
import json
import threading
import time

from . import config, intake, llm, orchestrator, services
from .rag.retrieval import find_references
from .safety.input_checks import screen_message
from .trace import Trace, log

# Best-effort, per server instance. On Vercel each instance has its own memory, so platform-wide protection
# should also use a Vercel Firewall rate-limit rule (see docs/SECURITY_PRIVACY.md).
RATE_LIMITS = {"voice": 10, "speak": 30, "default": 40}  # requests per minute per IP
_hits = {}
_hits_lock = threading.Lock()


def rate_limited(kind, ip):
    limit = RATE_LIMITS.get(kind, RATE_LIMITS["default"])
    now = time.time()
    with _hits_lock:
        recent = [t for t in _hits.get((kind, ip), []) if now - t < 60]
        recent.append(now)
        _hits[(kind, ip)] = recent
        if len(_hits) > 5000:
            _hits.clear()
    return len(recent) > limit


def public_error(e):
    """What the person sees when the AI service fails. Details stay in the server log."""
    if e.status in (401, 402):
        return "Medi is temporarily unavailable. Please try again later. In an emergency, call 911."
    return "Medi couldn't reach its AI service just now. Please try again in a moment. In an emergency, call 911."


def is_developer(headers):
    token = (headers or {}).get("X-Medi-Dev", "")
    return bool(config.DEV_TOKEN) and hmac.compare_digest(token, config.DEV_TOKEN)


def send_stream(handler, status, events):
    """Writes server-sent events to the client as they're produced."""
    handler.send_response(status)
    handler.send_header("Content-Type", "text/event-stream")
    handler.send_header("Cache-Control", "no-cache")
    handler.send_header("X-Accel-Buffering", "no")
    handler.end_headers()
    for chunk in events:
        handler.wfile.write(chunk)
        handler.wfile.flush()


def client_ip(handler):
    return (handler.headers.get("X-Forwarded-For") or handler.client_address[0]).split(",")[0].strip()


def make_handler(kind):
    """Builds the request handler class a Vercel Python function exposes as `handler`."""
    from http.server import BaseHTTPRequestHandler

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            raw = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            status, body = handle_post(kind, raw, self.headers, client_ip(self))
            respond(self, status, body)

    return Handler


def respond(handler, status, body):
    if hasattr(body, "__next__"):
        return send_stream(handler, status, body)
    audio = isinstance(body, bytes)
    data = body if audio else json.dumps(body).encode()
    handler.send_response(status)
    handler.send_header("Content-Type", "audio/mpeg" if audio else "application/json")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


def inspect_retrieval(text, mode, trace):
    """Developer view: the same query through three retrieval setups, side by side, with every score."""
    from . import analyzer
    from .rag import rerank, retrieval

    analysis = analyzer.analyze([{"role": "user", "content": text}], mode, usage=trace.usage)
    query = analyzer.search_text(analysis, text)
    cfg = config.DEFAULT
    qvec = retrieval.embed_query(query, retrieval.index.get(cfg.index), trace.usage)
    fields = ("t", "u", "heading", "score", "cosine", "bm25", "grade")
    vector = retrieval.candidates(query, cfg.but(retriever="vector", min_score=0.0), mode, qvec=qvec)
    hybrid = retrieval.candidates(query, cfg, mode, qvec=qvec)
    graded = rerank.rerank(text, hybrid[:cfg.rerank_pool], usage=trace.usage)
    view = lambda ps: [{k: p.get(k) for k in fields} for p in retrieval.select(ps, cfg)]  # noqa: E731
    return {"analysis": analysis, "search_query": query,
            "results": {"Vector search only": view(vector), "Hybrid (vector + keyword)": view(hybrid),
                        "Hybrid + reranker (production)": view(graded)},
            "grades_all": [{"t": p["t"], "grade": p["grade"]} for p in graded],
            "cost_usd": llm.cost(trace.usage)}


def _logged_stream(events, trace):
    try:
        yield from events
    finally:
        log("request", status=200, **trace.summary(redact=True))


def handle_post(kind, raw, headers=None, ip="local"):
    """Shared request handling. Returns (status, body); body is a dict, MP3 bytes, or a server-sent-event generator."""
    trace = Trace(kind)
    status, body = 500, {"error": "Something went wrong."}
    try:
        if rate_limited(kind, ip):
            status, body = 429, {"error": "Too many requests. Please wait a minute and try again."}
            return status, body
        if len(raw) > config.MAX_BODY:
            status, body = 413, {"error": "That upload is too large. Try a smaller photo."}
            return status, body
        if not config.API_KEY:
            status, body = 500, {"error": "OPENAI_API_KEY is not configured on the server."}
            return status, body
        payload = json.loads(raw or b"{}")
        turn = intake.parse(payload)
        trace.info.update(mode=turn.mode, lang=turn.lang, messages=len(turn.messages), dropped_messages=turn.dropped)
        developer = is_developer(headers)

        if kind == "stream":
            status = 200
            body = _logged_stream(orchestrator.consult_stream(turn, trace=trace, include_trace=developer), trace)
            return status, body
        if kind == "summary":
            status, body = 200, services.summarize(turn.messages, turn.profile, turn.patient, turn.lang)
        elif kind == "speak":
            text = str(payload.get("text", "")).strip()
            status, body = (200, services.speak(text)) if text else (400, {"error": "Nothing to read aloud."})
        elif kind == "retrieve":
            hint = str(payload.get("hint") or "")[:500]
            passages = find_references(turn.messages, turn.mode, hint, turn.lang, usage=trace.usage) if config.DEFAULT.rag else []
            status, body = 200, {"passages": [{"t": p["t"], "s": p["s"], "u": p["u"], "x": p["x"][:900]} for p in passages]}
        elif kind == "inspect":
            if not developer:
                status, body = 403, {"error": "Developer token required."}
            else:
                status, body = 200, inspect_retrieval(str(payload.get("text", ""))[:2000], turn.mode, trace)
        elif kind == "screen":
            status, body = 200, {"alerts": screen_message(str(payload.get("text", ""))[:config.MAX_MESSAGE_CHARS], turn.lang, trace.usage)}
        elif kind == "voice":
            sdp = str(payload.get("sdp", ""))
            if not sdp.strip():
                status, body = 400, {"error": "Missing voice connection offer."}
            else:
                status, body = 200, services.voice_session(sdp, turn.profile, turn.patient, turn.messages, turn.mode, turn.lang)
        else:
            result = orchestrator.consult(turn, trace=trace)
            result.pop("retrieved", None)
            if developer:
                result["trace"] = trace.summary()
            else:
                result.pop("analysis", None)
            status, body = 200, result
        return status, body
    except (intake.InvalidRequest, json.JSONDecodeError) as e:
        status, body = 400, {"error": f"Invalid request: {e}"}
        return status, body
    except llm.OpenAIError as e:
        trace.info["error"] = f"openai_{e.status}"
        status, body = 502, {"error": public_error(e)}
        return status, body
    except Exception as e:
        trace.info["error"] = type(e).__name__
        status, body = 500, {"error": "Medi ran into a problem. Please try again."}
        return status, body
    finally:
        if not hasattr(body, "__next__"):
            log("request", status=status, **trace.summary(redact=True))
