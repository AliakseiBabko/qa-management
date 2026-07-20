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
search_workspace.assert_private_mirror = lambda m, d, init_allowed=False: None

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

    def tearDown(self):
        shutil.rmtree(self.mirror, onerror=remove_readonly)

    def _git(self, *args):
        subprocess.run(["git", *args], cwd=self.mirror, check=True, capture_output=True)

    def _write(self, path, content):
        p = self.mirror / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        
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

    def test_read_only_proof(self):
        self._write("10_M1_People_Management/a.md", "M1 file")
        self._git("add", ".")
        self._git("commit", "-m", "A")
        
        cmd = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.mirror, capture_output=True, text=True)
        head_before = cmd.stdout.strip()
        cmd = subprocess.run(["git", "status", "--porcelain"], cwd=self.mirror, capture_output=True, text=True)
        status_before = cmd.stdout
        
        self.run_cli("search", "M1 file")
        self.run_cli("history", "M1 file")
        
        cmd = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.mirror, capture_output=True, text=True)
        head_after = cmd.stdout.strip()
        cmd = subprocess.run(["git", "status", "--porcelain"], cwd=self.mirror, capture_output=True, text=True)
        status_after = cmd.stdout
        
        self.assertEqual(head_before, head_after, "HEAD changed")
        self.assertEqual(status_before, status_after, "Status changed")
        
    def test_regex_error(self):
        self._write("10_M1_People_Management/a.md", "M1 file")
        self._git("add", ".")
        self._git("commit", "-m", "A")
        
        res = self.run_cli("search", "[unclosed", "--regex", "--json", check=False)
        self.assertNotEqual(res.returncode, 0)
        
    def test_path_bounds(self):
        self._write("00_Source_Docs/a.md", "M1 file")
        self._git("add", ".")
        self._git("commit", "-m", "A")
        
        res = self.run_cli("search", "M1 file", "--json")
        data = json.loads(res.stdout)
        self.assertEqual(data["data"]["result_count"], 0) # 00_Source_Docs is not canonical by default
        
    def test_unicode_filenames(self):
        filename = "10_M1_People_Management/файл.md"
        self._write(filename, "M1 file")
        self._git("add", ".")
        self._git("commit", "-m", "A")
        
        res = self.run_cli("search", "M1 file", "--json")
        data = json.loads(res.stdout)
        self.assertEqual(data["data"]["result_count"], 1)
        self.assertEqual(data["data"]["matches"][0]["path"], filename)

if __name__ == "__main__":
    unittest.main()
