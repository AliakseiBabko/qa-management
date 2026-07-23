#!/usr/bin/env python3
"""Unit tests for Google-native source handling (.gdoc/.gsheet), metadata hashing,
fail-closed Drive item resolution, and HTTP rate-limit exponential backoff."""

from __future__ import annotations

import hashlib
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from pipeline_common import execute_with_backoff
from qa_manage import compute_source_file_hash, find_drive_item_by_path


class DummyHttpError(Exception):
    def __init__(self, status: int, headers: dict | None = None):
        self.resp = MagicMock()
        self.resp.status = status
        self.resp.headers = headers or {}


class TestGoogleNativeIntake(unittest.TestCase):
    def test_compute_source_file_hash_regular_file(self):
        tmp_dir = TESTS_DIR / "tmp_test_hash"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        try:
            file_path = tmp_dir / "sample.txt"
            file_path.write_bytes(b"Hello world content")
            expected_hash = hashlib.sha256(b"Hello world content").hexdigest()[:16]
            self.assertEqual(compute_source_file_hash(file_path, "00_Inbox/sample.txt"), expected_hash)
        finally:
            if (tmp_dir / "sample.txt").exists():
                (tmp_dir / "sample.txt").unlink()
            tmp_dir.rmdir()

    def test_compute_source_file_hash_gdoc_drive_metadata(self):
        tmp_file = TESTS_DIR / "doc_test.gdoc"
        tmp_file.write_text("placeholder pointer", encoding="utf-8")
        try:
            # Mock services with drive API returning revision id
            mock_drive = MagicMock()

            def mock_get(fileId, fields):
                mock_req = MagicMock()
                mock_req.execute.return_value = {
                    "id": "drive_file_123",
                    "headRevisionId": "rev_001",
                    "modifiedTime": "2026-07-23T10:00:00Z",
                }
                return mock_req

            mock_drive.files().get.side_effect = mock_get

            # Mock folder resolution
            services = {"drive": mock_drive}
            with unittest.mock.patch("m2_workspace_layout.find_folder_path", return_value={"id": "folder_1"}), \
                 unittest.mock.patch("m2_workspace_layout.list_children", return_value=[{"id": "drive_file_123", "name": "doc_test", "mimeType": "application/vnd.google-apps.document"}]):
                h1 = compute_source_file_hash(tmp_file, "00_Inbox/doc_test.gdoc", services)

            # Change revision ID
            def mock_get_v2(fileId, fields):
                mock_req = MagicMock()
                mock_req.execute.return_value = {
                    "id": "drive_file_123",
                    "headRevisionId": "rev_002",
                    "modifiedTime": "2026-07-23T10:05:00Z",
                }
                return mock_req

            mock_drive.files().get.side_effect = mock_get_v2

            with unittest.mock.patch("m2_workspace_layout.find_folder_path", return_value={"id": "folder_1"}), \
                 unittest.mock.patch("m2_workspace_layout.list_children", return_value=[{"id": "drive_file_123", "name": "doc_test", "mimeType": "application/vnd.google-apps.document"}]):
                h2 = compute_source_file_hash(tmp_file, "00_Inbox/doc_test.gdoc", services)

            # Verify hash changed when metadata revision changed
            self.assertNotEqual(h1, h2)

            # Verify hash is NOT just the filename hash
            filename_only_hash = hashlib.sha256("doc_test.gdoc".encode("utf-8")).hexdigest()[:16]
            self.assertNotEqual(h1, filename_only_hash)
            self.assertNotEqual(h2, filename_only_hash)
        finally:
            if tmp_file.exists():
                tmp_file.unlink()

    def test_find_drive_item_by_path_native_extensionless_and_fail_closed(self):
        mock_drive = MagicMock()

        # Case 1: Native sheet match without .gsheet extension in Drive item name
        children = [
            {"id": "item1", "name": "CBS NFR v0.2", "mimeType": "application/vnd.google-apps.spreadsheet"}
        ]
        with unittest.mock.patch("m2_workspace_layout.find_folder_path", return_value={"id": "p1", "name": "PKF"}), \
             unittest.mock.patch("m2_workspace_layout.list_children", return_value=children):
            found = find_drive_item_by_path(mock_drive, "00_Inbox/PKF/CBS NFR v0.2.gsheet")
            self.assertEqual(found["id"], "item1")

        # Case 2: Non-Google native file extensionless should NOT match
        children_non_native = [
            {"id": "item2", "name": "Report", "mimeType": "text/plain"}
        ]
        with unittest.mock.patch("m2_workspace_layout.find_folder_path", return_value={"id": "p1", "name": "PKF"}), \
             unittest.mock.patch("m2_workspace_layout.list_children", return_value=children_non_native):
            with self.assertRaises(SystemExit):
                find_drive_item_by_path(mock_drive, "00_Inbox/PKF/Report.txt")

        # Case 3: Multiple matching candidates -> fail closed with SystemExit
        children_ambiguous = [
            {"id": "item1", "name": "CBS NFR v0.2", "mimeType": "application/vnd.google-apps.spreadsheet"},
            {"id": "item2", "name": "CBS NFR v0.2.gsheet", "mimeType": "application/vnd.google-apps.spreadsheet"}
        ]
        with unittest.mock.patch("m2_workspace_layout.find_folder_path", return_value={"id": "p1", "name": "PKF"}), \
             unittest.mock.patch("m2_workspace_layout.list_children", return_value=children_ambiguous):
            with self.assertRaises(SystemExit) as cm:
                find_drive_item_by_path(mock_drive, "00_Inbox/PKF/CBS NFR v0.2.gsheet")
            self.assertIn("Multiple Drive items match", str(cm.exception))

    def test_execute_with_backoff_retry_429_500_503(self):
        slept = []

        def mock_sleep(seconds):
            slept.append(seconds)

        req = MagicMock()
        # Fail twice with 429 then succeed
        req.execute.side_effect = [
            DummyHttpError(429, {"retry-after": "2.5"}),
            DummyHttpError(503, {}),
            {"status": "ok", "data": 123}
        ]

        result = execute_with_backoff(req, max_retries=5, initial_backoff=1.0, sleep_fn=mock_sleep)
        self.assertEqual(result, {"status": "ok", "data": 123})
        self.assertEqual(len(slept), 2)
        self.assertEqual(slept[0], 2.5)
        self.assertEqual(slept[1], 2.0)

    def test_execute_with_backoff_exceeds_max_retries(self):
        slept = []

        def mock_sleep(seconds):
            slept.append(seconds)

        req = MagicMock()
        req.execute.side_effect = DummyHttpError(500)

        with self.assertRaises(DummyHttpError):
            execute_with_backoff(req, max_retries=3, initial_backoff=1.0, sleep_fn=mock_sleep)

        self.assertEqual(len(slept), 3)


if __name__ == "__main__":
    unittest.main()
