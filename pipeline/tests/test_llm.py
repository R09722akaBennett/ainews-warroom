from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout
from unittest import mock

import httpx
from google.genai import errors

from labs import llm
from helpers import ScriptedGemini, response


def server_error(code: int = 503):
    return errors.ServerError(code, {"error": {"code": code, "message": "overloaded", "status": "UNAVAILABLE"}})


def client_error(code: int):
    return errors.ClientError(code, {"error": {"code": code, "message": "nope", "status": "X"}})


class CallLlmRetryTest(unittest.TestCase):
    def setUp(self):
        for p in (mock.patch.object(llm.time, "sleep"), redirect_stdout(io.StringIO())):
            p.__enter__()
            self.addCleanup(p.__exit__, None, None, None)

    def _run(self, outcomes):
        fake = ScriptedGemini(outcomes)
        with mock.patch.object(llm.genai, "Client", fake):
            return fake, llm.call_llm("prompt")

    def test_a_503_is_retried_once_and_the_second_answer_is_used(self):
        fake, (text, usage) = self._run([server_error(503), response("ok", tokens=7)])
        self.assertEqual(fake.calls, 2, "one failure must cost exactly one retry")
        self.assertEqual(text, "ok", "the successful retry's text is the result")
        self.assertEqual(usage, {"input": 7, "output": 7, "total": 14}, "token usage must survive the retry")

    def test_a_429_is_retried(self):
        fake, (text, _) = self._run([client_error(429), response("ok")])
        self.assertEqual((fake.calls, text), (2, "ok"), "rate limiting clears, so 429 must be retried")

    def test_an_empty_answer_is_retried_instead_of_returning_none(self):
        fake, (text, _) = self._run([response(None), response("ok")])
        self.assertEqual((fake.calls, text), (2, "ok"), "a blocked (None) answer must be retried, never returned")

    def test_dropped_connections_and_timeouts_are_still_retried(self):
        fake, (text, _) = self._run([httpx.RemoteProtocolError("gone"), httpx.ReadTimeout("slow"), response("ok")])
        self.assertEqual((fake.calls, text), (3, "ok"), "the httpx errors retried before must stay retryable")

    def test_a_400_is_raised_at_once_because_a_retry_gets_the_same_answer(self):
        fake = ScriptedGemini([client_error(400), response("ok")])
        with mock.patch.object(llm.genai, "Client", fake), self.assertRaises(errors.ClientError):
            llm.call_llm("prompt")
        self.assertEqual(fake.calls, 1, "a non-429 4xx must not be retried")

    def test_persistent_503s_raise_llm_unavailable_after_the_last_attempt(self):
        fake = ScriptedGemini([server_error()] * llm.MAX_RETRIES)
        with mock.patch.object(llm.genai, "Client", fake), self.assertRaises(llm.LLMUnavailable) as cm:
            llm.call_llm("prompt")
        self.assertEqual(fake.calls, llm.MAX_RETRIES, "every attempt is used before giving up")
        self.assertIsInstance(cm.exception.__cause__, errors.ServerError, "the last error is chained for the log")


if __name__ == "__main__":
    unittest.main()
