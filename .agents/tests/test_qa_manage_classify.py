"""Unit tests for qa_manage.py's read-only `classify <run-id>` command.

classify is the pre-`start` helper for a `discovered` run: deterministic
format signals (no AI/LLM call) plus unranked candidate_routes hints, read
from Current source (falling back to Source). Covers source-path
selection, missing-file handling, preview truncation, signal detection,
candidate-route generation, low-confidence/manual and ignore-suggestion
paths, read-only enforcement, and the JSON envelope. All fixture text is
synthetic placeholders - no real names/projects, and nothing here writes
anywhere (so there is nothing to "store" in the queue or repo either).

Run:  python -m unittest discover -s .agents/tests
"""

from __future__ import annotations

import inspect
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import qa_manage

GRAPH = {
    "sources": {
        "qa_1to1": {
            "routes": {
                "m1": {"skills": ["m1-skill"], "entry": ["m1_doc"]},
                "m2": {"skills": ["m2-skill"], "entry": ["m2_doc"]},
                "mixed": {"skills": ["m1-skill", "m2-skill"], "entry": ["m1_doc", "m2_doc"]},
            }
        },
        "meeting_transcript": {
            "routes": {
                "multi_project": {"skills": ["meeting-skill"], "entry": ["m2_input_doc"]},
                "single_project": {"skills": ["shared-rules"], "entry": ["m2_input_doc"]},
            }
        },
        "strategy_chat": {"skills": ["strategy-skill"], "entry": ["m2_input_doc"]},
        "admin_note": {"skills": ["admin-skill"], "entry": ["people_registry_doc"]},
        "people_case_chat": {"skills": ["risk-skill"], "entry": ["m1_risk_doc"], "scope_required": ["person"]},
    },
    "documents": {
        "m1_doc": {"scope": "person", "downstream": []},
        "m2_doc": {"scope": "project", "downstream": []},
        "m2_input_doc": {"scope": "project", "downstream": []},
        "people_registry_doc": {"scope": "workspace", "downstream": []},
        "m1_risk_doc": {"scope": "workspace", "downstream": []},
    },
}

TRANSCRIPT_TWO_SPEAKERS = (
    "<Person1>:\n"
    "Hello, how are things going on <Project1>?\n\n"
    "<Person2>:\n"
    "Good, we shipped the fix yesterday.\n\n"
    "<Person1>:\n"
    "Great, let's continue next week.\n"
)

TRANSCRIPT_THREE_SPEAKERS = (
    "<Person1>:\n"
    "Status update please.\n\n"
    "<Person2>:\n"
    "All green on my side.\n\n"
    "<Person3>:\n"
    "Same here, no blockers.\n"
)

CHAT_TEXT = (
    "<Person1>, Feb 5, 3:13 PM\n"
    "Quick question about the release.\n"
    "<Person2>, Feb 5, 3:14 PM\n"
    "Sure, go ahead.\n"
    "<Person1>, Fri 11:58 AM\n"
    "Thanks, resolved now.\n"
)

EMAIL_TEXT = (
    "From: person1@example.com\n"
    "To: person2@example.com\n"
    "Subject: Status update\n"
    "Sent: Monday\n\n"
    "Please see the attached summary.\n"
)

PLAIN_TEXT = (
    "This is a plain reference note with no speaker turns, no chat "
    "headers, and no email headers at all, just ordinary prose text "
    "spanning a couple of lines for good measure.\n"
)


def row(run_id, **extra) -> dict:
    base = {
        "Run ID": run_id, "Source": f"00_Inbox/{run_id}.txt",
        "Current source": f"00_Inbox/{run_id}.txt", "Source disposition": "inbox",
        "Source type": "raw_transcript", "Route variant": "",
        "Project": "", "Person": "", "Scopes": "",
        "Status": "discovered", "Stage": "", "Skills": "", "Entries": "",
        "Discovered": "2026-01-01 00:00", "Started": "", "Last mutation": "2026-01-01 00:00",
        "Completed": "", "Snapshot": "", "Reason": "", "Summary": "", "Source text version": "",
    }
    base.update(extra)
    return base


class Args:
    def __init__(self, run_id, json=True, debug=False, max_preview_chars=None):
        self.run_id = run_id
        self.json = json
        self.debug = debug
        self.max_preview_chars = max_preview_chars


