"""Tests for the repo-maintenance pass that closed four document-quality
gaps found in real use:

1. `individual_metrics` document-contract previously described an
   append-only history model that contradicted `project_metrics` and
   `m2-role-rules.md`, both of which already treat these Sheets as
   current-state dashboards updated in place.
2. Project Knowledge QA docs (`pk_test_plan`/`pk_test_strategy`/
   `pk_performance_test_plan`) had no explicit rule against being created
   as generic placeholders.
3. `_project_registry` refresh after a `project_risk` change (not just an
   `individual_metrics`/`project_metrics` change) was not explicit.
4. `action_items`/`Дата события` guidance ("never blank, use nearest
   concrete placeholder") invited fabricating dates like "today" for
   vague follow-ups.

Run:  python -m unittest discover -s .agents/tests
"""

from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SKILLS_DIR = REPO_ROOT / ".agents" / "skills"


def _read(relative_path: str) -> str:
    return (SKILLS_DIR / relative_path).read_text(encoding="utf-8")


def _normalized(text: str) -> str:
    return " ".join(text.split())


class IndividualMetricsCurrentStateTests(unittest.TestCase):
    def setUp(self):
        self.text = _read(
            "m2-individual-qa-metrics-report/references/document-contract.md"
        )
        self.normalized = _normalized(self.text)

    def test_no_longer_documented_as_append_only_history(self):
        self.assertNotIn("append-only history of snapshots", self.normalized)

    def test_documented_as_current_state_dashboard(self):
        self.assertIn("current-state dashboard", self.normalized)
        self.assertIn(
            "one row per (`Проект`, `Сотрудник`, `Метрика`)".replace("`", "`"),
            self.normalized,
        )

    def test_dedup_key_excludes_date(self):
        self.assertIn(
            "Deduplicate on (`Проект`, `Сотрудник`, `Метрика`)", self.normalized
        )
        self.assertIn("`Дата` is not part of", self.normalized)

    def test_history_belongs_in_evidence_log_not_second_row(self):
        self.assertIn("second row", self.normalized)
        self.assertIn("evidence_log", self.normalized)

    def test_internal_variant_matches_current_state_model(self):
        self.assertIn("Same current-state/dedup mechanics", self.normalized)
        self.assertNotIn("Same append-only/dedup mechanics", self.normalized)


class ProjectKnowledgePlaceholderRuleTests(unittest.TestCase):
    def setUp(self):
        self.roles_text = _normalized(_read("project-knowledge-roles/SKILL.md"))
        self.intake_text = _normalized(_read("project-knowledge-intake/SKILL.md"))

    def test_roles_forbid_placeholder_creation(self):
        self.assertIn("Never create one of these three as a placeholder", self.roles_text)
        self.assertIn("explicitly asks for it", self.roles_text)
        self.assertIn("worse than no document", self.roles_text)

    def test_intake_cross_references_placeholder_rule_on_creation(self):
        self.assertIn(
            "creating it here is still subject to the same rule as any other",
            self.intake_text,
        )
        self.assertIn("Never create one of these three as a placeholder", self.intake_text)


class RegistryRefreshAfterProjectRiskTests(unittest.TestCase):
    def setUp(self):
        self.text = _normalized(
            _read("qa-management-roles/references/m2-role-rules.md")
        )

    def test_refresh_discipline_applies_regardless_of_entry_point(self):
        self.assertIn(
            "The same refresh discipline applies no matter which document the change",
            self.text,
        )

    def test_names_registry_is_generated_only_from_project_metrics(self):
        self.assertIn("never reads", self.text)
        self.assertIn("project_risk", self.text)

    def test_names_mirrored_fields_that_trigger_refresh(self):
        for field in (
            "Статус проекта",
            "Горизонт совместной работы",
            "Бизнес-риск продукта клиента",
            "Вклад в проект: <Имя>",
            "Качество QA-процесса",
        ):
            self.assertIn(field, self.text)

    def test_instructs_rerunning_refresh_script_in_same_pass(self):
        self.assertIn("rerun", self.text)
        self.assertIn("refresh_project_registry.py", self.text)


class ActionItemsDueDateRuleTests(unittest.TestCase):
    def setUp(self):
        self.contract_text = _normalized(
            _read("m2-timeline/references/document-contract.md")
        )
        self.skill_text = _normalized(_read("m2-timeline/SKILL.md"))

    def test_contract_forbids_inventing_unsupported_dates(self):
        self.assertIn(
            "Never invent a date that nothing in the source supports", self.contract_text
        )

    def test_contract_offers_cadence_labels_instead_of_fake_dates(self):
        for label in ("Еженедельный review", "Backlog", "Следующий цикл планирования"):
            self.assertIn(label, self.contract_text)

    def test_skill_workflow_step_forbids_fabricated_today_date(self):
        self.assertIn(
            'Do not invent a "today" or other near-term date for a vague follow-up',
            self.skill_text,
        )

    def test_skill_guardrail_updated_to_reject_placeholder_dates(self):
        self.assertIn(
            'Do not fabricate a due date — not a nearest-concrete-date guess, not "today."',
            self.skill_text,
        )


class NoRealNamesInEditedFilesTests(unittest.TestCase):
    def test_no_real_project_or_person_names(self):
        for relative_path in (
            "m2-individual-qa-metrics-report/references/document-contract.md",
            "project-knowledge-roles/SKILL.md",
            "project-knowledge-intake/SKILL.md",
            "qa-management-roles/references/m2-role-rules.md",
            "m2-timeline/references/document-contract.md",
            "m2-timeline/SKILL.md",
        ):
            text = _read(relative_path)
            for name in ("<Project>", "<Project>", "<Project>", "<Project>", "<Project>"):
                self.assertNotIn(name, text)


if __name__ == "__main__":
    unittest.main()
