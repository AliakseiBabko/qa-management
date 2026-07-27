"""Focused tests for the Phase 5B m2-role-rules.md split.

The 36,613-byte monolith was replaced with a thin routing index
(`m2-role-rules.md`) plus eight physically separated, task-scoped modules
under `m2-role/`. These tests guard the two things a future edit could
silently break:

1. the loading-contract shape itself - the index stays thin, every module
   it lists exists and is titled/scoped/size-bounded, and no consuming
   skill mandates a whole-monolith read;
2. the content-preservation/ownership shape - each original semantic
   section still has exactly one canonical module owner, and key M2
   anchors (Cascading Updates, Project-Level Rollups, `m2_input`, risk
   rules/feedback confidence, business-value framing, communication/
   visibility, contribution/project metrics calibration) live in their
   owning module.

Uses concise semantic anchors, never a large copy of module content.

Run:  python -m unittest discover -s .agents/tests
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ROLES_DIR = REPO_ROOT / ".agents" / "skills" / "qa-management-roles"
INDEX = ROLES_DIR / "references" / "m2-role-rules.md"
MODULE_DIR = ROLES_DIR / "references" / "m2-role"
SKILLS_DIR = REPO_ROOT / ".agents" / "skills"

EXPECTED_MODULES = [
    "m2-role-basics.md",
    "m2-cascading-updates.md",
    "m2-project-rollups.md",
    "m2-risk-rules.md",
    "m2-metrics-calibration.md",
    "m2-metrics-attribution.md",
    "m2-communication-visibility.md",
    "m2-development-plans.md",
]

ORIGINAL_MONOLITH_BYTES = 36613


def _all_skill_md_texts() -> dict[Path, str]:
    return {p: p.read_text(encoding="utf-8") for p in SKILLS_DIR.glob("*/SKILL.md")}


class ThinIndexTests(unittest.TestCase):
    def test_index_is_at_most_4kib(self):
        size = INDEX.stat().st_size
        self.assertLessEqual(size, 4 * 1024, f"index is {size} bytes, over the 4 KiB target")

    def test_index_lists_every_module_and_instructs_selective_loading(self):
        text = INDEX.read_text(encoding="utf-8")
        for name in EXPECTED_MODULES:
            self.assertIn(name, text, f"index does not list {name}")
        normalized = " ".join(text.split())
        self.assertIn("Load only", normalized)

    def test_index_carries_no_normative_rule_prose(self):
        """A routing index describes modules; it must not restate a rule
        like the risk-level dictionary or the rollup gate itself."""
        text = INDEX.read_text(encoding="utf-8")
        for leaked_rule in (
            "Низкий",
            "Средний",
            "Высокий",
            "Do not add an optional metric",
            "RCA (root cause analysis) is required",
        ):
            self.assertNotIn(leaked_rule, text)


class ModuleShapeTests(unittest.TestCase):
    def test_every_listed_module_exists(self):
        for name in EXPECTED_MODULES:
            self.assertTrue((MODULE_DIR / name).is_file(), f"missing module {name}")

    def test_no_unlisted_module_files_exist(self):
        actual = {p.name for p in MODULE_DIR.glob("*.md")}
        self.assertEqual(actual, set(EXPECTED_MODULES))

    def test_every_module_has_a_title_and_scope_statement(self):
        for name in EXPECTED_MODULES:
            text = (MODULE_DIR / name).read_text(encoding="utf-8")
            lines = text.splitlines()
            self.assertTrue(lines[0].startswith("# "), f"{name} has no H1 title")
            head = " ".join(lines[:6])
            self.assertIn("Scope:", head, f"{name} has no scope statement near the top")

    def test_every_module_is_at_most_16kib(self):
        for name in EXPECTED_MODULES:
            size = (MODULE_DIR / name).stat().st_size
            self.assertLessEqual(size, 16 * 1024, f"{name} is {size} bytes, over the 16 KiB hard cap")

    def test_aggregate_size_within_preservation_band(self):
        total = INDEX.stat().st_size + sum(
            (MODULE_DIR / n).stat().st_size for n in EXPECTED_MODULES
        )
        low = ORIGINAL_MONOLITH_BYTES * 0.95
        high = ORIGINAL_MONOLITH_BYTES * 1.10
        self.assertTrue(
            low <= total <= high,
            f"combined index+modules is {total} bytes, outside the "
            f"{low:.0f}-{high:.0f} preservation band around the original "
            f"{ORIGINAL_MONOLITH_BYTES} bytes",
        )


class SectionOwnershipTests(unittest.TestCase):
    """Each original top-level semantic section has exactly one owner."""

    OWNERSHIP = {
        "m2-role-basics.md": [
            "Role Boundary", "Main Goal", "Minimum Project Artifacts",
            "Business Focus", "Project Entry and Onboarding",
            "M2 Development Path", "Common Anti-Patterns",
        ],
        "m2-cascading-updates.md": ["Cascading Updates"],
        "m2-project-rollups.md": ["Project-Level Rollups"],
        "m2-risk-rules.md": ["Risk Rules"],
        "m2-metrics-calibration.md": [
            "Metrics Are Signals, Not Verdicts", "Metric Rules", "Template Consistency",
        ],
        "m2-metrics-attribution.md": [
            "Automation Metric Layering", "Production Bug Leakage Attribution",
            "Вклад в проект Calibration", "Registry Data-Gap Semantics",
            "Owner Selection for Multi-Person qa_process_metrics",
        ],
        "m2-communication-visibility.md": ["Communication and Visibility"],
        "m2-development-plans.md": ["Development Plans"],
    }

    def test_each_heading_owned_by_exactly_one_module(self):
        """Owned = appears as an actual Markdown heading line, not just any
        cross-reference mention (a module is allowed to *name* another
        module's heading in a "see also" pointer)."""
        heading_lines = {
            n: [
                line.lstrip("#").strip()
                for line in (MODULE_DIR / n).read_text(encoding="utf-8").splitlines()
                if line.startswith("#")
            ]
            for n in EXPECTED_MODULES
        }
        all_headings = set()
        for headings in self.OWNERSHIP.values():
            all_headings.update(headings)
        for heading in all_headings:
            owners = [
                n for n, lines in heading_lines.items()
                if any(heading in line for line in lines)
            ]
            self.assertEqual(
                len(owners), 1,
                f"heading {heading!r} is an actual heading in {owners}, expected exactly one owner",
            )

    def test_ownership_map_matches_declared_module(self):
        for module, headings in self.OWNERSHIP.items():
            text = (MODULE_DIR / module).read_text(encoding="utf-8")
            for heading in headings:
                self.assertIn(heading, text, f"{module} missing expected heading {heading!r}")


class NoMandatoryWholeFileReadTests(unittest.TestCase):
    """No skill may mandate reading the thin index."""

    def test_no_skill_mandates_reading_the_thin_index(self):
        pattern = re.compile(r"references/m2-role-rules\.md")
        for path, text in _all_skill_md_texts().items():
            for line in text.splitlines():
                if pattern.search(line) and re.match(r"^\d+\.\s*Read", line.strip()):
                    self.fail(f"{path} has a Required-Start mandatory read of the thin index")

    def test_every_referenced_module_path_exists(self):
        pattern = re.compile(r"m2-role/([a-z0-9-]+\.md)")
        for path, text in _all_skill_md_texts().items():
            for name in pattern.findall(text):
                self.assertTrue(
                    (MODULE_DIR / name).is_file(),
                    f"{path} references m2-role/{name}, which does not exist",
                )

    def test_at_least_some_skills_reference_modules(self):
        """Sanity check that the retargeting actually happened."""
        pattern = re.compile(r"m2-role/[a-z0-9-]+\.md")
        matching = [p for p, text in _all_skill_md_texts().items() if pattern.search(text)]
        self.assertGreaterEqual(len(matching), 10)


class KeyAnchorsPresentInOwningModuleTests(unittest.TestCase):
    """Spot-check load-bearing rules by exact owning module, not just
    "somewhere in the split" - a misplaced rule would still pass a looser
    "present anywhere" check."""

    def _text(self, name: str) -> str:
        return (MODULE_DIR / name).read_text(encoding="utf-8")

    def test_cascading_updates_anchor(self):
        text = self._text("m2-cascading-updates.md")
        self.assertIn("individual_metrics", text)
        self.assertIn("project_metrics", text)
        self.assertIn("_project_registry", text)

    def test_project_rollups_and_m2_input_anchor(self):
        text = self._text("m2-project-rollups.md")
        self.assertIn("m2_input", text)

    def test_risk_rules_feedback_confidence_anchor(self):
        text = self._text("m2-risk-rules.md")
        self.assertIn("feedback", text.lower())

    def test_business_value_framing_anchor(self):
        text = self._text("m2-role-basics.md")
        self.assertIn("Business Focus", text)

    def test_communication_visibility_anchor(self):
        text = self._text("m2-communication-visibility.md")
        self.assertIn("Communication and Visibility", text)

    def test_metrics_calibration_anchor(self):
        text = self._text("m2-metrics-calibration.md")
        self.assertIn("Metrics Are Signals, Not Verdicts", text)

    def test_metrics_attribution_anchor(self):
        text = self._text("m2-metrics-attribution.md")
        self.assertIn("Вклад в проект Calibration", text)


if __name__ == "__main__":
    unittest.main()
