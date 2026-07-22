"""Unit tests for the Project Knowledge knowledge-quality gate.

Guards the key rule phrases added to project-knowledge-roles/SKILL.md and
project-knowledge-intake/SKILL.md so a later edit doesn't silently drop
them: promoting concrete formulas/examples/syntax into the durable record,
correcting resolved uncertainty in place, keeping the knowledge base keyed
by topic, requiring actionable open questions, distinguishing summary from
knowledge base, and the intake skill's mandatory closing quality gate
(including the performance-test-relevant checklist).

Run:  python -m unittest discover -s .agents/tests
"""

from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SKILLS_DIR = REPO_ROOT / ".agents" / "skills"


def _read(relative_path: str) -> str:
    return (SKILLS_DIR / relative_path).read_text(encoding="utf-8")


class ProjectKnowledgeRolesQualityRuleTests(unittest.TestCase):
    def setUp(self):
        self.text = _read("project-knowledge-roles/SKILL.md")

    def test_promotes_formulas_examples_syntax(self):
        for phrase in ("formula", "worked example", "configuration/string syntax", "threshold"):
            self.assertIn(phrase, self.text, f"missing phrase: {phrase!r}")

    def test_corrects_resolved_uncertainty_in_place(self):
        self.assertIn("Correct resolved uncertainty in place", self.text)
        self.assertIn("do not leave the stale", self.text.replace("\n", " "))

    def test_knowledge_base_keyed_by_topic_not_append_only(self):
        self.assertIn("keyed by topic", self.text)
        self.assertIn("upsert", self.text)

    def test_open_questions_must_be_actionable(self):
        self.assertIn("specific and actionable", self.text)

    def test_summary_vs_knowledge_base_distinction(self):
        self.assertIn("source-local", self.text)
        self.assertIn("durable and", self.text.replace("\n", " "))


class ProjectKnowledgeIntakeQualityGateTests(unittest.TestCase):
    def setUp(self):
        self.text = _read("project-knowledge-intake/SKILL.md")

    def test_mandatory_closing_quality_gate_present(self):
        self.assertIn("closing quality gate (mandatory)", self.text)

    def test_gate_checks_formulas_examples_syntax(self):
        for phrase in ("formulas", "worked examples", "configuration/string syntax", "thresholds"):
            self.assertIn(phrase, self.text, f"missing phrase: {phrase!r}")

    def test_gate_checks_performance_relevant_facts(self):
        for phrase in (
            "workload\n     formulas",
            "data volumes",
            "latency/timing targets",
            "concurrency\n     assumptions",
            "async/batch boundaries",
            "consistency windows",
            "startup/restart behavior",
            "scaling/failover assumptions",
            "observability\n     signals",
            "configurable limits",
        ):
            normalized_text = " ".join(self.text.split())
            normalized_phrase = " ".join(phrase.split())
            self.assertIn(normalized_phrase, normalized_text, f"missing phrase: {normalized_phrase!r}")

    def test_gate_checks_qa_doc_update_need(self):
        self.assertIn("Update QA docs when the gate found a reason to", self.text)

    def test_gate_checks_open_questions_and_resolved_uncertainty(self):
        normalized_text = " ".join(self.text.split())
        self.assertIn("corrected in place", normalized_text)
        self.assertIn("specific and actionable", normalized_text)


class NoRealNamesInEditedSkillsTests(unittest.TestCase):
    def test_no_real_project_or_person_names(self):
        for relative_path in (
            "project-knowledge-roles/SKILL.md",
            "project-knowledge-intake/SKILL.md",
        ):
            text = _read(relative_path)
            for name in ("CyberProAi", "McKinsey", "Hamkorbank", "PKF"):
                self.assertNotIn(name, text)


if __name__ == "__main__":
    unittest.main()
