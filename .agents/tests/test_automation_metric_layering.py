"""Tests for the repo-maintenance pass that clarified automation metric
layering (2026-07-26):

Automation coverage %, automation framework/code-quality assessment, pass
rate, flaky-test status, and CI/CD state are project/team QA-process
metrics that belong in `qa_process_metrics` -> `project_metrics` ->
`_project_registry`, not `individual_metrics` rows — even when only one QA
engineer currently owns or maintains the framework. `individual_metrics`
may only describe that person's contribution, ownership, or behavior
around the automation.

Run:  python -m unittest discover -s .agents/tests
"""

from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SKILLS_DIR = REPO_ROOT / ".agents" / "skills"
TEMPLATES_DIR = REPO_ROOT / "Templates"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(text: str) -> str:
    return " ".join(text.split())


class IndividualDocumentContractLayeringTests(unittest.TestCase):
    def setUp(self):
        self.text = _normalized(
            _read(
                SKILLS_DIR
                / "m2-individual-qa-metrics-report"
                / "references"
                / "document-contract.md"
            )
        )

    def test_states_automation_facts_are_project_not_individual(self):
        self.assertIn(
            "Automation coverage percentage and automation framework/code "
            "quality are project/team QA-process metrics, not individual "
            "metrics",
            self.text,
        )

    def test_applies_even_with_single_owner(self):
        self.assertIn(
            "this applies even when only one QA engineer currently owns or "
            "maintains the framework",
            self.text,
        )

    def test_lists_allowed_individual_framing_examples(self):
        for example in (
            "owns the automation framework",
            "contributes tests",
            "improves visibility/reporting",
            "needs support to present automation progress",
            "lacks autonomy maintaining the framework",
        ):
            self.assertIn(example, self.text)

    def test_forbids_project_level_facts_as_individual_rows(self):
        self.assertIn(
            "Do not store the automation coverage percentage, a "
            "framework/code-quality assessment, pass rate, flaky-test "
            "status, or CI/CD state as an `individual_metrics` row, even "
            "when this person is the framework's sole owner",
            self.text,
        )

    def test_states_update_order(self):
        self.assertIn(
            "update `qa_process_metrics` first, then `project_metrics`, "
            "then `_project_registry`",
            self.text,
        )


class ProjectDocumentContractLayeringTests(unittest.TestCase):
    def setUp(self):
        self.text = _normalized(
            _read(
                SKILLS_DIR
                / "m2-project-qa-metrics-report"
                / "references"
                / "document-contract.md"
            )
        )

    def test_states_automation_facts_are_project_not_individual(self):
        self.assertIn(
            "Automation coverage, automation framework/code-quality "
            "assessment, pass rate, flaky-test status, and CI/CD state are "
            "project/team QA-process facts, not individual performance "
            "metrics",
            self.text,
        )

    def test_applies_even_with_single_owner(self):
        self.assertIn(
            "this holds even when only one QA engineer currently owns or "
            "maintains the automation framework",
            self.text,
        )

    def test_states_update_order_and_individual_scope(self):
        self.assertIn(
            "update `qa_process_metrics` first, then `project_metrics`, "
            "then `_project_registry` — `individual_metrics` is used only "
            "for the person-specific contribution/ownership angle",
            self.text,
        )


class RoleRulesAutomationLayeringTests(unittest.TestCase):
    def setUp(self):
        self.text = _normalized(
            _read(
                SKILLS_DIR
                / "qa-management-roles"
                / "references"
                / "m2-role-rules.md"
            )
        )

    def test_has_automation_metric_layering_section(self):
        self.assertIn("Automation Metric Layering", self.text)

    def test_states_automation_facts_are_project_not_individual(self):
        self.assertIn(
            "Automation coverage percentage, automation framework/code-"
            "quality assessment, pass rate, flaky-test status, and CI/CD "
            "state are project/team QA-process metrics, not individual "
            "performance metrics",
            self.text,
        )

    def test_applies_even_with_single_owner(self):
        self.assertIn(
            "even when only one QA engineer currently owns or maintains "
            "the framework",
            self.text,
        )

    def test_states_cascade_order(self):
        self.assertIn(
            "A source that reports these facts updates the chain in this "
            "order: `qa_process_metrics` first, then `project_metrics`, "
            "then `_project_registry`",
            self.text,
        )

    def test_individual_metrics_scoped_to_contribution(self):
        self.assertIn(
            "individual_metrics` reflects only the person's contribution, "
            "ownership, or behavior around that automation",
            self.text,
        )


class IndividualCatalogTemplateLayeringTests(unittest.TestCase):
    def setUp(self):
        self.text = _normalized(_read(TEMPLATES_DIR / "метрики_qa_по_проекту.md"))

    def test_has_automation_metric_layering_note(self):
        self.assertIn("Automation Metric Layering", self.text)

    def test_automation_coverage_removed_from_individual_additional_metrics(self):
        self.assertNotIn(
            "Automation coverage** (для AQA) — доля согласованного объёма (agreed",
            self.text,
        )

    def test_redirects_automation_coverage_to_project_level(self):
        self.assertIn(
            "Automation coverage (доля согласованного объёма automation, реально",
            self.text,
        )

    def test_redirects_flaky_ci_state_to_project_level(self):
        self.assertIn(
            "False positive/flaky rate, % тестов в CI, время прогона в CI и "
            "% тестов с подготовкой данных через API сюда не входят",
            self.text,
        )


class ProjectCatalogTemplateLayeringTests(unittest.TestCase):
    def setUp(self):
        self.text = _normalized(_read(TEMPLATES_DIR / "метрики_проекта_qa.md"))

    def test_has_automation_metric_layering_note(self):
        self.assertIn("Automation Metric Layering", self.text)

    def test_applies_even_with_single_owner(self):
        self.assertIn(
            "project/team QA-process факты, не персональные, даже когда "
            "фреймворк сейчас единолично ведёт один QA-инженер",
            self.text,
        )


if __name__ == "__main__":
    unittest.main()
