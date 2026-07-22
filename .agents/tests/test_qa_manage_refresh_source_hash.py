"""Unit tests for qa_manage.py's `refresh-source-hash <run-id>` command and
its `guide`/`pack` integration.

Problem it solves: a human sometimes manually edits an 00_Inbox source
after `scan` already recorded its hash (e.g. adding speaker names/
person-card details to a transcript before `start`) - this intentionally
changes the file's content hash, and the pipeline used to force an agent
to reconcile `Source hash` by hand. `refresh-source-hash` is the explicit,
narrow fix: recompute the same short hash `scan` uses, and only if it
actually differs, update `Source hash` plus an appended `Reason` audit
note and `Last mutation` - nothing else (never source_type/route/scope/
status/stage/entries/outcomes/disposition), and only for a pre-processing
run (discovered/needs_scope/ready) whose Current source resolves under
00_Inbox as a plain-text file. Covers: a successful refresh touching only
the allowed fields, a no-op when the hash already matches, refusal for
every non-pre-processing status and an archived disposition, refusal for
a path outside 00_Inbox, a missing file, a non-text extension, undecodable
bytes, the JSON envelope, and that `guide`/`pack` only surface a
`refresh-source-hash` recommendation for a pre-processing mismatch - never
for an archived or completed run. All fixtures use placeholder names - no
real names/projects.

Run:  python -m unittest discover -s .agents/tests
"""

from __future__ import annotations

import hashlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import qa_manage


def row(run_id, **extra) -> dict:
    base = {
        "Run ID": run_id, "Source": f"00_Inbox/sample-project/{run_id}.txt",
        "Source hash": "aaaaaaaaaaaaaaaa", "Current source": f"00_Inbox/sample-project/{run_id}.txt",
        "Source disposition": "inbox", "Source type": "", "Route variant": "",
        "Project": "", "Person": "", "Scopes": "",
        "Status": "discovered", "Stage": "", "Skills": "", "Entries": "",
        "Discovered": "2026-01-01 00:00", "Started": "", "Last mutation": "2026-01-01 00:00",
        "Completed": "", "Snapshot": "", "Reason": "", "Summary": "", "Source text version": "",
    }
    base.update(extra)
    return base


class Args:
    def __init__(self, run_id, json=True, debug=False):
        self.run_id = run_id
        self.json = json
        self.debug = debug


def write_file(root: Path, relative_path: str, content) -> Path:
    # Always write raw bytes - write_text() would let Windows translate "\n"
    # to "\r\n" on write, which would silently change the hash the test
    # expects vs. the bytes actually read back by hashlib.
    full = root / relative_path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))
    return full


def run_refresh(target_row, data_root, other_rows=None):
    rows = (other_rows or []) + [target_row]
    written: list[list[dict]] = []

    def fake_write_queue(services, sheet, rows_arg):
        written.append([dict(r) for r in rows_arg])

    mock_services = {"drive": MagicMock(), "sheets": MagicMock()}
    with patch("qa_manage.get_services_cached", return_value=mock_services), \
         patch("qa_manage.find_queue", return_value={"id": "sheet_id"}), \
         patch("qa_manage.read_queue", return_value=rows), \
         patch("qa_manage.write_queue", side_effect=fake_write_queue), \
         patch("qa_manage.DATA_ROOT", data_root):
        res = qa_manage.cmd_refresh_source_hash(Args(target_row["Run ID"]))
    return res, written


