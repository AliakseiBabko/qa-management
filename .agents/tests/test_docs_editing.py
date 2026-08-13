"""Unit tests for .agents/scripts/docs_editing.py.

No real Google API calls anywhere in this file - `build_*_requests()`
functions are pure and tested directly; `safe_*`/`delete_and_reinsert()`
are tested against a FakeDocsService (same pattern as
test_pipeline_common_m2_input.py) that just records what it was called
with. No real document ids, project/person/client names, or business
content anywhere in this file - every doc/paragraph here is synthetic
placeholder text.

Run:  python -m unittest discover -s .agents/tests
"""
from __future__ import annotations

import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import docs_editing as de  # noqa: E402


# ---------------------------------------------------------------------
# Shared fixture helpers (same shape as test_pipeline_common_m2_input.py)
# ---------------------------------------------------------------------

def _paragraph(text: str, style: str = "NORMAL_TEXT") -> dict:
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
    """Fake enough of the Docs API surface for this module:
    `.documents().get(...).execute()` returns a fixed doc body,
    `.documents().batchUpdate(...).execute()` just records the requests
    it was called with."""

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


# ---------------------------------------------------------------------
# Read-only inspection helpers
# ---------------------------------------------------------------------

class ListHeadingsTests(unittest.TestCase):
    def test_returns_only_heading_paragraphs_in_order(self):
        doc = _doc([
            ("Placeholder Doc Title", "HEADING_1"),
            ("Section A", "HEADING_2"),
            ("Some body prose about placeholder topic X.", "NORMAL_TEXT"),
            ("Section B", "HEADING_2"),
            ("Sub-section B.1", "HEADING_3"),
            ("More placeholder prose.", "NORMAL_TEXT"),
        ])
        service = FakeDocsService(doc)
        headings = de.list_headings(service, "doc-1")
        self.assertEqual([h[3].strip() for h in headings], ["Placeholder Doc Title", "Section A", "Section B", "Sub-section B.1"])
        self.assertEqual([h[0] for h in headings], ["HEADING_1", "HEADING_2", "HEADING_2", "HEADING_3"])

    def test_levels_filter_restricts_which_styles_are_returned(self):
        doc = _doc([
            ("Title", "HEADING_1"),
            ("Section", "HEADING_2"),
            ("Sub-section", "HEADING_3"),
        ])
        service = FakeDocsService(doc)
        headings = de.list_headings(service, "doc-1", levels=("HEADING_2",))
        self.assertEqual([h[3].strip() for h in headings], ["Section"])

    def test_no_headings_returns_empty_list(self):
        doc = _doc([("Just prose, no headings at all.", "NORMAL_TEXT")])
        service = FakeDocsService(doc)
        self.assertEqual(de.list_headings(service, "doc-1"), [])


class FindParagraphContainingTests(unittest.TestCase):
    def test_finds_first_matching_paragraph(self):
        doc = _doc([
            ("First placeholder paragraph.", "NORMAL_TEXT"),
            ("Second placeholder paragraph with a needle inside it.", "NORMAL_TEXT"),
            ("Third placeholder paragraph, also with needle.", "NORMAL_TEXT"),
        ])
        service = FakeDocsService(doc)
        result = de.find_paragraph_containing(service, "doc-1", "needle")
        self.assertIsNotNone(result)
        start, end, text = result
        self.assertEqual(start, doc["body"]["content"][1]["startIndex"])
        self.assertIn("Second placeholder paragraph", text)

    def test_no_match_returns_none(self):
        doc = _doc([("Nothing relevant here.", "NORMAL_TEXT")])
        service = FakeDocsService(doc)
        self.assertIsNone(de.find_paragraph_containing(service, "doc-1", "needle"))


class DocumentEndIndexTests(unittest.TestCase):
    def test_returns_index_before_trailing_empty_paragraph(self):
        doc = _doc([
            ("Some placeholder content.", "NORMAL_TEXT"),
            ("", "NORMAL_TEXT"),  # the trailing empty paragraph every real Doc ends with
        ])
        service = FakeDocsService(doc)
        end_index = de.document_end_index(service, "doc-1")
        trailing_para = doc["body"]["content"][-1]
        self.assertEqual(end_index, trailing_para["endIndex"] - 1)
        self.assertEqual(end_index, trailing_para["startIndex"])


