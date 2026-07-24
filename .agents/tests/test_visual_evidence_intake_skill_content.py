"""Tests for the visual-evidence-intake skill.

Guards the drop-folder convention, the required workflow steps, and the
guardrails (screenshots as supporting evidence only, no automatic
document updates, no deletion of originals, no real screenshot content in
this public repo) so a later edit doesn't silently drop them.

Run:  python -m unittest discover -s .agents/tests
"""

from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SKILL_MD = REPO_ROOT / ".agents" / "skills" / "visual-evidence-intake" / "SKILL.md"
AGENTS_MD = REPO_ROOT / "AGENTS.md"
README = REPO_ROOT / "README.md"
PROMPTS = REPO_ROOT / ".agents" / "references" / "operator-prompts.md"


class VisualEvidenceIntakeSkillExistsTests(unittest.TestCase):
    def test_skill_file_exists(self):
        self.assertTrue(SKILL_MD.exists(), f"missing {SKILL_MD}")

    def test_frontmatter_name_matches_directory(self):
        text = SKILL_MD.read_text(encoding="utf-8")
        self.assertIn("name: visual-evidence-intake", text)


class VisualEvidenceIntakeSkillContentTests(unittest.TestCase):
    def setUp(self):
        self.text = SKILL_MD.read_text(encoding="utf-8")
        self.normalized = " ".join(self.text.split())

    def test_drop_folder_convention(self):
        self.assertIn("00_Inbox/_Visual_Drop/", self.text)

    def test_optional_context_notes_documented(self):
        self.assertIn("visual_context.md", self.text)
        self.assertIn("visual_context_notes.txt", self.text)
        self.assertIn("do not need a formal structure", self.normalized)

    def test_notes_are_identity_context_source(self):
        self.assertIn("identity/context source of truth", self.normalized)
        self.assertIn("the screenshots are the visual evidence", self.normalized)

    def test_bundle_output_shape(self):
        self.assertIn("visual-bundle-<topic>", self.text)
        self.assertIn("screenshots/", self.text)

    def test_mapping_columns_preserved(self):
        for column in ("original filename", "new filename", "short description", "confidence"):
            self.assertIn(column, self.normalized, f"missing mapping column: {column!r}")

    def test_workflow_requires_inspection_not_guessing(self):
        self.assertIn("Do not guess", self.normalized)

    def test_recommends_downstream_path_only(self):
        self.assertIn("project_knowledge_notes", self.normalized)
        self.assertIn("Recommend a downstream path", self.normalized)

    def test_guardrail_supporting_evidence_not_substitute(self):
        self.assertIn("not a substitute for source", self.normalized)
        self.assertIn("sidecar evidence", self.normalized)

    def test_guardrail_no_identity_inference_from_screenshot_only(self):
        self.assertIn("Do not infer project/person/meeting identity", self.normalized)
        self.assertIn("registry-backed lookup", self.normalized)

    def test_guardrail_no_automatic_document_updates(self):
        self.assertIn("Do not update M1/M2/Project Knowledge documents automatically", self.normalized)

    def test_guardrail_no_deleting_originals(self):
        self.assertIn("Do not delete the original screenshots unless the user explicitly asks", self.normalized)

    def test_guardrail_no_committing_real_content_to_repo(self):
        self.assertIn("Do not commit real screenshot filenames or content to this", self.normalized)

    def test_guardrail_ui_and_vscode_screenshot_limits(self):
        self.assertIn("UI screenshots", self.text)
        self.assertIn("not enough for real code analysis", self.normalized)

    def test_qa_automation_overview_is_descriptive_not_numeric_score(self):
        self.assertIn("QA automation screenshots", self.text)
        self.assertIn("automation implementation overview", self.normalized)
        self.assertIn("Do not turn this into a numeric quality score", self.normalized)

    def test_guardrail_prefer_copied_text_over_ocr(self):
        self.assertIn("OCR", self.text)
        self.assertIn("prefer that", self.normalized)

    def test_notes_read_before_inspection(self):
        self.assertIn("Read the context notes first", self.text)
        self.assertIn("before opening any image", self.normalized)

    def test_per_screenshot_processing_plan_before_inspection(self):
        self.assertIn("Build a per-screenshot processing plan", self.normalized)
        self.assertIn("`process` or `skip`", self.normalized)

    def test_user_notes_authoritative_for_skip(self):
        self.assertIn("authoritative instruction for triage", self.normalized)
        self.assertIn("duplicate, bad quality, or not important", self.normalized)

    def test_skip_reason_recorded_without_opening_file(self):
        self.assertIn("do not open/describe them", self.normalized)
        self.assertIn("n/a (not inspected)", self.normalized)

    def test_bundle_naming_convention_must_be_written_down(self):
        self.assertIn("it must be written down", self.normalized)

    def test_ai_estimate_labeled_not_verified(self):
        self.assertIn("self-reported/AI-estimated with unclear methodology", self.normalized)
        self.assertIn("Do not build automated verification of such a number", self.normalized)

    def test_recommends_project_knowledge_lane_when_plan_becomes_dumping_ground(self):
        self.assertIn("30_Project_Knowledge/<Project>", self.text)
        self.assertIn("is itself a signal", self.normalized)


class VisualEvidenceIntakeMirrorSyncTests(unittest.TestCase):
    def test_agents_md_table_row(self):
        text = AGENTS_MD.read_text(encoding="utf-8")
        self.assertIn("`visual-evidence-intake`", text)
        self.assertIn(".agents/skills/visual-evidence-intake/SKILL.md", text)

    def test_agents_md_inbox_bullet_mentions_visual_drop(self):
        text = AGENTS_MD.read_text(encoding="utf-8")
        self.assertIn("_Visual_Drop", text)
        self.assertIn("visual_context_notes.txt", text)
        self.assertIn("sidecar visual evidence", text)

    def test_readme_documents_the_drop_folder(self):
        text = README.read_text(encoding="utf-8")
        self.assertIn("_Visual_Drop", text)
        self.assertIn("visual-evidence-intake", text)
        self.assertIn("visual_context_notes.txt", text)
        self.assertIn("sidecar", text)

    def test_operator_prompt_present(self):
        text = PROMPTS.read_text(encoding="utf-8")
        self.assertIn("visual-evidence-intake", text)
        self.assertIn("_Visual_Drop", text)


class NoRealNamesOrPathsTests(unittest.TestCase):
    """Only placeholders allowed - no real project/person names, and the
    repo-wide sensitive-data rule applies to this new skill file too."""

    def test_no_real_project_or_person_names(self):
        text = SKILL_MD.read_text(encoding="utf-8")
        for name in ("<Project>", "<Project>", "<Project>", "<Project>", "<Project>"):
            self.assertNotIn(name, text)

    def test_only_placeholder_project_token(self):
        text = SKILL_MD.read_text(encoding="utf-8")
        self.assertIn("<Project>", text)
        self.assertIn("<topic>", text)


if __name__ == "__main__":
    unittest.main()
