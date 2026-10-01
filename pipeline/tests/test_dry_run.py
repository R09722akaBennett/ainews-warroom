from __future__ import annotations

import io
import json
import os
import socket
import sys
import tempfile
import unittest
import urllib.request
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

import httpx

from candidates import __main__ as candidates_main
from db.summaries import save_summary
from labs import __main__ as labs_main
from labs import llm, x_source
from helpers import TempDB


class NetworkUsed(AssertionError):
    pass


def _refuse(*args, **kwargs):
    raise NetworkUsed("a dry-run made a network call")


class NoNetwork(TempDB):
    """Block every way the pipeline reaches the network: httpx, genai, urllib, raw sockets."""

    def setUp(self):
        super().setUp()
        for target, attr in [(httpx.Client, "send"), (httpx.AsyncClient, "send"), (llm.genai, "Client"),
                             (urllib.request, "urlopen"), (socket.socket, "connect"), (socket, "create_connection")]:
            p = mock.patch.object(target, attr, _refuse)
            p.start()
            self.addCleanup(p.stop)
        p = mock.patch.object(x_source, "STATE", Path(self.tmp) / "x_state.json")
        p.start()
        self.addCleanup(p.stop)
        p = mock.patch.dict(os.environ, {"X_BEARER_TOKEN": "fake", "INGEST_API_TOKEN": "fake",
                                         "TYPESAFE_API_KEY": "fake"})
        p.start()
        self.addCleanup(p.stop)

    def _main(self, module, *args):
        out = io.StringIO()
        with mock.patch.object(sys, "argv", ["prog", *args]), redirect_stdout(out):
            rc = module.main()
        lines = out.getvalue().splitlines()
        self.assertTrue(lines, "a dry-run must say what it would do")
        self.assertEqual([l for l in lines if not l.startswith("[dry-run] ")], [],
                         "every line of a dry-run starts with [dry-run]")
        return rc, lines


class LabsDryRunTest(NoNetwork):
    def test_labs_without_live_makes_no_request_and_only_prints_dry_run_lines(self):
        self.insert_item()
        x_source.STATE.write_text(json.dumps({"users": {"openai": "1"}, "since": {"1": "5"}}), encoding="utf-8")
        _, lines = self._main(labs_main, "--date", "2026-10-01")
        text = "\n".join(lines)
        self.assertIn("Will read 23 X accounts (1 from their since_id", text, "the accounts to read are listed")
        self.assertIn("looking up 22 new handles", text, "uncached handles cost a lookup, so they are counted")
        self.assertIn("Will classify 1 pending items", text, "the pending backlog is reported")
        self.assertIn("Will not write the weekly report", text, "without --classify there is no weekly report")

    def test_labs_classify_without_live_reports_the_weekly_report_it_would_write(self):
        save_summary("labs_daily", "2026-09-29", "2026-09-29", "d", "content")
        save_summary("labs_daily", "2026-09-30", "2026-09-30", "d", "今天沒有重要動態。")
        _, lines = self._main(labs_main, "--classify", "--date", "2026-10-05")
        self.assertIn("[dry-run] Will write the labs weekly report for 2026-09-28 ~ 2026-10-04 from 1 daily briefs",
                      lines, "the weekly window is reported, counting only briefs the report would use")

    def test_labs_dry_run_does_not_write_x_state(self):
        self._main(labs_main)
        self.assertFalse(x_source.STATE.exists(), "a dry-run must not touch the X state")

    def test_labs_classify_since_without_live_only_counts_the_backlog(self):
        self.insert_item(date="2026-09-20")
        _, lines = self._main(labs_main, "--classify-since", "2026-09-01", "--date", "2026-10-01")
        self.assertEqual(len(lines), 1, "a reclassify run neither collects nor writes a brief")
        self.assertIn("Will classify 1 pending items from 2026-09-01", lines[0], "the backlog since the date is counted")


class CandidatesDryRunTest(NoNetwork):
    def test_candidates_without_live_makes_no_request_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as out_dir, \
                mock.patch.object(candidates_main, "OUT_DIR", Path(out_dir) / "pipeline" / "data" / "candidates"):
            rc, lines = self._main(candidates_main)
            self.assertFalse((Path(out_dir) / "pipeline").exists(), "a dry-run must not write the candidates file")
        self.assertEqual(rc, 0, "a dry-run exits 0")
        self.assertTrue(any("Will score every candidate with jev-" in l for l in lines),
                        "with a key set, the Jev step is described")

    def test_candidates_dry_run_says_jev_will_be_skipped_without_a_key(self):
        with mock.patch.dict(os.environ, {"TYPESAFE_API_KEY": ""}):
            _, lines = self._main(candidates_main)
        self.assertTrue(any("Will skip Jev (TYPESAFE_API_KEY is not set)" in l for l in lines),
                        "the reason Jev will not run is stated")


if __name__ == "__main__":
    unittest.main()
