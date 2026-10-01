"""Shared fakes for the pipeline tests: a throwaway warroom.db and a scripted Gemini client."""

from __future__ import annotations

import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

import db.connection


class TempDB(unittest.TestCase):
    """Point warroom.db at a fresh file for each test and create the schema."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = self._tmp.name
        patcher = mock.patch.object(db.connection, "DB_PATH", os.path.join(self.tmp, "warroom.db"))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self._tmp.cleanup)
        db.connection.init_db()

    def insert_item(self, **kw) -> int:
        row = {"date": "2026-10-01", "company": "openai", "title": "t", "url": "https://x.com/OpenAI/status/1",
               "source": "X @OpenAI", "published_at": "2026-10-01T00:00:00Z", "category": "pending",
               "ai_related": 1, "summary": "", "content": "c", **kw}
        conn = db.connection.get_conn()
        cur = conn.execute(f"INSERT INTO competitor_items ({','.join(row)}) VALUES ({','.join('?' * len(row))})",
                           tuple(row.values()))
        conn.commit()
        conn.close()
        return cur.lastrowid

    def rows(self, sql: str, params: tuple = ()) -> list[dict]:
        conn = db.connection.get_conn()
        out = [dict(r) for r in conn.execute(sql, params).fetchall()]
        conn.close()
        return out


def response(text: str | None, tokens: int = 10):
    """Return an object shaped like a google-genai GenerateContentResponse."""
    return SimpleNamespace(text=text, usage_metadata=SimpleNamespace(
        prompt_token_count=tokens, candidates_token_count=tokens, total_token_count=2 * tokens))


class ScriptedGemini:
    """Stand in for genai.Client; each generate_content call takes the next scripted outcome.

    An outcome that is an exception is raised, anything else is returned.
    """

    def __init__(self, outcomes: list):
        self.outcomes = list(outcomes)
        self.calls = 0
        self.models = self

    def __call__(self, *args, **kwargs):
        return self

    def generate_content(self, **kwargs):
        self.calls += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome
