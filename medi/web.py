"""HTTP layer shared by the local server and the Vercel functions."""
import json

from . import config, llm, orchestrator, services
from .language import LANG_NAMES
from .rag.retrieval import find_references
from .safety.input_checks import screen_message


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


def make_handler(kind):
    """Builds the request handler class a Vercel Python function exposes as `handler`."""
    from http.server import BaseHTTPRequestHandler

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            raw = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            status, body = handle_post(kind, raw)
            if hasattr(body, "__next__"):
                return send_stream(self, status, body)
            audio = isinstance(body, bytes)
            data = body if audio else json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "audio/mpeg" if audio else "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    return Handler


def handle_post(kind, raw):
    """Shared request handling for the local server and the Vercel functions. Returns (status, body)."""
    try:
        if len(raw) > config.MAX_BODY:
            return 413, {"error": "That upload is too large. Try a smaller photo."}
        if not config.API_KEY:
            return 500, {"error": "OPENAI_API_KEY is not configured on the server."}
        payload = json.loads(raw or b"{}")
        messages, profile = payload.get("messages", []), payload.get("profile", {})
        patient = "self" if payload.get("patient") == "self" else "other"
        mode = "wellbeing" if payload.get("mode") == "wellbeing" else "health"
        lang = payload.get("lang") if payload.get("lang") in LANG_NAMES else "en"
        if kind == "summary":
            return 200, services.summarize(messages, profile, patient, lang)
        if kind == "stream":
            return 200, orchestrator.consult_stream(messages, profile, patient, mode, lang)
        if kind == "speak":
            text = str(payload.get("text", "")).strip()
            return (200, services.speak(text)) if text else (400, {"error": "Nothing to read aloud."})
        if kind == "retrieve":
            hint = str(payload.get("hint") or "")
            passages = find_references(messages, mode, hint, lang) if config.DEFAULT.rag else []
            return 200, {"passages": [{"t": p["t"], "s": p["s"], "u": p["u"], "x": p["x"][:900]} for p in passages]}
        if kind == "screen":
            return 200, {"alerts": screen_message(str(payload.get("text", "")), lang)}
        if kind == "voice":
            if not str(payload.get("sdp", "")).strip():
                return 400, {"error": "Missing voice connection offer."}
            return 200, services.voice_session(payload["sdp"], profile, patient, messages, mode, lang)
        result = orchestrator.consult(messages, profile, patient, mode, lang)
        result.pop("retrieved", None)
        return 200, result
    except llm.OpenAIError as e:
        return 502, {"error": str(e)}
    except Exception as e:
        return 500, {"error": str(e)}
