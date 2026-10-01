from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout
from unittest import mock

from db.summaries import save_summary
from labs import weekly
from helpers import TempDB


class WeeklyFallbackTest(TempDB):
    def setUp(self):
        super().setUp()
        save_summary("labs_daily", "2026-09-29", "2026-09-29", "d", "**OpenAI** shipped a model")

    def _run(self, text):
        with mock.patch.object(weekly, "call_llm", return_value=(text, {"input": 1, "output": 2, "total": 3})), \
                redirect_stdout(io.StringIO()):
            report = weekly.generate_weekly_from_daily("2026-10-05")
        saved = self.rows("SELECT title, content, start_date, end_date FROM periodic_summaries "
                          "WHERE period = 'labs_weekly'")
        return report, saved

    def test_bad_json_still_saves_the_week_under_the_fallback_title(self):
        report, saved = self._run("## 本週重點\n- not JSON at all")
        self.assertEqual(len(saved), 1, "a malformed answer must not lose the weekly report")
        self.assertEqual(saved[0]["title"], "實驗室週報 (2026-09-28 ~ 2026-10-04)",
                         "the fallback title names the covered week")
        self.assertEqual(saved[0]["content"], "## 本週重點\n- not JSON at all", "the raw text becomes the content")
        self.assertEqual(report["title"], saved[0]["title"], "the returned report matches what was saved")

    def test_json_without_content_falls_back_too(self):
        _, saved = self._run('{"title": "only a title"}')
        self.assertEqual(saved[0]["title"], "實驗室週報 (2026-09-28 ~ 2026-10-04)",
                         "a report without content is not usable, so the fallback applies")

    def test_a_proper_json_report_is_saved_as_given(self):
        _, saved = self._run('```json\n{"title": "T", "content": "C"}\n```')
        self.assertEqual((saved[0]["title"], saved[0]["content"]), ("T", "C"), "a fenced JSON report is parsed")


if __name__ == "__main__":
    unittest.main()