# ---------------------------------------------------------------------
# build_batch_insert_requests / safe_batch_insert_text - the ordering fix
# ---------------------------------------------------------------------

class BuildBatchInsertRequestsTests(unittest.TestCase):
    def test_edits_are_applied_in_descending_index_order_regardless_of_input_order(self):
        # Deliberately given in ASCENDING order - the exact shape that
        # caused the real corruption incident this module fixes.
        edits = [
            de.DocEdit(index=100, text="low index text"),
            de.DocEdit(index=500, text="high index text"),
        ]
        requests = de.build_batch_insert_requests(edits)
        insert_locations = [r["insertText"]["location"]["index"] for r in requests if "insertText" in r]
        self.assertEqual(insert_locations, [500, 100])  # higher index applied first

    def test_three_edits_arbitrary_order_sorted_correctly(self):
        edits = [
            de.DocEdit(index=250, text="middle"),
            de.DocEdit(index=10, text="lowest"),
            de.DocEdit(index=900, text="highest"),
        ]
        requests = de.build_batch_insert_requests(edits)
        insert_locations = [r["insertText"]["location"]["index"] for r in requests if "insertText" in r]
        self.assertEqual(insert_locations, [900, 250, 10])

    def test_style_range_matches_exactly_the_inserted_text_length(self):
        edits = [de.DocEdit(index=42, text="a placeholder sentence.", style="HEADING_2")]
        requests = de.build_batch_insert_requests(edits)
        insert_req = next(r for r in requests if "insertText" in r)
        style_req = next(r for r in requests if "updateParagraphStyle" in r)

        inserted_text = insert_req["insertText"]["text"]
        insert_index = insert_req["insertText"]["location"]["index"]
        style_range = style_req["updateParagraphStyle"]["range"]

        self.assertEqual(insert_index, 42)
        self.assertEqual(style_range["startIndex"], 42)
        self.assertEqual(style_range["endIndex"], 42 + len(inserted_text))
        self.assertEqual(style_req["updateParagraphStyle"]["paragraphStyle"]["namedStyleType"], "HEADING_2")

    def test_default_style_is_normal_text(self):
        requests = de.build_batch_insert_requests([de.DocEdit(index=1, text="x")])
        style_req = next(r for r in requests if "updateParagraphStyle" in r)
        self.assertEqual(style_req["updateParagraphStyle"]["paragraphStyle"]["namedStyleType"], "NORMAL_TEXT")

    def test_each_edit_produces_exactly_one_insert_and_one_restyle_request(self):
        edits = [de.DocEdit(index=i, text=f"text {i}") for i in (5, 50, 500)]
        requests = de.build_batch_insert_requests(edits)
        self.assertEqual(len(requests), 6)
        self.assertEqual(sum(1 for r in requests if "insertText" in r), 3)
        self.assertEqual(sum(1 for r in requests if "updateParagraphStyle" in r), 3)

    def test_insert_and_its_own_restyle_are_paired_adjacently(self):
        # Regression guard: each edit's insertText must be immediately
        # followed by its own updateParagraphStyle, in the SAME position
        # in the request list every time - never separated or reordered
        # relative to each other (only relative to OTHER edits).
        edits = [de.DocEdit(index=300, text="B"), de.DocEdit(index=100, text="A")]
        requests = de.build_batch_insert_requests(edits)
        self.assertIn("insertText", requests[0])
        self.assertIn("updateParagraphStyle", requests[1])
        self.assertEqual(requests[0]["insertText"]["location"]["index"], 300)
        self.assertEqual(requests[1]["updateParagraphStyle"]["range"]["startIndex"], 300)
        self.assertIn("insertText", requests[2])
        self.assertIn("updateParagraphStyle", requests[3])
        self.assertEqual(requests[2]["insertText"]["location"]["index"], 100)


