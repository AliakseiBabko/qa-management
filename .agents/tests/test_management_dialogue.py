"""Tests for the local multi-model dialogue coordinator."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import sys
import importlib.util

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / ".agents" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

SHARED_COORDINATOR = REPO_ROOT.parent / "ai-skills" / "scripts" / "management_dialogue.py"
_spec = importlib.util.spec_from_file_location("management_dialogue", SHARED_COORDINATOR)
assert _spec and _spec.loader
management_dialogue = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(management_dialogue)


class ManagementDialogueTests(unittest.TestCase):
    def test_init_next_and_complete_turn(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan = root / "plan.md"
            plan.write_text("# Generic plan\n", encoding="utf-8")
            state_path = root / "state.json"
            turn_path = root / "NEXT_TURN.md"
            artifact = root / "review.md"

            with mock.patch.object(management_dialogue, "REPO_ROOT", root), \
                 mock.patch.object(management_dialogue, "MANAGEMENT_ROOT", root / "management"), \
                 mock.patch.object(management_dialogue, "DIALOGUE_ROOT", root / "management" / "dialogue"):
                self.assertEqual(
                    management_dialogue.main([
                        "init", "--topic", "TEST_PLAN", "--plan", "plan.md",
                        "--agents", "CODEX", "GEMINI",
                    ]),
                    0,
                )
                state_file = root / "management" / "dialogue" / "TEST_PLAN_state.json"
                self.assertTrue(state_file.exists())
                self.assertEqual(
                    management_dialogue.main(["next", "--topic", "TEST_PLAN"]), 0
                )
                self.assertTrue((root / "management" / "dialogue" / "TEST_PLAN_NEXT_TURN.md").exists())
                artifact.parent.mkdir(parents=True, exist_ok=True)
                artifact.write_text("# Review\n", encoding="utf-8")
                self.assertEqual(
                    management_dialogue.main([
                        "complete-turn", "--topic", "TEST_PLAN", "--agent", "CODEX",
                        "--artifact", "review.md", "--kind", "review",
                        "--validation", "focused tests: passed",
                    ]),
                    0,
                )
                state = json.loads(state_file.read_text(encoding="utf-8"))
                self.assertEqual(state["next_agent"], "GEMINI")
                self.assertEqual(state["latest_artifact"], "review.md")
                self.assertEqual(state["status"], "ready_for_agent")
                self.assertEqual(len(state["plan_revision"]), 64)
                self.assertEqual(state["history"][0]["changed_files"], [])
                self.assertEqual(state["history"][0]["validation_evidence"], ["focused tests: passed"])

    def test_decision_verify_and_close_commands(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "plan.md").write_text("# Generic plan\n", encoding="utf-8")
            decision = root / "decision.md"
            decision.write_text("# User decision\n", encoding="utf-8")
            with mock.patch.object(management_dialogue, "REPO_ROOT", root), \
                 mock.patch.object(management_dialogue, "MANAGEMENT_ROOT", root / "management"), \
                 mock.patch.object(management_dialogue, "DIALOGUE_ROOT", root / "management" / "dialogue"):
                management_dialogue.main([
                    "init", "--topic", "TEST_PLAN", "--plan", "plan.md",
                    "--agents", "CODEX", "GEMINI", "--phase", "phase-2",
                    "--acceptance-criteria", "Template headers are synchronized",
                ])
                self.assertEqual(
                    management_dialogue.main([
                        "decision", "--topic", "TEST_PLAN", "--id", "D-001",
                        "--question", "Which schema is canonical?", "--proposal", "The template",
                        "--status", "accepted", "--decided-by", "USER",
                    ]),
                    0,
                )
                self.assertEqual(
                    management_dialogue.main(["user-input", "--topic", "TEST_PLAN", "--artifact", "decision.md"]),
                    0,
                )
                self.assertEqual(
                    management_dialogue.main(["verify", "--topic", "TEST_PLAN", "--result", "pass", "--notes", "Focused checks passed"]),
                    0,
                )
                self.assertEqual(
                    management_dialogue.main(["close", "--topic", "TEST_PLAN", "--reason", "Design accepted"]),
                    0,
                )
                state_file = root / "management" / "dialogue" / "TEST_PLAN_state.json"
                state = json.loads(state_file.read_text(encoding="utf-8"))
                self.assertEqual(state["status"], "closed")
                self.assertEqual(state["decisions"][0]["id"], "D-001")

    def test_complete_turn_rejects_wrong_agent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "plan.md").write_text("# Generic plan\n", encoding="utf-8")
            with mock.patch.object(management_dialogue, "REPO_ROOT", root), \
                 mock.patch.object(management_dialogue, "MANAGEMENT_ROOT", root / "management"), \
                 mock.patch.object(management_dialogue, "DIALOGUE_ROOT", root / "management" / "dialogue"):
                management_dialogue.main([
                    "init", "--topic", "TEST_PLAN", "--plan", "plan.md",
                    "--agents", "CODEX", "GEMINI",
                ])
                (root / "review.md").write_text("# Review\n", encoding="utf-8")
                management_dialogue.main(["next", "--topic", "TEST_PLAN"])
                self.assertEqual(
                    management_dialogue.main([
                        "complete-turn", "--topic", "TEST_PLAN", "--agent", "GEMINI",
                        "--artifact", "review.md", "--kind", "review",
                    ]),
                    2,
                )

    def test_unresolved_questions_hard_stop_until_user_input(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "plan.md").write_text("# Generic plan\n", encoding="utf-8")
            (root / "review.md").write_text("# Blocked review\n", encoding="utf-8")
            (root / "decision.md").write_text("# User direction\n", encoding="utf-8")
            with mock.patch.object(management_dialogue, "REPO_ROOT", root), \
                 mock.patch.object(management_dialogue, "MANAGEMENT_ROOT", root / "management"), \
                 mock.patch.object(management_dialogue, "DIALOGUE_ROOT", root / "management" / "dialogue"):
                management_dialogue.main([
                    "init", "--topic", "BLOCKED_PLAN", "--plan", "plan.md",
                    "--agents", "CODEX", "GEMINI",
                ])
                management_dialogue.main(["next", "--topic", "BLOCKED_PLAN"])
                self.assertEqual(
                    management_dialogue.main([
                        "complete-turn", "--topic", "BLOCKED_PLAN", "--agent", "CODEX",
                        "--artifact", "review.md", "--kind", "review",
                        "--unresolved", "Need owner decision on scope",
                    ]),
                    0,
                )
                state_file = root / "management" / "dialogue" / "BLOCKED_PLAN_state.json"
                state = json.loads(state_file.read_text(encoding="utf-8"))
                self.assertEqual(state["status"], "waiting_for_user")
                self.assertEqual(
                    management_dialogue.main(["next", "--topic", "BLOCKED_PLAN"]), 2
                )
                self.assertEqual(
                    management_dialogue.main([
                        "user-input", "--topic", "BLOCKED_PLAN", "--artifact", "decision.md",
                    ]),
                    0,
                )
                state = json.loads(state_file.read_text(encoding="utf-8"))
                self.assertEqual(state["status"], "ready_for_agent")


if __name__ == "__main__":
    unittest.main()
