"""Tests for the commit-candidate sensitive-data guard.

Every test builds a throwaway git repository in a temporary directory and
injects a synthetic watch string. Nothing here touches Drive, needs
credentials, or contains a real name - the watch list is a parameter of
`scan()` precisely so it can be exercised without a live registry.

The synthetic token below is deliberately meaningless. It must never be
replaced with a real or realistic organization/person name.

Run:  python -m unittest discover -s .agents/tests
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import check_sensitive_data as guard

# Synthetic only. Not a real name, not derived from one.
TOKEN = "Zzyzx Quorbling"
OTHER_TOKEN = "Blorptastic Widgetry"
WATCH = {TOKEN}


class RepoTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = Path(self._tmp.name).resolve()
        self.git("init", "-q")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "user.name", "Test")
        self.git("config", "commit.gpgsign", "false")

    def git(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-C", str(self.repo), *args],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )

    def write(self, rel: str, text: str) -> Path:
        p = self.repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return p

    def commit_all(self, message: str = "seed") -> None:
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)

    def paths(self, findings) -> list[str]:
        return [f.path for f in findings]


class DetectionTests(RepoTestCase):
    def test_sensitive_text_in_clean_tracked_file_is_caught(self) -> None:
        """The original defect: committed content was never re-examined."""
        self.write(".agents/skills/demo.md", f"context {TOKEN} here\n")
        self.commit_all()
        findings = guard.scan(self.repo, WATCH)
        self.assertEqual([".agents/skills/demo.md"], self.paths(findings))
        self.assertEqual(1, findings[0].line_no)
        self.assertEqual({guard.INDEX, guard.WORKTREE}, findings[0].sources)

    def test_file_outside_dot_agents_is_caught(self) -> None:
        self.write("docs/notes.md", f"line one\nline two {TOKEN}\n")
        self.commit_all()
        findings = guard.scan(self.repo, WATCH)
        self.assertEqual(["docs/notes.md"], self.paths(findings))
        self.assertEqual(2, findings[0].line_no)

    def test_staged_sensitive_with_clean_worktree_is_caught(self) -> None:
        """Index/worktree divergence: staged, then removed before scanning."""
        self.write("notes.md", "clean\n")
        self.commit_all()
        self.write("notes.md", f"{TOKEN}\n")
        self.git("add", "notes.md")
        self.write("notes.md", "clean again\n")  # unstaged removal
        findings = guard.scan(self.repo, WATCH)
        self.assertEqual(["notes.md"], self.paths(findings))
        self.assertEqual({guard.INDEX}, findings[0].sources)

    def test_unstaged_worktree_edit_is_caught(self) -> None:
        self.write("notes.md", "clean\n")
        self.commit_all()
        self.write("notes.md", f"{TOKEN}\n")  # never staged
        findings = guard.scan(self.repo, WATCH)
        self.assertEqual({guard.WORKTREE}, findings[0].sources)

    def test_untracked_nonignored_file_is_caught(self) -> None:
        self.write("seed.md", "seed\n")
        self.commit_all()
        self.write("scratch.md", f"{TOKEN}\n")
        findings = guard.scan(self.repo, WATCH)
        self.assertEqual(["scratch.md"], self.paths(findings))
        self.assertEqual({guard.UNTRACKED}, findings[0].sources)

    def test_clean_tree_passes(self) -> None:
        self.write(".agents/ok.md", "nothing to see\n")
        self.write("README.md", "also fine\n")
        self.commit_all()
        self.assertEqual([], guard.scan(self.repo, WATCH))

    def test_multiple_distinct_matches_share_one_finding_per_line(self) -> None:
        self.write("notes.md", f"{TOKEN} and {OTHER_TOKEN}\n")
        self.commit_all()
        findings = guard.scan(self.repo, {TOKEN, OTHER_TOKEN})
        self.assertEqual(1, len(findings), "two matches on one line are one finding")
        self.assertNotIn(TOKEN, findings[0].render())


class ExclusionTests(RepoTestCase):
    def test_gitignored_content_is_ignored(self) -> None:
        self.write(".gitignore", ".local/\ntmp/\n")
        self.write(".local/google/token.json", f'{{"note": "{TOKEN}"}}\n')
        self.write("tmp/scratch.txt", f"{TOKEN}\n")
        self.commit_all()
        self.assertEqual([], guard.scan(self.repo, WATCH))

    def test_deleted_file_is_ignored(self) -> None:
        self.write("gone.md", f"{TOKEN}\n")
        self.commit_all()
        self.git("rm", "-q", "gone.md")  # staged deletion
        self.assertEqual([], guard.scan(self.repo, WATCH))

    def test_unstaged_deletion_still_reports_staged_content(self) -> None:
        """The commit candidate still contains it, so it must be reported."""
        self.write("gone.md", f"{TOKEN}\n")
        self.commit_all()
        (self.repo / "gone.md").unlink()  # deleted on disk, still in index
        findings = guard.scan(self.repo, WATCH)
        self.assertEqual({guard.INDEX}, findings[0].sources)

    def test_binary_file_is_skipped(self) -> None:
        (self.repo / "blob.bin").write_bytes(
            TOKEN.encode("utf-8") + b"\x00\x01\x02\xff"
        )
        self.commit_all()
        self.assertEqual([], guard.scan(self.repo, WATCH))

    def test_git_directory_is_never_scanned(self) -> None:
        self.write("seed.md", "seed\n")
        self.commit_all()
        (self.repo / ".git" / "description").write_text(TOKEN, encoding="utf-8")
        self.assertEqual([], guard.scan(self.repo, WATCH))
        self.assertFalse(
            any(f.path.startswith(".git/") for f in guard.scan(self.repo, WATCH))
        )


class PathScanningTests(RepoTestCase):
    def test_sensitive_filename_is_detected(self) -> None:
        self.write(f"docs/{TOKEN} notes.md", "clean contents\n")
        self.commit_all()
        path_findings = guard.scan_paths(self.repo, WATCH)
        self.assertEqual(1, len(path_findings))
        self.assertEqual({guard.INDEX, guard.WORKTREE}, path_findings[0].sources)
        self.assertEqual([], guard.scan(self.repo, WATCH), "contents are clean")

    def test_sensitive_directory_component_is_detected(self) -> None:
        self.write(f"{TOKEN}/inner.md", "clean\n")
        self.commit_all()
        self.assertEqual(1, len(guard.scan_paths(self.repo, WATCH)))

    def test_untracked_sensitive_filename_is_detected(self) -> None:
        self.write("seed.md", "seed\n")
        self.commit_all()
        self.write(f"{TOKEN}.md", "clean\n")
        path_findings = guard.scan_paths(self.repo, WATCH)
        self.assertEqual({guard.UNTRACKED}, path_findings[0].sources)

    def test_path_finding_render_never_contains_the_path(self) -> None:
        self.write(f"docs/{TOKEN} notes.md", "clean\n")
        self.commit_all()
        rendered = "\n".join(f.render() for f in guard.scan_paths(self.repo, WATCH))
        self.assertIn("sensitive path detected", rendered)
        self.assertIn("#1", rendered)
        self.assertIn(guard.INDEX, rendered)
        self.assertNotIn(TOKEN, rendered)
        self.assertNotIn("notes.md", rendered)
        for word in TOKEN.split():
            self.assertNotIn(word, rendered)

    def test_sensitive_path_and_contents_leak_nothing(self) -> None:
        """A sensitive filename must not leak via its own content findings."""
        import io, contextlib
        self.write(f"docs/{TOKEN} notes.md", f"body mentions {TOKEN} too\n")
        self.commit_all()
        buf = io.StringIO()
        with mock.patch.object(guard, "load_watch_strings", return_value=WATCH), \
             mock.patch.object(guard, "ensure_utf8_stdout", lambda: None), \
             mock.patch("pipeline_common.get_services", return_value={}), \
             contextlib.redirect_stdout(buf):
            code = guard.main(["--repo", str(self.repo)])
        out = buf.getvalue()

        self.assertEqual(1, code)
        self.assertIn("sensitive path detected #1", out)
        self.assertIn("path withheld", out)
        self.assertIn("line 1", out)

        self.assertNotIn(TOKEN, out)
        self.assertNotIn("notes.md", out)
        self.assertNotIn("docs/", out)
        for word in TOKEN.split():
            self.assertNotIn(word, out)

    def test_coordinate_withholds_path_of_sensitive_named_file(self) -> None:
        self.write(f"{TOKEN}.md", f"{TOKEN}\n")
        self.commit_all()
        findings = guard.scan(self.repo, WATCH)
        path_findings = guard.scan_paths(self.repo, WATCH)
        guard.coordinate(findings, path_findings)
        rendered = "\n".join(f.render() for f in findings)
        self.assertNotIn(TOKEN, rendered)
        self.assertIn("path withheld", rendered)
        self.assertIsNotNone(findings[0].path_ordinal)

    def test_clean_named_file_still_renders_its_path(self) -> None:
        self.write("ordinary.md", f"{TOKEN}\n")
        self.commit_all()
        findings = guard.scan(self.repo, WATCH)
        guard.coordinate(findings, guard.scan_paths(self.repo, WATCH))
        self.assertIn("ordinary.md", findings[0].render())
        self.assertIsNone(findings[0].path_ordinal)

    def test_clean_paths_produce_no_path_findings(self) -> None:
        self.write("docs/ordinary.md", "clean\n")
        self.commit_all()
        self.assertEqual([], guard.scan_paths(self.repo, WATCH))


class SymlinkTests(RepoTestCase):
    def _symlink(self, link: Path, target: Path) -> None:
        try:
            link.symlink_to(target)
        except (OSError, NotImplementedError) as exc:  # Windows without privilege
            self.skipTest(f"cannot create symlinks here: {exc}")

    def test_untracked_symlink_to_outside_file_is_not_followed(self) -> None:
        outside = Path(self._tmp.name).parent / f"outside-{id(self)}.txt"
        outside.write_text(f"{TOKEN}\n", encoding="utf-8")
        self.addCleanup(lambda: outside.unlink(missing_ok=True))
        self.write("seed.md", "seed\n")
        self.commit_all()
        self._symlink(self.repo / "link.txt", outside)
        self.assertEqual([], guard.scan(self.repo, WATCH))

    def test_symlink_inside_repo_is_not_double_read(self) -> None:
        self.write("real.md", "clean\n")
        self.commit_all()
        self._symlink(self.repo / "alias.md", self.repo / "real.md")
        self.assertEqual([], guard.scan(self.repo, WATCH))

    def test_staged_symlink_blob_is_scanned_as_text_not_dereferenced(self) -> None:
        outside = Path(self._tmp.name).parent / f"{TOKEN}-target-{id(self)}.txt"
        outside.write_text("secret contents\n", encoding="utf-8")
        self.addCleanup(lambda: outside.unlink(missing_ok=True))
        self._symlink(self.repo / "link.txt", outside)
        self.commit_all()
        findings = guard.scan(self.repo, WATCH)
        # The blob holds the link target path, which carries the token.
        self.assertEqual([guard.INDEX], list(findings[0].sources) if findings else [])
        self.assertEqual("link.txt", findings[0].path)


class LinkGuardUnitTests(RepoTestCase):
    """Privilege-free coverage of the link guard itself.

    The real-symlink tests above skip on Windows without Developer Mode, so
    the decision function is also exercised directly - otherwise the rule
    that keeps the scanner inside the repository would be untested on the
    platform this repo is developed on.
    """

    def test_symlink_is_rejected(self) -> None:
        target = self.write("real.md", "clean\n")
        with mock.patch.object(Path, "is_symlink", return_value=True):
            self.assertFalse(guard._is_safe_regular_file(self.repo, target))

    def test_junction_is_rejected(self) -> None:
        target = self.write("real.md", "clean\n")
        if not hasattr(Path, "is_junction"):
            self.skipTest("Path.is_junction unavailable")
        with mock.patch.object(Path, "is_junction", return_value=True):
            self.assertFalse(guard._is_safe_regular_file(self.repo, target))

    def test_target_resolving_outside_repo_is_rejected(self) -> None:
        outside = Path(self._tmp.name).parent / f"outside-{id(self)}.txt"
        outside.write_text("clean\n", encoding="utf-8")
        self.addCleanup(lambda: outside.unlink(missing_ok=True))
        inside = self.repo / "alias.md"
        real_resolve = Path.resolve

        def fake_resolve(self, *a, **kw):  # only the link target escapes
            return outside if self == inside else real_resolve(self, *a, **kw)

        with mock.patch.object(Path, "resolve", fake_resolve):
            self.assertFalse(guard._is_safe_regular_file(self.repo, inside))

    def test_ordinary_file_inside_repo_is_accepted(self) -> None:
        target = self.write("real.md", "clean\n")
        self.assertTrue(guard._is_safe_regular_file(self.repo, target))

    def test_directory_is_not_read_as_a_file(self) -> None:
        (self.repo / "subdir").mkdir()
        self.assertFalse(guard._is_safe_regular_file(self.repo, self.repo / "subdir"))

    @unittest.skipUnless(sys.platform == "win32", "junctions are Windows-only")
    def test_real_junction_out_of_repo_is_not_followed(self) -> None:
        """Unprivileged on Windows, so this exercises a genuine escape."""
        outside_dir = Path(self._tmp.name).parent / f"outdir-{id(self)}"
        outside_dir.mkdir()
        (outside_dir / "leak.txt").write_text(f"{TOKEN}\n", encoding="utf-8")
        self.addCleanup(lambda: __import__("shutil").rmtree(outside_dir, ignore_errors=True))
        self.write("seed.md", "seed\n")
        self.commit_all()
        made = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(self.repo / "linked"), str(outside_dir)],
            capture_output=True,
        )
        if made.returncode != 0:
            self.skipTest("could not create a junction here")
        self.assertEqual([], guard.scan(self.repo, WATCH))


class FailClosedTests(RepoTestCase):
    def test_invalid_repo_path_fails(self) -> None:
        with self.assertRaises(guard.ScanError):
            guard.require_git_repo(self.repo / "does-not-exist")

    def test_non_git_directory_fails(self) -> None:
        with tempfile.TemporaryDirectory() as plain:
            with self.assertRaises(guard.ScanError):
                guard.require_git_repo(Path(plain))

    def test_failed_git_enumeration_fails_closed(self) -> None:
        self.write("notes.md", f"{TOKEN}\n")
        self.commit_all()
        broken = subprocess.CompletedProcess(args=[], returncode=128, stdout=b"", stderr=b"fatal: boom")
        with mock.patch.object(guard.subprocess, "run", return_value=broken):
            with self.assertRaises(guard.ScanError):
                guard.scan(self.repo, WATCH)

    def test_git_missing_from_path_fails_closed(self) -> None:
        with mock.patch.object(guard.subprocess, "run", side_effect=OSError("no git")):
            with self.assertRaises(guard.ScanError):
                guard.scan(self.repo, WATCH)

    def test_truncated_cat_file_output_fails_closed(self) -> None:
        self.write("a.md", "clean\n")
        self.write("b.md", "clean\n")
        self.commit_all()
        real = guard.subprocess.run

        def fake(argv, **kwargs):
            if "cat-file" in argv:
                return subprocess.CompletedProcess(args=argv, returncode=0, stdout=b"", stderr=b"")
            return real(argv, **kwargs)

        with mock.patch.object(guard.subprocess, "run", side_effect=fake):
            with self.assertRaises(guard.ScanError):
                guard.scan(self.repo, WATCH)

    def test_short_object_body_fails_closed(self) -> None:
        self.write("a.md", "some content here\n")
        self.commit_all()
        real = guard.subprocess.run

        def fake(argv, **kwargs):
            if "cat-file" in argv:
                # Header promises more bytes than the body carries.
                return subprocess.CompletedProcess(
                    args=argv, returncode=0, stdout=b"deadbeef blob 999\nshort\n", stderr=b""
                )
            return real(argv, **kwargs)

        with mock.patch.object(guard.subprocess, "run", side_effect=fake):
            with self.assertRaises(guard.ScanError):
                guard.scan(self.repo, WATCH)

    def _fake_batch(self, stdout: bytes):
        real = guard.subprocess.run

        def fake(argv, **kwargs):
            if "cat-file" in argv:
                return subprocess.CompletedProcess(args=argv, returncode=0,
                                                   stdout=stdout, stderr=b"")
            return real(argv, **kwargs)
        return fake

    def test_missing_body_separator_newline_fails_closed(self) -> None:
        self.write("a.md", "abc\n")
        self.commit_all()
        # Body of the declared length, then no separator newline at all.
        stream = b"deadbeef blob 4\nabc\n"[:-1] + b"X"
        with mock.patch.object(guard.subprocess, "run", side_effect=self._fake_batch(stream)):
            with self.assertRaises(guard.ScanError) as raised:
                guard.scan(self.repo, WATCH)
        self.assertIn("separator", str(raised.exception))

    def test_unexpected_trailing_output_fails_closed(self) -> None:
        self.write("a.md", "abc\n")
        self.commit_all()
        stream = b"deadbeef blob 4\nabc\n\nleftover garbage\n"
        with mock.patch.object(guard.subprocess, "run", side_effect=self._fake_batch(stream)):
            with self.assertRaises(guard.ScanError) as raised:
                guard.scan(self.repo, WATCH)
        self.assertIn("trailing", str(raised.exception))

    def test_unreadable_enumerated_file_fails_closed_without_path(self) -> None:
        secret_name = f"{TOKEN}.md"
        self.write(secret_name, "clean\n")
        self.commit_all()
        real_read = Path.read_bytes

        def fake_read(self, *a, **kw):
            if self.name == secret_name:
                raise PermissionError("denied")
            return real_read(self, *a, **kw)

        with mock.patch.object(Path, "read_bytes", fake_read):
            with self.assertRaises(guard.ScanError) as raised:
                guard.scan(self.repo, WATCH)
        message = str(raised.exception)
        self.assertIn("path withheld", message)
        self.assertIn("PermissionError", message)
        self.assertNotIn(TOKEN, message)
        for word in TOKEN.split():
            self.assertNotIn(word, message)

    def test_unstaged_deletion_is_not_an_unreadable_file_error(self) -> None:
        """Deleted on disk is a skip, not a read failure - index still covers it."""
        self.write("gone.md", f"{TOKEN}\n")
        self.commit_all()
        (self.repo / "gone.md").unlink()
        findings = guard.scan(self.repo, WATCH)  # must not raise
        self.assertEqual({guard.INDEX}, findings[0].sources)

    def test_missing_object_line_fails_closed(self) -> None:
        self.write("a.md", "clean\n")
        self.commit_all()
        real = guard.subprocess.run

        def fake(argv, **kwargs):
            if "cat-file" in argv:
                return subprocess.CompletedProcess(
                    args=argv, returncode=0, stdout=b"deadbeef missing\n", stderr=b""
                )
            return real(argv, **kwargs)

        with mock.patch.object(guard.subprocess, "run", side_effect=fake):
            with self.assertRaises(guard.ScanError):
                guard.scan(self.repo, WATCH)

    def test_main_returns_two_on_scan_error(self) -> None:
        import io, contextlib
        buf = io.StringIO()
        with mock.patch.object(guard, "load_watch_strings", return_value=WATCH), \
             mock.patch.object(guard, "ensure_utf8_stdout", lambda: None), \
             mock.patch("pipeline_common.get_services", return_value={}), \
             mock.patch.object(guard, "require_git_repo",
                               side_effect=guard.ScanError("boom")), \
             contextlib.redirect_stdout(buf):
            code = guard.main(["--repo", str(self.repo)])
        self.assertEqual(2, code)
        self.assertIn("incomplete scan", buf.getvalue())
        self.assertIn("not a clean result", buf.getvalue())


class SafeOutputTests(RepoTestCase):
    def test_no_stable_hash_is_emitted(self) -> None:
        """A truncated hash over a few hundred registry names is reversible."""
        source = (SCRIPTS / "check_sensitive_data.py").read_text(encoding="utf-8")
        self.assertNotIn("hashlib", source)
        self.assertNotIn("sha256", source)
        self.assertFalse(hasattr(guard, "match_id"))
        self.write("notes.md", f"{TOKEN}\n")
        self.commit_all()
        rendered = "\n".join(f.render() for f in guard.scan(self.repo, WATCH))
        self.assertNotIn("match_id", rendered)

    def test_output_has_metadata_but_never_the_value_or_line(self) -> None:
        line = f"prefix {TOKEN} suffix"
        self.write("docs/notes.md", f"first\n{line}\n")
        self.commit_all()
        findings = guard.scan(self.repo, WATCH)
        rendered = "\n".join(f.render() for f in findings)

        self.assertIn("docs/notes.md", rendered)
        self.assertIn(":2", rendered)
        self.assertIn(guard.INDEX, rendered)

        self.assertNotIn(TOKEN, rendered)
        self.assertNotIn(line, rendered)
        for word in TOKEN.split():
            self.assertNotIn(word, rendered)

    def test_main_summary_does_not_echo_findings_content(self) -> None:
        import io, contextlib
        self.write("notes.md", f"{TOKEN}\n")
        self.commit_all()
        buf = io.StringIO()
        with mock.patch.object(guard, "load_watch_strings", return_value=WATCH), \
             mock.patch.object(guard, "ensure_utf8_stdout", lambda: None), \
             mock.patch("pipeline_common.get_services", return_value={}), \
             contextlib.redirect_stdout(buf):
            code = guard.main(["--repo", str(self.repo)])
        out = buf.getvalue()
        self.assertEqual(1, code)
        self.assertIn("notes.md:1", out)
        self.assertNotIn(TOKEN, out)


class ReadOnlyRegistryTests(unittest.TestCase):
    """The loader must never be able to create Drive state."""

    MUTATING = {
        "find_or_create_folder", "ensure_folder_path", "ensure_child_folder",
        "ensure_document_folder", "batchUpdate", "move_item", "create",
    }

    def test_loader_imports_and_calls_no_mutating_helper(self) -> None:
        """AST-level, so a docstring naming a helper is not a false positive."""
        import ast
        tree = ast.parse((SCRIPTS / "check_sensitive_data.py").read_text(encoding="utf-8"))
        imported: set[str] = set()
        called: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                imported.update(a.name for a in node.names)
            elif isinstance(node, ast.Call):
                name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
                if name:
                    called.add(name)
        self.assertEqual(set(), imported & self.MUTATING, "imports a mutating helper")
        self.assertEqual(set(), called & self.MUTATING, "calls a mutating helper")
        self.assertIn("find_folder", imported)
        self.assertIn("find_sheet_in_folder", imported)

    def test_missing_registry_folder_raises_instead_of_creating(self) -> None:
        drive = mock.Mock()
        services = {"drive": drive}
        with mock.patch("show_project_state.find_folder", return_value=None):
            with self.assertRaises(guard.RegistryLookupError):
                guard.load_watch_strings(services)
        drive.files.assert_not_called()

    def test_missing_registry_sheet_raises_instead_of_creating(self) -> None:
        services = {"drive": mock.Mock()}
        with mock.patch("show_project_state.find_folder",
                        return_value={"id": "f", "name": "folder"}), \
             mock.patch("sync_m2_source_docs_to_sheets.find_sheet_in_folder",
                        return_value=None):
            with self.assertRaises(guard.RegistryLookupError):
                guard.load_watch_strings(services)

    def test_empty_watch_list_fails_closed(self) -> None:
        """An empty list would pass every file - that is not an all-clear."""
        services = {"drive": mock.Mock()}
        with mock.patch("show_project_state.find_folder",
                        return_value={"id": "f", "name": "folder"}), \
             mock.patch("sync_m2_source_docs_to_sheets.find_sheet_in_folder",
                        return_value={"id": "s"}), \
             mock.patch("sync_m2_source_docs_to_sheets.read_sheet_values",
                        return_value=[["Name (RU)", "Name (EN)"]]):
            with self.assertRaises(guard.RegistryLookupError):
                guard.load_watch_strings(services)

    def test_watch_list_of_only_short_tokens_fails_closed(self) -> None:
        services = {"drive": mock.Mock()}
        rows = [["Name (RU)", "Name (EN)"], ["ab", "cd"]]
        with mock.patch("show_project_state.find_folder",
                        return_value={"id": "f", "name": "folder"}), \
             mock.patch("sync_m2_source_docs_to_sheets.find_sheet_in_folder",
                        return_value={"id": "s"}), \
             mock.patch("sync_m2_source_docs_to_sheets.read_sheet_values",
                        return_value=rows):
            with self.assertRaises(guard.RegistryLookupError):
                guard.load_watch_strings(services)

    def test_short_strings_are_filtered_out(self) -> None:
        services = {"drive": mock.Mock()}
        rows = [["Name (RU)", "Name (EN)"], ["ab", "abc"], ["abcd", ""]]
        with mock.patch("show_project_state.find_folder",
                        return_value={"id": "f", "name": "folder"}), \
             mock.patch("sync_m2_source_docs_to_sheets.find_sheet_in_folder",
                        return_value={"id": "s"}), \
             mock.patch("sync_m2_source_docs_to_sheets.read_sheet_values",
                        return_value=rows):
            watch = guard.load_watch_strings(services)
        self.assertTrue(all(len(w) >= guard.MIN_NAME_LEN for w in watch))
        self.assertIn("abcd", watch)


class NoRealValuesInThisModuleTests(unittest.TestCase):
    def test_fixture_tokens_are_synthetic_placeholders(self) -> None:
        """Guards the guard: this module must stay free of real names."""
        text = Path(__file__).read_text(encoding="utf-8")
        self.assertIn("Synthetic only", text)
        self.assertIn("must never be", text)
        self.assertNotIn("@", TOKEN)
        self.assertNotIn("@", OTHER_TOKEN)


if __name__ == "__main__":
    unittest.main()