def write_file(root: Path, relative_path: str, content: str) -> None:
    full = root / relative_path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content, encoding="utf-8")


def run_classify(target_row, data_root, other_rows=None, max_preview_chars=None):
    rows = (other_rows or []) + [target_row]
    mock_services = {"drive": MagicMock(), "sheets": MagicMock()}
    with patch("qa_manage.get_services_cached", return_value=mock_services), \
         patch("qa_manage.find_queue", return_value={"id": "sheet_id"}), \
         patch("qa_manage.read_queue", return_value=rows), \
         patch("qa_manage.load_graph", return_value=GRAPH), \
         patch("qa_manage.DATA_ROOT", data_root):
        res = qa_manage.cmd_classify(Args(target_row["Run ID"], max_preview_chars=max_preview_chars))
    return res, mock_services


class SourcePathSelectionTests(unittest.TestCase):
    def test_uses_current_source_when_it_differs_from_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_file(root, "00_Inbox/live.txt", TRANSCRIPT_TWO_SPEAKERS)
            r = row("r1", Source="00_Source_Docs\\legacy\\gone.txt", **{"Current source": "00_Inbox/live.txt"})
            res, _ = run_classify(r, root)
            self.assertTrue(res.ok)
            self.assertEqual(res.data["source_path_field_used"], "current_source")
            self.assertEqual(res.data["source_path_used"], "00_Inbox/live.txt")

    def test_falls_back_to_source_when_current_source_blank(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_file(root, "00_Inbox/only.txt", TRANSCRIPT_TWO_SPEAKERS)
            r = row("r1", Source="00_Inbox/only.txt", **{"Current source": ""})
            res, _ = run_classify(r, root)
            self.assertTrue(res.ok)
            self.assertEqual(res.data["source_path_field_used"], "source")
            self.assertEqual(res.data["source_path_used"], "00_Inbox/only.txt")

    def test_missing_file_returns_ok_false_via_main(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)  # nothing written - file genuinely absent
            rows = [row("r1", **{"Current source": "00_Inbox/does-not-exist.txt"})]
            mock_services = {"drive": MagicMock(), "sheets": MagicMock()}
            with patch("sys.argv", ["qa_manage.py", "classify", "r1", "--json"]), \
                 patch("qa_manage.get_services_cached", return_value=mock_services), \
                 patch("qa_manage.find_queue", return_value={"id": "sheet_id"}), \
                 patch("qa_manage.read_queue", return_value=rows), \
                 patch("qa_manage.load_graph", return_value=GRAPH), \
                 patch("qa_manage.DATA_ROOT", root):
                buf = io.StringIO()
                with patch("sys.stdout", buf):
                    code = qa_manage.main()
            self.assertEqual(code, 1)
            envelope = json.loads(buf.getvalue())
            self.assertFalse(envelope["ok"])
            self.assertEqual(envelope["command"], "classify")
            self.assertEqual(len(envelope["errors"]), 1)
            self.assertIn("not found", envelope["errors"][0])
            self.assertIn("current_source", envelope["errors"][0])


class PreviewTruncationTests(unittest.TestCase):
    def test_preview_is_capped_at_max_preview_chars(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            long_text = "<Person1>:\n" + ("filler line of placeholder text\n" * 500)
            write_file(root, "00_Inbox/big.txt", long_text)
            r = row("r1", **{"Current source": "00_Inbox/big.txt"})
            res, _ = run_classify(r, root, max_preview_chars=50)
            self.assertEqual(len(res.data["preview"]), 50)
            self.assertTrue(res.data["preview_truncated"])
            self.assertEqual(res.data["preview_max_chars"], 50)

    def test_default_preview_cap_used_when_not_specified(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_file(root, "00_Inbox/small.txt", TRANSCRIPT_TWO_SPEAKERS)
            r = row("r1", **{"Current source": "00_Inbox/small.txt"})
            res, _ = run_classify(r, root)
            self.assertEqual(res.data["preview_max_chars"], qa_manage.DEFAULT_MAX_PREVIEW_CHARS)
            self.assertFalse(res.data["preview_truncated"])
            self.assertLessEqual(len(res.data["preview"]), qa_manage.DEFAULT_MAX_PREVIEW_CHARS)


class SignalDetectionTests(unittest.TestCase):
    def test_transcript_signal(self):
        signals = qa_manage.detect_format_signals(TRANSCRIPT_TWO_SPEAKERS, ".txt")
        self.assertTrue(signals["text_readable"])
        self.assertEqual(signals["distinct_speaker_prefixes"], 2)
        self.assertTrue(signals["likely_transcript"])
        self.assertFalse(signals["likely_chat"])
        self.assertFalse(signals["likely_email"])

    def test_chat_signal(self):
        signals = qa_manage.detect_format_signals(CHAT_TEXT, ".txt")
        self.assertGreaterEqual(signals["chat_header_line_count"], 3)
        self.assertTrue(signals["likely_chat"])

    def test_email_signal(self):
        signals = qa_manage.detect_format_signals(EMAIL_TEXT, ".txt")
        self.assertGreaterEqual(signals["email_marker_count"], 2)
        self.assertTrue(signals["likely_email"])

    def test_binary_extension_not_read(self):
        signals = qa_manage.detect_format_signals(None, ".docx")
        self.assertFalse(signals["text_readable"])
        self.assertTrue(signals["likely_binary_document"])
        self.assertIsNone(signals["line_count"])


class CandidateRouteGenerationTests(unittest.TestCase):
    def test_two_speaker_transcript_yields_qa_1to1_candidates(self):
        signals = qa_manage.detect_format_signals(TRANSCRIPT_TWO_SPEAKERS, ".txt")
        candidates = qa_manage.classify_candidate_routes(GRAPH, signals, row("r1"))
        types = {(c["source_type"], c["variant"]) for c in candidates}
        self.assertEqual(types, {("qa_1to1", "m1"), ("qa_1to1", "m2"), ("qa_1to1", "mixed")})
        mixed = next(c for c in candidates if c["variant"] == "mixed")
        self.assertEqual(sorted(mixed["required_scope"]), ["person", "project"])
        self.assertIn("2 distinct speaker-like prefixes", mixed["reason"])

    def test_three_speaker_transcript_yields_meeting_transcript_candidates(self):
        signals = qa_manage.detect_format_signals(TRANSCRIPT_THREE_SPEAKERS, ".txt")
        candidates = qa_manage.classify_candidate_routes(GRAPH, signals, row("r1"))
        types = {(c["source_type"], c["variant"]) for c in candidates}
        self.assertEqual(types, {("meeting_transcript", "multi_project"), ("meeting_transcript", "single_project")})

    def test_chat_signal_yields_strategy_chat_candidate(self):
        signals = qa_manage.detect_format_signals(CHAT_TEXT, ".txt")
        candidates = qa_manage.classify_candidate_routes(GRAPH, signals, row("r1"))
        self.assertEqual([(c["source_type"], c["variant"]) for c in candidates], [("strategy_chat", "")])
        self.assertEqual(candidates[0]["required_scope"], ["project"])

    def test_email_signal_yields_admin_note_and_people_case_chat(self):
        signals = qa_manage.detect_format_signals(EMAIL_TEXT, ".txt")
        candidates = qa_manage.classify_candidate_routes(GRAPH, signals, row("r1"))
        types = {(c["source_type"], c["variant"]) for c in candidates}
        self.assertEqual(types, {("admin_note", ""), ("people_case_chat", "")})
        pcc = next(c for c in candidates if c["source_type"] == "people_case_chat")
        self.assertEqual(pcc["required_scope"], ["person"])


class LowConfidenceTests(unittest.TestCase):
    def test_plain_text_yields_no_candidates_and_manual_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_file(root, "00_Inbox/plain.txt", PLAIN_TEXT)
            r = row("r1", **{"Current source": "00_Inbox/plain.txt"})
            res, _ = run_classify(r, root)
            self.assertEqual(res.data["candidate_routes"], [])
            self.assertEqual(res.data["confidence"], "low")
            self.assertTrue(any("manual classification required" in c for c in res.data["commands"]))
            self.assertIn("qa_1to1", res.data["routed_source_types"])


class IgnoreSuggestionTests(unittest.TestCase):
    def test_duplicate_reason_suggests_ignore_and_suppresses_candidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_file(root, "00_Inbox/dup.txt", TRANSCRIPT_TWO_SPEAKERS)
            r = row("r1", **{"Current source": "00_Inbox/dup.txt"},
                    Reason="duplicate content of 20260101-other-run-abc123")
            res, _ = run_classify(r, root)
            self.assertEqual(res.data["candidate_routes"], [])
            self.assertEqual(res.data["ignore_suggestion"]["category"], "duplicate_data_quality")
            self.assertIn("duplicate content of", res.data["ignore_suggestion"]["reason_hint"])
            self.assertTrue(any(c.startswith(f"ignore r1 --category duplicate_data_quality")
                                for c in res.data["commands"]))


class ReadOnlyEnforcementTests(unittest.TestCase):
    FORBIDDEN_SUBSTRINGS = [
        "write_queue(", "export_queue_terminal(", "mirror_git(MIRROR, \"add\"",
        "mirror_git(MIRROR, \"commit\"", ".values().update(", ".values().clear(",
        ".values().append(", "files().create(", "files().update(", ".write_text(", ".write_bytes(",
    ]

    def test_cmd_classify_source_never_calls_write_functions(self):
        source = inspect.getsource(qa_manage.cmd_classify)
        for needle in self.FORBIDDEN_SUBSTRINGS:
            self.assertNotIn(needle, source, f"cmd_classify source contains forbidden call: {needle!r}")

    def test_cmd_classify_never_invokes_write_queue_or_sheet_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_file(root, "00_Inbox/r1.txt", TRANSCRIPT_TWO_SPEAKERS)
            r = row("r1", **{"Current source": "00_Inbox/r1.txt"})
            with patch("qa_manage.write_queue") as mock_write_queue, \
                 patch("qa_manage.export_queue_terminal") as mock_export:
                res, mock_services = run_classify(r, root)

            mock_write_queue.assert_not_called()
            mock_export.assert_not_called()
            mock_services["sheets"].spreadsheets().values().update.assert_not_called()
            mock_services["sheets"].spreadsheets().values().append.assert_not_called()
            mock_services["sheets"].spreadsheets().values().clear.assert_not_called()
            mock_services["drive"].files().create.assert_not_called()
            mock_services["drive"].files().update.assert_not_called()
            self.assertTrue(res.ok)
            # the source file on disk is untouched - classify only reads it
            self.assertEqual((root / "00_Inbox" / "r1.txt").read_text(encoding="utf-8"), TRANSCRIPT_TWO_SPEAKERS)


class NoStoredFullTextTests(unittest.TestCase):
    def test_preview_never_exceeds_requested_cap_even_for_large_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            long_text = "<Person1>:\n" + ("placeholder filler content\n" * 2000)
            write_file(root, "00_Inbox/huge.txt", long_text)
            r = row("r1", **{"Current source": "00_Inbox/huge.txt"})
            res, _ = run_classify(r, root, max_preview_chars=100)
            self.assertLessEqual(len(res.data["preview"]), 100)
            self.assertLess(len(res.data["preview"]), len(long_text))
            self.assertTrue(any("Never write the preview text" in g for g in res.data["guardrails"]))


class JsonEnvelopeTests(unittest.TestCase):
    def test_json_envelope_shape_via_main(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_file(root, "00_Inbox/r1.txt", TRANSCRIPT_TWO_SPEAKERS)
            rows = [row("r1", **{"Current source": "00_Inbox/r1.txt"})]
            mock_services = {"drive": MagicMock(), "sheets": MagicMock()}
            with patch("sys.argv", ["qa_manage.py", "classify", "r1", "--json"]), \
                 patch("qa_manage.get_services_cached", return_value=mock_services), \
                 patch("qa_manage.find_queue", return_value={"id": "sheet_id"}), \
                 patch("qa_manage.read_queue", return_value=rows), \
                 patch("qa_manage.load_graph", return_value=GRAPH), \
                 patch("qa_manage.DATA_ROOT", root):
                buf = io.StringIO()
                with patch("sys.stdout", buf):
                    code = qa_manage.main()
            self.assertEqual(code, 0)
            envelope = json.loads(buf.getvalue())
            self.assertEqual(envelope["schema_version"], 1)
            self.assertTrue(envelope["ok"])
            self.assertEqual(envelope["command"], "classify")
            for key in ("run_id", "source_path_used", "source_path_field_used", "signals",
                        "candidate_routes", "confidence", "commands", "guardrails"):
                self.assertIn(key, envelope["data"])
            self.assertEqual(envelope["warnings"], [])
            self.assertEqual(envelope["errors"], [])


if __name__ == "__main__":
    unittest.main()
