"""Tests for the Claude Code skill-discovery adapter.

Every test runs against a throwaway repository built under a temporary
directory. Nothing here touches the real workspace adapter: the mutating
helpers all take an explicit `repo` argument, and the two tests that exercise
`main()` patch the module's `REPO` constant at the boundary.

Link states (correct / misdirected / dangling) are driven through the module's
`_link_destination` seam rather than real links, so the suite needs no
Administrator rights, no Developer Mode, and no junction support in the test
environment. One end-to-end test does create a real link and skips itself if
the platform refuses.
"""

from __future__ import annotations

import contextlib
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import setup_agent_adapters as adapters


class AdapterTestCase(unittest.TestCase):
    """Builds a fake repo with a canonical skill dir and no adapter."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = Path(self._tmp.name).resolve()
        self.canonical = adapters.canonical_dir(self.repo)
        self.canonical.mkdir(parents=True)
        (self.canonical / "some-skill").mkdir()
        self.adapter = adapters.adapter_path(self.repo)

    def link_to(self, destination: Path):
        """Make the adapter path classify as a link pointing at `destination`."""
        return mock.patch.object(
            adapters, "_link_destination", side_effect=lambda _path: destination
        )


class TestClassifyAdapter(AdapterTestCase):
    def test_missing_adapter(self) -> None:
        self.assertEqual(
            adapters.MISSING, adapters.classify_adapter(self.adapter, self.canonical)
        )

    def test_correct_adapter(self) -> None:
        self.adapter.mkdir(parents=True)
        with self.link_to(self.canonical):
            state = adapters.classify_adapter(self.adapter, self.canonical)
        self.assertEqual(adapters.OK, state)

    def test_misdirected_adapter(self) -> None:
        elsewhere = self.repo / "elsewhere"
        elsewhere.mkdir()
        self.adapter.mkdir(parents=True)
        with self.link_to(elsewhere):
            state = adapters.classify_adapter(self.adapter, self.canonical)
        self.assertEqual(adapters.MISDIRECTED, state)

    def test_dangling_adapter(self) -> None:
        gone = self.repo / "gone"
        with mock.patch.object(
            adapters.os.path, "lexists", lambda _path: True
        ), self.link_to(gone):
            state = adapters.classify_adapter(self.adapter, self.canonical)
        self.assertEqual(adapters.DANGLING, state)

    def test_real_directory_collision(self) -> None:
        self.adapter.mkdir(parents=True)
        (self.adapter / "copied-skill").mkdir()
        self.assertEqual(
            adapters.REAL_DIRECTORY,
            adapters.classify_adapter(self.adapter, self.canonical),
        )

    def test_real_file_collision(self) -> None:
        self.adapter.parent.mkdir(parents=True)
        self.adapter.write_text("not a link", encoding="utf-8")
        self.assertEqual(
            adapters.REAL_FILE, adapters.classify_adapter(self.adapter, self.canonical)
        )


class TestSetupAdapter(AdapterTestCase):
    def test_setup_creates_missing_adapter(self) -> None:
        def fake_create(adapter: Path, _canonical: Path) -> None:
            adapter.parent.mkdir(parents=True, exist_ok=True)
            adapter.mkdir()

        with mock.patch.object(
            adapters, "_create_link", side_effect=fake_create
        ) as create, self.link_to(self.canonical):
            outcome = adapters.setup_adapter(self.repo)
        self.assertEqual("created", outcome)
        create.assert_called_once()

    def test_setup_is_idempotent_for_correct_adapter(self) -> None:
        self.adapter.mkdir(parents=True)
        with mock.patch.object(adapters, "_create_link") as create, self.link_to(
            self.canonical
        ):
            outcome = adapters.setup_adapter(self.repo)
        self.assertEqual("already-correct", outcome)
        create.assert_not_called()

    def test_setup_refuses_real_directory_without_touching_it(self) -> None:
        self.adapter.mkdir(parents=True)
        keeper = self.adapter / "copied-skill"
        keeper.mkdir()
        with mock.patch.object(adapters, "_create_link") as create:
            with self.assertRaises(adapters.AdapterError) as raised:
                adapters.setup_adapter(self.repo)
        create.assert_not_called()
        self.assertIn("real directory", str(raised.exception))
        self.assertTrue(keeper.is_dir(), "refusal must not delete existing content")

    def test_setup_refuses_misdirected_adapter(self) -> None:
        elsewhere = self.repo / "elsewhere"
        elsewhere.mkdir()
        self.adapter.mkdir(parents=True)
        with mock.patch.object(adapters, "_create_link") as create, self.link_to(
            elsewhere
        ):
            with self.assertRaises(adapters.AdapterError):
                adapters.setup_adapter(self.repo)
        create.assert_not_called()
        self.assertTrue(elsewhere.is_dir())

    def test_setup_requires_canonical_directory(self) -> None:
        with tempfile.TemporaryDirectory() as empty:
            with self.assertRaises(adapters.AdapterError):
                adapters.setup_adapter(Path(empty))


class TestCheckAdapter(AdapterTestCase):
    def test_check_fails_when_missing_and_creates_nothing(self) -> None:
        ok, message = adapters.check_adapter(self.repo)
        self.assertFalse(ok)
        self.assertIn(".claude/skills", message)
        self.assertFalse(
            self.adapter.parent.exists(), "check mode must not create .claude"
        )

    def test_check_passes_for_correct_adapter(self) -> None:
        self.adapter.mkdir(parents=True)
        with self.link_to(self.canonical):
            ok, _message = adapters.check_adapter(self.repo)
        self.assertTrue(ok)

    def test_check_fails_for_misdirected_adapter(self) -> None:
        elsewhere = self.repo / "elsewhere"
        elsewhere.mkdir()
        self.adapter.mkdir(parents=True)
        with self.link_to(elsewhere):
            ok, message = adapters.check_adapter(self.repo)
        self.assertFalse(ok)
        self.assertIn("Remove it manually", message)

    def test_check_mode_mutates_nothing(self) -> None:
        before = sorted(p.name for p in self.repo.iterdir())
        with mock.patch.object(adapters, "REPO", self.repo), mock.patch.object(
            adapters, "_create_link"
        ) as create, contextlib.redirect_stdout(io.StringIO()):
            exit_code = adapters.main(["--check"])
        self.assertEqual(1, exit_code)
        create.assert_not_called()
        self.assertEqual(before, sorted(p.name for p in self.repo.iterdir()))

    def test_main_check_exits_zero_for_correct_adapter(self) -> None:
        self.adapter.mkdir(parents=True)
        with mock.patch.object(adapters, "REPO", self.repo), self.link_to(
            self.canonical
        ), contextlib.redirect_stdout(io.StringIO()):
            exit_code = adapters.main(["--check"])
        self.assertEqual(0, exit_code)


class TestPlatformCreation(AdapterTestCase):
    """Both branches are exercised on either OS, with no real link created."""

    def test_windows_uses_unprivileged_directory_junction(self) -> None:
        completed = mock.Mock(returncode=0, stdout="", stderr="")
        with mock.patch.object(adapters, "_is_windows", return_value=True), (
            mock.patch.object(adapters.subprocess, "run", return_value=completed)
        ) as run:
            adapters._create_link(self.adapter, self.canonical)
        command = run.call_args.args[0]
        self.assertEqual(
            ["cmd", "/c", "mklink", "/J", str(self.adapter), str(self.canonical)],
            command,
        )
        self.assertTrue(self.adapter.parent.is_dir(), ".claude must be created")

    def test_windows_junction_failure_is_reported_without_local_detail(self) -> None:
        completed = mock.Mock(returncode=1, stdout="", stderr="C:\\secret\\path denied")
        with mock.patch.object(adapters, "_is_windows", return_value=True), (
            mock.patch.object(adapters.subprocess, "run", return_value=completed)
        ):
            with self.assertRaises(adapters.AdapterError) as raised:
                adapters._create_link(self.adapter, self.canonical)
        self.assertNotIn("secret", str(raised.exception))

    def test_posix_uses_relative_symlink(self) -> None:
        with mock.patch.object(adapters, "_is_windows", return_value=False), (
            mock.patch.object(adapters.os, "symlink")
        ) as symlink:
            adapters._create_link(self.adapter, self.canonical)
        symlink.assert_called_once_with(
            adapters.POSIX_LINK_TARGET, self.adapter, target_is_directory=True
        )

    def test_posix_link_target_is_relative_to_the_adapter_parent(self) -> None:
        self.assertEqual("../.agents/skills", adapters.POSIX_LINK_TARGET)
        resolved = os.path.normpath(self.adapter.parent / adapters.POSIX_LINK_TARGET)
        self.assertEqual(str(self.canonical), resolved)


class TestRealLinkEndToEnd(AdapterTestCase):
    """Optional confirmation with a genuine link, skipped where unsupported."""

    def test_real_setup_then_check_is_idempotent(self) -> None:
        try:
            adapters._create_link(self.adapter, self.canonical)
        except (adapters.AdapterError, OSError, NotImplementedError):
            self.skipTest("platform cannot create links unprivileged here")
        self.assertEqual(
            adapters.OK, adapters.classify_adapter(self.adapter, self.canonical)
        )
        with mock.patch.object(adapters, "_create_link") as create:
            self.assertEqual("already-correct", adapters.setup_adapter(self.repo))
        create.assert_not_called()
        ok, _message = adapters.check_adapter(self.repo)
        self.assertTrue(ok)
        self.assertTrue((self.adapter / "some-skill").is_dir())


class TestRealWorkspaceIsUntouched(unittest.TestCase):
    def test_module_repo_is_not_used_by_the_mutating_helpers(self) -> None:
        """setup/check take an explicit repo, so tests never write to REPO."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()
            adapters.canonical_dir(repo).mkdir(parents=True)
            self.assertNotEqual(adapters.REPO, repo)
            ok, _message = adapters.check_adapter(repo)
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
