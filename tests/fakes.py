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


ANALYSIS = {"intent": "symptom_information", "language": "English", "reported_symptoms": ["headache"], "duration": "",
            "severity": "", "relevant_context": [], "already_answered": ["has a headache"],
            "missing_information": ["when it started"], "search_query": "headache", "search_topics": ["Headache"]}


class FakeOpenAI:
    def __init__(self, turn=None, rewrite="headache tension headache", fail_embed=False, analysis=None, grade=3):
        self.turn = turn or HEALTH_TURN
        self.rewrite = rewrite
        self.fail_embed = fail_embed
        self.analysis = analysis or ANALYSIS
        self.grade = grade
        self.calls = []

    def schema(self, payload):
        fmt = payload.get("response_format") or {}
        return fmt.get("json_schema", {}).get("name") if fmt.get("type") == "json_schema" else None

    def chat_text(self, payload, **kwargs):
        name = self.schema(payload)
        self.calls.append((name or "chat", payload))
        if name == "turn_analysis":
            return json.dumps(self.analysis)
        if name == "passage_grades":
            count = payload["messages"][1]["content"].count("\n[") + 1
            return json.dumps({"grades": [{"n": n, "grade": self.grade} for n in range(1, count + 1)]})
        if name:
            return json.dumps(self.turn)
        return self.rewrite

    def generation_payload(self):
        return next(p for kind, p in self.calls if kind in ("doctor_turn", "wellbeing_turn", "stream"))

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
