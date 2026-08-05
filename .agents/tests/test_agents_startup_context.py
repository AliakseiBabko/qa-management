"""Focused tests for the Phase 4 AGENTS.md startup-context reduction.

AGENTS.md was turned from a detailed operating manual into a compact
startup router: the full canonical-skills table, the detailed folder
tree, per-command CLI flag prose, and telemetry command syntax all moved
to their real canonical owners (README, skill frontmatter, `--help`,
`validate_repo.py`). These tests guard the two things a future edit could
silently break:

1. every rule AGENTS.md is required to retain is still present, checked
   with positive semantic anchors rather than a large literal copy of the
   file;
2. the removed content stays removed, and skill-inventory validation is
   now genuinely filesystem/frontmatter-based rather than depending on a
   table in AGENTS.md.

Run:  python -m unittest discover -s .agents/tests
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[2]
AGENTS_MD = REPO_ROOT / "AGENTS.md"

SCRIPTS = REPO_ROOT / ".agents" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import validate_repo  # noqa: E402


def _normalized() -> str:
    return " ".join(AGENTS_MD.read_text(encoding="utf-8").split())


class SizeBudgetTests(unittest.TestCase):
    def test_agents_md_is_at_most_16_kib(self):
        size = AGENTS_MD.stat().st_size
        self.assertLessEqual(size, 16 * 1024, f"AGENTS.md is {size} bytes, over the 16 KiB hard budget")


class RetainedPolicyTests(unittest.TestCase):
    """Positive semantic anchors for every rule AGENTS.md must keep."""

    def setUp(self):
        self.text = AGENTS_MD.read_text(encoding="utf-8")
        self.normalized = _normalized()

    def test_public_repository_safety_rule_present(self):
        self.assertIn("public", self.text)
        self.assertIn("real business data", self.normalized)
        self.assertIn("<Person>", self.text)
        self.assertIn("<Project>", self.text)
        self.assertIn("commit messages", self.normalized)

    def test_leak_flagging_and_drive_scoped_exception_present(self):
        self.assertIn("flag it", self.normalized)
        self.assertIn("git log --all -p", self.text)
        self.assertIn("Drive workspace itself", self.normalized)
        self.assertIn("carry this repo", self.normalized)

    def test_local_google_oauth_exception_is_narrow(self):
        self.assertIn(".local/google/credentials.json", self.text)
        self.assertIn("a general place for audit exports", self.normalized)
        self.assertIn("process memory", self.normalized)

    def test_skills_directory_and_adapter_referenced(self):
        self.assertIn(".agents/skills/", self.text)
        self.assertIn("setup_agent_adapters.py", self.text)
        self.assertIn("load only the skill needed", self.normalized)

    def test_dashboard_and_readme_pipeline_scripts_routing_present(self):
        self.assertIn("qa_manage.py dashboard", self.text)
        self.assertIn("Current pipeline scripts", self.text)

    def test_drive_root_id_present(self):
        self.assertIn("1QtIOTEd0fVi4eAhCo_I0xqDSIUiEITRc", self.text)

    def test_m1_m2_project_knowledge_separation_present(self):
        self.assertIn("10_M1_People_Management", self.text)
        self.assertIn("20_M2_Project_Management", self.text)
        self.assertIn("30_Project_Knowledge", self.text)
        self.assertIn("private/", self.text)
        self.assertIn("shared/", self.text)
        self.assertIn("not a universal", self.normalized)

    def test_repo_maintenance_and_three_runtimes_present(self):
        self.assertIn("repo-maintenance", self.text)
        self.assertIn("Codex", self.text)
        self.assertIn("Claude Code", self.text)
        self.assertIn("Antigravity", self.text)

    def test_core_judgment_rules_present(self):
        self.assertIn("smallest relevant evidence source", self.normalized)
        self.assertIn("do not invent", self.normalized)
        self.assertIn("Russian", self.text)
        self.assertIn("Google Sheets", self.text)
        self.assertIn("Google Docs", self.text)

    def test_validation_commands_referenced(self):
        self.assertIn("validate_repo.py", self.text)
        self.assertIn("check_sensitive_data.py", self.text)

    def test_drive_network_sandbox_retry_rule_present(self):
        self.assertIn("WinError 10013", self.text)
        self.assertIn("network/escalated permissions", self.normalized)
        self.assertIn("Do not treat that first sandbox failure", self.normalized)

    def test_dev_tool_provider_exception_present(self):
        self.assertIn("technically necessary", self.normalized)
        self.assertIn("Co-Authored-By", self.text)
        self.assertIn("commit trailers", self.normalized)

    def test_catch_all_identifying_detail_prohibition_present(self):
        self.assertIn(
            "any other detail that identifies a specific real person, team, or engagement",
            self.normalized,
        )

    def test_adapter_refusal_vs_setup_boundary_present(self):
        self.assertIn("reports the", self.normalized)
        self.assertIn("adapter missing", self.normalized)
        self.assertIn("collision or misdirected link", self.normalized)
        self.assertIn("follow its printed", self.normalized)
        self.assertIn("never replaces an existing path", self.normalized)

    def test_multi_agent_shared_content_vs_adapter_wording_present(self):
        self.assertIn("Canonical skill content is shared under", self.normalized)
        self.assertIn("machine-local discovery adapters", self.normalized)
        self.assertIn("never a duplicated runtime-specific skill body", self.normalized)


class RemovedContentStaysRemovedTests(unittest.TestCase):
    """The specific things Phase 4 removed must not silently creep back."""

    def setUp(self):
        self.text = AGENTS_MD.read_text(encoding="utf-8")

    def test_full_skill_table_is_gone(self):
        self.assertNotIn("| Skill | Role | Outcome | Canonical source |", self.text)
        # A handful of skill-table-only rows that would only reappear if
        # the table itself came back.
        for marker in (
            "m2-strategy-chat-analysis",
            "m1-people-risk-report",
            "project-knowledge-intake",
        ):
            self.assertNotIn(marker, self.text)

    def test_detailed_cli_flag_prose_is_gone(self):
        for marker in (
            "--max-preview-chars",
            "score_breakdown",
            "route_description",
            "--scoped --run-id",
            "recommend-next --project",
            "closeout_telemetry.py --run-id",
        ):
            self.assertNotIn(marker, self.text)

    def test_detailed_folder_tree_is_gone(self):
        self.assertNotIn("individual_risk.gsheet", self.text)
        self.assertNotIn("qa_process_metrics.gsheet", self.text)

    def test_telemetry_command_syntax_is_gone(self):
        self.assertNotIn("No-queue direct-note/conversational rollup passes are different", self.text)


class ValidatorUsesFilesystemNotTableTests(unittest.TestCase):
    """validate_repo's skill-inventory check must not depend on AGENTS.md."""

    def _write_skill(self, root: Path, name: str, description: str = "Does a thing.") -> None:
        skill_dir = root / name
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: {description}\n---\n\n# {name}\n",
            encoding="utf-8",
        )

    def test_check_skills_never_reads_agents_md(self):
        source = (SCRIPTS / "validate_repo.py").read_text(encoding="utf-8")
        # The function that used to cross-check AGENTS.md's table is gone.
        self.assertNotIn("check_skills_vs_agents_md", source)
        self.assertNotIn('"AGENTS.md"', source.split("def check_skills(")[1].split("\ndef ")[0])

    def test_valid_skill_passes_with_no_agents_md_at_all(self):
        with tempfile.TemporaryDirectory() as tmp:
            skills_dir = Path(tmp) / "skills"
            skills_dir.mkdir()
            self._write_skill(skills_dir, "demo-skill")
            # Deliberately no AGENTS.md anywhere under `tmp` - proves the
            # check cannot be reading one.
            validate_repo.failures.clear()
            validate_repo.warnings.clear()
            with mock.patch.object(validate_repo, "SKILLS_DIR", skills_dir):
                validate_repo.check_skills()
            self.assertEqual(validate_repo.failures, [])

    def test_missing_description_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            skills_dir = Path(tmp) / "skills"
            skills_dir.mkdir()
            skill_dir = skills_dir / "bad-skill"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                "---\nname: bad-skill\ndescription:\n---\n\n# bad-skill\n",
                encoding="utf-8",
            )
            validate_repo.failures.clear()
            validate_repo.warnings.clear()
            with mock.patch.object(validate_repo, "SKILLS_DIR", skills_dir):
                validate_repo.check_skills()
            self.assertTrue(
                any("no non-empty frontmatter" in f for f in validate_repo.failures),
                validate_repo.failures,
            )

    def test_name_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            skills_dir = Path(tmp) / "skills"
            skills_dir.mkdir()
            self._write_skill(skills_dir, "mismatched-skill")
            skill_md = skills_dir / "mismatched-skill" / "SKILL.md"
            skill_md.write_text(
                skill_md.read_text(encoding="utf-8").replace(
                    "name: mismatched-skill", "name: wrong-name"
                ),
                encoding="utf-8",
            )
            validate_repo.failures.clear()
            validate_repo.warnings.clear()
            with mock.patch.object(validate_repo, "SKILLS_DIR", skills_dir):
                validate_repo.check_skills()
            self.assertTrue(
                any("!=" in f for f in validate_repo.failures), validate_repo.failures
            )

    def test_real_skill_tree_passes_check_skills(self):
        validate_repo.failures.clear()
        validate_repo.warnings.clear()
        validate_repo.check_skills()
        self.assertEqual(validate_repo.failures, [])


if __name__ == "__main__":
    unittest.main()
