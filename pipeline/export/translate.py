"""Translate exported site text between Traditional Chinese and English, with a cache.

Each kind of site data is written in one language (digests, lab briefs and
podcast summaries in Chinese, reading summaries in English) and the site
serves both, so the exporters ask here for the other language. Every
translation is cached in pipeline/data/translations.db under a hash of the
text, so a text goes to Gemini once and an unchanged report costs nothing on
later runs.

Without GOOGLE_API_KEY (or GEMINI_API_KEY) nothing is translated: every call
returns None and the exporters leave the translated fields out, so the site
shows the native text in both languages. Tests and local dry runs work in
that mode.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

CACHE_PATH = Path(__file__).resolve().parents[1] / "data" / "translations.db"
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
# One request carries several texts as a JSON array; these bounds keep the
# answer well inside the output limit and a mismatch cheap to redo.
BATCH_ITEMS = 25
BATCH_CHARS = 15_000

PROMPTS = {
    "en": """Translate every string in the JSON array below from Traditional Chinese into natural English
for AI engineers. Keep Markdown structure, links, code, numbers, emoji and reference markers such as
(ref-3) exactly as they are. Keep names of products, companies, models, papers and people as written,
and keep English phrases unchanged. Return only a JSON array of strings, same length and order.

{items}""",
    "zh": """把下面 JSON 陣列裡的每一段英文翻成台灣繁體中文，讀者是 AI 工程師。保留 Markdown 結構、連結、程式碼、
數字、emoji 與 (ref-3) 這類標記；產品、公司、模型、論文、人名與技術名詞保留英文。只輸出一個 JSON 陣列的字串，
長度與順序跟輸入一樣。

{items}""",
}
CJK = re.compile(r"[㐀-鿿]")
LATIN = re.compile(r"[A-Za-z]")


def _key(dst: str, text: str) -> str:
    return hashlib.sha256(f"{dst}\x00{text}".encode("utf-8")).hexdigest()


def already_in(dst: str, text: str) -> bool:
    """Return whether text already reads as the target language, so it needs no call.

    A target of "zh" is satisfied by text that is mostly CJK (a Chinese
    newsletter summarised before extraction switched to English); a target of
    "en" by text without any CJK character.
    """
    cjk, latin = len(CJK.findall(text)), len(LATIN.findall(text))
    if dst == "en":
        return cjk == 0
    return cjk > 0 and cjk >= 0.3 * (cjk + latin)


class Translator:
    """Translate texts into "en" or "zh", reading the cache first and Gemini for the rest.

    enabled defaults to whether a Gemini key is in the environment; a
    disabled translator answers None for everything without opening the
    cache. stats counts texts served from the cache, texts sent and calls
    made, for the exporter's log line.
    """

    def __init__(self, cache: Path = CACHE_PATH, enabled: bool | None = None, client=None):
        self.enabled = bool(os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")) if enabled is None else enabled
        self.cache_path = cache
        self._db: sqlite3.Connection | None = None
        self._client = client
        self.stats = {"cached": 0, "translated": 0, "calls": 0, "failed": 0}

    # ---- cache ----
    def _db_conn(self) -> sqlite3.Connection:
        if self._db is None:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            self._db = sqlite3.connect(self.cache_path)
            self._db.execute("CREATE TABLE IF NOT EXISTS translations (key TEXT PRIMARY KEY, dst TEXT NOT NULL, "
                             "text TEXT NOT NULL, translated TEXT NOT NULL, created TEXT NOT NULL)")
        return self._db

    def _cached(self, dst: str, text: str) -> str | None:
        row = self._db_conn().execute("SELECT translated FROM translations WHERE key = ?", (_key(dst, text),)).fetchone()
        return row[0] if row else None

    def _store(self, dst: str, pairs: list[tuple[str, str]]) -> None:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        self._db_conn().executemany(
            "INSERT OR REPLACE INTO translations (key, dst, text, translated, created) VALUES (?, ?, ?, ?, ?)",
            [(_key(dst, t), dst, t, tr, now) for t, tr in pairs])
        self._db_conn().commit()

    # ---- model ----
    def _gemini(self):
        # One client per translator: a client created inline is garbage-collected
        # while its request is still open ("client has been closed").
        if self._client is None:
            from google import genai
            self._client = genai.Client()
        return self._client

    def _call(self, dst: str, texts: list[str]) -> list[str] | None:
        """Return the translations of texts in order, or None when the answer does not line up."""
        self.stats["calls"] += 1
        prompt = PROMPTS[dst].format(items=json.dumps(texts, ensure_ascii=False))
        resp = self._gemini().models.generate_content(
            model=GEMINI_MODEL, contents=prompt, config={"response_mime_type": "application/json"})
        try:
            out = json.loads(resp.text)
        except (TypeError, ValueError):
            return None
        if not isinstance(out, list) or len(out) != len(texts) or not all(isinstance(x, str) and x.strip() for x in out):
            return None
        return out

    # ---- public ----
    def many(self, texts: list[str | None], dst: str) -> list[str | None]:
        """Return the translation of each text into dst, None where it is unavailable.

        Texts already in the target language and empty texts come back as
        they are. Nothing is sent when the translator is disabled.
        """
        if dst not in PROMPTS:
            raise ValueError(f"dst must be one of {sorted(PROMPTS)}")
        result: list[str | None] = [None] * len(texts)
        if not self.enabled:
            return result
        todo: list[int] = []
        for i, text in enumerate(texts):
            if text is None or not text.strip() or already_in(dst, text):
                result[i] = text
            elif (hit := self._cached(dst, text)) is not None:
                result[i] = hit
                self.stats["cached"] += 1
            else:
                todo.append(i)
        batch: list[int] = []
        size = 0
        for i in todo + [None]:  # type: ignore[list-item]
            if batch and (i is None or len(batch) >= BATCH_ITEMS or size + len(texts[i]) > BATCH_CHARS):
                self._run_batch(dst, texts, batch, result)
                batch, size = [], 0
            if i is not None:
                batch.append(i)
                size += len(texts[i])
        return result

    def _run_batch(self, dst: str, texts: list, batch: list[int], result: list) -> None:
        items = [texts[i] for i in batch]
        out = self._call(dst, items)
        if out is None and len(items) > 1:
            # The array came back misaligned; one text per call cannot misalign.
            out = [(self._call(dst, [t]) or [None])[0] for t in items]
        elif out is None:
            out = [None]
        pairs = []
        for i, tr in zip(batch, out):
            result[i] = tr
            if tr is None:
                self.stats["failed"] += 1
            else:
                self.stats["translated"] += 1
                pairs.append((texts[i], tr))
        if pairs:
            self._store(dst, pairs)

    def one(self, text: str | None, dst: str) -> str | None:
        return self.many([text], dst)[0]

    def report(self, prefix: str) -> None:
        """Print one log line with the run's counts, or nothing when the translator is disabled."""
        if not self.enabled:
            print(f"{prefix}: translation off (no Gemini key), native text only")
            return
        s = self.stats
        print(f"{prefix}: translated {s['translated']} texts in {s['calls']} calls, {s['cached']} from cache"
              + (f", {s['failed']} failed" if s["failed"] else ""))
