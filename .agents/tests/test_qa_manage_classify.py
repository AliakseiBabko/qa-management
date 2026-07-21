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

BRACKETED_TWO_SPEAKERS = (
    "[Speaker 1]\n"
    "Hello, how are things going.\n\n"
    "[Speaker 2]\n"
    "Good, we shipped the fix yesterday.\n\n"
    "[Speaker 1]\n"
    "Great, let's continue next week.\n"
)

BRACKETED_THREE_SPEAKERS = (
    "[Speaker 1]\n"
    "Status update please.\n\n"
    "[Speaker 2]\n"
    "All green on my side.\n\n"
    "[Speaker 3]\n"
    "Same here, no blockers.\n"
)

BRACKETED_TIMESTAMP_ONLY = (
    "[00:00:01]\n"
    "Hello, how are things going.\n\n"
    "[00:00:12]\n"
    "Good, we shipped the fix yesterday.\n\n"
    "[00:00:20]\n"
    "Great, let's continue next week.\n"
)

TIMESTAMPED_TURNS = (
    "00:00:01 Alex:\n"
    "Hello, how are things going.\n\n"
    "00:00:12 Bay:\n"
    "Good, we shipped the fix yesterday.\n\n"
    "00:00:20 Alex:\n"
    "Great, let's continue next week.\n"
)

LOW_CONTENT_BRACKETED_NOTE = (
    "This is a short reference note.\n\n"
    "[Speaker 1]\n\n"
    "Nothing else here worth flagging as a transcript.\n"
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
        # schema stability: new Phase 8.1 keys are additive, always present
        for key in ("bracketed_speaker_marker_count", "timestamp_turn_marker_count",
                    "distinct_turn_identities", "paragraph_turn_density"):
            self.assertIn(key, signals)

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

    def test_bracketed_two_speaker_signal(self):
        signals = qa_manage.detect_format_signals(BRACKETED_TWO_SPEAKERS, ".txt")
        self.assertGreaterEqual(signals["bracketed_speaker_marker_count"], 2)
        self.assertEqual(signals["distinct_turn_identities"], 2)
        self.assertTrue(signals["likely_transcript"])

    def test_bracketed_three_speaker_signal(self):
        signals = qa_manage.detect_format_signals(BRACKETED_THREE_SPEAKERS, ".txt")
        self.assertGreaterEqual(signals["bracketed_speaker_marker_count"], 3)
        self.assertEqual(signals["distinct_turn_identities"], 3)
        self.assertTrue(signals["likely_transcript"])

    def test_bracketed_timestamp_only_gives_no_identity(self):
        signals = qa_manage.detect_format_signals(BRACKETED_TIMESTAMP_ONLY, ".txt")
        self.assertGreaterEqual(signals["bracketed_speaker_marker_count"], 3)
        # bare "[00:00:01]" style brackets mark a turn boundary but name no
        # one - must not be inferred as any particular speaker count.
        self.assertEqual(signals["distinct_turn_identities"], 0)
        self.assertTrue(signals["likely_transcript"])

    def test_timestamped_turn_signal(self):
        signals = qa_manage.detect_format_signals(TIMESTAMPED_TURNS, ".txt")
        self.assertGreaterEqual(signals["timestamp_turn_marker_count"], 3)
        self.assertEqual(signals["distinct_turn_identities"], 2)
        self.assertTrue(signals["likely_transcript"])

    def test_low_content_bracketed_note_does_not_over_trigger(self):
        signals = qa_manage.detect_format_signals(LOW_CONTENT_BRACKETED_NOTE, ".txt")
        self.assertEqual(signals["bracketed_speaker_marker_count"], 1)
        self.assertFalse(signals["likely_transcript"])

    def test_paragraph_turn_density_present_and_bounded(self):
        signals = qa_manage.detect_format_signals(BRACKETED_TWO_SPEAKERS, ".txt")
        self.assertGreaterEqual(signals["paragraph_turn_density"], 0.0)
        self.assertLessEqual(signals["paragraph_turn_density"], 1.0)


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

    def test_bracketed_two_speaker_transcript_suggests_qa_1to1(self):
        signals = qa_manage.detect_format_signals(BRACKETED_TWO_SPEAKERS, ".txt")
        candidates = qa_manage.classify_candidate_routes(GRAPH, signals, row("r1"))
        types = {(c["source_type"], c["variant"]) for c in candidates}
        self.assertIn(("qa_1to1", "m1"), types)
        self.assertIn(("qa_1to1", "m2"), types)
        self.assertIn(("qa_1to1", "mixed"), types)
        qa = next(c for c in candidates if c["source_type"] == "qa_1to1")
        self.assertIn("bracketed/timestamped turn markers", qa["reason"])

    def test_bracketed_three_speaker_transcript_suggests_meeting_transcript_only(self):
        signals = qa_manage.detect_format_signals(BRACKETED_THREE_SPEAKERS, ".txt")
        candidates = qa_manage.classify_candidate_routes(GRAPH, signals, row("r1"))
        types = {(c["source_type"], c["variant"]) for c in candidates}
        self.assertEqual(types, {("meeting_transcript", "multi_project"), ("meeting_transcript", "single_project")})
        self.assertNotIn(("qa_1to1", "m1"), types)

    def test_bracketed_timestamp_only_suggests_meeting_transcript_not_qa_1to1(self):
        signals = qa_manage.detect_format_signals(BRACKETED_TIMESTAMP_ONLY, ".txt")
        candidates = qa_manage.classify_candidate_routes(GRAPH, signals, row("r1"))
        types = {(c["source_type"], c["variant"]) for c in candidates}
        self.assertEqual(types, {("meeting_transcript", "multi_project"), ("meeting_transcript", "single_project")})
        self.assertFalse(any(c["source_type"] == "qa_1to1" for c in candidates))

    def test_timestamped_turns_suggest_meeting_transcript_and_qa_1to1(self):
        signals = qa_manage.detect_format_signals(TIMESTAMPED_TURNS, ".txt")
        candidates = qa_manage.classify_candidate_routes(GRAPH, signals, row("r1"))
        types = {(c["source_type"], c["variant"]) for c in candidates}
        self.assertIn(("meeting_transcript", "multi_project"), types)
        self.assertIn(("qa_1to1", "m2"), types)

    def test_low_content_bracketed_note_yields_no_candidates(self):
        signals = qa_manage.detect_format_signals(LOW_CONTENT_BRACKETED_NOTE, ".txt")
        candidates = qa_manage.classify_candidate_routes(GRAPH, signals, row("r1"))
        self.assertEqual(candidates, [])

    def test_candidates_never_carry_project_or_person_values(self):
        signals = qa_manage.detect_format_signals(BRACKETED_TWO_SPEAKERS, ".txt")
        candidates = qa_manage.classify_candidate_routes(GRAPH, signals, row("r1"))
        for c in candidates:
            self.assertNotIn("project", c)
            self.assertNotIn("person", c)
            self.assertIn(set(c["required_scope"]), [set(), {"project"}, {"person"}, {"project", "person"}])


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
