from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from export import translate
from helpers import ScriptedGemini, response


class TranslatorTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.cache = Path(self._tmp.name) / "translations.db"

    def _translator(self, answers: list, enabled=True):
        fake = ScriptedGemini([response(a) if isinstance(a, str) else a for a in answers])
        return translate.Translator(cache=self.cache, enabled=enabled, client=fake), fake

    def test_without_a_key_nothing_is_translated_and_no_cache_is_created(self):
        with mock.patch.dict(os.environ, {"GOOGLE_API_KEY": "", "GEMINI_API_KEY": ""}):
            t = translate.Translator(cache=self.cache)
        self.assertEqual(t.many(["今天的重點", "x"], "en"), [None, None])
        self.assertFalse(self.cache.exists(), "a disabled translator must not touch the disk")

    def test_texts_are_batched_cached_and_served_from_cache_next_time(self):
        t, fake = self._translator([json.dumps(["Today's highlights", "Second"])])
        self.assertEqual(t.many(["今天的重點", "第二段"], "en"), ["Today's highlights", "Second"])
        self.assertEqual(fake.calls, 1, "two short texts go in one request")
        again, fake2 = self._translator([])
        self.assertEqual(again.many(["第二段", "今天的重點"], "en"), ["Second", "Today's highlights"])
        self.assertEqual((fake2.calls, again.stats["cached"]), (0, 2), "the second run reads the cache only")

    def test_text_already_in_the_target_language_is_returned_without_a_call(self):
        t, fake = self._translator([])
        self.assertEqual(t.many(["Plain English", "", None], "en"), ["Plain English", "", None])
        self.assertEqual(t.many(["已經是中文的摘要"], "zh"), ["已經是中文的摘要"])
        self.assertEqual(fake.calls, 0)

    def test_a_misaligned_array_is_redone_one_text_per_call(self):
        t, fake = self._translator([json.dumps(["only one"]), json.dumps(["A"]), json.dumps(["B"])])
        self.assertEqual(t.many(["甲", "乙"], "en"), ["A", "B"])
        self.assertEqual(fake.calls, 3, "one batch call plus one call per text")

    def test_an_unparseable_single_answer_leaves_that_text_untranslated(self):
        t, fake = self._translator(["not json"])
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(t.many(["甲"], "en"), [None])
            t.report("test")
        self.assertEqual(t.stats["failed"], 1)
        self.assertIn("1 failed", out.getvalue())

    def test_a_long_text_starts_a_new_batch(self):
        long = "長" * translate.BATCH_CHARS
        t, fake = self._translator([json.dumps(["short"]), json.dumps(["long"])])
        self.assertEqual(t.many(["短", long], "en"), ["short", "long"])
        self.assertEqual(fake.calls, 2, "a text that would overflow the batch goes in its own call")


if __name__ == "__main__":
    unittest.main()
