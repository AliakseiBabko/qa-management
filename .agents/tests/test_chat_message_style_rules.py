"""Tests for shared chat-message style rules.

These guard the user's preferred short-message calibration without copying
real chat text, names, projects, or source details into the public repo.

Run:  python -m unittest discover -s .agents/tests
"""

from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
STYLE_RULES = (
    REPO_ROOT
    / ".agents"
    / "skills"
    / "qa-management-roles"
    / "references"
    / "chat-message-style-rules.md"
)


class ChatMessageStyleRulesTests(unittest.TestCase):
    def setUp(self):
        self.text = STYLE_RULES.read_text(encoding="utf-8")
        self.normalized = " ".join(self.text.split())

    def test_conversational_update_framing_preferred(self):
        self.assertIn("conversational update framing", self.normalized)
        self.assertIn("updates from my side", self.normalized)
        self.assertIn("Do not inflate it into formal report language", self.normalized)

    def test_balanced_evaluation_tone_preserved(self):
        self.assertIn("balanced evaluation tone", self.normalized)
        self.assertIn("workable starting point", self.normalized)
        self.assertIn("visible improvement areas", self.normalized)
        self.assertIn("plan to support the person", self.normalized)

    def test_no_real_project_or_person_names(self):
        for forbidden in ("<Project>", "<Project>", "<Project>", "<Project>", "<Project>"):
            self.assertNotIn(forbidden, self.text)


if __name__ == "__main__":
    unittest.main()
