"""Tests for the repo-maintenance pass that added "Production bug leakage /
Баги, утекшие в прод" as a 6th Core `qa_process_metrics` metric
(2026-07-26):

- Separate from the "known open bugs" current-defect snapshot: leakage is
  defects found after release/in production/by users/client/business/
  product owner.
- Classify each finding where possible (QA leakage / requirement-product
  gap / environment-data-config issue / known accepted risk / unclear-
  needs-triage); it's a strong process signal but not automatically
  personal underperformance.
- Qualitative value with evidence when an exact count is unknown: no data /
  no confirmed leakage / confirmed cases exist, count unknown / N
  confirmed cases.
- Rolls up qa_process_metrics -> project_metrics -> _project_registry; not
  an individual_metrics row unless the source directly and evidence-backed
  attributes responsibility to a named person.

Run:  python -m unittest discover -s .agents/tests
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SKILLS_DIR = REPO_ROOT / ".agents" / "skills"
SCRIPTS_DIR = REPO_ROOT / ".agents" / "scripts"
TEMPLATES_DIR = REPO_ROOT / "Templates"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(text: str) -> str:
    return " ".join(text.split())


class ProjectCatalogTemplateLeakageTests(unittest.TestCase):
    def setUp(self):
        self.text = _normalized(_read(TEMPLATES_DIR / "метрики_проекта_qa.md"))

    def test_core_count_updated_to_six(self):
        self.assertIn("Ровно 6 строк", self.text)
        self.assertNotIn("Ровно 5 строк", self.text)

    def test_new_core_metric_present(self):
        self.assertIn(
            "Production bug leakage (Баги, утекшие в прод)", self.text
        )

    def test_distinguishes_from_known_open_bugs_snapshot(self):
        self.assertIn(
            "отдельная метрика от «Снимок открытых/известных багов» выше",
            self.text,
        )

    def test_lists_classification_categories(self):
        for category in (
            "пропуск QA",
            "пробел в требованиях или продукте",
            "проблема окружения-данных-конфигурации",
            "известный принятый риск",
            "неясно",
            "требует триажа",
        ):
            self.assertIn(category, self.text)

    def test_lists_qualitative_scale(self):
        for value in (
            "нет данных",
            "утечек не подтверждено",
            "подтверждённые случаи есть, число неизвестно",
            "N подтверждённых случаев",
        ):
            self.assertIn(value, self.text)

    def test_rolls_up_through_registry_not_individual_by_default(self):
        self.assertIn(
            "не становится строкой `individual_metrics`, если источник явно и с опорой",
            self.text,
        )

    def test_cross_references_role_rules_section(self):
        self.assertIn("Production Bug Leakage Attribution", self.text)

    def test_extended_defect_escape_rate_cross_references_core_metric(self):
        self.assertIn(
            "Квантитативная версия Core-метрики «Production bug leakage",
            self.text,
        )


class IndividualCatalogTemplateLeakageTests(unittest.TestCase):
    def setUp(self):
        self.text = _normalized(_read(TEMPLATES_DIR / "метрики_qa_по_проекту.md"))

    def test_excludes_leakage_from_individual_core_metrics(self):
        self.assertIn(
            "Production bug leakage (Баги, утекшие в прод), Production-баги, "
            "Bug leakage rate и Regression/smoke coverage не входят",
            self.text,
        )

    def test_states_evidence_backed_attribution_exception(self):
        self.assertIn(
            "если источник явно и с опорой на свидетельства называет "
            "конкретного человека ответственным за утёкший в прод дефект",
            self.text,
        )

    def test_rejects_sole_qa_as_automatic_attribution(self):
        self.assertIn(
            "не эквивалент атрибуции с опорой на свидетельства", self.text
        )


class ProjectDocumentContractLeakageTests(unittest.TestCase):
    def setUp(self):
        self.text = _normalized(
            _read(
                SKILLS_DIR
                / "m2-project-qa-metrics-report"
                / "references"
                / "document-contract.md"
            )
        )

    def test_core_count_updated_to_six(self):
        self.assertIn("Core (6 metrics)", self.text)
        self.assertNotIn("Core (5 metrics)", self.text)

    def test_describes_new_metric_and_classification(self):
        self.assertIn(
            "Production bug leakage (Баги, утекшие в прод)", self.text
        )
        for category in (
            "QA leakage / requirement-or-product gap / environment-data-config",
        ):
            self.assertIn(category, self.text)

    def test_describes_qualitative_scale(self):
        self.assertIn(
            "no data / no confirmed leakage / confirmed cases exist, "
            "count unknown / N confirmed cases",
            self.text,
        )

    def test_states_not_individual_row_by_default(self):
        self.assertIn(
            "it does not become an `individual_metrics` row unless the "
            "source directly attributes responsibility to a named person "
            "and that attribution is evidence-backed",
            self.text,
        )


class RoleRulesLeakageAttributionTests(unittest.TestCase):
    def setUp(self):
        self.text = _normalized(
            _read(
                SKILLS_DIR
                / "qa-management-roles"
                / "references"
                / "m2-role-rules.md"
            )
        )

    def test_has_production_bug_leakage_attribution_section(self):
        self.assertIn("Production Bug Leakage Attribution", self.text)

    def test_distinguishes_leakage_from_open_bugs_snapshot(self):
        self.assertIn(
            "as distinct from the \"known open bugs\" current-defect "
            "snapshot",
            self.text,
        )

    def test_states_classification_categories(self):
        for category in (
            "QA leakage (should reasonably have been caught)",
            "requirement/product gap",
            "environment/data/ config",
            "known accepted risk",
            "unclear/needs triage",
        ):
            self.assertIn(category, self.text)

    def test_states_qualitative_scale(self):
        self.assertIn(
            "no data, no confirmed leakage, confirmed cases exist but "
            "count unknown, or N confirmed cases",
            self.text,
        )

    def test_rejects_sole_qa_as_automatic_attribution(self):
        self.assertIn(
            "being the only QA on a project is not the same as "
            "RCA-backed attribution",
            self.text,
        )

    def test_states_cascade_order_still_first(self):
        self.assertIn(
            "and even then `qa_process_metrics`/`project_metrics`/ "
            "`_project_registry` are updated first",
            self.text,
        )


class ScaffoldScriptLeakageTests(unittest.TestCase):
    def setUp(self):
        sys.path.insert(0, str(SCRIPTS_DIR))
        import scaffold_project_dashboard as module

        self.module = module

    def test_template_has_six_core_metrics(self):
        self.assertEqual(len(self.module.QA_METRICS_TEMPLATE), 6)

    def test_template_includes_production_bug_leakage(self):
        names = [name for name, _ in self.module.QA_METRICS_TEMPLATE]
        self.assertIn("Production bug leakage (Баги, утекшие в прод)", names)

    def test_qa_process_rows_produces_six_rows(self):
        rows = self.module.qa_process_rows("TestProject", "Test Owner", "2026-07-26")
        self.assertEqual(len(rows), 6)
        metrics = [row[2] for row in rows]
        self.assertIn("Production bug leakage (Баги, утекшие в прод)", metrics)


class NoRealNamesInEditedFilesTests(unittest.TestCase):
    def test_no_real_project_or_person_names(self):
        for path in (
            SKILLS_DIR
            / "m2-project-qa-metrics-report"
            / "references"
            / "document-contract.md",
            SKILLS_DIR / "qa-management-roles" / "references" / "m2-role-rules.md",
            TEMPLATES_DIR / "метрики_qa_по_проекту.md",
            TEMPLATES_DIR / "метрики_проекта_qa.md",
            SCRIPTS_DIR / "scaffold_project_dashboard.py",
        ):
            text = _read(path)
            for name in ("<Project>", "<Project>", "<Project>", "<Project>", "<Project>", "<Person>"):
                self.assertNotIn(name, text)


if __name__ == "__main__":
    unittest.main()
