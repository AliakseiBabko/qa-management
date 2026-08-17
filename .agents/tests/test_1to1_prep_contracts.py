"""Unit tests for 1to1 prep contracts and shared 1to1-prep-core framework.

Pure logic/file contract tests - no network or Google APIs.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SKILLS_DIR = REPO_ROOT / ".agents" / "skills"


class OneToOnePrepContractsTests(unittest.TestCase):
    def setUp(self):
        self.core_skill = SKILLS_DIR / "1to1-prep-core" / "SKILL.md"
        self.core_rules = SKILLS_DIR / "1to1-prep-core" / "references" / "prep-core-rules.md"
        self.m1_skill = SKILLS_DIR / "m1-1to1-prep" / "SKILL.md"
        self.m1_contract = SKILLS_DIR / "m1-1to1-prep" / "references" / "document-contract.md"
        self.m2_skill = SKILLS_DIR / "m2-1to1-prep" / "SKILL.md"
        self.m2_contract = SKILLS_DIR / "m2-1to1-prep" / "references" / "document-contract.md"
        self.all_files = [
            self.core_skill,
            self.core_rules,
            self.m1_skill,
            self.m1_contract,
            self.m2_skill,
            self.m2_contract,
        ]

    def test_core_files_exist(self):
        self.assertTrue(self.core_skill.is_file(), "1to1-prep-core/SKILL.md must exist")
        self.assertTrue(self.core_rules.is_file(), "1to1-prep-core/references/prep-core-rules.md must exist")

    def test_core_frontmatter_valid(self):
        content = self.core_skill.read_text(encoding="utf-8")
        self.assertTrue(content.startswith("---\nname: 1to1-prep-core\n"), "Name must be 1to1-prep-core")
        self.assertIn("description:", content)

    def test_core_rules_content(self):
        rules_text = self.core_rules.read_text(encoding="utf-8")
        self.assertIn("Evidence-Grounded Derivation", rules_text)
        self.assertIn("Freshness & Deduplication", rules_text)
        self.assertIn("Confidentiality & Neutral Questioning", rules_text)
        self.assertIn("Non-Mutation Guardrail", rules_text)
        self.assertIn("Default Transient Output", rules_text)

    def test_adapters_explicitly_load_core_in_required_start(self):
        m1_skill_text = self.m1_skill.read_text(encoding="utf-8")
        self.assertIn("1to1-prep-core/references/prep-core-rules.md", m1_skill_text)

        m2_skill_text = self.m2_skill.read_text(encoding="utf-8")
        self.assertIn("1to1-prep-core/references/prep-core-rules.md", m2_skill_text)

    def test_m1_adapter_contract_references_core(self):
        m1_contract_text = self.m1_contract.read_text(encoding="utf-8")
        self.assertIn("1to1-prep-core/references/prep-core-rules.md", m1_contract_text)
        self.assertIn("светофор_рисков.csv", m1_contract_text)
        self.assertIn("People requiring attention", m1_contract_text)
        self.assertIn("Do not produce project-level content here", m1_contract_text)

    def test_m2_adapter_contract_references_core(self):
        m2_contract_text = self.m2_contract.read_text(encoding="utf-8")
        self.assertIn("1to1-prep-core/references/prep-core-rules.md", m2_contract_text)
        self.assertIn("individual_metrics", m2_contract_text)
        self.assertIn("individual_development_plan", m2_contract_text)
        self.assertIn("Вклад в проект", m2_contract_text)
        self.assertIn("Do not produce project-level status or risk content here", m2_contract_text)

    def test_all_relative_md_references_resolve_to_existing_files(self):
        """Extracts backticked and linked .md file paths and verifies they resolve on disk."""
        md_ref_pattern = re.compile(r"`([^`]+\.md)`")

        for file_path in self.all_files:
            content = file_path.read_text(encoding="utf-8")
            matches = md_ref_pattern.findall(content)
            self.assertTrue(len(matches) > 0, f"Expected markdown references in {file_path.name}")

            for match in matches:
                # Resolve relative to the file's parent directory
                resolved = (file_path.parent / match).resolve()
                self.assertTrue(
                    resolved.is_file(),
                    f"Broken reference `{match}` in {file_path.relative_to(REPO_ROOT)} -> resolved to {resolved}",
                )

    def test_non_mutation_guardrail_present_across_all(self):
        for path in self.all_files:
            text = path.read_text(encoding="utf-8")
            self.assertTrue(
                "Do not write" in text or "never mutate" in text or "Non-Mutation" in text or "Do not append" in text,
                f"Non-mutation guardrail must be present in {path.name}",
            )


if __name__ == "__main__":
    unittest.main()