class SafeBatchInsertTextTests(unittest.TestCase):
    def test_empty_edits_issues_no_api_call(self):
        service = FakeDocsService(_doc([("x", "NORMAL_TEXT")]))
        de.safe_batch_insert_text(service, "doc-1", [])
        self.assertEqual(service.batch_update_calls, [])

    def test_single_batch_update_call_with_all_edits(self):
        service = FakeDocsService(_doc([("x", "NORMAL_TEXT")]))
        edits = [de.DocEdit(index=200, text="second"), de.DocEdit(index=10, text="first")]
        de.safe_batch_insert_text(service, "doc-1", edits)
        self.assertEqual(len(service.batch_update_calls), 1)
        requests = service.batch_update_calls[0]["requests"]
        insert_locations = [r["insertText"]["location"]["index"] for r in requests if "insertText" in r]
        self.assertEqual(insert_locations, [200, 10])

    def test_safe_insert_text_wraps_a_single_edit(self):
        service = FakeDocsService(_doc([("x", "NORMAL_TEXT")]))
        de.safe_insert_text(service, "doc-1", 77, "placeholder text", style="HEADING_3")
        self.assertEqual(len(service.batch_update_calls), 1)
        requests = service.batch_update_calls[0]["requests"]
        insert_req = next(r for r in requests if "insertText" in r)
        style_req = next(r for r in requests if "updateParagraphStyle" in r)
        self.assertEqual(insert_req["insertText"]["location"]["index"], 77)
        self.assertEqual(style_req["updateParagraphStyle"]["paragraphStyle"]["namedStyleType"], "HEADING_3")


# ---------------------------------------------------------------------
# delete_and_reinsert - the repair primitive
# ---------------------------------------------------------------------

class BuildDeleteAndReinsertRequestsTests(unittest.TestCase):
    def test_delete_only_when_no_reinsert(self):
        requests = de.build_delete_and_reinsert_requests(100, 150)
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0]["deleteContentRange"]["range"], {"startIndex": 100, "endIndex": 150})

    def test_reinsert_after_delete_range_applies_insert_first(self):
        # Reinsertion point is AFTER the deleted range - insert must be
        # applied first (higher index), matching the ordering rule.
        reinsert = de.DocEdit(index=1000, text="placeholder repair text")
        requests = de.build_delete_and_reinsert_requests(100, 150, reinsert=reinsert)
        self.assertIn("insertText", requests[0])
        self.assertIn("updateParagraphStyle", requests[1])
        self.assertIn("deleteContentRange", requests[2])
        self.assertEqual(requests[0]["insertText"]["location"]["index"], 1000)

    def test_reinsert_before_delete_range_applies_delete_first(self):
        # Reinsertion point is BEFORE the deleted range - delete must be
        # applied first (higher start position among the two operations).
        reinsert = de.DocEdit(index=10, text="placeholder repair text")
        requests = de.build_delete_and_reinsert_requests(100, 150, reinsert=reinsert)
        self.assertIn("deleteContentRange", requests[0])
        self.assertIn("insertText", requests[1])
        self.assertEqual(requests[1]["insertText"]["location"]["index"], 10)

    def test_reinsert_index_inside_deleted_range_raises(self):
        reinsert = de.DocEdit(index=120, text="ambiguous")
        with self.assertRaises(ValueError):
            de.build_delete_and_reinsert_requests(100, 150, reinsert=reinsert)

    def test_reinsert_index_exactly_at_delete_start_is_allowed_and_treated_as_before(self):
        # Boundary case: index == delete_start is NOT strictly inside
        # (100 < 100 is False), so this must not raise.
        reinsert = de.DocEdit(index=100, text="boundary case")
        requests = de.build_delete_and_reinsert_requests(100, 150, reinsert=reinsert)
        self.assertIn("deleteContentRange", requests[0])


class DeleteAndReinsertExecutionTests(unittest.TestCase):
    def test_issues_single_batch_update_call(self):
        service = FakeDocsService(_doc([("x", "NORMAL_TEXT")]))
        reinsert = de.DocEdit(index=1000, text="repaired placeholder text")
        de.delete_and_reinsert(service, "doc-1", 100, 150, reinsert=reinsert)
        self.assertEqual(len(service.batch_update_calls), 1)
        requests = service.batch_update_calls[0]["requests"]
        self.assertTrue(any("deleteContentRange" in r for r in requests))
        self.assertTrue(any("insertText" in r for r in requests))


