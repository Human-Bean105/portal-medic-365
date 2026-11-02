"""The only module that talks to the OpenAI API: timeouts, retries for temporary failures, and usage accounting."""
import json
import os
import time
import urllib.error
import urllib.request

from . import config

API = "https://api.openai.com/v1"
RETRY_STATUS = {429, 500, 502, 503, 504}
RETRIES = int(os.environ.get("MEDI_LLM_RETRIES", "2"))


class OpenAIError(Exception):
    def __init__(self, status, detail):
        super().__init__(f"OpenAI error {status}: {detail}")
        self.status = status
        self.detail = detail


def _request(path, body, content_type="application/json"):
    return urllib.request.Request(
        f"{API}/{path}", data=body,
        headers={"Authorization": f"Bearer {config.API_KEY}", "Content-Type": content_type},
    )


def _open(path, body, timeout, retries, content_type="application/json"):
    """Opens a request, retrying temporary failures (rate limits, server errors, timeouts) with a short backoff."""
    for attempt in range(retries + 1):
        try:
            return urllib.request.urlopen(_request(path, body, content_type), timeout=timeout)
        except urllib.error.HTTPError as e:
            if e.code in RETRY_STATUS and attempt < retries:
                time.sleep(0.5 * 3 ** attempt)
                continue
            detail = "the OpenAI API key is invalid or expired" if e.code == 401 else e.read().decode(errors="replace")[:300]
            raise OpenAIError(e.code, detail) from None
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt < retries:
                time.sleep(0.5 * 3 ** attempt)
                continue
            raise OpenAIError(504, f"no response from OpenAI ({e})") from None


def post(path, payload, timeout=90, retries=None):
    retries = RETRIES if retries is None else retries
    with _open(path, json.dumps(payload).encode(), timeout, retries) as resp:
        return json.load(resp)


def chat(payload, timeout=90, retries=None, usage=None):
    """Chat Completions call. If a usage list is given, the call's model and token counts are appended to it."""
    data = post("chat/completions", payload, timeout, retries)
    if usage is not None:
        usage.append({"model": payload["model"], **{k: data.get("usage", {}).get(k, 0) for k in ("prompt_tokens", "completion_tokens")}})
    return data


def chat_text(payload, **kwargs):
    return chat(payload, **kwargs)["choices"][0]["message"]["content"]


def chat_stream(payload, timeout=90, usage=None):
    """Streams a Chat Completions answer, yielding text pieces. Not retried once text has started arriving."""
    body = json.dumps({**payload, "stream": True, "stream_options": {"include_usage": True}}).encode()
    with _open("chat/completions", body, timeout, retries=1) as resp:
        for line in resp:
            line = line.strip()
            if not line.startswith(b"data: ") or line == b"data: [DONE]":
                continue
            event = json.loads(line[6:])
            if event.get("usage") and usage is not None:
                usage.append({"model": payload["model"], "prompt_tokens": event["usage"].get("prompt_tokens", 0),
                              "completion_tokens": event["usage"].get("completion_tokens", 0)})
            choices = event.get("choices") or [{}]
            delta = choices[0].get("delta", {}).get("content")
            if delta:
                yield delta


def embed(texts, dims, timeout=30, usage=None, retries=None):
    data = post("embeddings", {"model": config.EMBED_MODEL, "input": texts, "dimensions": dims}, timeout, retries)
    if usage is not None:
        usage.append({"model": config.EMBED_MODEL, "prompt_tokens": data.get("usage", {}).get("prompt_tokens", 0), "completion_tokens": 0})
    return [d["embedding"] for d in sorted(data["data"], key=lambda d: d["index"])]


def speech(text, voice, instructions, timeout=60):
    body = json.dumps({"model": config.TTS_MODEL, "voice": voice, "input": text, "instructions": instructions,
                       "response_format": "mp3"}).encode()
    with _open("audio/speech", body, timeout, retries=1) as resp:
        return resp.read()


def realtime_call(body, boundary, timeout=30):
    with _open("realtime/calls", body, timeout, retries=1, content_type=f"multipart/form-data; boundary={boundary}") as resp:
        return resp.read().decode()


def cost(usage):
    """Estimated US$ cost of a list of usage records."""
    total = 0.0
    for u in usage:
        price_in, price_out = config.PRICES.get(u["model"], (0.0, 0.0))
        total += (u["prompt_tokens"] * price_in + u["completion_tokens"] * price_out) / 1e6
    return round(total, 5)
