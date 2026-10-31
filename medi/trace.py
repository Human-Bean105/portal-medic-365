"""A content-free record of how one answer was produced: stage timings, decisions, scores, and token usage.

Traces never contain what the person wrote or what Medi replied. They are logged as one JSON line per request
and returned to the browser only when the request carries the developer token."""
import json
import os
import sys
import time
from contextlib import contextmanager

from . import llm


class Trace:
    def __init__(self, kind):
        self.id = os.urandom(6).hex()
        self.kind = kind
        self.started = time.perf_counter()
        self.stages = []
        self.usage = []
        self.info = {}

    @contextmanager
    def stage(self, name):
        details = {}
        start = time.perf_counter()
        try:
            yield details
        except Exception as e:
            details["error"] = type(e).__name__
            raise
        finally:
            self.stages.append({"stage": name, "ms": round((time.perf_counter() - start) * 1000), **details})

    def summary(self, redact=False):
        """The full trace for the developer view. With redact=True (for server logs), anything that hints at the
        person's health, like alert labels, source titles, or the level of care, is reduced to counts and scores."""
        stages = self.stages
        info = self.info
        if redact:
            stages = [{k: (len(v) if k in ("alerts", "passages", "checks") else v) for k, v in s.items()} |
                      ({"scores": [p.get("score") for p in s["passages"]]} if "passages" in s else {}) for s in stages]
            info = {k: v for k, v in info.items() if k != "level"}
        return {
            "id": self.id,
            "kind": self.kind,
            "total_ms": round((time.perf_counter() - self.started) * 1000),
            "stages": stages,
            "tokens": {k: sum(u[k] for u in self.usage) for k in ("prompt_tokens", "completion_tokens")},
            "cost_usd": llm.cost(self.usage),
            **info,
        }


def log(event, **fields):
    """One JSON line per event on stdout, which Vercel keeps in its function logs."""
    print(json.dumps({"event": event, "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **fields}), file=sys.stdout, flush=True)
