from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stdout
from unittest import mock

from google.genai import errors

from labs import classifier, llm
from labs import __main__ as labs_main
from helpers import ScriptedGemini, TempDB, response

ITEMS = [{"id": 1, "title": "Model A", "content": "a"}, {"id": 2, "title": "Model B", "content": "b"}]


def answer(*entries):
    return json.dumps([{"index": i, "ai_related": True, "category": "model_release", "summary": f"s{i}"}
                       for i in entries])


class ClassifyBatchTest(unittest.TestCase):
    def _classify(self, text):
        with mock.patch.object(classifier, "call_llm", return_value=(text, None)), redirect_stdout(io.StringIO()):
            out, _ = classifier.classify_batch("OpenAI", "US", ITEMS)
        return out

    def test_unparseable_json_leaves_every_item_pending(self):
        out = self._classify("sorry, I cannot help with that")
        self.assertEqual([i["category"] for i in out], ["pending", "pending"],
                         "a failed parse must not label items; pending items are retried on the next run")

    def test_an_index_missing_from_the_answer_leaves_that_item_pending(self):
        out = self._classify(answer(0))
        self.assertEqual([i["category"] for i in out], ["model_release", "pending"],
                         "only the item the model answered for is classified")

    def test_a_gemini_outage_leaves_the_chunk_pending_instead_of_raising(self):
        with mock.patch.object(classifier, "call_llm", side_effect=llm.LLMUnavailable("down")), \
                redirect_stdout(io.StringIO()):
            out, usage = classifier.classify_batch("OpenAI", "US", ITEMS)
        self.assertEqual([i["category"] for i in out], ["pending", "pending"], "an outage must not label items")
        self.assertIsNone(usage, "no call succeeded, so no usage is reported")

    def test_a_503_then_success_classifies_with_the_retried_answer(self):
        fake = ScriptedGemini([errors.ServerError(503, {"error": {"code": 503, "message": "x", "status": "U"}}),
                               response(answer(0, 1))])
        with mock.patch.object(llm.genai, "Client", fake), mock.patch.object(llm.time, "sleep"), \
                redirect_stdout(io.StringIO()):
            out, _ = classifier.classify_batch("OpenAI", "US", ITEMS)
        self.assertEqual(fake.calls, 2, "one 503 costs one retry")
        self.assertEqual([i["category"] for i in out], ["model_release", "model_release"],
                         "the retried answer is the one applied")


class RunClassifyTest(TempDB):
    def _run(self, text):
        with mock.patch.object(classifier, "call_llm", return_value=(text, {"input": 1, "output": 1, "total": 2})), \
                redirect_stdout(io.StringIO()):
            labs_main.run_classify("2026-10-01")
        return {r["id"]: r for r in self.rows("SELECT id, category, ai_related, summary FROM competitor_items")}

    def test_bad_json_leaves_the_rows_pending_in_the_db(self):
        a = self.insert_item(summary="kept")
        b = self.insert_item(url="https://x.com/OpenAI/status/2")
        rows = self._run("not json")
        self.assertEqual((rows[a]["category"], rows[b]["category"]), ("pending", "pending"),
                         "rows the model did not classify must stay pending, not become other")
        self.assertEqual(rows[a]["summary"], "kept", "an unclassified row keeps its stored fields")

    def test_a_partial_answer_writes_only_the_classified_row(self):
        a = self.insert_item()
        b = self.insert_item(url="https://x.com/OpenAI/status/2")
        rows = self._run(answer(0))
        self.assertEqual(rows[a]["category"], "model_release", "the answered row is written")
        self.assertEqual(rows[b]["category"], "pending", "the missing row stays pending for the next run")


if __name__ == "__main__":
    unittest.main()
