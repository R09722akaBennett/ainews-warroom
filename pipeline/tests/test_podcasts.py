from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from podcasts import __main__ as pod
from helpers import ScriptedGemini, response

POST = {"id": 1, "slug": "ep-one", "title": "Episode one", "post_date": "2026-09-20T00:00:00Z"}
EPISODE = {"slug": "ep-one", "title": "Episode one", "subtitle": "", "intro": ["notes"], "we_discuss": [],
           "guests": [], "chapters": [], "transcript": [], "date": "2026-09-20", "url": "u"}


class PodcastFailureTrackingTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.cache = Path(self._tmp.name)
        for target, value in [("CACHE", self.cache), ("list_episodes", lambda: [POST]),
                              ("ingest", lambda ep: "skipped")]:
            p = mock.patch.object(pod, target, value)
            p.start()
            self.addCleanup(p.stop)
        self.collect = mock.MagicMock(side_effect=lambda post: dict(EPISODE))
        p = mock.patch.object(pod, "collect", self.collect)
        p.start()
        self.addCleanup(p.stop)

    def _run(self, gemini_text, *args):
        fake = ScriptedGemini([response(gemini_text)])
        out = io.StringIO()
        with mock.patch.object(pod, "_gemini", fake), mock.patch.object(sys, "argv", ["podcasts", "--live", *args]), \
                redirect_stdout(out):
            rc = pod.main()
        return rc, out.getvalue(), fake

    def _failed(self):
        return json.loads((self.cache / "ep-one.failed").read_text(encoding="utf-8"))

    def test_an_unparseable_summary_is_recorded_with_its_attempt_count(self):
        rc, _, _ = self._run("this is not JSON")
        self.assertEqual(rc, 1, "a failed episode makes the run fail so cron alerts")
        self.assertEqual(self._failed()["attempts"], 1, "the first failure is attempt 1")
        self.assertIn("unparseable", self._failed()["error"], "the error is kept for the owner to read")
        self.assertFalse((self.cache / "ep-one.json").exists(), "a failed episode is not cached as done")

    def test_after_three_failures_the_slug_is_skipped_and_the_log_says_so(self):
        for _ in range(3):
            self._run("not JSON")
        self.assertEqual(self._failed()["attempts"], 3, "each run adds one attempt")
        self.collect.reset_mock()
        rc, out, fake = self._run('{"one_liner": "x"}')
        self.assertEqual(fake.calls, 0, "a given-up slug must not cost another Gemini call")
        self.collect.assert_not_called()
        self.assertIn("ep-one skipped after 3 unparseable summaries", out, "the skip must be visible in the log")
        self.assertEqual(rc, 0, "a known bad episode must not alert every day")

    def test_force_retries_a_skipped_slug_and_success_clears_the_failure(self):
        for _ in range(3):
            self._run("not JSON")
        rc, _, fake = self._run('{"one_liner": "x", "quotes": []}', "--force", "ep-one")
        self.assertEqual((rc, fake.calls), (0, 1), "--force must retry the slug")
        self.assertTrue((self.cache / "ep-one.json").exists(), "the episode is cached after success")
        self.assertFalse((self.cache / "ep-one.failed").exists(), "success removes the failure record")


if __name__ == "__main__":
    unittest.main()
