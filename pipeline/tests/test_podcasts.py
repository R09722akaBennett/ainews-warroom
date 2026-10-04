from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
import urllib.error
from email.message import EmailMessage
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from podcasts import __main__ as pod
from helpers import ScriptedGemini, response

POST = {"id": 1, "slug": "ep-one", "title": "Episode one", "post_date": "2026-09-20T00:00:00Z"}
EPISODE = {"slug": "ep-one", "title": "Episode one", "subtitle": "", "intro": ["notes"], "we_discuss": [],
           "guests": [], "chapters": [], "transcript": [], "date": "2026-09-20", "url": "u",
           "fetchedFrom": "api"}


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


def _mail(subject: str, html: str) -> bytes:
    m = EmailMessage()
    m["From"] = "Latent.Space <swyx@substack.com>"
    m["Subject"] = subject
    m.set_content("text")
    m.add_alternative(html, subtype="html")
    return m.as_bytes()


TRANSCRIPT_HTML = ('<p>Show notes.</p><h1>Transcript</h1><h2>Opening</h2>'
                   '<p><strong>Alex [00:00:05]:</strong> Hello from the mail.</p>')
# Substack mails wrap the post in div.body.markup and follow it with a referral box.
MAIL_HTML = (f'<div class="post"><div class="body markup">{TRANSCRIPT_HTML}</div></div>'
             '<div class="post-cta"><h4>Invite your friends</h4><p>© 2026 Latent.Space</p></div>')
MAILS = [_mail("[AINews] not much happened today", "<p>issue</p>"),
         _mail("Episode one", MAIL_HTML)]


class FakeImap:
    """Stand in for imaplib.IMAP4_SSL over MAILS; records how the mailbox was opened."""

    instances: list = []

    def __init__(self, host):
        self.selected = None
        self.logged_out = False
        FakeImap.instances.append(self)

    def login(self, user, password):
        pass

    def select(self, mailbox, readonly=False):
        self.selected = (mailbox, readonly)

    def search(self, charset, query):
        return "OK", [b"1 2"]

    def fetch(self, num, what):
        return "OK", [(b"", MAILS[int(num) - 1])]

    def logout(self):
        self.logged_out = True


class PodcastMailFallbackTest(unittest.TestCase):
    def setUp(self):
        FakeImap.instances = []
        p = mock.patch.object(pod.imaplib, "IMAP4_SSL", FakeImap)
        p.start()
        self.addCleanup(p.stop)
        p = mock.patch.dict(os.environ, {"SUBSTACK_SID": "sid", "GMAIL_IMAP_USER": "u", "GMAIL_IMAP_PASSWORD": "p"})
        p.start()
        self.addCleanup(p.stop)

    def _api(self, outcome):
        def get_json(url, ua, cookie=None):
            if isinstance(outcome, BaseException):
                raise outcome
            return outcome
        p = mock.patch.object(pod, "_get_json", get_json)
        p.start()
        self.addCleanup(p.stop)

    def test_a_rejected_cookie_falls_back_to_the_subscriber_mail(self):
        self._api(urllib.error.HTTPError("u", 403, "Forbidden", {}, None))
        with redirect_stdout(io.StringIO()) as out:
            ep = pod.collect(POST)
        self.assertEqual(ep["fetchedFrom"], "mail")
        self.assertEqual([t["text"] for c in ep["transcript"] for t in c["turns"]], ["Hello from the mail."],
                         "the transcript comes from the mail whose subject matches the post title, "
                         "without the referral box after the post")
        self.assertIn("SUBSTACK_SID expired?", out.getvalue(), "the log says why the mail was used")
        imap = FakeImap.instances[0]
        self.assertEqual(imap.selected, ('"[Gmail]/All Mail"', True), "the mailbox is opened read-only")
        self.assertTrue(imap.logged_out)

    def test_without_imap_credentials_the_api_error_is_reported(self):
        self._api(urllib.error.HTTPError("u", 403, "Forbidden", {}, None))
        with mock.patch.dict(os.environ, {"GMAIL_IMAP_USER": ""}):
            with self.assertRaises(ValueError) as cm:
                pod.collect(POST)
        self.assertIn("403", str(cm.exception))
        self.assertEqual(FakeImap.instances, [], "no credentials, no IMAP connection")

    def test_a_usable_api_post_never_opens_the_mailbox(self):
        self._api({"post": {"body_html": TRANSCRIPT_HTML.replace("mail", "api")}})
        ep = pod.collect(POST)
        self.assertEqual(ep["fetchedFrom"], "api")
        self.assertEqual(FakeImap.instances, [])

    def test_a_post_without_transcript_in_both_places_fails_with_both_reasons(self):
        self._api({"post": {"body_html": "<p>short</p>"}})
        with mock.patch.object(FakeImap, "search", lambda *a: ("OK", [b""])):
            with self.assertRaises(ValueError) as cm:
                pod.collect(POST)
        self.assertIn("no usable subscriber mail", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
