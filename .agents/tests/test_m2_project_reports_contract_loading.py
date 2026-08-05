"""Focused tests for the Phase 5C-B split of the two M2 project-facing
report document contracts, plus making `presale-upsell-rules.md`
situational instead of mandatory:

- `m2-project-development-plan/references/document-contract.md` (10,468
  bytes) -> a thin index plus `plan-schema.md` and
  `plan-sources-normalization.md` (both mandatory every invocation).
  `presale-upsell-rules.md` is no longer read unconditionally - it is read
  only when filling/changing the Возможности расширения (Upsell) section.
- `m2-project-risk-report/references/document-contract.md` (10,472 bytes)
  -> a thin index plus `risk-schema.md` and `risk-evidence-rules.md` (both
  mandatory every invocation).
- `m2-department-traffic-light/SKILL.md`'s existing situational read of
  `presale-upsell-rules.md`'s Rule (for `Upsale opportunity`/`Upsale
  comment`) is reworded to use explicit "when"/"if" conditional language
  so the same continuation-line-aware detector from Phase 5C-A's
  test-hardening pass can verify it.

`presale-upsell-rules.md` itself (12,193 bytes) was left whole, not split:
the audit found no internally duplicated content and only one consumer
(`m2-department-traffic-light`) that needs a strict subset (just its Rule
section) - splitting out a single ~300-byte section for one situational
consumer would be an unwarranted extra abstraction for a modest, already-
conditional load. `m2-project-development-plan` genuinely needs nearly the
whole file for its Upsell section, so there's no real duplication to
extract there either.

Run:  python -m unittest discover -s .agents/tests
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = REPO_ROOT / ".agents" / "skills"

PLAN_REFS = SKILLS_DIR / "m2-project-development-plan" / "references"
RISK_REFS = SKILLS_DIR / "m2-project-risk-report" / "references"

PLAN_INDEX = PLAN_REFS / "document-contract.md"
RISK_INDEX = RISK_REFS / "document-contract.md"

PLAN_MODULES = ["plan-schema.md", "plan-sources-normalization.md"]
RISK_MODULES = ["risk-schema.md", "risk-evidence-rules.md"]

PLAN_ORIGINAL_BYTES = 10468
RISK_ORIGINAL_BYTES = 12150  # re-anchored 2026-08-05: project_risk moved from a dated-snapshot
# versioning model (_vN, project_risk_predecessor backups) to a living one-row-per-project
# record (same shape as project_metrics/individual_risk), a legitimate content change.

CONDITIONAL = re.compile(r"\b(when|if)\b", re.IGNORECASE)


def _all_skill_md_texts() -> dict[Path, str]:
    return {p: p.read_text(encoding="utf-8") for p in SKILLS_DIR.glob("*/SKILL.md")}


def _mandates_reading(text: str, pattern: re.Pattern) -> bool:
    """Continuation-line-aware detector (Phase 5A/5B/5C-A): a Required
    Start "N. Read ..." step can span an indented continuation line."""
    in_read_step = False
    for line in text.splitlines():
        stripped = line.strip()
        if re.match(r"^\d+\.\s*Read", stripped):
            in_read_step = True
        elif not line.startswith((" ", "\t")) or not stripped:
            in_read_step = False
        if in_read_step and pattern.search(line):
            return True
    return False


def _required_start_read_steps(text: str) -> list[str]:
    """Split Required Start into whole numbered 'N. Read ...' step spans
    (the numbered line plus every indented continuation line beneath it)."""
    steps: list[str] = []
    current: list[str] = []
    in_step = False
    for line in text.splitlines():
        stripped = line.strip()
        if re.match(r"^\d+\.\s*Read", stripped):
            if current:
                steps.append("\n".join(current))
            current = [line]
            in_step = True
        elif in_step and line.startswith((" ", "\t")) and stripped:
            current.append(line)
        else:
            if current:
                steps.append("\n".join(current))
            current = []
            in_step = False
    if current:
        steps.append("\n".join(current))
    return steps


def _mandates_unconditional_situational_read(text: str, module_pattern: re.Pattern) -> bool:
    """A situational module/reference may appear inside a Required Start
    "N. Read ..." step - same-line or continuation-line - only when that
    whole step also carries conditional language ("when", "if", "only
    when", "too when", "too if", ...). Without a condition anywhere in the
    step, it reads as an unconditional mandatory read."""
    for step in _required_start_read_steps(text):
        if module_pattern.search(step) and not CONDITIONAL.search(step):
            return True
    return False


class ModuleShapeTests(unittest.TestCase):
    def test_every_plan_module_exists(self):
        for name in PLAN_MODULES:
            self.assertTrue((PLAN_REFS / name).is_file(), f"missing module {name}")

    def test_every_risk_module_exists(self):
        for name in RISK_MODULES:
            self.assertTrue((RISK_REFS / name).is_file(), f"missing module {name}")

    def test_every_module_has_a_title_and_scope_statement(self):
        for refs_dir, modules in ((PLAN_REFS, PLAN_MODULES), (RISK_REFS, RISK_MODULES)):
            for name in modules:
                text = (refs_dir / name).read_text(encoding="utf-8")
                lines = text.splitlines()
                self.assertTrue(lines[0].startswith("# "), f"{name} has no H1 title")
                head = " ".join(lines[:6])
                self.assertIn("Scope:", head, f"{name} has no scope statement near the top")

    def test_every_module_is_at_most_16kib(self):
        for refs_dir, modules in ((PLAN_REFS, PLAN_MODULES), (RISK_REFS, RISK_MODULES)):
            for name in modules:
                size = (refs_dir / name).stat().st_size
                self.assertLessEqual(size, 16 * 1024, f"{name} is {size} bytes, over the 16 KiB hard cap")

    def test_thin_indexes_are_at_most_4kib(self):
        for index in (PLAN_INDEX, RISK_INDEX):
            size = index.stat().st_size
            self.assertLessEqual(size, 4 * 1024, f"{index} is {size} bytes, over the 4 KiB target")

    def test_plan_aggregate_size_within_preservation_band(self):
        total = PLAN_INDEX.stat().st_size + sum((PLAN_REFS / n).stat().st_size for n in PLAN_MODULES)
        low = PLAN_ORIGINAL_BYTES * 0.95
        high = PLAN_ORIGINAL_BYTES * 1.10
        self.assertTrue(
            low <= total <= high,
            f"plan contract split is {total} bytes, outside the "
            f"{low:.0f}-{high:.0f} band around the original {PLAN_ORIGINAL_BYTES}",
        )

    def test_risk_aggregate_size_within_preservation_band(self):
        total = RISK_INDEX.stat().st_size + sum((RISK_REFS / n).stat().st_size for n in RISK_MODULES)
        low = RISK_ORIGINAL_BYTES * 0.95
        high = RISK_ORIGINAL_BYTES * 1.10
        self.assertTrue(
            low <= total <= high,
            f"risk contract split is {total} bytes, outside the "
            f"{low:.0f}-{high:.0f} band around the original {RISK_ORIGINAL_BYTES}",
        )


class NoMandatoryWholeFileReadTests(unittest.TestCase):
    def test_no_skill_mandates_reading_plan_thin_index(self):
        pattern = re.compile(r"m2-project-development-plan/references/document-contract\.md|references/document-contract\.md")
        text = (SKILLS_DIR / "m2-project-development-plan" / "SKILL.md").read_text(encoding="utf-8")
        self.assertFalse(
            _mandates_reading(text, pattern),
            "m2-project-development-plan/SKILL.md still has a Required-Start mandatory read of the thin index",
        )

    def test_no_skill_mandates_reading_risk_thin_index(self):
        pattern = re.compile(r"references/document-contract\.md")
        text = (SKILLS_DIR / "m2-project-risk-report" / "SKILL.md").read_text(encoding="utf-8")
        self.assertFalse(
            _mandates_reading(text, pattern),
            "m2-project-risk-report/SKILL.md still has a Required-Start mandatory read of the thin index",
        )

    def test_every_referenced_plan_module_path_exists(self):
        pattern = re.compile(r"(?<!qa-management-roles/)references/([a-z0-9-]+\.md)")
        text = (SKILLS_DIR / "m2-project-development-plan" / "SKILL.md").read_text(encoding="utf-8")
        for name in pattern.findall(text):
            self.assertTrue(
                (PLAN_REFS / name).is_file(),
                f"m2-project-development-plan/SKILL.md references references/{name}, which does not exist",
            )

    def test_every_referenced_risk_module_path_exists(self):
        pattern = re.compile(r"(?<!qa-management-roles/)references/([a-z0-9-]+\.md)")
        text = (SKILLS_DIR / "m2-project-risk-report" / "SKILL.md").read_text(encoding="utf-8")
        for name in pattern.findall(text):
            self.assertTrue(
                (RISK_REFS / name).is_file(),
                f"m2-project-risk-report/SKILL.md references references/{name}, which does not exist",
            )


class PresaleUpsellSituationalTests(unittest.TestCase):
    """presale-upsell-rules.md must not be an unconditional Required Start
    read in either consuming skill - it may appear in a numbered "N. Read
    ..." step only when that step also carries conditional language."""

    PATTERN = re.compile(r"presale-upsell-rules\.md")

    def test_plan_skill_read_is_conditional(self):
        text = (SKILLS_DIR / "m2-project-development-plan" / "SKILL.md").read_text(encoding="utf-8")
        self.assertFalse(
            _mandates_unconditional_situational_read(text, self.PATTERN),
            "m2-project-development-plan/SKILL.md reads presale-upsell-rules.md unconditionally",
        )

    def test_traffic_light_skill_read_is_conditional(self):
        text = (SKILLS_DIR / "m2-department-traffic-light" / "SKILL.md").read_text(encoding="utf-8")
        self.assertFalse(
            _mandates_unconditional_situational_read(text, self.PATTERN),
            "m2-department-traffic-light/SKILL.md reads presale-upsell-rules.md unconditionally",
        )

    def test_detector_catches_same_line_unconditional_read(self):
        bad_shape = (
            "## Required Start\n\n"
            "1. Read `references/plan-schema.md` and "
            "`../qa-management-roles/references/presale-upsell-rules.md`.\n"
            "2. Identify the target project.\n"
        )
        self.assertTrue(
            _mandates_unconditional_situational_read(bad_shape, self.PATTERN),
            "detector failed to catch a same-line unconditional read",
        )

    def test_detector_catches_continuation_line_unconditional_read(self):
        bad_shape = (
            "## Required Start\n\n"
            "1. Read `references/plan-schema.md` and\n"
            "   `../qa-management-roles/references/presale-upsell-rules.md`.\n"
            "2. Identify the target project.\n"
        )
        self.assertTrue(
            _mandates_unconditional_situational_read(bad_shape, self.PATTERN),
            "detector failed to catch a continuation-line unconditional read",
        )

    def test_detector_passes_current_conditional_wording(self):
        plan_shape = (
            "## Required Start\n\n"
            "1. Read `references/plan-schema.md`.\n"
            "4. Read `../qa-management-roles/references/presale-upsell-rules.md` too\n"
            "   when filling or changing the Возможности расширения (Upsell)\n"
            "   section - not needed for the rest of the plan.\n"
        )
        self.assertFalse(
            _mandates_unconditional_situational_read(plan_shape, self.PATTERN),
            "detector false-positived on the current conditional plan wording",
        )

        traffic_light_shape = (
            "## Required Start\n\n"
            "2. Read `../qa-management-roles/references/presale-upsell-rules.md`'s Rule\n"
            "   too when filling or changing `Upsale opportunity`/`Upsale comment` for\n"
            "   any row (see Workflow step 6) - not needed for the rest of the tracker.\n"
        )
        self.assertFalse(
            _mandates_unconditional_situational_read(traffic_light_shape, self.PATTERN),
            "detector false-positived on the current conditional traffic-light wording",
        )

    def test_presale_upsell_rules_not_split(self):
        """The audit found no internal duplication and no clean subset
        split worth the added abstraction - it stays one file."""
        shared_split_dir = SKILLS_DIR / "qa-management-roles" / "references" / "presale-upsell"
        self.assertFalse(shared_split_dir.exists())
        self.assertTrue(
            (SKILLS_DIR / "qa-management-roles" / "references" / "presale-upsell-rules.md").is_file()
        )


class KeyAnchorsPresentInOwningModuleTests(unittest.TestCase):
    def test_plan_section_skeleton_anchor(self):
        text = (PLAN_REFS / "plan-schema.md").read_text(encoding="utf-8")
        self.assertIn("## Section Skeleton", text)
        for item in (
            "Текущее состояние",
            "**План**",
            "Открытые вопросы",
            "Риски проекта",
            "Источники",
        ):
            self.assertIn(item, text)

    def test_plan_upsell_section_pointer_anchor(self):
        text = (PLAN_REFS / "plan-schema.md").read_text(encoding="utf-8")
        self.assertIn("Возможности расширения (Upsell)", text)
        self.assertIn("presale-upsell-rules.md", text)

    def test_plan_versioning_output_anchor(self):
        text = (PLAN_REFS / "plan-schema.md").read_text(encoding="utf-8")
        self.assertIn("## Versioning", text)
        self.assertIn("Update the living `project_development_plan` Doc in place", text)

    def test_risk_schema_dimensions_anchor(self):
        text = (RISK_REFS / "risk-schema.md").read_text(encoding="utf-8")
        for column in (
            "Общий уровень риска",
            "Риск delivery",
            "Риск QA process",
            "Риск staffing / continuity",
            "Риск communication / client",
        ):
            self.assertIn(column, text)

    def test_risk_action_plan_owner_review_anchor(self):
        text = (RISK_REFS / "risk-schema.md").read_text(encoding="utf-8")
        self.assertIn("План действий", text)
        self.assertIn("Owner", text)
        self.assertIn("Следующий review", text)

    def test_risk_evidence_confidence_anchor(self):
        text = (RISK_REFS / "risk-evidence-rules.md").read_text(encoding="utf-8")
        self.assertIn(
            "Name the feedback path when it affects confidence: direct client, intermediary, DC/QA Lead, team, or employee self-report",
            text,
        )

    def test_risk_versioning_output_anchor(self):
        text = (RISK_REFS / "risk-schema.md").read_text(encoding="utf-8")
        self.assertIn("## Versioning", text)
        self.assertIn("One row per project, always", text)
        self.assertNotIn("_vN", text)


if __name__ == "__main__":
    unittest.main()
