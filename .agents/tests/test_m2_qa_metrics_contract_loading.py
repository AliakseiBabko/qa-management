"""Focused tests for the Phase 5C-A split of the two M2 QA metrics
document contracts:

- `m2-project-qa-metrics-report/references/document-contract.md` (19,587
  bytes) -> a thin index plus `project-metrics-schema.md` and
  `qa-process-metrics-schema.md` (mandatory every invocation) and
  `extended-metrics-catalog.md` (situational - only when adding an
  Extended-tier qa_process_metrics row or extracting a raw source doc).
- `m2-individual-qa-metrics-report/references/document-contract.md`
  (14,581 bytes) -> a thin index plus `individual-metrics-schema.md`
  (mandatory) and `internal-variant.md` (situational - only when writing
  the private individual_metrics_internal Sheet).

The one genuinely duplicated concept found in the audit - the Automation
Metric Layering rule, near-identically restated in both original
contracts - was not given a new shared directory. It already has a
canonical home in `qa-management-roles/references/m2-role/
m2-metrics-attribution.md` (Phase 5B), so both split contracts now point
there instead of restating the general rule, keeping only their own
schema-specific framing.

Run:  python -m unittest discover -s .agents/tests
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = REPO_ROOT / ".agents" / "skills"

PROJECT_REFS = SKILLS_DIR / "m2-project-qa-metrics-report" / "references"
INDIVIDUAL_REFS = SKILLS_DIR / "m2-individual-qa-metrics-report" / "references"

PROJECT_INDEX = PROJECT_REFS / "document-contract.md"
INDIVIDUAL_INDEX = INDIVIDUAL_REFS / "document-contract.md"

PROJECT_MODULES = [
    "project-metrics-schema.md",
    "qa-process-metrics-schema.md",
    "extended-metrics-catalog.md",
]
INDIVIDUAL_MODULES = [
    "individual-metrics-schema.md",
    "internal-variant.md",
]

PROJECT_ORIGINAL_BYTES = 19587
INDIVIDUAL_ORIGINAL_BYTES = 14581


def _all_skill_md_texts() -> dict[Path, str]:
    return {p: p.read_text(encoding="utf-8") for p in SKILLS_DIR.glob("*/SKILL.md")}


def _mandates_reading(text: str, pattern: re.Pattern) -> bool:
    """Same continuation-line-aware detector used by the Phase 5A/5B
    loading-contract tests: a Required Start "N. Read ..." step can span
    an indented continuation bullet on the following line(s)."""
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
    """Split a SKILL.md's Required Start numbered "N. Read ..." steps into
    whole-step strings (the numbered line plus every indented continuation
    line under it, joined), so a situational module's conditioning
    language can be checked against the *whole step it lives in*, not
    just the single line it happens to appear on."""
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


_CONDITIONAL_LANGUAGE = re.compile(r"\b(when|if)\b", re.IGNORECASE)


def _mandates_unconditional_situational_read(text: str, module_pattern: re.Pattern) -> bool:
    """A situational module (extended-metrics-catalog.md,
    internal-variant.md) may appear inside a Required Start "N. Read ..."
    step - same-line or on a continuation line - but only when that whole
    step also carries conditional language ("when", "if", "only when",
    "too when", "too if", ...). Without a condition anywhere in the step,
    the module reads as an unconditional mandatory read, same as any
    other path named in that step."""
    for step in _required_start_read_steps(text):
        if module_pattern.search(step) and not _CONDITIONAL_LANGUAGE.search(step):
            return True
    return False


class ModuleShapeTests(unittest.TestCase):
    def test_every_project_module_exists(self):
        for name in PROJECT_MODULES:
            self.assertTrue((PROJECT_REFS / name).is_file(), f"missing module {name}")

    def test_every_individual_module_exists(self):
        for name in INDIVIDUAL_MODULES:
            self.assertTrue((INDIVIDUAL_REFS / name).is_file(), f"missing module {name}")

    def test_every_module_has_a_title_and_scope_statement(self):
        for refs_dir, modules in ((PROJECT_REFS, PROJECT_MODULES), (INDIVIDUAL_REFS, INDIVIDUAL_MODULES)):
            for name in modules:
                text = (refs_dir / name).read_text(encoding="utf-8")
                lines = text.splitlines()
                self.assertTrue(lines[0].startswith("# "), f"{name} has no H1 title")
                head = " ".join(lines[:6])
                self.assertIn("Scope:", head, f"{name} has no scope statement near the top")

    def test_every_module_is_at_most_16kib(self):
        for refs_dir, modules in ((PROJECT_REFS, PROJECT_MODULES), (INDIVIDUAL_REFS, INDIVIDUAL_MODULES)):
            for name in modules:
                size = (refs_dir / name).stat().st_size
                self.assertLessEqual(size, 16 * 1024, f"{name} is {size} bytes, over the 16 KiB hard cap")

    def test_thin_indexes_are_at_most_4kib(self):
        for index in (PROJECT_INDEX, INDIVIDUAL_INDEX):
            size = index.stat().st_size
            self.assertLessEqual(size, 4 * 1024, f"{index} is {size} bytes, over the 4 KiB target")

    def test_project_aggregate_size_within_preservation_band(self):
        total = PROJECT_INDEX.stat().st_size + sum((PROJECT_REFS / n).stat().st_size for n in PROJECT_MODULES)
        low = PROJECT_ORIGINAL_BYTES * 0.95
        high = PROJECT_ORIGINAL_BYTES * 1.10
        self.assertTrue(
            low <= total <= high,
            f"project contract split is {total} bytes, outside the "
            f"{low:.0f}-{high:.0f} band around the original {PROJECT_ORIGINAL_BYTES}",
        )

    def test_individual_aggregate_size_within_preservation_band(self):
        total = INDIVIDUAL_INDEX.stat().st_size + sum((INDIVIDUAL_REFS / n).stat().st_size for n in INDIVIDUAL_MODULES)
        low = INDIVIDUAL_ORIGINAL_BYTES * 0.95
        high = INDIVIDUAL_ORIGINAL_BYTES * 1.10
        self.assertTrue(
            low <= total <= high,
            f"individual contract split is {total} bytes, outside the "
            f"{low:.0f}-{high:.0f} band around the original {INDIVIDUAL_ORIGINAL_BYTES}",
        )


class NoMandatoryWholeFileReadTests(unittest.TestCase):
    def test_no_skill_mandates_reading_project_thin_index(self):
        pattern = re.compile(r"m2-project-qa-metrics-report/references/document-contract\.md|references/document-contract\.md")
        text = (SKILLS_DIR / "m2-project-qa-metrics-report" / "SKILL.md").read_text(encoding="utf-8")
        self.assertFalse(
            _mandates_reading(text, pattern),
            "m2-project-qa-metrics-report/SKILL.md still has a Required-Start "
            "mandatory read of the thin index",
        )

    def test_no_skill_mandates_reading_individual_thin_index(self):
        pattern = re.compile(r"references/document-contract\.md")
        text = (SKILLS_DIR / "m2-individual-qa-metrics-report" / "SKILL.md").read_text(encoding="utf-8")
        self.assertFalse(
            _mandates_reading(text, pattern),
            "m2-individual-qa-metrics-report/SKILL.md still has a Required-Start "
            "mandatory read of the thin index",
        )

    def test_extended_catalog_not_read_unconditionally(self):
        """extended-metrics-catalog.md is situational - it may appear
        inside a Required Start "N. Read ..." step, same-line or on a
        continuation line, only when that step also carries conditional
        language. A same-line or continuation-line read with no condition
        anywhere in the step reads as unconditionally mandatory, the same
        as the two schema modules."""
        pattern = re.compile(r"references/extended-metrics-catalog\.md")
        text = (SKILLS_DIR / "m2-project-qa-metrics-report" / "SKILL.md").read_text(encoding="utf-8")
        self.assertFalse(
            _mandates_unconditional_situational_read(text, pattern),
            "extended-metrics-catalog.md is read unconditionally, not situationally",
        )

    def test_internal_variant_not_read_unconditionally(self):
        pattern = re.compile(r"references/internal-variant\.md")
        text = (SKILLS_DIR / "m2-individual-qa-metrics-report" / "SKILL.md").read_text(encoding="utf-8")
        self.assertFalse(
            _mandates_unconditional_situational_read(text, pattern),
            "internal-variant.md is read unconditionally, not situationally",
        )

    def test_detector_catches_same_line_unconditional_multi_path_read(self):
        """Regression fixture: all three project modules named on one
        numbered Read line, with no conditional language anywhere in the
        step - the situational module reads as unconditionally mandatory."""
        pattern = re.compile(r"references/extended-metrics-catalog\.md")
        bad_shape = (
            "## Required Start\n\n"
            "1. Read `references/project-metrics-schema.md`, "
            "`references/qa-process-metrics-schema.md`, and "
            "`references/extended-metrics-catalog.md`.\n"
            "2. Identify the target project and reporting period.\n"
        )
        self.assertTrue(
            _mandates_unconditional_situational_read(bad_shape, pattern),
            "detector failed to catch a same-line unconditional multi-path read",
        )

    def test_detector_catches_continuation_line_unconditional_read(self):
        """Regression fixture: the situational module named on an indented
        continuation line under the same numbered step, still with no
        conditional language anywhere in that step."""
        pattern = re.compile(r"references/extended-metrics-catalog\.md")
        bad_shape = (
            "## Required Start\n\n"
            "1. Read `references/project-metrics-schema.md` and\n"
            "   `references/qa-process-metrics-schema.md` and\n"
            "   `references/extended-metrics-catalog.md`.\n"
            "2. Identify the target project and reporting period.\n"
        )
        self.assertTrue(
            _mandates_unconditional_situational_read(bad_shape, pattern),
            "detector failed to catch a continuation-line unconditional read",
        )

    def test_detector_passes_current_conditional_wording(self):
        """Regression fixture: the actual current wording in both
        SKILL.md files - the situational module is named on a
        continuation line, gated by "too when"/"too if" later in the
        same step."""
        project_pattern = re.compile(r"references/extended-metrics-catalog\.md")
        project_shape = (
            "## Required Start\n\n"
            "1. Read `references/project-metrics-schema.md` and\n"
            "   `references/qa-process-metrics-schema.md`. Read\n"
            "   `references/extended-metrics-catalog.md` too when adding an\n"
            "   Extended-tier `qa_process_metrics` row or extracting a raw "
            "DOCX/XLSX\n"
            "   source (steps 5-6 below).\n"
            "2. Identify the target project and reporting period.\n"
        )
        self.assertFalse(
            _mandates_unconditional_situational_read(project_shape, project_pattern),
            "detector false-positived on the current conditional project wording",
        )

        individual_pattern = re.compile(r"references/internal-variant\.md")
        individual_shape = (
            "## Required Start\n\n"
            "1. Read `references/individual-metrics-schema.md`. Read\n"
            "   `references/internal-variant.md` too if also writing or "
            "updating the\n"
            "   private `individual_metrics_internal` Sheet.\n"
            "2. Identify the target person and project scope.\n"
        )
        self.assertFalse(
            _mandates_unconditional_situational_read(individual_shape, individual_pattern),
            "detector false-positived on the current conditional individual wording",
        )

    def test_detector_allows_prose_only_mention_outside_required_start(self):
        """A situational module named in prose outside any numbered Read
        step (e.g. in Guardrails or Workflow) is not a Required Start read
        at all, conditional or not, and must not be flagged."""
        pattern = re.compile(r"references/internal-variant\.md")
        prose_only = (
            "## Guardrails\n\n"
            "- See `references/internal-variant.md` for the private Sheet's "
            "schema.\n"
        )
        self.assertFalse(
            _mandates_unconditional_situational_read(prose_only, pattern),
            "detector should not flag a prose-only mention outside Required Start",
        )

    def test_every_referenced_project_module_path_exists(self):
        pattern = re.compile(r"references/([a-z0-9-]+\.md)")
        text = (SKILLS_DIR / "m2-project-qa-metrics-report" / "SKILL.md").read_text(encoding="utf-8")
        for name in pattern.findall(text):
            self.assertTrue(
                (PROJECT_REFS / name).is_file(),
                f"m2-project-qa-metrics-report/SKILL.md references references/{name}, which does not exist",
            )

    def test_every_referenced_individual_module_path_exists(self):
        pattern = re.compile(r"references/([a-z0-9-]+\.md)")
        text = (SKILLS_DIR / "m2-individual-qa-metrics-report" / "SKILL.md").read_text(encoding="utf-8")
        for name in pattern.findall(text):
            self.assertTrue(
                (INDIVIDUAL_REFS / name).is_file(),
                f"m2-individual-qa-metrics-report/SKILL.md references references/{name}, which does not exist",
            )


class NoDuplicatedOwnershipTests(unittest.TestCase):
    """The Automation Metric Layering rule has exactly one canonical
    owner (m2-role/m2-metrics-attribution.md) - neither split contract
    may restate the general project-vs-individual rule itself, only
    point to it plus their own schema-specific framing."""

    GENERAL_RULE_FRAGMENTS = (
        "are project/team QA-process metrics, not individual metrics",
        "are project/team QA-process facts, not individual performance metrics",
    )

    def test_individual_schema_does_not_restate_general_rule(self):
        text = (INDIVIDUAL_REFS / "individual-metrics-schema.md").read_text(encoding="utf-8")
        for fragment in self.GENERAL_RULE_FRAGMENTS:
            self.assertNotIn(fragment, text)
        self.assertIn("m2-role/m2-metrics-attribution.md", text)

    def test_extended_catalog_does_not_restate_general_rule(self):
        text = (PROJECT_REFS / "extended-metrics-catalog.md").read_text(encoding="utf-8")
        for fragment in self.GENERAL_RULE_FRAGMENTS:
            self.assertNotIn(fragment, text)
        self.assertIn("m2-role/m2-metrics-attribution.md", text)

    def test_no_new_shared_metrics_contract_directory_was_created(self):
        """The audit found only one genuinely duplicated concept, and it
        already had a canonical home from Phase 5B - creating a new
        qa-management-roles/references/m2-metrics-contract/ directory
        would have been an unwarranted extra abstraction."""
        shared_dir = SKILLS_DIR / "qa-management-roles" / "references" / "m2-metrics-contract"
        self.assertFalse(shared_dir.exists())


class KeyAnchorsPresentInOwningModuleTests(unittest.TestCase):
    def test_project_metrics_schema_anchor(self):
        text = (PROJECT_REFS / "project-metrics-schema.md").read_text(encoding="utf-8")
        self.assertIn("Schema — `project_metrics`", text)
        self.assertIn("Вклад в проект: <Имя>", text)

    def test_qa_process_metrics_schema_anchor(self):
        text = (PROJECT_REFS / "qa-process-metrics-schema.md").read_text(encoding="utf-8")
        self.assertIn("Schema — `qa_process_metrics`", text)
        self.assertIn("Core (6 metrics)", text)

    def test_individual_metrics_schema_anchor(self):
        text = (INDIVIDUAL_REFS / "individual-metrics-schema.md").read_text(encoding="utf-8")
        self.assertIn("## Schema", text)
        self.assertIn("Дата", text)

    def test_internal_individual_metrics_anchor(self):
        text = (INDIVIDUAL_REFS / "internal-variant.md").read_text(encoding="utf-8")
        self.assertIn("individual_metrics_internal", text)
        self.assertIn("Сторона", text)

    def test_registry_project_rollup_anchor(self):
        text = (PROJECT_REFS / "project-metrics-schema.md").read_text(encoding="utf-8")
        self.assertIn("_project_registry", text)
        internal_text = (INDIVIDUAL_REFS / "internal-variant.md").read_text(encoding="utf-8")
        self.assertIn("m2-role/m2-project-rollups.md", internal_text)


if __name__ == "__main__":
    unittest.main()
