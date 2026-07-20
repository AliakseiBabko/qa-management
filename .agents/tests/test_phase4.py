import os
import sys
import unittest
import json
import zipfile
import io
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
import hashlib

# Fix paths to allow imports
repo_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(repo_root / ".agents" / "scripts"))

import export_source_text
from export_source_text import ExtractionError, docx_to_text_v1, process_utf8_v1, resolve_first_export, resolve_relocation, verify_manifest_entry, process_row
import qa_manage
import commit_workspace_state
from commit_workspace_state import orchestrate_export

class TestPhase4(unittest.TestCase):

    def test_import_smoke(self):
        import subprocess
        import sys
        import os
        res = subprocess.run([
            sys.executable,
            "-c",
            "import qa_manage, commit_workspace_state, export_source_text"
        ], cwd=".agents/scripts", capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"Import smoke test failed: {res.stderr}")

    def setUp(self):
        self.td = TemporaryDirectory()
        self.root = Path(self.td.name).resolve()
        self.data_root = self.root / "data"
        self.mirror = self.root / "mirror"
        self.data_root.mkdir()
        self.mirror.mkdir()

        # Approved roots
        for r in export_source_text.SOURCE_TEXT_SEARCH_ROOTS:
            (self.data_root / r).mkdir(parents=True, exist_ok=True)

        subprocess.run(["git", "init"], cwd=self.mirror, capture_output=True, check=True)
        (self.mirror / "README.md").write_text("dummy", encoding="utf-8")
        subprocess.run(["git", "config", "user.name", "test"], cwd=self.mirror, check=True)
        subprocess.run(["git", "config", "user.email", "test@test"], cwd=self.mirror, check=True)

    def tearDown(self):
        self.td.cleanup()

    def test_docx_nested_tables(self):
        # Construct a DOCX with a table nested inside a cell
        b = io.BytesIO()
        with zipfile.ZipFile(b, "w") as z:
            z.writestr("[Content_Types].xml", "<Types/>")
            z.writestr("_rels/.rels", "<Relationships/>")
            z.writestr("word/_rels/document.xml.rels", "<Relationships/>")

            # Nested table
            doc_xml = """<?xml version="1.0" encoding="UTF-8"?>
            <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
                <w:body>
                    <w:p><w:r><w:t>Before table</w:t></w:r></w:p>
                    <w:tbl>
                        <w:tr>
                            <w:tc>
                                <w:p><w:r><w:t>Outer cell 1</w:t></w:r></w:p>
                                <w:tbl>
                                    <w:tr>
                                        <w:tc><w:p><w:r><w:t>Inner cell 1</w:t></w:r></w:p></w:tc>
                                        <w:tc><w:p><w:r><w:t>Inner cell 2</w:t></w:r></w:p></w:tc>
                                    </w:tr>
                                </w:tbl>
                            </w:tc>
                        </w:tr>
                    </w:tbl>
                    <w:p><w:r><w:t>After table</w:t></w:r></w:p>
                </w:body>
            </w:document>
            """
            z.writestr("word/document.xml", doc_xml.encode("utf-8"))

        out = docx_to_text_v1(b.getvalue())

        # "Outer cell 1" should appear exactly once.
        self.assertEqual(out.count("Outer cell 1"), 1)
        self.assertEqual(out.count("Inner cell 1"), 1)
        self.assertTrue("Inner cell 1\tInner cell 2" in out)

    def test_cmd_start_v1_assignment(self):
        # Mock queue services for cmd_start
        rows = []
        def fake_write_queue(services, queue_id, updated_rows):
            rows.extend(updated_rows)

        original_write = qa_manage.write_queue
        def fake_find(s): return "q_id"
        def fake_read(s, q): return [test_row]
        def fake_get_services(): return {}
        original_find = qa_manage.find_queue
        original_read = qa_manage.read_queue
        original_get_services = qa_manage.get_services_cached
        qa_manage.find_queue = fake_find
        qa_manage.read_queue = fake_read
        qa_manage.get_services_cached = fake_get_services
        qa_manage.write_queue = fake_write_queue
        try:
            # Create a raw_transcript row in scan state
            test_row = {
                "Run ID": "test-run-123",
                "Status": "discovered",
                "Source type": "raw_transcript",
                "Stage": "",
                "Source": "02_Transcripts_Inbox/test.txt",
                "Source text version": ""
            }
            # Start it as qa_1to1
            class DummyArgs:
                source_type="qa_1to1"
                variant="m1"
                scope=[]
                project=""
                person=""
                run_id="test-run-123"
            qa_manage.cmd_start(DummyArgs())

            # The mutated row should be written to the queue with Source text version = 1
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["Status"], "needs_scope")
            self.assertEqual(rows[0]["Source type"], "qa_1to1")
            self.assertEqual(str(rows[0]["Source text version"]).strip(), "1")
        finally:
            qa_manage.write_queue = original_write
            qa_manage.find_queue = original_find
            qa_manage.read_queue = original_read
            qa_manage.get_services_cached = original_get_services

    def test_end_to_end_workspace_export(self):
        # We need to simulate orchestrate_export over fake Drive and valid queue rows
        test_txt = b"Hello from fake drive"
        test_hash = hashlib.sha256(test_txt).hexdigest()

        inbox = self.data_root / "02_Transcripts_Inbox"
        src_path = inbox / "test.txt"
        src_path.write_bytes(test_txt)

        rows = [{
            "Run ID": "test-run-001",
            "Status": "needs_scope",
            "Source type": "qa_1to1",
            "Source": "02_Transcripts_Inbox/test.txt",
            "Source hash": test_hash[:16],
            "Source text version": "1"
        }]

        def fake_walk(services, folder_id, out_dir, rel, manifest, written, errors, warnings):
            written.append("dummy.txt")
            (out_dir / "dummy.txt").write_text("hello", encoding="utf-8")

        def fake_find(services): return "q_id"
        def fake_read(services, q): return rows

        written, manifest, removed, warnings, errors = orchestrate_export(
            None, self.mirror, self.data_root, fake_walk, export_source_text.export, fake_find, fake_read
        )

        self.assertEqual(len(errors), 0)
        self.assertTrue(any("test-run-001:v1" in w for w in written) or (self.mirror / "_source_text_manifest.json").exists())

        manifest_data = json.loads((self.mirror / "_source_text_manifest.json").read_text(encoding="utf-8"))
        self.assertIn("test-run-001:v1", manifest_data)

    def test_snapshot_verification_and_evaluate_run(self):
        # Setup git mirror
        test_txt = b"Commit me\n"
        test_hash = hashlib.sha256(test_txt).hexdigest()
        src_path = self.data_root / "02_Transcripts_Inbox" / "test2.txt"
        src_path.parent.mkdir(parents=True, exist_ok=True)
        src_path.write_bytes(test_txt)

        row = {
            "Run ID": "run-snap",
            "Status": "completed",
            "Source type": "qa_1to1",
            "Source": "02_Transcripts_Inbox/test2.txt",
            "Source hash": test_hash[:16],
            "Source text version": "1"
        }

        # Export
        protected, errs, warns = export_source_text.export([row], self.data_root, self.mirror)
        self.assertEqual(len(errs), 0)

        subprocess.run(["git", "add", "-A"], cwd=self.mirror, check=True)
        subprocess.run(["git", "commit", "-m", "Snapshot"], cwd=self.mirror, check=True)
        sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.mirror, capture_output=True, text=True, check=True).stdout.strip()

        # Check snapshot
        orig_mirror = qa_manage.MIRROR
        orig_data = qa_manage.DATA_ROOT
        qa_manage.MIRROR = self.mirror
        qa_manage.DATA_ROOT = self.data_root
        try:
            row["Snapshot"] = sha
            errs = qa_manage.check_source_text_snapshot(sha, row)
            self.assertEqual(len(errs), 0)

            class DummyCtx:
                def __init__(self, r):
                    self.row = r
                    self.log = []
                    self.graph = {}
                    self.inv_rows = [["header"], ["run:run-snap"]]
            
            # Test evaluate_run using it implicitly
            res = qa_manage.evaluate_run(DummyCtx(row))
            self.assertEqual(res.snapshot_problem, "")

            # Delete the blob from tree
            blob_p = self.mirror / [p for p in protected if "blobs" in p][0]
            blob_p.unlink()
            subprocess.run(["git", "add", "-A"], cwd=self.mirror, check=True)
            subprocess.run(["git", "commit", "-m", "Delete"], cwd=self.mirror, check=True)
            deleted_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.mirror, capture_output=True, text=True, check=True).stdout.strip()

            row["Snapshot"] = deleted_sha
            errs = qa_manage.check_source_text_snapshot(deleted_sha, row)
            self.assertGreater(len(errs), 0)
            self.assertTrue(any("Missing or unreadable blob" in e for e in errs))
            
            res2 = qa_manage.evaluate_run(DummyCtx(row))
            self.assertNotEqual(res2.snapshot_problem, "")
            self.assertTrue("Missing or unreadable blob" in res2.snapshot_problem)

        finally:
            qa_manage.MIRROR = orig_mirror
            qa_manage.DATA_ROOT = orig_data

    def test_relocation(self):
        b = b"Relocation text"
        h = hashlib.sha256(b).hexdigest()

        src = self.data_root / "02_Transcripts_Inbox" / "orig.txt"
        src.write_bytes(b)

        # First export
        actual_path, sha256, raw = resolve_first_export(self.data_root, "02_Transcripts_Inbox/orig.txt", h[:16])
        self.assertEqual(actual_path.name, "orig.txt")
        self.assertEqual(sha256, h)

        # Relocate (rename + move)
        src.unlink()
        dest = self.data_root / "03_Transcripts_Processed" / "renamed.txt"
        dest.write_bytes(b)

        # Relocation search
        actual_path2, sha256_2, raw2 = resolve_relocation(self.data_root, h)
        self.assertEqual(actual_path2.name, "renamed.txt")
        self.assertEqual(sha256_2, h)

    def test_ambiguous_hash(self):
        b1 = b"Same prefix 1"
        b2 = b"Same prefix 2"
        # We will mock the hash function in resolve_first_export to simulate collision
        orig_hash = export_source_text.get_full_sha256

        def fake_hash(b):
            # return fake hash that shares prefix
            if b == b1: return "1234567890abcdef" + "1"*48
            if b == b2: return "1234567890abcdef" + "2"*48
            return orig_hash(b)

        export_source_text.get_full_sha256 = fake_hash
        try:
            p1 = self.data_root / "02_Transcripts_Inbox" / "f1.txt"
            p1.write_bytes(b1)
            p2 = self.data_root / "02_Transcripts_Inbox" / "f2.txt"
            p2.write_bytes(b2)

            with self.assertRaises(ExtractionError) as cm:
                resolve_first_export(self.data_root, "02_Transcripts_Inbox/nonexistent.txt", "1234567890abcdef")
            self.assertIn("Ambiguous hash prefix", str(cm.exception))
        finally:
            export_source_text.get_full_sha256 = orig_hash

    def test_pruning_orchestration(self):
        # Provide a malformed manifest initially
        manifest_path = self.mirror / "_source_text_manifest.json"
        manifest_path.write_text('{"bad_key": {}}', encoding="utf-8")

        row = {
            "Run ID": "run-prune",
            "Status": "needs_scope",
            "Source type": "qa_1to1",
            "Source": "02_Transcripts_Inbox/dummy.txt",
            "Source hash": "0000000000000000",
            "Source text version": "1"
        }

        protected, errs, warns = export_source_text.export([row], self.data_root, self.mirror)
        self.assertGreater(len(errs), 0)
        self.assertTrue(any("Manifest read error" in e for e in errs))

        # Assert manifest wasn't overwritten
        self.assertEqual(manifest_path.read_text(encoding="utf-8"), '{"bad_key": {}}')

    def test_json_parsing(self):
        # Run export_source_text as subprocess with bad args
        res = subprocess.run(
            [sys.executable, str(repo_root / ".agents" / "scripts" / "export_source_text.py"), "audit", "--bad", "--json"],
            capture_output=True, text=True
        )
        self.assertEqual(res.returncode, 1)
        data = json.loads(res.stdout)
        self.assertIn("schema_version", data)
        self.assertEqual(data["ok"], False)
        self.assertGreater(len(data["errors"]), 0)
        self.assertTrue(any("unrecognized arguments" in str(e) for e in data["errors"]))

        # Test help
        res_help = subprocess.run(
            [sys.executable, str(repo_root / ".agents" / "scripts" / "export_source_text.py"), "--help", "--json"],
            capture_output=True, text=True
        )
        self.assertEqual(res_help.returncode, 0)
        data_help = json.loads(res_help.stdout)
        self.assertEqual(data_help["command"], "help")
        self.assertEqual(data_help["ok"], True)

    def test_mirror_security(self):
        from mirror_common import assert_private_mirror

        with TemporaryDirectory() as td2:
            base = Path(td2)
            droot = base / "drive"
            mroot = base / "mirror"

            droot.mkdir()
            mroot.mkdir()

            # Base valid
            assert_private_mirror(mroot, droot, init_allowed=True)

            # Mirror inside Drive
            m_in_d = droot / "mirror"
            with self.assertRaises(SystemExit):
                assert_private_mirror(m_in_d, droot, init_allowed=True)

            # Mirror as ancestor of Drive
            with self.assertRaises(SystemExit):
                assert_private_mirror(base, droot, init_allowed=True)

            # Windows symlink test: symlink escape
            # If we can create symlinks (admin or developer mode enabled)
            import tempfile
            try:
                os.symlink(droot, base / "sym_drive")
                sym_drive = base / "sym_drive"
                # If sym_drive/mirror is used, resolve() would show it inside droot
                with self.assertRaises(SystemExit):
                    assert_private_mirror(sym_drive / "mirror", droot, init_allowed=True)
            except OSError:
                pass # Can't test symlinks without privileges

if __name__ == "__main__":
    unittest.main()
