"""Tests for the repo-maintenance pass that added a reusable, tiered QA
metrics catalog reference (2026-07-26):

`qa-management-roles/references/qa-metrics-catalog.md` is a new
cross-cutting map tying together three tiers:

1. Core minimum project QA-process metrics (6, mandatory, project-level) —
   defined in `Templates\метрики_проекта_qa.md` §2 Core.
2. Optional project/release quality metrics (incident-tracking, tooling-
   gated) — new subsection in `Templates\метрики_проекта_qa.md` §2
   Extended, "Релизы и инциденты".
3. Optional individual QA contribution metrics (tooling/comparability-
   gated) — new subsection in `Templates\метрики_qa_по_проекту.md`,
   "Личный вклад".

All three tiers share one governing principle, stated in `m2-role-rules.md`
under "Metrics Are Signals, Not Verdicts": metrics are diagnostic signals
for M2 judgment, not automatic verdicts; optional metrics are added only
with a real recurring data source and a real management question; missing
data is recorded as an explicit gap, never fabricated; and RCA is required
before attributing production leakage to a person.

Run:  python -m unittest discover -s .agents/tests
"""

from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SKILLS_DIR = REPO_ROOT / ".agents" / "skills"
TEMPLATES_DIR = REPO_ROOT / "Templates"

CATALOG_PATH = SKILLS_DIR / "qa-management-roles" / "references" / "qa-metrics-catalog.md"
ROLE_RULES_PATH = SKILLS_DIR / "qa-management-roles" / "references" / "m2-role-rules.md"
PROJECT_CATALOG_PATH = TEMPLATES_DIR / "метрики_проекта_qa.md"
INDIVIDUAL_CATALOG_PATH = TEMPLATES_DIR / "метрики_qa_по_проекту.md"
PROJECT_CONTRACT_PATH = (
    SKILLS_DIR / "m2-project-qa-metrics-report" / "references" / "document-contract.md"
)
INDIVIDUAL_CONTRACT_PATH = (
    SKILLS_DIR / "m2-individual-qa-metrics-report" / "references" / "document-contract.md"
)

CORE_PROJECT_METRICS = (
    "Покрытие (грубая оценка)",
    "Количество автотестов (тренд)",
    "Pass rate последнего прогона",
    "Ощущение по flaky-тестам",
    "Снимок открытых/известных багов",
    "Production bug leakage (Баги, утекшие в прод)",
)

OPTIONAL_PROJECT_RELEASE_METRICS = (
    "Incident-free releases",
    "Incident rate",
    "Customer-impacting incidents",
    "Downtime",
    "MTTA",
    "MTTR",
    "Repeat incident rate",
    "Reopened incident rate",
    "Pre-prod vs prod defect ratio",
    "Weighted production incident score",
    "Release success thresholds",
)

