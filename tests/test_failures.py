"""Failure handling: the AI service down or out of credits, and developer-only endpoints."""
import io
import json
import unittest
import urllib.error
from unittest import mock

from medi import config, llm, web


def http_error(code, body):
    return urllib.error.HTTPError("https://api.openai.com", code, "error", {}, io.BytesIO(body.encode()))


def post(kind, body, headers=None):
    return web.handle_post(kind, json.dumps(body).encode(), headers or {})


CHEST = {"messages": [{"role": "user", "content": "I have crushing chest pain right now"}]}


@mock.patch.object(config, "API_KEY", "test-key")
class FailureTest(unittest.TestCase):
    def test_exhausted_credits_fail_fast_without_retrying(self):
        calls = []

        def urlopen(*args, **kwargs):
            calls.append(1)
            raise http_error(429, '{"error": {"code": "insufficient_quota"}}')
        with mock.patch("urllib.request.urlopen", urlopen), self.assertRaises(llm.OpenAIError) as caught:
            llm.post("chat/completions", {}, retries=5)
        self.assertEqual(caught.exception.status, 402)
        self.assertEqual(len(calls), 1)

    def test_rate_limits_are_retried(self):
        calls = []

        def urlopen(*args, **kwargs):
            calls.append(1)
            raise http_error(429, '{"error": {"code": "rate_limit_exceeded"}}')
        with mock.patch("urllib.request.urlopen", urlopen), mock.patch("time.sleep"), self.assertRaises(llm.OpenAIError):
            llm.post("chat/completions", {}, retries=2)
        self.assertEqual(len(calls), 3)

    def test_ai_outage_still_sends_the_emergency_alert_first(self):
        def down(*args, **kwargs):
            raise llm.OpenAIError(402, "the OpenAI account has run out of credits")
        with mock.patch.object(llm, "chat_text", down), mock.patch.object(llm, "embed", down), \
             mock.patch.object(llm, "chat_stream", down):
            _, stream = post("stream", CHEST)
            events = [json.loads(chunk.decode()[6:]) for chunk in stream]
            status, body = post("consult", CHEST)
        self.assertEqual(events[0]["type"], "alerts")
        self.assertTrue(events[0]["alerts"])
        self.assertEqual(events[-1]["type"], "error")
        self.assertIn("911", events[-1]["error"])
        self.assertNotIn("credits", events[-1]["error"])
        self.assertEqual(status, 502)
        self.assertIn("911", body["error"])

    def test_screen_works_without_the_ai_service(self):
        with mock.patch.object(llm, "chat_text", side_effect=llm.OpenAIError(402, "x")):
            status, body = post("screen", {"text": "my dad collapsed and isn't responding"})
        self.assertEqual(status, 200)
        self.assertTrue(body["alerts"])

    def test_inspect_requires_the_developer_token(self):
        with mock.patch.object(config, "DEV_TOKEN", "secret"):
            self.assertEqual(post("inspect", {"text": "hi"})[0], 403)
            self.assertEqual(post("inspect", {"text": "hi"}, {"X-Medi-Dev": "wrong"})[0], 403)
        with mock.patch.object(config, "DEV_TOKEN", ""):
            self.assertEqual(post("inspect", {"text": "hi"}, {"X-Medi-Dev": ""})[0], 403)


if __name__ == "__main__":
    unittest.main()
