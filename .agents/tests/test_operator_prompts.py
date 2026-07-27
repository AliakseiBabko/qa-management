"""Tests for reusable operator prompt documentation.

The prompt cookbook exists so day-to-day prompts can stay short while the
actual workflow contract remains centralized in AGENTS.md, README.md, and
the relevant skills.
"""

from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
PROMPTS = ROOT / ".agents" / "references" / "operator-prompts.md"


class OperatorPromptsTests(unittest.TestCase):
    def test_shortcut_contract_centralizes_repeated_closure_steps(self) -> None:
        text = PROMPTS.read_text(encoding="utf-8")
        normalized = " ".join(text.split())

        self.assertIn("## Routine Shortcut Contract", text)
        self.assertIn("already completed or archived run", normalized)
        self.assertIn("refresh-source-hash <run-id>", text)
        self.assertIn("completed_run_review", text)
        self.assertIn("agent-sessions.csv", text)
        self.assertIn("mirror changed-files", text)

    def test_project_knowledge_prompts_inherit_shortcut_contract(self) -> None:
        text = PROMPTS.read_text(encoding="utf-8")

        self.assertIn("Process the next Project Knowledge source", text)
        self.assertIn("Process this Project Knowledge document", text)
        self.assertGreaterEqual(text.count("Routine Shortcut Contract"), 5)

    def test_recommend_next_person_alias_match_is_documented(self) -> None:
        text = PROMPTS.read_text(encoding="utf-8")
        normalized = " ".join(text.split())

        self.assertIn("## A note on `recommend-next`'s person-alias match", text)
        self.assertIn("person_alias_matches", normalized)
        self.assertIn("score_breakdown[\"person_alias_match\"]", normalized)
        self.assertIn("ranking hint only", normalized)
        self.assertIn("not a project/person scope decision", normalized)


if __name__ == "__main__":
    unittest.main()