class RefreshSucceedsTests(unittest.TestCase):
    def test_updates_only_hash_reason_and_last_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            content = "<Person1>:\nManually added speaker details.\n"
            write_file(root, "00_Inbox/sample-project/r1.txt", content)
            expected_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
            r = row("r1", **{"Source hash": "0000000000000000",
                             "Status": "needs_scope", "Reason": "missing project scope"})
            res, written = run_refresh(r, root)

            self.assertTrue(res.ok)
            self.assertTrue(res.data["changed"])
            self.assertEqual(res.data["old_hash"], "0000000000000000")
            self.assertEqual(res.data["new_hash"], expected_hash)
            self.assertEqual(len(written), 1)

            new_row = written[0][0]
            self.assertEqual(new_row["Source hash"], expected_hash)
            self.assertIn("missing project scope", new_row["Reason"])  # old reason preserved
            self.assertIn("intentionally", new_row["Reason"])  # audit note appended
            self.assertNotEqual(new_row["Last mutation"], "2026-01-01 00:00")

            # nothing else changed
            untouched_fields = ("Status", "Stage", "Source type", "Route variant", "Scopes",
                                "Entries", "Source disposition", "Project", "Person",
                                "Source", "Current source", "Skills", "Snapshot", "Completed")
            for field in untouched_fields:
                self.assertEqual(new_row[field], r[field], field)

    def test_reason_note_is_appended_not_a_bare_overwrite_when_blank(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            content = "<Person1>:\nEdited.\n"
            write_file(root, "00_Inbox/sample-project/r1.txt", content)
            r = row("r1", **{"Source hash": "0000000000000000", "Reason": ""})
            res, written = run_refresh(r, root)
            self.assertTrue(res.ok)
            new_row = written[0][0]
            self.assertTrue(new_row["Reason"].startswith("source hash refreshed"))


class RefreshNoopTests(unittest.TestCase):
    def test_no_write_when_hash_already_matches(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            content = "<Person1>:\nUnchanged content.\n"
            write_file(root, "00_Inbox/sample-project/r1.txt", content)
            current_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
            r = row("r1", **{"Source hash": current_hash})
            res, written = run_refresh(r, root)
            self.assertTrue(res.ok)
            self.assertFalse(res.data["changed"])
            self.assertEqual(res.data["old_hash"], current_hash)
            self.assertEqual(res.data["new_hash"], current_hash)
            self.assertEqual(written, [])  # write_queue never called


class RefreshRefusesWrongStateTests(unittest.TestCase):
    def _assert_refuses(self, **row_overrides):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_file(root, "00_Inbox/sample-project/r1.txt", "placeholder content")
            r = row("r1", **row_overrides)
            with self.assertRaises(SystemExit):
                run_refresh(r, root)

    def test_refuses_processing(self):
        self._assert_refuses(Status="processing", Stage="analysis")

    def test_refuses_blocked(self):
        self._assert_refuses(Status="blocked")

    def test_refuses_finalizing(self):
        self._assert_refuses(Status="finalizing")

    def test_refuses_completed(self):
        self._assert_refuses(Status="completed")

    def test_refuses_failed(self):
        self._assert_refuses(Status="failed")

    def test_refuses_historical(self):
        self._assert_refuses(Status="historical")

    def test_refuses_ignored(self):
        self._assert_refuses(Status="ignored")

    def test_refuses_archived_disposition_even_if_pre_processing(self):
        # Defense in depth: not reachable via the normal workflow (archive-source
        # requires processing/closure), but the guard must hold regardless.
        self._assert_refuses(Status="discovered", **{"Source disposition": "archived"})


class RefreshRefusesNonInboxPathTests(unittest.TestCase):
    def test_refuses_path_outside_00_inbox(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_file(root, "90_Storage/Processed_Sources/r1.txt", "placeholder content")
            r = row("r1", Source="90_Storage/Processed_Sources/r1.txt",
                    **{"Current source": "90_Storage/Processed_Sources/r1.txt"})
            with self.assertRaises(SystemExit):
                run_refresh(r, root)


class RefreshMissingOrUnreadableFileTests(unittest.TestCase):
    def test_missing_file_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)  # nothing written - file genuinely absent
            r = row("r1")
            with self.assertRaises(SystemExit):
                run_refresh(r, root)

    def test_refuses_non_text_extension(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_file(root, "00_Inbox/sample-project/r1.docx", b"not a real docx, just bytes")
            r = row("r1", Source="00_Inbox/sample-project/r1.docx",
                    **{"Current source": "00_Inbox/sample-project/r1.docx"})
            with self.assertRaises(SystemExit):
                run_refresh(r, root)

    def test_refuses_undecodable_utf8_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_file(root, "00_Inbox/sample-project/r1.txt", b"\xff\xfe\x00bad-bytes")
            r = row("r1")
            with self.assertRaises(SystemExit):
                run_refresh(r, root)


class JsonEnvelopeTests(unittest.TestCase):
    def test_json_envelope_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            content = "<Person1>:\nEdited.\n"
            write_file(root, "00_Inbox/sample-project/r1.txt", content)
            r = row("r1", **{"Source hash": "0000000000000000"})
            mock_services = {"drive": MagicMock(), "sheets": MagicMock()}

            def fake_write_queue(services, sheet, rows_arg):
                pass

            with patch("sys.argv", ["qa_manage.py", "refresh-source-hash", "r1", "--json"]), \
                 patch("qa_manage.get_services_cached", return_value=mock_services), \
                 patch("qa_manage.find_queue", return_value={"id": "sheet_id"}), \
                 patch("qa_manage.read_queue", return_value=[r]), \
                 patch("qa_manage.write_queue", side_effect=fake_write_queue), \
                 patch("qa_manage.DATA_ROOT", root):
                buf = io.StringIO()
                with patch("sys.stdout", buf):
                    code = qa_manage.main()

            self.assertEqual(code, 0)
            envelope = json.loads(buf.getvalue())
            self.assertTrue(envelope["ok"])
            self.assertEqual(envelope["command"], "refresh-source-hash")
            self.assertTrue(envelope["data"]["changed"])

    def test_json_envelope_error_for_processing_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_file(root, "00_Inbox/sample-project/r1.txt", "placeholder content")
            r = row("r1", Status="processing", Stage="analysis")
            mock_services = {"drive": MagicMock(), "sheets": MagicMock()}

            with patch("sys.argv", ["qa_manage.py", "refresh-source-hash", "r1", "--json"]), \
                 patch("qa_manage.get_services_cached", return_value=mock_services), \
                 patch("qa_manage.find_queue", return_value={"id": "sheet_id"}), \
                 patch("qa_manage.read_queue", return_value=[r]), \
                 patch("qa_manage.DATA_ROOT", root):
                buf = io.StringIO()
                with patch("sys.stdout", buf):
                    code = qa_manage.main()

            self.assertEqual(code, 1)
            envelope = json.loads(buf.getvalue())
            self.assertFalse(envelope["ok"])
            self.assertEqual(envelope["command"], "refresh-source-hash")
            self.assertEqual(len(envelope["errors"]), 1)


# ---------------------------------------------------------------------------
# detect_source_hash_mismatch (the read-only helper guide/pack reuse)
# ---------------------------------------------------------------------------

class DetectSourceHashMismatchTests(unittest.TestCase):
    def test_returns_none_when_status_not_pre_processing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_file(root, "00_Inbox/sample-project/r1.txt", "content")
            r = row("r1", Status="processing", **{"Source hash": "0000000000000000"})
            with patch("qa_manage.DATA_ROOT", root):
                self.assertIsNone(qa_manage.detect_source_hash_mismatch(r))

    def test_returns_none_when_archived(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_file(root, "00_Inbox/sample-project/r1.txt", "content")
            r = row("r1", **{"Source disposition": "archived", "Source hash": "0000000000000000"})
            with patch("qa_manage.DATA_ROOT", root):
                self.assertIsNone(qa_manage.detect_source_hash_mismatch(r))

    def test_returns_none_when_hash_matches(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            content = "content"
            write_file(root, "00_Inbox/sample-project/r1.txt", content)
            current_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
            r = row("r1", **{"Source hash": current_hash})
            with patch("qa_manage.DATA_ROOT", root):
                self.assertIsNone(qa_manage.detect_source_hash_mismatch(r))

    def test_returns_mismatch_dict_for_pre_processing_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            content = "content"
            write_file(root, "00_Inbox/sample-project/r1.txt", content)
            current_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
            r = row("r1", **{"Source hash": "0000000000000000"})
            with patch("qa_manage.DATA_ROOT", root):
                mismatch = qa_manage.detect_source_hash_mismatch(r)
            self.assertIsNotNone(mismatch)
            self.assertEqual(mismatch["recorded_hash"], "0000000000000000")
            self.assertEqual(mismatch["current_hash"], current_hash)


# ---------------------------------------------------------------------------
# guide / pack integration - recommendation only for a pre-processing mismatch
# ---------------------------------------------------------------------------

GUIDE_GRAPH = {
    "sources": {
        "qa_1to1": {"routes": {"m2": {"skills": ["m2-skill"], "entry": ["m2_doc"]}}},
    },
    "documents": {
        "m2_doc": {"scope": "project", "downstream": []},
    },
}


def guide_row(run_id, **extra) -> dict:
    base = {
        "Run ID": run_id, "Source": f"00_Inbox/sample-project/{run_id}.txt", "Source hash": "aaaaaaaaaaaaaaaa",
        "Current source": f"00_Inbox/sample-project/{run_id}.txt", "Source disposition": "inbox",
        "Source type": "", "Route variant": "",
        "Project": "", "Person": "", "Scopes": "",
        "Status": "discovered", "Stage": "", "Skills": "", "Entries": "",
        "Discovered": "2026-01-01 00:00", "Started": "", "Last mutation": "2026-01-01 00:00",
        "Completed": "", "Snapshot": "", "Reason": "", "Summary": "", "Source text version": "",
    }
    base.update(extra)
    return base


def ready_eval() -> qa_manage.EvaluationResult:
    return qa_manage.EvaluationResult(
        ready_for_completion=True, entry_problems=[], unresolved_edges=[],
        warnings=[], snapshot_sha="deadbeef", snapshot_problem="", invocation_present=True,
    )


class GuideArgs:
    def __init__(self, run_id, json=True, debug=False):
        self.run_id = run_id
        self.json = json
        self.debug = debug


def run_guide(target_row, data_root, other_rows=None, eval_res=None):
    rows = (other_rows or []) + [target_row]
    eval_res = eval_res or ready_eval()

    def fake_load_review_context(services, run_id, rows=None):
        return SimpleNamespace(row=next(r for r in (rows or []) if r["Run ID"] == run_id), all_rows=[])

    mock_services = {"drive": MagicMock(), "sheets": MagicMock()}
    with patch("qa_manage.get_services_cached", return_value=mock_services), \
         patch("qa_manage.find_queue", return_value={"id": "sheet_id"}), \
         patch("qa_manage.read_queue", return_value=rows), \
         patch("qa_manage.load_graph", return_value=GUIDE_GRAPH), \
         patch("qa_manage.load_review_context", side_effect=fake_load_review_context), \
         patch("qa_manage.evaluate_run", return_value=eval_res), \
         patch("qa_manage.DATA_ROOT", data_root):
        res = qa_manage.cmd_guide(GuideArgs(target_row["Run ID"]))
    return res


def run_pack(target_row, data_root, other_rows=None, eval_res=None):
    rows = (other_rows or []) + [target_row]
    eval_res = eval_res or ready_eval()

    def fake_load_review_context(services, run_id, rows=None):
        return SimpleNamespace(row=next(r for r in (rows or []) if r["Run ID"] == run_id), all_rows=[])

    mock_services = {"drive": MagicMock(), "sheets": MagicMock()}
    with patch("qa_manage.get_services_cached", return_value=mock_services), \
         patch("qa_manage.find_queue", return_value={"id": "sheet_id"}), \
         patch("qa_manage.read_queue", return_value=rows), \
         patch("qa_manage.load_graph", return_value=GUIDE_GRAPH), \
         patch("qa_manage.load_review_context", side_effect=fake_load_review_context), \
         patch("qa_manage.evaluate_run", return_value=eval_res), \
         patch("qa_manage.DATA_ROOT", data_root):
        res = qa_manage.cmd_pack(PackArgs(target_row["Run ID"]))
    return res


class PackArgs:
    def __init__(self, run_id, json=True, debug=False, max_preview_chars=None):
        self.run_id = run_id
        self.json = json
        self.debug = debug
        self.max_preview_chars = max_preview_chars


class GuideRecommendationTests(unittest.TestCase):
    def test_recommends_refresh_for_pre_processing_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            content = "<Person1>:\nManually edited content.\n"
            write_file(root, "00_Inbox/sample-project/r1.txt", content)
            r = guide_row("r1", **{"Source hash": "0000000000000000"})
            res = run_guide(r, root)
            self.assertTrue(res.ok)
            self.assertIsNotNone(res.data["source_hash_mismatch"])
            self.assertTrue(any("refresh-source-hash" in c for c in res.data["commands"]))
            self.assertTrue(any("hash" in c.lower() for c in res.data["checklist"]))

    def test_no_recommendation_when_hash_matches(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            content = "unchanged"
            write_file(root, "00_Inbox/sample-project/r1.txt", content)
            current_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
            r = guide_row("r1", **{"Source hash": current_hash})
            res = run_guide(r, root)
            self.assertTrue(res.ok)
            self.assertIsNone(res.data["source_hash_mismatch"])
            self.assertFalse(any("refresh-source-hash" in c for c in res.data["commands"]))

    def test_no_recommendation_for_archived_run_even_if_hash_differs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # archived run's file wouldn't normally still be in 00_Inbox, but
            # the disposition check must short-circuit before any path logic.
            r = guide_row(
                "r1", Status="processing", Stage="closure",
                **{"Source disposition": "archived", "Source hash": "0000000000000000",
                   "Current source": "90_Storage/Processed_Sources/2026/01/r1/r1.txt"},
            )
            res = run_guide(r, root, eval_res=ready_eval())
            self.assertTrue(res.ok)
            self.assertIsNone(res.data["source_hash_mismatch"])
            self.assertFalse(any("refresh-source-hash" in c for c in res.data["commands"]))

    def test_no_recommendation_for_completed_run_even_if_hash_differs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            r = guide_row("r1", Status="completed", **{"Source hash": "0000000000000000"})
            res = run_guide(r, root)
            self.assertTrue(res.ok)
            self.assertIsNone(res.data["source_hash_mismatch"])
            self.assertFalse(any("refresh-source-hash" in c for c in res.data["commands"]))


class PackRecommendationTests(unittest.TestCase):
    def test_recommends_refresh_for_pre_processing_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            content = "<Person1>:\nManually edited content.\n"
            write_file(root, "00_Inbox/sample-project/r1.txt", content)
            r = guide_row("r1", **{"Source hash": "0000000000000000"})
            res = run_pack(r, root)
            self.assertTrue(res.ok)
            self.assertIsNotNone(res.data["source_hash_mismatch"])
            self.assertTrue(any("refresh-source-hash" in c for c in res.data["commands"]))

    def test_no_recommendation_for_completed_run_even_if_hash_differs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            r = guide_row("r1", Status="completed", **{"Source hash": "0000000000000000"})
            res = run_pack(r, root)
            self.assertTrue(res.ok)
            self.assertIsNone(res.data["source_hash_mismatch"])
            self.assertFalse(any("refresh-source-hash" in c for c in res.data["commands"]))


if __name__ == "__main__":
    unittest.main()