OPTIONAL_INDIVIDUAL_METRICS = (
    "Test documentation created/updated",
    "Test cases executed",
    "Valid bugs raised",
    "Prod leakage attributable after RCA",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(text: str) -> str:
    return " ".join(text.split())


class CatalogFileExistsAndListsTiersTests(unittest.TestCase):
    def setUp(self):
        self.text = _normalized(_read(CATALOG_PATH))

    def test_file_exists(self):
        self.assertTrue(CATALOG_PATH.is_file())

    def test_states_governing_principle(self):
        self.assertIn(
            "Metrics — Core or optional, project-level or individual — "
            "are diagnostic signals for M2 review, 1:1s, retrospectives, "
            "and project-risk decisions",
            self.text,
        )
        self.assertIn(
            "not automatic performance verdicts", self.text
        )

    def test_lists_all_core_project_metrics(self):
        for metric in CORE_PROJECT_METRICS:
            self.assertIn(metric, self.text)

    def test_lists_all_optional_project_release_metrics(self):
        for metric in OPTIONAL_PROJECT_RELEASE_METRICS:
            self.assertIn(metric, self.text)

    def test_lists_all_optional_individual_metrics(self):
        for metric in OPTIONAL_INDIVIDUAL_METRICS:
            self.assertIn(metric, self.text)

    def test_does_not_redefine_schema_owning_source_of_truth(self):
        self.assertIn(
            "This is not a fourth schema to keep in sync by hand", self.text
        )

    def test_cross_references_owning_templates(self):
        self.assertIn("метрики_проекта_qa.md", self.text)
        self.assertIn("метрики_qa_по_проекту.md", self.text)


class RoleRulesSignalsNotVerdictsTests(unittest.TestCase):
    def setUp(self):
        self.text = _normalized(_read(ROLE_RULES_PATH))

    def test_has_signals_not_verdicts_section(self):
        self.assertIn("Metrics Are Signals, Not Verdicts", self.text)

    def test_states_no_default_optional_metrics(self):
        self.assertIn(
            "Do not add an optional metric to every project by default",
            self.text,
        )

    def test_states_recurring_source_and_question_requirement(self):
        self.assertIn(
            "Add one only when the project already has a recurring data "
            "source for it and there is a concrete management question it "
            "answers",
            self.text,
        )

    def test_states_no_fabrication_rule(self):
        self.assertIn(
            "record the gap explicitly (what's missing and why) instead "
            "of fabricating a value",
            self.text,
        )

    def test_cross_references_catalog_file(self):
        self.assertIn("qa-metrics-catalog.md", self.text)

    def test_leakage_attribution_requires_rca(self):
        self.assertIn(
            "RCA (root cause analysis) is required before attributing a "
            "leaked defect to a person",
            self.text,
        )
        self.assertIn(
            "not the same as RCA-backed attribution", self.text
        )


class ProjectCatalogTemplateReleaseIncidentTests(unittest.TestCase):
    def setUp(self):
        self.text = _normalized(_read(PROJECT_CATALOG_PATH))

    def test_has_release_incident_section(self):
        self.assertIn("Релизы и инциденты", self.text)

    def test_gated_on_incident_tracker(self):
        self.assertIn(
            "optional — только при наличии incident-трекера", self.text
        )

    def test_lists_all_optional_project_release_metrics(self):
        for metric in OPTIONAL_PROJECT_RELEASE_METRICS:
            self.assertIn(metric, self.text)

    def test_mttr_disambiguated_from_mean_time_to_fix(self):
        self.assertIn(
            "Не путать с «Mean Time to Fix» выше", self.text
        )


class IndividualCatalogTemplateContributionTests(unittest.TestCase):
    def setUp(self):
        self.text = _normalized(_read(INDIVIDUAL_CATALOG_PATH))

    def test_has_personal_contribution_section(self):
        self.assertIn("Личный вклад", self.text)

    def test_states_comparability_gate(self):
        self.assertIn(
            "только когда на проекте есть данные и они действительно "
            "сравнимы",
            self.text,
        )

    def test_lists_all_optional_individual_metrics(self):
        for metric in OPTIONAL_INDIVIDUAL_METRICS:
            self.assertIn(metric, self.text)

    def test_rca_gate_on_leakage_attribution(self):
        self.assertIn(
            "становится строкой `individual_metrics` только когда для "
            "конкретного случая production bug leakage",
            self.text,
        )
        self.assertIn("уже проведён RCA", self.text)


class DocumentContractsCrossReferenceCatalogTests(unittest.TestCase):
    def test_project_contract_references_catalog(self):
        text = _normalized(_read(PROJECT_CONTRACT_PATH))
        self.assertIn("qa-metrics-catalog.md", text)

    def test_individual_contract_references_catalog(self):
        text = _normalized(_read(INDIVIDUAL_CONTRACT_PATH))
        self.assertIn("qa-metrics-catalog.md", text)


class NoRealNamesInEditedFilesTests(unittest.TestCase):
    def test_no_real_project_or_person_names(self):
        for path in (
            CATALOG_PATH,
            ROLE_RULES_PATH,
            PROJECT_CATALOG_PATH,
            INDIVIDUAL_CATALOG_PATH,
            PROJECT_CONTRACT_PATH,
            INDIVIDUAL_CONTRACT_PATH,
        ):
            text = _read(path)
            for name in ("<Project>", "<Project>", "<Project>", "<Project>", "<Project>", "<Person>"):
                self.assertNotIn(name, text)


if __name__ == "__main__":
    unittest.main()
