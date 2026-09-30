"""Tests for sync_timeline_to_calendar.py calendar candidate policy.

Guarantees that Google Calendar only receives events requiring direct action
from the manager, filtering out engineer tasks, passive tracking, and soft
follow-ups.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = REPO_ROOT / ".agents" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from sync_timeline_to_calendar import is_calendar_candidate, CALENDAR_ALLOWED_TYPES


class CalendarCandidatePolicyTests(unittest.TestCase):
    def test_m2_meeting_is_accepted(self):
        item = {
            "scope": "M2",
            "project": "Alpha",
            "date": "2026-10-10",
            "type": "Встреча",
            "task": "Провести 1:1 с инженером",
            "owner": "M2",
        }
        allowed, reason = is_calendar_candidate(item)
        self.assertTrue(allowed)
        self.assertEqual(reason, "OK")

    def test_m2_deadline_is_accepted(self):
        item = {
            "scope": "M2",
            "project": "M2",
            "date": "2026-09-30",
            "type": "Дедлайн",
            "task": "Завершить и подать M2 monthly report",
            "owner": "M2",
        }
        allowed, reason = is_calendar_candidate(item)
        self.assertTrue(allowed)
        self.assertEqual(reason, "OK")

    def test_m2_weekly_review_is_accepted(self):
        item = {
            "scope": "M2",
            "project": "M2",
            "date": "2026-09-28",
            "type": "Weekly Review",
            "task": "Общее: проверить action items",
            "owner": "M2",
        }
        allowed, reason = is_calendar_candidate(item)
        self.assertTrue(allowed)

    def test_engineer_task_is_rejected(self):
        item = {
            "scope": "M2",
            "project": "Alpha",
            "date": "2026-09-19",
            "type": "Дедлайн",
            "task": "Заполнить первые значения метрик",
            "owner": "<Person>",
        }
        allowed, reason = is_calendar_candidate(item)
        self.assertFalse(allowed)
        self.assertIn("is not M2", reason)

    def test_passive_tracking_is_rejected(self):
        item = {
            "scope": "M2",
            "project": "Alpha",
            "date": "2026-09-18",
            "type": "Дедлайн",
            "task": "Подготовить план тестирования",
            "owner": "<Person> (M2 отслеживает)",
        }
        allowed, reason = is_calendar_candidate(item)
        self.assertFalse(allowed)
        self.assertIn("passive tracking", reason)

    def test_soft_followup_is_rejected(self):
        item = {
            "scope": "M2",
            "project": "Alpha",
            "date": "2026-09-30",
            "type": "Follow-up",
            "task": "Уточнить детали доступа",
            "owner": "M2",
        }
        allowed, reason = is_calendar_candidate(item)
        self.assertFalse(allowed)
        self.assertIn("not an actionable calendar event type", reason)

    def test_general_task_is_rejected(self):
        item = {
            "scope": "M2",
            "project": "Alpha",
            "date": "2026-09-19",
            "type": "Задача",
            "task": "Переслать ссылку на документ",
            "owner": "M2",
        }
        allowed, reason = is_calendar_candidate(item)
        self.assertFalse(allowed)
        self.assertIn("not an actionable calendar event type", reason)

    def test_m1_review_and_deadlines_accepted(self):
        item = {
            "scope": "M1",
            "project": "<Person>",
            "date": "2026-10-15",
            "type": "Performance Review",
            "task": "Провести Performance Review",
            "owner": "M1",
        }
        allowed, reason = is_calendar_candidate(item)
        self.assertTrue(allowed)


if __name__ == "__main__":
    unittest.main()
