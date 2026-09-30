"""Tests for resolving `.local/` credential paths from any working directory."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import google_api_smoke_test as g


class ResolveLocalPathTests(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        old_cwd = os.getcwd()
        os.chdir(self.td.name)
        self.addCleanup(os.chdir, old_cwd)

    def test_relative_path_missing_from_cwd_anchors_to_repo_root(self):
        path = Path(".local/google/placeholder.json")
        self.assertEqual(g.resolve_local_path(path), g.REPO_ROOT / path)

    def test_relative_path_existing_in_cwd_is_kept(self):
        path = Path("explicit.json")
        path.write_text("{}", encoding="utf-8")
        self.assertEqual(g.resolve_local_path(path), path)

    def test_absolute_path_is_kept(self):
        path = Path(self.td.name) / "absent.json"
        self.assertEqual(g.resolve_local_path(path), path)

    def test_repo_root_holds_the_agents_folder(self):
        self.assertTrue((g.REPO_ROOT / ".agents" / "scripts").is_dir())


if __name__ == "__main__":
    unittest.main()
