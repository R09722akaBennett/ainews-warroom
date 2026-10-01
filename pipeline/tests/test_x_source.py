from __future__ import annotations

import io
import json
import tempfile
import unittest
from datetime import datetime, timezone
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

import httpx

from labs import x_source

HANDLES = [h for _, h in x_source._handles()]
UID = {h.lower(): str(i + 1) for i, h in enumerate(HANDLES)}
KEY_OF = {str(i + 1): key for i, (key, _) in enumerate(x_source._handles())}


def _posts(uid: str, first: int, n: int) -> list[dict]:
    return [{"id": str(int(uid) * 1000 + first + i), "text": f"post {uid}-{first + i}", "created_at": "2026-10-01T00:00:00Z"}
            for i in range(n)]


def transport(fail_uid: str, failure):
    """Answer like X: two posts per account, but account fail_uid fails on its second page.

    Account fail_uid's first page carries a next_token, so the failing page
    comes after a page X has already billed.
    """
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        path = request.url.path
        if path == "/2/users/by":
            names = request.url.params["usernames"].split(",")
            return httpx.Response(200, json={"data": [{"username": n, "id": UID[n.lower()]} for n in names]})
        uid = path.split("/")[3]
        if uid == fail_uid:
            if "pagination_token" in request.url.params:
                if isinstance(failure, Exception):
                    raise failure
                return httpx.Response(failure, json={"title": "Service Unavailable"})
            return httpx.Response(200, json={"data": _posts(uid, 0, 3), "meta": {"next_token": "p2"}})
        return httpx.Response(200, json={"data": _posts(uid, 0, 2), "meta": {}})

    return httpx.MockTransport(handler), requests


class FetchXItemsFailureTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        patcher = mock.patch.object(x_source, "STATE", Path(self._tmp.name) / "x_state.json")
        patcher.start()
        self.addCleanup(patcher.stop)
        self.today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def _run(self, failure):
        t, requests = transport("8", failure)
        self.log = io.StringIO()
        with httpx.Client(transport=t) as client, redirect_stdout(self.log):
            out = x_source.fetch_x_items(client)
        return out, json.loads(x_source.STATE.read_text(encoding="utf-8")), requests

    def _check_partial_run(self, out, state):
        read = [str(i) for i in range(1, 8)]
        got_uids = {it["raw"]["id"][:-3] for items in out.values() for it in items}
        self.assertEqual(got_uids, set(read), "accounts 1-7 were read in full, so their posts must be returned")
        self.assertEqual(sum(len(v) for v in out.values()), 14, "two posts each from accounts 1-7, none from 8")
        self.assertNotIn("8", state["since"], "account 8 failed part-way, so its since_id must not advance")
        for uid in read:
            self.assertEqual(state["since"][uid], str(int(uid) * 1000 + 1),
                             f"account {uid} was read to the end, so since_id moves to its newest post")
        self.assertEqual(state["billed"][self.today], 14 + 3,
                         "X bills every post on a returned page, including account 8's first page")
        self.assertEqual(len([k for k in out if k == KEY_OF["8"]]), 0, "the failed account contributes nothing")

    def test_a_503_part_way_returns_the_accounts_already_read_and_bills_the_pages_fetched(self):
        out, state, requests = self._run(503)
        self._check_partial_run(out, state)
        self.assertIn("stopped for this run (HTTPStatusError: 503)", self.log.getvalue(), "the stop is logged")
        self.assertFalse(any(r.url.path.startswith("/2/users/9/") for r in requests),
                         "reading must stop at the failure instead of moving on to account 9")

    def test_a_read_timeout_part_way_returns_the_accounts_already_read(self):
        out, state, _ = self._run(httpx.ReadTimeout("timed out"))
        self._check_partial_run(out, state)

    def test_a_rerun_after_the_failure_reads_the_failed_account_again(self):
        self._run(503)
        t, requests = transport("none", 503)
        with httpx.Client(transport=t) as client, redirect_stdout(io.StringIO()):
            out = x_source.fetch_x_items(client)
        acct8 = [r for r in requests if r.url.path == "/2/users/8/tweets"]
        self.assertTrue(acct8 and "start_time" in acct8[0].url.params,
                        "account 8 never got a since_id, so the next run reads it from the start window again")
        self.assertIn(KEY_OF["8"], out, "the re-run must return account 8's posts")

    def test_user_lookups_are_counted_per_day_and_not_repeated_once_cached(self):
        _, state, _ = self._run(503)
        self.assertEqual(state["lookups"][self.today], len(HANDLES), "each handle X returned is one billed lookup")
        t, requests = transport("none", 503)
        with httpx.Client(transport=t) as client, redirect_stdout(io.StringIO()):
            x_source.fetch_x_items(client)
        state = json.loads(x_source.STATE.read_text(encoding="utf-8"))
        self.assertFalse(any(r.url.path == "/2/users/by" for r in requests), "cached ids must not be looked up again")
        self.assertEqual(state["lookups"][self.today], len(HANDLES), "no new lookups, so the count stays")


if __name__ == "__main__":
    unittest.main()
