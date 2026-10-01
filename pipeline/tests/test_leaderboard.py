"""The arena.ai score cell is read by shape, not by the utility class of the day."""
import unittest

from bs4 import BeautifulSoup

from leaderboard.scraper import _parse_category_page, _parse_score_cell

CURRENT_CELL = (
    '<td><div class="flex items-center gap-2"><span class="body-sm">1525</span>'
    '<span class="text-text-tertiary body-xs">±9</span>'
    '<button><span class="border text-[10px]">Preliminary</span></button></div></td>'
)
OLD_CELL = '<td><span class="text-sm">1,287</span><span class="text-tertiary">±6</span></td>'


def _table(score_cell: str) -> str:
    return (
        "<table><thead><tr><th>Rank</th><th>Rank Spread</th><th>Model</th><th>Score</th><th>Votes</th></tr></thead>"
        "<tbody><tr><td>1</td><td>1</td><td><a>gemini-4-argon-high</a><span>Google · Proprietary</span></td>"
        f"{score_cell}<td>4,942</td></tr></tbody></table>"
    )


class ScoreCellTest(unittest.TestCase):
    def test_the_current_arena_markup_yields_the_score_and_interval(self):
        """With the old class-based selector this cell parsed as score 0, which is what the site showed."""
        cell = BeautifulSoup(CURRENT_CELL, "html.parser").td
        self.assertEqual(_parse_score_cell(cell), (1525, "±9"))

    def test_the_previous_arena_markup_still_parses(self):
        cell = BeautifulSoup(OLD_CELL, "html.parser").td
        self.assertEqual(_parse_score_cell(cell), (1287, "±6"))

    def test_a_cell_without_a_number_reports_zero_rather_than_raising(self):
        cell = BeautifulSoup("<td><span>N/A</span></td>", "html.parser").td
        self.assertEqual(_parse_score_cell(cell), (0, ""))

    def test_a_category_page_row_carries_the_parsed_score(self):
        rows = _parse_category_page(_table(CURRENT_CELL))
        self.assertEqual(len(rows), 1, "one model row")
        self.assertEqual(rows[0]["score"], 1525)
        self.assertEqual(rows[0]["ci"], "±9")
        self.assertEqual(rows[0]["votes"], 4942)
