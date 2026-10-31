"""Input validation: turns a raw request body into a clean, bounded Turn, or rejects it with a clear message.

Only "user" and "assistant" messages are accepted, so a client can't inject its own system instructions."""
from dataclasses import dataclass, field

from . import config
from .language import LANG_NAMES

ROLES = {"user", "assistant"}
MAX_HISTORY = 200
MAX_ASSISTANT_CHARS = 20000
MAX_PROFILE_FIELDS = 20
MAX_PROFILE_CHARS = 500


class InvalidRequest(ValueError):
    pass


@dataclass
class Turn:
    messages: list
    profile: dict = field(default_factory=dict)
    patient: str = "other"
    mode: str = "health"
    lang: str = "en"
    dropped: int = 0


def _clean_content(content, limit):
    if isinstance(content, str):
        return content[:limit]
    if not isinstance(content, list):
        raise InvalidRequest("Message content must be text or a list of parts.")
    parts = []
    for part in content:
        if not isinstance(part, dict):
            raise InvalidRequest("Message parts must be objects.")
        if part.get("type") == "text" and isinstance(part.get("text"), str):
            parts.append({"type": "text", "text": part["text"][:limit]})
        elif part.get("type") == "image_url":
            url = (part.get("image_url") or {}).get("url", "")
            if not isinstance(url, str) or not url.startswith("data:image/"):
                raise InvalidRequest("Photos must be sent as image data.")
            parts.append({"type": "image_url", "image_url": {"url": url}})
        else:
            raise InvalidRequest("Unsupported message part.")
    return parts


def clean_messages(messages):
    """Keeps well-formed user and assistant messages; anything else is dropped and counted."""
    if not isinstance(messages, list):
        raise InvalidRequest("'messages' must be a list.")
    if len(messages) > MAX_HISTORY:
        messages = messages[-MAX_HISTORY:]
    kept, dropped = [], 0
    for m in messages:
        if not isinstance(m, dict) or m.get("role") not in ROLES:
            dropped += 1
            continue
        limit = config.MAX_MESSAGE_CHARS if m["role"] == "user" else MAX_ASSISTANT_CHARS
        kept.append({"role": m["role"], "content": _clean_content(m.get("content", ""), limit)})
    return kept, dropped


def clean_profile(profile):
    if not isinstance(profile, dict):
        return {}
    items = [(str(k)[:60], str(v)[:MAX_PROFILE_CHARS]) for k, v in profile.items() if isinstance(v, (str, int, float))]
    return dict(items[:MAX_PROFILE_FIELDS])


def parse(payload):
    if not isinstance(payload, dict):
        raise InvalidRequest("The request body must be a JSON object.")
    messages, dropped = clean_messages(payload.get("messages", []))
    return Turn(
        messages=messages,
        profile=clean_profile(payload.get("profile", {})),
        patient="self" if payload.get("patient") == "self" else "other",
        mode="wellbeing" if payload.get("mode") == "wellbeing" else "health",
        lang=payload.get("lang") if payload.get("lang") in LANG_NAMES else "en",
        dropped=dropped,
    )
