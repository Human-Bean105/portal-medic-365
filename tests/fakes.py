"""A stand-in for the OpenAI API so the pipeline can be tested offline, quickly, and for free."""
import json
from contextlib import contextmanager
from unittest import mock

from medi import llm
from medi.rag import index

HEALTH_TURN = {
    "reply": "That sounds uncomfortable. How long has it been going on?",
    "stage": "gathering",
    "triage": {"level": "unknown", "headline": "Tell me a bit more.", "reasons": []},
    "conditions": [], "important_unknowns": [], "next_steps": [], "red_flags_to_watch": [],
    "quick_replies": [], "citations": [1],
}
WELLBEING_TURN = {"reply": "That sounds really hard.", "risk": {"level": "none", "reason": ""}, "quick_replies": [], "citations": []}


class FakeOpenAI:
    def __init__(self, turn=None, rewrite="headache tension headache", fail_embed=False):
        self.turn = turn or HEALTH_TURN
        self.rewrite = rewrite
        self.fail_embed = fail_embed
        self.calls = []

    def chat_text(self, payload, **kwargs):
        self.calls.append(("chat", payload))
        if "response_format" in payload and payload["response_format"].get("type") == "json_schema":
            return json.dumps(self.turn)
        return self.rewrite

    def chat_stream(self, payload, **kwargs):
        self.calls.append(("stream", payload))
        text = json.dumps(self.turn)
        for i in range(0, len(text), 40):
            yield text[i:i + 40]

    def embed(self, texts, dims, **kwargs):
        self.calls.append(("embed", texts))
        if self.fail_embed:
            raise llm.OpenAIError(503, "embedding service unavailable")
        # Every query "means" the first passage in the index, so retrieval returns it with a perfect score.
        data, vectors = index.load()
        count = 1 if isinstance(texts, str) else len(texts)
        return [list(vectors[0:data["dims"]])] * count

    @contextmanager
    def installed(self):
        with mock.patch.object(llm, "chat_text", self.chat_text), \
             mock.patch.object(llm, "chat_stream", self.chat_stream), \
             mock.patch.object(llm, "embed", self.embed):
            yield self
