import json
import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import search_workspace

def remove_readonly(func, path, _):
    os.chmod(path, stat.S_IWRITE)
    func(path)

class TestSearchWorkspace(unittest.TestCase):
    def setUp(self):
        self.mirror = Path(tempfile.mkdtemp())
        self.script = Path(__file__).resolve().parents[1] / "scripts" / "search_workspace.py"
        self._git("init", "-b", "main")
        self._git("config", "user.name", "Test")
        self._git("config", "user.email", "test@example.com")
        self._git("config", "core.quotePath", "false")

        # Make the temp mirror structurally look like a private mirror to pass assert_private_mirror
        (self.mirror / ".git").mkdir(exist_ok=True)
        (self.mirror / "README.md").write_text("Private mirror")

    def tearDown(self):
        shutil.rmtree(self.mirror, onerror=remove_readonly)

    def _git(self, *args):
        subprocess.run(["git", *args], cwd=self.mirror, check=True, capture_output=True)

    def _write(self, path, content):
        p = self.mirror / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

    def _create_commit(self, msg, files, date=None):
        for path, content in files.items():
            if content is None:
                self._git("rm", "--ignore-unmatch", path)
            else:
                self._write(path, content)
        self._git("add", ".")
        if date:
            import os
            import subprocess
            env = os.environ.copy()
            env["GIT_AUTHOR_DATE"] = date
            env["GIT_COMMITTER_DATE"] = date
            subprocess.run(["git", "commit", "-m", msg], cwd=self.mirror, env=env, check=True)
        else:
            self._git("commit", "-m", msg)

    def run_cli(self, *args, check=True):
        cmd = [sys.executable, str(self.script), *args, "--mirror", str(self.mirror)]
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", cwd=self.mirror)
        if check and res.returncode != 0:
            self.fail(f"CLI failed: {res.stderr}\nStdout: {res.stdout}")
        return res

    def test_current_search_basic(self):
        self._write("10_M1_People_Management/a.md", "M1 file")
        self._git("add", ".")
        self._git("commit", "-m", "A")

        res = self.run_cli("search", "M1 file", "--json")
        data = json.loads(res.stdout)
        self.assertTrue(data["ok"])
        self.assertEqual(data["data"]["result_count"], 1)

    def test_absent_paths_zero_matches(self):
        self._write("10_M1_People_Management/a.md", "M1 file")
        self._git("add", ".")
        self._git("commit", "-m", "A")

        res = self.run_cli("search", "missing", "--path", "10_M1_People_Management/nonexistent.md", "--json", check=False)
        data = json.loads(res.stdout)
        self.assertTrue(data["ok"])
        self.assertEqual(data["data"]["result_count"], 0)

    def test_history_search_basic(self):
        self._write("10_M1_People_Management/a.md", "M1 file")
        self._git("add", ".")
        self._git("commit", "-m", "A")

        res = self.run_cli("history", "M1 file", "--json")
        data = json.loads(res.stdout)
        if not data["ok"] or data["data"]["result_count"] != 1:
            self.fail(f"History search failed: {data}")
        self.assertTrue(data["ok"])
        self.assertEqual(data["data"]["result_count"], 1)
        self.assertEqual(data["data"]["commits"][0]["changes"][0]["change"], "introduced")

    def test_merge_commit_first_parent(self):
        self._write("10_M1_People_Management/a.md", "M1 file")
        self._git("add", ".")
        self._git("commit", "-m", "A")

        self._git("checkout", "-b", "feature")
        self._write("10_M1_People_Management/a.md", "M1 file changed")
        self._git("add", ".")
        self._git("commit", "-m", "B")

        self._git("checkout", "main")
        self._git("merge", "--no-ff", "feature")

        res = self.run_cli("history", "changed", "--json")
        data = json.loads(res.stdout)
        self.assertTrue(data["ok"])
        self.assertEqual(data["data"]["result_count"], 1)
        self.assertEqual(data["data"]["commits"][0]["subject"], "Merge branch 'feature'")

    def test_regex_error(self):
        self._write("10_M1_People_Management/a.md", "M1 file")
        self._git("add", ".")
        self._git("commit", "-m", "A")

        res = self.run_cli("search", "[unclosed", "--regex", "--json", check=False)
        self.assertNotEqual(res.returncode, 0)
        data = json.loads(res.stdout)
        self.assertFalse(data["ok"])
        self.assertTrue(any("unmatched" in err.lower() or "invalid" in err.lower() or "grep failed" in err.lower() for err in data["errors"]))

    def test_path_bounds(self):
        self._write("00_Source_Docs/a.md", "M1 file")
        self._git("add", ".")
        self._git("commit", "-m", "A")

        # 00_Source_Docs is not canonical, so --path fails structurally
        res = self.run_cli("search", "M1 file", "--path", "00_Source_Docs/a.md", "--json", check=False)
        data = json.loads(res.stdout)
        self.assertFalse(data["ok"])
        self.assertTrue(any("outside allowed structural boundaries" in err for err in data["errors"]))

    def test_unicode_filenames(self):
        filename = "10_M1_People_Management/Привет.md"
        self._write(filename, "M1 file")
        self._git("add", ".")
        self._git("commit", "-m", "A")

        res = self.run_cli("search", "M1 file", "--json")
        data = json.loads(res.stdout)
        self.assertEqual(data["data"]["result_count"], 1)
        self.assertEqual(data["data"]["matches"][0]["path"], filename)

    def _valid_manifest_entry(self, run_id):
        return {
            "queue_source_hash": "0123456789abcdef",
            "source_sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            "text_sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            "text_path": "_source_text/blobs/v1/0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef.txt",
            "source_path": "a.txt",
            "extractor_profile": "utf8_text_v1"
        }

    # 1. Direct-root Phase 4 manifest shape
    def test_manifest_shape(self):
        manifest = {
            "run123:v1": self._valid_manifest_entry("run123")
        }
        tp = manifest["run123:v1"]["text_path"]
        self._write("_source_text_manifest.json", json.dumps(manifest))
        self._write(tp, "source data")
        self._git("add", ".")
        self._git("commit", "-m", "A")

        res = self.run_cli("search", "source", "--kind", "source", "--json")
        data = json.loads(res.stdout)
        self.assertTrue(data["ok"])
        self.assertEqual(data["data"]["result_count"], 1)
        runs = data["data"]["matches"][0]["source_runs"]
        self.assertEqual(runs[0]["queue_source_hash"], "0123456789abcdef")
        self.assertEqual(runs[0]["source_sha256"], "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef")
        self.assertEqual(runs[0]["text_sha256"], "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef")

    # 2. Actual queue header capitalization + 4. Queue as warning
    def test_queue_headers_and_warning(self):
        manifest = {
            "run123:v1": self._valid_manifest_entry("run123")
        }
        tp = manifest["run123:v1"]["text_path"]
        queue = {
            "Sheet1": [
                ["Run ID", "Project", "Discovered", "Status"],
                ["run123", "ProjA", "2023-01-01", "Closed"]
            ]
        }
        self._write("_source_text_manifest.json", json.dumps(manifest))
        self._write("_intake_queue.values.json", json.dumps(queue))
        self._write(tp, "source data")
        self._git("add", ".")
        self._git("commit", "-m", "A")

        res = self.run_cli("search", "source", "--kind", "source", "--json")
        data = json.loads(res.stdout)
        self.assertTrue(data["ok"])
        runs = data["data"]["matches"][0]["source_runs"]
        self.assertEqual(runs[0]["project"], "ProjA")
        self.assertEqual(runs[0]["discovered"], "2023-01-01")

        # Test missing queue (warning)
        self._git("rm", "_intake_queue.values.json")
        self._git("commit", "-m", "B")
        res = self.run_cli("search", "source", "--kind", "source", "--json")
        data = json.loads(res.stdout)
        self.assertTrue(data["ok"])
        self.assertEqual(len(data["warnings"]), 1)
        self.assertTrue("Queue error" in data["warnings"][0]["condition"])
        # Runs still returned via manifest
        runs = data["data"]["matches"][0]["source_runs"]
        self.assertEqual(runs[0]["run_id"], "run123")

    # 3. Source/canonical history isolation
    def test_history_isolation(self):
        self._write("10_M1_People_Management/a.md", "shared term")
        self._write("_source_text/blobs/v1/a.txt", "shared term")
        self._git("add", ".")
        self._git("commit", "-m", "A")

        res = self.run_cli("history", "shared", "--kind", "canonical", "--json")
        data = json.loads(res.stdout)
        paths = [ch["path"] for ch in data["data"]["commits"][0]["changes"]]
        self.assertIn("10_M1_People_Management/a.md", paths)
        self.assertNotIn("_source_text/blobs/v1/a.txt", paths)

    # 4. Missing/malformed metadata policies
    def test_metadata_policies(self):
        self._write("10_M1_People_Management/a.md", "content")
        self._git("add", ".")
        self._git("commit", "-m", "A")

        # canonical: no manifest -> no error
        res = self.run_cli("search", "content", "--kind", "canonical", "--json")
        data = json.loads(res.stdout)
        self.assertTrue(data["ok"])

        # source: no manifest -> error
        self._write("_source_text/blobs/v1/a.txt", "content")
        self._git("add", ".")
        self._git("commit", "-m", "B")
        res = self.run_cli("search", "content", "--kind", "source", "--json", check=False)
        data = json.loads(res.stdout)
        self.assertFalse(data["ok"])

        # all: no manifest, but source blobs exist -> error
        res = self.run_cli("search", "content", "--kind", "all", "--json", check=False)
        data = json.loads(res.stdout)
        self.assertFalse(data["ok"])

    # 5. Removal metadata from parent
    def test_removal_metadata(self):
        manifest = {"run123:v1": self._valid_manifest_entry("run123")}
        tp = manifest["run123:v1"]["text_path"]
        self._write("_source_text_manifest.json", json.dumps(manifest))
        self._write(tp, "content")
        self._git("add", ".")
        self._git("commit", "-m", "A")

        self._git("rm", tp)
        self._git("commit", "-m", "B")

        # At B, tp is removed. Metadata must be fetched from parent (A).
        res = self.run_cli("history", "content", "--kind", "source", "--json")
        data = json.loads(res.stdout)
        self.assertTrue(data["ok"])
        self.assertEqual(data["data"]["result_count"], 2) # A (introduced), B (removed)
        change_b = next(ch for c in data["data"]["commits"] for ch in c["changes"] if c["subject"] != "A")
        self.assertEqual(change_b["change"], "removed")
        self.assertEqual(change_b["source_runs"][0]["run_id"], "run123")

    # 6. run-id plus mismatching path
    def test_runid_mismatch_path(self):
        manifest = {"run123:v1": self._valid_manifest_entry("run123")}
        tp = manifest["run123:v1"]["text_path"]
        self._write("_source_text_manifest.json", json.dumps(manifest))
        self._write(tp, "content")
        self._git("add", ".")
        self._git("commit", "-m", "A")

        res = self.run_cli("search", "content", "--run-id", "run123", "--path", "_source_text/blobs/v1/b.txt", "--json", check=False)
        data = json.loads(res.stdout)
        self.assertTrue(data["ok"])
        self.assertEqual(data["data"]["result_count"], 0)

    # 7. Exact-limit truncation
    def test_exact_limit(self):
        # 1. Test 3 matches with limit 2 (should truncate)
        self._write("10_M1_People_Management/a.md", "content\ncontent\ncontent")
        self._git("add", ".")
        self._git("commit", "-m", "A")

        res = self.run_cli("search", "content", "--limit", "2", "--json")
        data = json.loads(res.stdout)
        self.assertTrue(data["ok"])
        self.assertTrue(data["data"]["truncated"])
        self.assertEqual(data["data"]["result_count"], 2)

        # 2. Test 2 matches with limit 2 (should NOT truncate)
        self._write("10_M1_People_Management/b.md", "def\ndef")
        self._git("add", ".")
        self._git("commit", "-m", "B")
        
        res2 = self.run_cli("search", "def", "--limit", "2", "--json")
        data2 = json.loads(res2.stdout)
        self.assertTrue(data2["ok"])
        self.assertFalse(data2["data"]["truncated"])
        self.assertEqual(data2["data"]["result_count"], 2)

    # 8. Deterministic ordering
    def test_deterministic_ordering(self):
        self._write("10_M1_People_Management/b.md", "content\ncontent")
        self._write("10_M1_People_Management/a.md", "content\ncontent")
        self._git("add", ".")
        self._git("commit", "-m", "A")

        res = self.run_cli("search", "content", "--json")
        data = json.loads(res.stdout)
        self.assertTrue(data["ok"])
        paths = [m["path"] for m in data["data"]["matches"]]
        self.assertEqual(paths, ["10_M1_People_Management/a.md", "10_M1_People_Management/a.md", "10_M1_People_Management/b.md", "10_M1_People_Management/b.md"])

    # 9. --json placement and dash-prefixed query
    def test_dash_query(self):
        self._write("10_M1_People_Management/a.md", "-foo is cool")
        self._git("add", ".")
        self._git("commit", "-m", "A")

        # Use python directly to bypass run_cli constructing --mirror at the end
        cmd = [sys.executable, str(self.script), "--json", "search", "-foo", "--mirror", str(self.mirror)]
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", cwd=self.mirror)
        self.assertEqual(res.returncode, 0)
        data = json.loads(res.stdout)
        self.assertTrue(data["ok"])
        self.assertEqual(data["data"]["result_count"], 1)

    # 10. Guard rejection propagates as nonzero JSON error
    def test_guard_rejection(self):
        # Pass a bogus mirror
        cmd = [sys.executable, str(self.script), "search", "content", "--json", "--mirror", str(tempfile.gettempdir())]
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        self.assertNotEqual(res.returncode, 0)
        data = json.loads(res.stdout)
        self.assertFalse(data["ok"])
        self.assertTrue(any("Mirror error" in err for err in data["errors"]))

    # Same-count context changes
    def test_same_count_context_change(self):
        self._write("10_M1_People_Management/a.md", "Hello\nTarget\nGoodbye")
        self._git("add", ".")
        self._git("commit", "-m", "A")

        self._write("10_M1_People_Management/a.md", "Hola\nTarget\nAdios")
        self._git("add", ".")
        self._git("commit", "-m", "B")

        res = self.run_cli("history", "Target", "--json")
        data = json.loads(res.stdout)
        self.assertTrue(data["ok"])
        commits = [c for c in data["data"]["commits"] if c["subject"] != "A"]
        # Should be detected as a change even though the count is 1->1
        self.assertEqual(len(commits), 1)
        self.assertEqual(commits[0]["changes"][0]["change"], "changed")
        self.assertEqual(commits[0]["changes"][0]["matches_before"][0]["context_before"], ["Hello"])
        self.assertEqual(commits[0]["changes"][0]["matches_after"][0]["context_before"], ["Hola"])

    # Directory prefix path matching
    def test_path_prefix(self):
        self._write("10_M1_People_Management/team/a.md", "content")
        self._write("10_M1_People_Management/b.md", "content")
        self._git("add", ".")
        self._git("commit", "-m", "A")

        res = self.run_cli("search", "content", "--path", "10_M1_People_Management/team/", "--json")
        data = json.loads(res.stdout)
        self.assertTrue(data["ok"])
        self.assertEqual(data["data"]["result_count"], 1)
        self.assertEqual(data["data"]["matches"][0]["path"], "10_M1_People_Management/team/a.md")


    def test_multiple_runs_per_blob(self):
        b64 = "b"*64
        manifest = {
            "run1:v1": {
                "source_path": "dummy1.txt",
                "queue_source_hash": "a"*16,
                "source_sha256": "a"*64,
                "text_path": f"_source_text/blobs/v1/{b64}.txt",
                "text_sha256": b64,
                "extractor_profile": "utf8_text_v1"
            },
            "run2:v1": {
                "source_path": "dummy2.txt",
                "queue_source_hash": "c"*16,
                "source_sha256": "c"*64,
                "text_path": f"_source_text/blobs/v1/{b64}.txt",
                "text_sha256": b64,
                "extractor_profile": "utf8_text_v1"
            }
        }

        queue_json = json.dumps({
            "values": [
                ["Snapshot", "Run ID"],
                ["a"*16, "run1"],
                ["c"*16, "run2"]
            ]
        })
        self._create_commit("Init", {
            f"_source_text/blobs/v1/{b64}.txt": "multiple runs content",
            "_source_text_manifest.json": json.dumps(manifest),
            "_intake_queue.values.json": queue_json
        })
        res = self.run_cli("search", "multiple runs", "--kind", "source", "--json")
        out = json.loads(res.stdout)
        self.assertEqual(len(out["data"]["matches"]), 1)
        runs = out["data"]["matches"][0].get("source_runs", [])
        self.assertEqual(len(runs), 2)
        self.assertEqual(runs[0]["run_id"], "run1")
        self.assertEqual(runs[1]["run_id"], "run2")

    def test_malformed_metadata(self):
        # Malformed manifest
        self._create_commit("Malformed", {
            "_source_text/blobs/v1/malformed.txt": "content",
            "_source_text_manifest.json": '{"not": "a valid format"}',
            "_intake_queue.values.json": "[]"
        })
        # For kind=source, this should be a hard error according to policy (or return empty matches + warning depending on strict mode).
        # Actually since strict_manifest=True, it will throw an error at parse time.
        res = subprocess.run([sys.executable, str(self.script), "search", "content", "--kind", "source", "--json", "--mirror", str(self.mirror)], capture_output=True, text=True)
        self.assertNotEqual(res.returncode, 0)

        # Malformed queue
        b64 = "b"*64
        manifest = {
            "run1:v1": {
                "source_path": "dummy1.txt",
                "queue_source_hash": "a"*16,
                "source_sha256": "a"*64,
                "text_path": f"_source_text/blobs/v1/{b64}.txt",
                "text_sha256": b64,
                "extractor_profile": "utf8_text_v1"
            }
        }

        self._create_commit("Malformed", {
            f"_source_text/blobs/v1/{b64}.txt": "content queue",
            "_source_text_manifest.json": json.dumps(manifest),
            "_intake_queue.values.json": '{"not": "a list"}'
        })
        res = self.run_cli("search", "content queue", "--kind", "source", "--json")
        out = json.loads(res.stdout)
        # Queue malformation is a warning
        self.assertTrue(any("Queue error" in w.get("condition", "") for w in out["warnings"]))

    def test_historical_regex_error(self):
        self._create_commit("A", {"10_M1_People_Management/a.md": "content"})
        self._create_commit("B", {"10_M1_People_Management/a.md": "content2"})
        # Unclosed bracket
        res = subprocess.run([sys.executable, str(self.script), "history", "[unclosed", "--regex", "--json", "--mirror", str(self.mirror)], capture_output=True, text=True)
        self.assertNotEqual(res.returncode, 0)
        out = json.loads(res.stdout)
        self.assertTrue(any("unmatched" in err.lower() or "invalid" in err.lower() or "grep failed" in err.lower() for err in out["errors"]))

    def test_date_boundary(self):
        self._create_commit("A", {"10_M1_People_Management/date.md": "content A"}, date="2026-07-19 10:00:00 +0000")
        self._create_commit("B", {"10_M1_People_Management/date.md": "content B"}, date="2026-07-20 12:00:00 +0000")
        self._create_commit("C", {"10_M1_People_Management/date.md": "content C"}, date="2026-07-21 14:00:00 +0000")

        # Test since
        res = self.run_cli("history", "content", "--since", "2026-07-20", "--json")
        out = json.loads(res.stdout)
        self.assertTrue(out["ok"])
        self.assertEqual(out["data"]["result_count"], 2) # Should include B and C

        # Test until
        res = self.run_cli("history", "content", "--until", "2026-07-20", "--json")
        out = json.loads(res.stdout)
        self.assertTrue(out["ok"])
        self.assertEqual(out["data"]["result_count"], 2) # Should include A and B

    def test_history_change_beyond_bound(self):
        # We need a file with 101 matches, and we modify the 101th match
        content1 = "\n".join(f"Match {i}" for i in range(150))
        content2 = content1.replace("Match 149", "Modified 149")
        self._create_commit("A", {"10_M1_People_Management/bound.md": content1})
        self._create_commit("B", {"10_M1_People_Management/bound.md": content2})
        res = self.run_cli("history", "Match", "--limit", "1", "--json")
        out = json.loads(res.stdout)
        self.assertEqual(len(out["data"]["commits"]), 1)
        changes = out["data"]["commits"][0]["changes"]
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0]["change"], "changed")
        self.assertTrue(changes[0]["matches_before_truncated"])
        self.assertTrue(changes[0]["matches_after_truncated"])

if __name__ == "__main__":
    unittest.main()