# ---------------------------------------------------------------------
# CLI - targeted, read-only verification (no real Google API calls: the
# CLI dispatch functions are called directly against a FakeDocsService,
# bypassing build_cli_parser()'s own auth-wiring main() function)
# ---------------------------------------------------------------------

class PreviewTests(unittest.TestCase):
    def test_short_text_returned_unchanged(self):
        self.assertEqual(de.preview("a short placeholder line"), "a short placeholder line")

    def test_long_text_truncated_with_ellipsis(self):
        long_text = "placeholder word " * 20  # far longer than PREVIEW_LEN
        result = de.preview(long_text)
        self.assertLessEqual(len(result), de.PREVIEW_LEN + 1)  # +1 for the ellipsis char
        self.assertTrue(result.endswith("…"))
        self.assertNotEqual(result, long_text.strip())

    def test_embedded_newlines_and_whitespace_collapsed(self):
        text = "line one\n\n   line two\twith a tab\nline three"
        result = de.preview(text, limit=200)
        self.assertNotIn("\n", result)
        self.assertNotIn("\t", result)
        self.assertEqual(result, "line one line two with a tab line three")

    def test_custom_limit_respected(self):
        result = de.preview("placeholder " * 10, limit=10)
        self.assertLessEqual(len(result), 11)


class BuildCliParserDispatchTests(unittest.TestCase):
    def test_headings_subcommand_parses_and_dispatches(self):
        args = de.build_cli_parser().parse_args(["headings", "--id", "doc-1"])
        self.assertEqual(args.command, "headings")
        self.assertEqual(args.id, "doc-1")
        self.assertIsNone(args.levels)
        self.assertIs(args.func, de._cmd_headings)

    def test_headings_subcommand_accepts_levels(self):
        args = de.build_cli_parser().parse_args(["headings", "--id", "doc-1", "--levels", "HEADING_1,HEADING_2"])
        self.assertEqual(args.levels, "HEADING_1,HEADING_2")

    def test_find_subcommand_parses_and_dispatches(self):
        args = de.build_cli_parser().parse_args(["find", "--id", "doc-1", "--text", "needle"])
        self.assertEqual(args.command, "find")
        self.assertEqual(args.text, "needle")
        self.assertIs(args.func, de._cmd_find)

    def test_end_index_subcommand_parses_and_dispatches(self):
        args = de.build_cli_parser().parse_args(["end-index", "--id", "doc-1"])
        self.assertEqual(args.command, "end-index")
        self.assertIs(args.func, de._cmd_end_index)

    def test_missing_command_is_a_parse_error(self):
        with self.assertRaises(SystemExit):
            de.build_cli_parser().parse_args([])

    def test_find_without_text_is_a_parse_error(self):
        with self.assertRaises(SystemExit):
            de.build_cli_parser().parse_args(["find", "--id", "doc-1"])


