import json
import unittest
from unittest import mock

from medi import config, web
from medi.conversation import profile_note
from tests.fakes import FakeOpenAI, WELLBEING_TURN


def post(kind, body):
    return web.handle_post(kind, json.dumps(body).encode())


def events(stream):
    return [json.loads(chunk.decode()[6:]) for chunk in stream]


@mock.patch.object(config, "API_KEY", "test-key")
class ApiTest(unittest.TestCase):
    def test_consult_returns_reply_sources_and_alerts(self):
        with FakeOpenAI().installed():
            status, body = post("consult", {"messages": [{"role": "user", "content": "I have a headache"}]})
        self.assertEqual(status, 200)
        self.assertIn("reply", body)
        self.assertEqual(body["safety_alerts"], [])
        self.assertEqual(len(body["sources"]), 1)
        self.assertNotIn("retrieved", body)

    def test_stream_sends_alerts_first_then_text_then_result(self):
        with FakeOpenAI().installed():
            _, stream = post("stream", {"messages": [{"role": "user", "content": "crushing chest pain"}]})
            evs = events(stream)
        self.assertEqual(evs[0]["type"], "alerts")
        self.assertEqual(evs[0]["alerts"][0]["label"], "Chest pain or pressure")
        self.assertEqual(evs[-1]["type"], "done")
        self.assertTrue(any(e["type"] == "delta" for e in evs))

    def test_retrieval_failure_still_answers(self):
        with FakeOpenAI(fail_embed=True).installed():
            status, body = post("consult", {"messages": [{"role": "user", "content": "I have a headache"}]})
        self.assertEqual(status, 200)
        self.assertEqual(body["sources"], [])

    def test_wellbeing_crisis_always_has_crisis_line(self):
        with FakeOpenAI(turn=WELLBEING_TURN).installed():
            _, body = post("consult", {"mode": "wellbeing", "messages": [{"role": "user", "content": "I want to die"}]})
        self.assertIn("9-8-8", body["reply"])

    def test_oversized_body_is_rejected(self):
        status, _ = web.handle_post("consult", b"x" * (config.MAX_BODY + 1))
        self.assertEqual(status, 413)

    def test_unknown_language_falls_back_to_english(self):
        with FakeOpenAI().installed() as fake:
            post("consult", {"lang": "xx", "messages": [{"role": "user", "content": "hi"}]})
        system = next(p for kind, p in fake.calls if kind == "chat" and "response_format" in p)["messages"][0]["content"]
        self.assertIn("chose English", system)


class ProfileTest(unittest.TestCase):
    def test_profile_never_used_for_someone_else(self):
        note = profile_note({"conditions": "asthma"}, "other")
        self.assertNotIn("asthma", note)
        self.assertIn("asthma", profile_note({"conditions": "asthma"}, "self"))


if __name__ == "__main__":
    unittest.main()
