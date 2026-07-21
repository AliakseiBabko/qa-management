from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import pipeline_common as pc


def _paragraph(text: str, style: str = "NORMAL_TEXT") -> dict:
    length = len(text) + 1  # matches the trailing "\n" convention used by _insert_blocks
    return {
        "startIndex": 0,  # overwritten by _doc()
        "endIndex": 0,
        "paragraph": {
            "paragraphStyle": {"namedStyleType": style},
            "elements": [{"textRun": {"content": text + "\n"}}],
        },
    }


def _doc(paragraphs: list[tuple[str, str]]) -> dict:
    """Build a minimal Docs API document body from (text, style) pairs,
    assigning sequential start/end indices the way a real Doc would."""
    content = []
    cursor = 1
    for text, style in paragraphs:
        para = _paragraph(text, style)
        start = cursor
        end = start + len(text) + 1
        para["startIndex"] = start
        para["endIndex"] = end
        content.append(para)
        cursor = end
    return {"body": {"content": content}}


class FakeDocsService:
    """Fake enough of the Docs API surface for _find_answer_heading_start,
    append_to_pending_round and append_doc_round: .documents().get(...).execute()
    returns a fixed doc body, .documents().batchUpdate(...).execute() just
    records the requests it was called with."""

    def __init__(self, doc: dict) -> None:
        self._doc = doc
        self.batch_update_calls: list[dict] = []

    def documents(self):
        return self

    def get(self, documentId: str):  # noqa: N803 - matches google api client naming
        return self

    def batchUpdate(self, documentId: str, body: dict):  # noqa: N802, N803
        self.batch_update_calls.append(body)
        return self

    def execute(self):
        return self._doc


ANSWER = pc.ANSWER_HEADING


class TestFindAnswerHeadingStart(unittest.TestCase):
    def test_single_round_existing_behavior_preserved(self) -> None:
        doc = _doc([
            ("Round A - входные данные M2", "NORMAL_TEXT"),
            ("Раунд: 2026-01-01", "HEADING_2"),
            ("Вопросы от предварительного анализа", "HEADING_2"),
            ("Some open question about placeholder project", "NORMAL_TEXT"),
            (ANSWER, "HEADING_2"),
            ("", "NORMAL_TEXT"),
        ])
        service = FakeDocsService(doc)
        _, start = pc._find_answer_heading_start(service, "doc-1")
        expected = doc["body"]["content"][4]["startIndex"]
        self.assertEqual(expected, start)

    def test_two_rounds_first_answered_second_pending_selects_last(self) -> None:
        doc = _doc([
            ("Placeholder Project - входные данные M2", "NORMAL_TEXT"),
            ("Раунд: 2026-01-01", "HEADING_2"),
            ("Вопросы от предварительного анализа", "HEADING_2"),
            ("Old question about Person A", "NORMAL_TEXT"),
            (ANSWER, "HEADING_2"),
            ("Answered already - resolved.", "NORMAL_TEXT"),
            ("Раунд: 2026-01-15", "HEADING_2"),
            ("Вопросы от предварительного анализа", "HEADING_2"),
            ("New open question about Person B", "NORMAL_TEXT"),
            (ANSWER, "HEADING_2"),
            ("", "NORMAL_TEXT"),
        ])
        service = FakeDocsService(doc)
        _, start = pc._find_answer_heading_start(service, "doc-2")
        # Must be the SECOND answer heading (index 9), not the first (index 4).
        expected = doc["body"]["content"][9]["startIndex"]
        self.assertEqual(expected, start)
        self.assertNotEqual(doc["body"]["content"][4]["startIndex"], start)

    def test_multiple_answer_headings_selects_the_last(self) -> None:
        doc = _doc([
            ("Placeholder Project - входные данные M2", "NORMAL_TEXT"),
            ("Раунд: 2026-01-01", "HEADING_2"),
            (ANSWER, "HEADING_2"),
            ("Answered.", "NORMAL_TEXT"),
            ("Раунд: 2026-02-01", "HEADING_2"),
            (ANSWER, "HEADING_2"),
            ("Also answered.", "NORMAL_TEXT"),
            ("Раунд: 2026-03-01", "HEADING_2"),
            (ANSWER, "HEADING_2"),
            ("", "NORMAL_TEXT"),
        ])
        service = FakeDocsService(doc)
        _, start = pc._find_answer_heading_start(service, "doc-3")
        expected = doc["body"]["content"][8]["startIndex"]
        self.assertEqual(expected, start)

    def test_no_answer_heading_returns_none(self) -> None:
        doc = _doc([
            ("Placeholder Project - входные данные M2", "NORMAL_TEXT"),
            ("Раунд: 2026-01-01", "HEADING_2"),
            ("Вопросы от предварительного анализа", "HEADING_2"),
            ("Some question, no answer heading in this doc at all.", "NORMAL_TEXT"),
        ])
        service = FakeDocsService(doc)
        _, start = pc._find_answer_heading_start(service, "doc-4")
        self.assertIsNone(start)


class TestAppendToPendingRound(unittest.TestCase):
    def test_inserts_addendum_into_current_pending_round_not_old_answered_one(self) -> None:
        doc = _doc([
            ("Placeholder Project - входные данные M2", "NORMAL_TEXT"),
            ("Раунд: 2026-01-01", "HEADING_2"),
            ("Вопросы от предварительного анализа", "HEADING_2"),
            ("Old question about Person A", "NORMAL_TEXT"),
            (ANSWER, "HEADING_2"),
            ("Answered already - resolved.", "NORMAL_TEXT"),
            ("Раунд: 2026-01-15", "HEADING_2"),
            ("Вопросы от предварительного анализа", "HEADING_2"),
            ("New open question about Person B", "NORMAL_TEXT"),
            (ANSWER, "HEADING_2"),
            ("", "NORMAL_TEXT"),
        ])
        pending_answer_start = doc["body"]["content"][9]["startIndex"]
        service = FakeDocsService(doc)

        pc.append_to_pending_round(service, "doc-5", [("normal", "Addendum about Placeholder Project")])

        self.assertEqual(1, len(service.batch_update_calls))
        insert_request = service.batch_update_calls[0]["requests"][0]
        self.assertEqual(pending_answer_start, insert_request["insertText"]["location"]["index"])
        self.assertIn("Addendum about Placeholder Project", insert_request["insertText"]["text"])

    def test_raises_when_no_answer_heading_present(self) -> None:
        doc = _doc([
            ("Placeholder Project - входные данные M2", "NORMAL_TEXT"),
            ("Раунд: 2026-01-01", "HEADING_2"),
            ("Вопросы от предварительного анализа", "HEADING_2"),
            ("Question with no answer heading anywhere in the doc.", "NORMAL_TEXT"),
        ])
        service = FakeDocsService(doc)
        with self.assertRaises(ValueError):
            pc.append_to_pending_round(service, "doc-6", [("normal", "Addendum")])


if __name__ == "__main__":
    unittest.main()