class CliHeadingsOutputTests(unittest.TestCase):
    def test_output_is_compact_one_line_per_heading(self):
        doc = _doc([
            ("Placeholder Title", "HEADING_1"),
            ("Section One", "HEADING_2"),
            ("Some placeholder body prose, not a heading.", "NORMAL_TEXT"),
            ("Section Two", "HEADING_2"),
        ])
        service = FakeDocsService(doc)
        args = de.build_cli_parser().parse_args(["headings", "--id", "doc-1"])
        buf = io.StringIO()
        with redirect_stdout(buf):
            exit_code = de._cmd_headings(service, args)
        output = buf.getvalue()
        self.assertEqual(exit_code, 0)
        lines = [line for line in output.strip().split("\n") if line]
        self.assertEqual(len(lines), 3)  # 3 headings, not the NORMAL_TEXT paragraph
        self.assertIn("Placeholder Title", lines[0])
        self.assertIn("HEADING_1", lines[0])

    def test_levels_filter_applied_from_cli_args(self):
        doc = _doc([("Title", "HEADING_1"), ("Section", "HEADING_2")])
        service = FakeDocsService(doc)
        args = de.build_cli_parser().parse_args(["headings", "--id", "doc-1", "--levels", "HEADING_2"])
        buf = io.StringIO()
        with redirect_stdout(buf):
            de._cmd_headings(service, args)
        output = buf.getvalue()
        self.assertNotIn("Title", output)
        self.assertIn("Section", output)

    def test_no_headings_prints_a_short_placeholder_not_an_error(self):
        doc = _doc([("Just prose.", "NORMAL_TEXT")])
        service = FakeDocsService(doc)
        args = de.build_cli_parser().parse_args(["headings", "--id", "doc-1"])
        buf = io.StringIO()
        with redirect_stdout(buf):
            exit_code = de._cmd_headings(service, args)
        self.assertEqual(exit_code, 0)
        self.assertIn("no headings", buf.getvalue())

    def test_never_prints_the_full_long_paragraph_text_only_preview(self):
        # A single heading whose text is far longer than the preview
        # limit - proves the CLI never echoes the whole paragraph, only
        # a bounded preview, regardless of how large the document is.
        long_heading_text = "Placeholder Section Heading About A Very Long Topic " * 5
        doc = _doc([(long_heading_text, "HEADING_2")])
        service = FakeDocsService(doc)
        args = de.build_cli_parser().parse_args(["headings", "--id", "doc-1"])
        buf = io.StringIO()
        with redirect_stdout(buf):
            de._cmd_headings(service, args)
        output = buf.getvalue()
        self.assertLess(len(output), len(long_heading_text))
        self.assertNotIn(long_heading_text.strip(), output)


class CliFindOutputTests(unittest.TestCase):
    def test_found_paragraph_prints_compact_preview_with_indices(self):
        doc = _doc([
            ("First placeholder paragraph.", "NORMAL_TEXT"),
            ("Second placeholder paragraph with a needle inside it.", "NORMAL_TEXT"),
        ])
        service = FakeDocsService(doc)
        args = de.build_cli_parser().parse_args(["find", "--id", "doc-1", "--text", "needle"])
        buf = io.StringIO()
        with redirect_stdout(buf):
            exit_code = de._cmd_find(service, args)
        output = buf.getvalue()
        self.assertEqual(exit_code, 0)
        expected_start = doc["body"]["content"][1]["startIndex"]
        self.assertIn(f"start={expected_start}", output)
        self.assertIn("Second placeholder paragraph", output)
        self.assertEqual(len(output.strip().split("\n")), 1)  # one compact line, not a dump

    def test_not_found_prints_not_found_and_returns_nonzero(self):
        doc = _doc([("Nothing relevant here.", "NORMAL_TEXT")])
        service = FakeDocsService(doc)
        args = de.build_cli_parser().parse_args(["find", "--id", "doc-1", "--text", "needle"])
        buf = io.StringIO()
        with redirect_stdout(buf):
            exit_code = de._cmd_find(service, args)
        self.assertEqual(exit_code, 1)
        self.assertIn("not found", buf.getvalue())

    def test_never_prints_the_full_long_paragraph_text_only_preview(self):
        long_text = "Placeholder paragraph content repeated many times to be very long. " * 6 + "needle"
        doc = _doc([(long_text, "NORMAL_TEXT")])
        service = FakeDocsService(doc)
        args = de.build_cli_parser().parse_args(["find", "--id", "doc-1", "--text", "needle"])
        buf = io.StringIO()
        with redirect_stdout(buf):
            de._cmd_find(service, args)
        output = buf.getvalue()
        self.assertLess(len(output), len(long_text))
        self.assertNotIn(long_text.strip(), output)


class CliEndIndexOutputTests(unittest.TestCase):
    def test_prints_bare_index_only(self):
        doc = _doc([("Some placeholder content.", "NORMAL_TEXT"), ("", "NORMAL_TEXT")])
        service = FakeDocsService(doc)
        args = de.build_cli_parser().parse_args(["end-index", "--id", "doc-1"])
        buf = io.StringIO()
        with redirect_stdout(buf):
            exit_code = de._cmd_end_index(service, args)
        expected = de.document_end_index(service, "doc-1")
        self.assertEqual(exit_code, 0)
        self.assertEqual(buf.getvalue().strip(), str(expected))


if __name__ == "__main__":
    unittest.main()
