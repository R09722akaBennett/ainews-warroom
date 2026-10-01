from __future__ import annotations

import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from export import costs, from_wiki


class TagsByDateTest(unittest.TestCase):
    def _call(self, error):
        err = io.StringIO()
        with mock.patch.object(from_wiki.subprocess, "run", side_effect=error), redirect_stderr(err):
            tags = from_wiki._tags_by_date(["2026-10-01"])
        return tags, err.getvalue()

    def test_a_failing_psql_returns_no_tags_and_warns(self):
        tags, err = self._call(subprocess.CalledProcessError(1, ["docker"], stderr="the database system is starting up"))
        self.assertEqual(tags, {}, "a restarting postgres must not stop the export")
        self.assertIn("warning", err, "the failure must be visible on stderr")
        self.assertIn("starting up", err, "the psql message tells the reader why")

    def test_a_missing_docker_binary_returns_no_tags_and_warns(self):
        tags, err = self._call(FileNotFoundError(2, "No such file or directory", "docker"))
        self.assertEqual(tags, {}, "no docker on the host must not stop the export")
        self.assertIn("warning", err, "the failure must be visible on stderr")

    def test_main_still_writes_reports_json_when_postgres_is_down(self):
        with tempfile.TemporaryDirectory() as tmp:
            wiki = Path(tmp) / "wiki"
            (wiki / "notes" / "news").mkdir(parents=True)
            (wiki / "notes" / "news" / "2026-10-01.md").write_text("---\ntitle: x\n---\n# 快報\n內容\n", encoding="utf-8")
            data = Path(tmp) / "reports.json"
            with mock.patch.object(from_wiki, "DATA", data), \
                    mock.patch.object(from_wiki, "SUMMARIES", Path(tmp) / "summaries.json"), \
                    mock.patch.object(from_wiki, "_archive_items", return_value=[]), \
                    mock.patch.object(from_wiki.subprocess, "run",
                                      side_effect=subprocess.CalledProcessError(2, ["docker"], stderr="down")), \
                    mock.patch.object(sys, "argv", ["from_wiki", "--wiki", str(wiki)]), \
                    redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                from_wiki.main()
            reports = json.loads(data.read_text(encoding="utf-8"))
        self.assertEqual([r["date"] for r in reports], ["2026-10-01"], "the day's digest must reach reports.json")
        self.assertEqual(reports[0]["tags"], {"companies": [], "models": [], "topics": []},
                         "without the DB the report goes out untagged")


class CostsTest(unittest.TestCase):
    def test_x_counts_start_on_the_backfill_day_and_include_user_lookups(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            state = tmp / "x_state.json"
            state.write_text(json.dumps({"billed": {"2026-09-30": 5, "2026-10-01": 44, "2026-10-02": 10},
                                         "lookups": {"2026-10-02": 2}}), encoding="utf-8")
            out = tmp / "costs.json"
            with mock.patch.object(costs, "X_STATE", state), mock.patch.object(costs, "DATA", out), \
                    mock.patch.object(costs, "CANDIDATES", tmp), mock.patch.object(costs, "WIKI_NEWS", tmp), \
                    redirect_stdout(io.StringIO()):
                costs.main()
            days = {d["date"]: d for d in json.loads(out.read_text(encoding="utf-8"))["days"]}
        self.assertNotIn("2026-09-30", days, "days before X_DAILY_FROM are covered by the one-off entry")
        self.assertEqual(days["2026-10-01"]["x_posts_billed"], 44,
                         "the regular reads on the backfill day are not part of the one-off and must be counted")
        self.assertEqual(days["2026-10-02"]["x_user_lookups"], 2, "lookups are carried per day")
        self.assertAlmostEqual(days["2026-10-02"]["x_usd"], 10 * 0.005 + 2 * 0.01,
                               msg="X cost is posts at $0.005 plus lookups at $0.01")


class SiteDataDiffTest(unittest.TestCase):
    """Run site-data.sh's own change check against a scratch repo."""

    def setUp(self):
        script = (Path(__file__).resolve().parents[1] / "site-data.sh").read_text(encoding="utf-8")
        line = next(line for line in script.splitlines() if line.startswith("if git diff"))
        self.check = line.removeprefix("if ").split("; then")[0]
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = Path(self._tmp.name)
        self.file = self.repo / "labs.json"
        git = ["git", "-C", str(self.repo), "-c", "user.email=t@t", "-c", "user.name=t"]
        subprocess.run([*git, "init", "-q"], check=True)
        self.file.write_text('{\n  "updatedAt": "2026-10-01T10:00:00Z",\n  "items": [1]\n}\n', encoding="utf-8")
        subprocess.run([*git, "add", "."], check=True)
        subprocess.run([*git, "commit", "-qm", "init"], check=True)

    def _unchanged(self) -> bool:
        cmd = f'FILES=(labs.json); {self.check}'
        return subprocess.run(["bash", "-c", cmd], cwd=self.repo).returncode == 0

    def test_a_rewritten_updated_at_alone_counts_as_no_change(self):
        self.file.write_text('{\n  "updatedAt": "2026-10-02T10:00:00Z",\n  "items": [1]\n}\n', encoding="utf-8")
        self.assertTrue(self._unchanged(), "only the timestamp moved, so the day must not commit and deploy")

    def test_a_data_change_next_to_updated_at_is_still_a_change(self):
        self.file.write_text('{\n  "updatedAt": "2026-10-02T10:00:00Z",\n  "items": [1, 2]\n}\n', encoding="utf-8")
        self.assertFalse(self._unchanged(), "real data changed, so the site must be updated")


if __name__ == "__main__":
    unittest.main()
