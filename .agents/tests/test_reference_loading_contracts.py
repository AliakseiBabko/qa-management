"""Focused tests for the Phase 5A google-workspace-rules.md split.

The 46 KB monolith was replaced with a thin routing index
(`google-workspace-rules.md`) plus nine physically separated, task-scoped
modules under `google-workspace/`. `ORIGINAL_MONOLITH_BYTES` re-anchors to
the current combined size whenever a legitimate rule addition pushes past
the preservation band below (most recently 2026-07-28, for the
conversational-processing closeout rule added to operational-registries.md)
- the band's job is catching accidental content loss/duplication on an
edit, not capping the docs' total size forever. These tests guard the two
things a future edit could silently break:

1. the loading-contract shape itself - the index stays thin, every module
   it lists exists and is titled/scoped/size-bounded, and no consuming
   skill mandates a whole-monolith or whole-module-set read;
2. the content-preservation/ownership shape - each original semantic
   section still has exactly one canonical module owner, source_type
   documentation lives in operational-registries.md, and validate_repo.py
   checks that module directly.

Uses concise semantic anchors, never a large copy of module content.

Run:  python -m unittest discover -s .agents/tests
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ROLES_DIR = REPO_ROOT / ".agents" / "skills" / "qa-management-roles"
INDEX = ROLES_DIR / "references" / "google-workspace-rules.md"
MODULE_DIR = ROLES_DIR / "references" / "google-workspace"
SKILLS_DIR = REPO_ROOT / ".agents" / "skills"

SCRIPTS = REPO_ROOT / ".agents" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import validate_repo  # noqa: E402

EXPECTED_MODULES = [
    "workspace-basics.md",
    "m1-layout.md",
    "m2-layout.md",
    "people-registry.md",
    "operational-registries.md",
    "artifact-conventions.md",
    "api-sharing-editing.md",
    "search-source-extraction.md",
    "pipeline-architecture.md",
]

ORIGINAL_MONOLITH_BYTES = 53829  # re-anchored 2026-07-28, see module docstring


def _all_skill_md_texts() -> dict[Path, str]:
    return {p: p.read_text(encoding="utf-8") for p in SKILLS_DIR.glob("*/SKILL.md")}


def _mandates_reading_thin_index(text: str, pattern: re.Pattern) -> bool:
    """A Required Start "N. Read ..." step can span a continuation bullet
    on the following indented line(s) - e.g.:

        2. Read the relevant reference:
           - `references/google-workspace-rules.md`

    The thin index must not appear on the numbered line itself, nor on any
    indented continuation line directly under it, up until a blank line,
    a new numbered step, or unindented text ends the step."""
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


class ThinIndexTests(unittest.TestCase):
    def test_index_is_at_most_4kib(self):
        size = INDEX.stat().st_size
        self.assertLessEqual(size, 4 * 1024, f"index is {size} bytes, over the 4 KiB target")

    def test_index_lists_every_module_and_instructs_selective_loading(self):
        text = INDEX.read_text(encoding="utf-8")
        for name in EXPECTED_MODULES:
            self.assertIn(name, text, f"index does not list {name}")
        normalized = " ".join(text.split())
        self.assertIn("Load only", normalized)

    def test_index_carries_no_normative_rule_prose(self):
        """A routing index describes modules; it must not restate a rule
        like the em-dash prohibition or the Sharing Safety folder rules."""
        text = INDEX.read_text(encoding="utf-8")
        for leaked_rule in (
            "em dash",
            "drive.file",
            "appNotAuthorizedToFile",
            "Наименьший вклад",
        ):
            self.assertNotIn(leaked_rule, text)


class ModuleShapeTests(unittest.TestCase):
    def test_every_listed_module_exists(self):
        for name in EXPECTED_MODULES:
            self.assertTrue((MODULE_DIR / name).is_file(), f"missing module {name}")

    def test_no_unlisted_module_files_exist(self):
        actual = {p.name for p in MODULE_DIR.glob("*.md")}
        self.assertEqual(actual, set(EXPECTED_MODULES))

    def test_every_module_has_a_title_and_scope_statement(self):
        for name in EXPECTED_MODULES:
            text = (MODULE_DIR / name).read_text(encoding="utf-8")
            lines = text.splitlines()
            self.assertTrue(lines[0].startswith("# "), f"{name} has no H1 title")
            head = " ".join(lines[:6])
            self.assertIn("Scope:", head, f"{name} has no scope statement near the top")

    def test_every_module_is_at_most_16kib(self):
        for name in EXPECTED_MODULES:
            size = (MODULE_DIR / name).stat().st_size
            self.assertLessEqual(size, 16 * 1024, f"{name} is {size} bytes, over the 16 KiB hard cap")

    def test_aggregate_size_within_preservation_band(self):
        total = INDEX.stat().st_size + sum(
            (MODULE_DIR / n).stat().st_size for n in EXPECTED_MODULES
        )
        low = ORIGINAL_MONOLITH_BYTES * 0.95
        high = ORIGINAL_MONOLITH_BYTES * 1.10
        self.assertTrue(
            low <= total <= high,
            f"combined index+modules is {total} bytes, outside the "
            f"{low:.0f}-{high:.0f} preservation band around the original "
            f"{ORIGINAL_MONOLITH_BYTES} bytes",
        )


class SectionOwnershipTests(unittest.TestCase):
    """Each original top-level semantic section has exactly one owner."""

    OWNERSHIP = {
        "workspace-basics.md": ["Canonical Workspace", "Output Preference", "Folder Mapping"],
        "m1-layout.md": ["M1 Person-Based Layout"],
        "m2-layout.md": ["M2 Project-Based Layout"],
        "people-registry.md": ["`_people_registry`", "Person Card Intake", "HRM Worker-Record Card"],
        "operational-registries.md": [
            "`_skill_invocations`", "`_closure_outcomes`", "`_intake_queue`",
            "Canonical `source_type` List",
        ],
        "artifact-conventions.md": [
            "Naming And Versioning", "Sheet Rules", "Docs Rules", "Language Rules",
        ],
        "api-sharing-editing.md": ["API Safety", "Sharing Safety", "Docs API Editing"],
        "search-source-extraction.md": ["Search Strategy", "Source Extraction"],
        "pipeline-architecture.md": ["Pipeline Architecture"],
    }

    def test_each_heading_owned_by_exactly_one_module(self):
        """Owned = appears as an actual Markdown heading line, not just any
        cross-reference mention (a module is allowed to *name* another
        module's heading in a "see also" pointer)."""
        heading_lines = {
            n: [
                line.lstrip("#").strip()
                for line in (MODULE_DIR / n).read_text(encoding="utf-8").splitlines()
                if line.startswith("#")
            ]
            for n in EXPECTED_MODULES
        }
        all_headings = set()
        for headings in self.OWNERSHIP.values():
            all_headings.update(headings)
        for heading in all_headings:
            owners = [
                n for n, lines in heading_lines.items()
                if any(heading in line for line in lines)
            ]
            self.assertEqual(
                len(owners), 1,
                f"heading {heading!r} is an actual heading in {owners}, expected exactly one owner",
            )

    def test_ownership_map_matches_declared_module(self):
        for module, headings in self.OWNERSHIP.items():
            text = (MODULE_DIR / module).read_text(encoding="utf-8")
            for heading in headings:
                self.assertIn(heading, text, f"{module} missing expected heading {heading!r}")


class NoMandatoryWholeFileReadTests(unittest.TestCase):
    """No skill may mandate reading the thin index, or every module."""

    def test_no_skill_mandates_reading_the_thin_index(self):
        pattern = re.compile(r"references/google-workspace-rules\.md")
        for path, text in _all_skill_md_texts().items():
            if _mandates_reading_thin_index(text, pattern):
                self.fail(f"{path} has a Required-Start mandatory read of the thin index")

    def test_detector_catches_continuation_line_regression_fixture(self):
        """Regression fixture mirroring the qa-management-roles/SKILL.md
        shape found for m2-role-rules.md: the thin-index path sat on an
        indented bullet under a numbered "Read" step, not on the numbered
        line itself. A pattern match scoped to only the numbered line
        would have missed this."""
        pattern = re.compile(r"references/google-workspace-rules\.md")
        old_shape = (
            "## Required Start\n\n"
            "1. Identify the workspace area in scope.\n"
            "2. Read the relevant reference:\n"
            "   - `references/google-workspace-rules.md`\n"
            "3. Apply the layout rules before writing outputs.\n"
        )
        self.assertTrue(
            _mandates_reading_thin_index(old_shape, pattern),
            "detector failed to catch the continuation-line shape",
        )

        new_shape = (
            "## Required Start\n\n"
            "1. Identify the workspace area in scope.\n"
            "2. Read the relevant reference:\n"
            "   - `references/google-workspace/workspace-basics.md`\n"
            "3. Apply the layout rules before writing outputs.\n"
        )
        self.assertFalse(
            _mandates_reading_thin_index(new_shape, pattern),
            "detector false-positived on the corrected module-scoped shape",
        )

        prose_only = (
            "## Guardrails\n\n"
            "- see `google-workspace-rules.md` or a similar shared "
            "reference for more.\n"
        )
        self.assertFalse(
            _mandates_reading_thin_index(prose_only, pattern),
            "detector should not flag a prose-only see-also mention",
        )

    def test_no_skill_requires_every_module(self):
        pattern = re.compile(r"google-workspace/([a-z0-9-]+)\.md")
        for path, text in _all_skill_md_texts().items():
            found = set(pattern.findall(text))
            self.assertLess(
                len(found), len(EXPECTED_MODULES),
                f"{path} references all {len(EXPECTED_MODULES)} modules - "
                "should load only what it needs",
            )

    def test_every_referenced_module_path_exists(self):
        pattern = re.compile(r"google-workspace/([a-z0-9-]+\.md)")
        for path, text in _all_skill_md_texts().items():
            for name in pattern.findall(text):
                self.assertTrue(
                    (MODULE_DIR / name).is_file(),
                    f"{path} references google-workspace/{name}, which does not exist",
                )

    def test_at_least_some_skills_reference_modules(self):
        """Sanity check that the retargeting actually happened."""
        pattern = re.compile(r"google-workspace/[a-z0-9-]+\.md")
        matching = [p for p, text in _all_skill_md_texts().items() if pattern.search(text)]
        self.assertGreaterEqual(len(matching), 15)


class SourceTypeCanonicalOwnerTests(unittest.TestCase):
    def test_source_type_list_lives_in_operational_registries(self):
        text = (MODULE_DIR / "operational-registries.md").read_text(encoding="utf-8")
        for stype in ("strategy_chat", "meeting_transcript", "m2_conversation", "retro"):
            self.assertIn(f"`{stype}`", text)

    def test_source_type_list_not_duplicated_in_thin_index(self):
        text = INDEX.read_text(encoding="utf-8")
        self.assertNotIn("strategy_chat", text)
        self.assertNotIn("meeting_transcript", text)

    def test_validate_repo_rules_constant_points_at_operational_registries(self):
        self.assertEqual(validate_repo.RULES.name, "operational-registries.md")
        self.assertEqual(validate_repo.RULES.parent.name, "google-workspace")

    def test_validate_repo_check_source_types_documented_passes_for_real_repo(self):
        source_types = validate_repo.load_source_types()
        validate_repo.failures.clear()
        validate_repo.warnings.clear()
        validate_repo.check_source_types_documented(source_types)
        self.assertEqual(validate_repo.failures, [])

    def test_validate_repo_check_source_types_documented_fails_on_missing_type(self):
        validate_repo.failures.clear()
        validate_repo.warnings.clear()
        validate_repo.check_source_types_documented({"definitely_not_a_real_source_type"})
        self.assertTrue(
            any("operational-registries.md" in f for f in validate_repo.failures),
            validate_repo.failures,
        )


class KeyAnchorsPresentInOwningModuleTests(unittest.TestCase):
    """Spot-check load-bearing rules by exact owning module, not just
    "somewhere in the split" - a misplaced rule would still pass a looser
    "present anywhere" check."""

    def _text(self, name: str) -> str:
        return (MODULE_DIR / name).read_text(encoding="utf-8")

    def test_m1_m2_visibility_anchors(self):
        m1 = self._text("m1-layout.md")
        self.assertIn("10_M1_People_Management", m1)
        m2 = self._text("m2-layout.md")
        self.assertIn("private", m2)
        self.assertIn("shared", m2)

    def test_people_registry_anchor(self):
        text = self._text("people-registry.md")
        self.assertIn("05_People_Management", text)
        self.assertIn("Дата трудоустройства", text)

    def test_naming_convention_anchor(self):
        text = self._text("artifact-conventions.md")
        self.assertIn("_vN", text)

    def test_api_safety_anchor(self):
        text = self._text("api-sharing-editing.md")
        self.assertIn("drive.file", text)
        self.assertIn("Never share the project root", text)

    def test_pipeline_boundary_anchor(self):
        text = self._text("pipeline-architecture.md")
        self.assertIn("no automated observer/dispatcher", text)

    def test_m2_layout_path_literals_are_well_formed(self):
        """A prior pass carried forward concatenated path typos
        (e.g. `privateproject_risk`) from the original monolith. These
        must read as explicit `private\\...`/`team_shared\\...` paths."""
        text = self._text("m2-layout.md")
        good = [
            r"private\project_risk",
            r"private\process_checklist",
            r"private\project_development_plan",
            r"private\project_metrics",
            r"team_shared\qa_process_metrics",
            r"private\evidence_log",
        ]
        bad = [
            "privateproject_risk",
            "privateprocess_checklist",
            "privateproject_development_plan",
            "privateproject_metrics",
            "team_sharedqa_process_metrics",
            "privateevidence_log",
        ]
        for g in good:
            self.assertIn(g, text, f"expected explicit path {g!r} not found")
        for b in bad:
            self.assertNotIn(b, text, f"concatenated path typo {b!r} still present")


class ApiSharingEditingCoverageTests(unittest.TestCase):
    """Any skill that writes a final Google Sheet, Google Doc, Drive
    folder/artifact, registry row, evidence_log row, _skill_invocations
    row, action_items row, m2_input content, Project Knowledge artifact, or
    external Google Sheet must load api-sharing-editing.md, unless it is
    truly read-only/chat-only and never saves by default. Exceptions are
    named here, each with a one-line reason - silence is not an allowlist,
    and writing through a pipeline_common helper (add_questions/
    add_answer/log_skill_invocation/etc.) is *not* a valid reason, since
    the helper still performs the same Drive write this module covers."""

    # Reason substrings that are never an acceptable exemption on their own -
    # "it's helper-mediated" does not change that a Drive write happens.
    BANNED_REASON_SUBSTRINGS = (
        "pipeline_common helper", "helper-mediated", "via a helper",
        "routes through pipeline_common",
    )

    # skill -> reason it is exempt from requiring api-sharing-editing.md
    ALLOWLIST = {
        "qa-retro": "edits this repo's own skills/references, not a Drive "
            "artifact - explicitly out of scope per its own guardrails",
        "repo-maintenance": "a checklist skill with no Required Start "
            "section and no Drive output of its own",
    }

    # Skills with a genuine Required-Start google-workspace module list that
    # writes a final Drive artifact (Sheet, Doc, registry row, evidence log,
    # _skill_invocations row, action_items row, m2_input content, Project
    # Knowledge artifact, or an external/foreign Google Sheet).
    FINAL_OUTPUT_SKILLS = [
        "m1-individual-development-plan", "m1-monthly-report",
        "m1-people-1to1-file", "m1-people-risk-report", "m1-timeline",
        "m2-admin-note-intake", "m2-individual-development-plan",
        "m2-individual-qa-metrics-report", "m2-monthly-report",
        "m2-people-1to1-file", "m2-project-development-plan",
        "m2-project-process-checklist", "m2-project-qa-metrics-report",
        "m2-project-risk-report", "m2-project-status-report",
        "m2-strategy-chat-analysis", "m2-timeline",
        "m2-status-meeting-intake", "m2-1to1-apply",
        "project-knowledge-intake", "m-self-review", "salary-review-prep",
        "m2-department-traffic-light",
    ]

    def test_every_final_output_skill_loads_api_sharing_editing(self):
        for skill in self.FINAL_OUTPUT_SKILLS:
            self.assertNotIn(
                skill, self.ALLOWLIST,
                f"{skill} is both in FINAL_OUTPUT_SKILLS and ALLOWLIST - pick one",
            )
            text = (SKILLS_DIR / skill / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn(
                "google-workspace/api-sharing-editing.md", text,
                f"{skill} writes a final Drive artifact but does not load "
                "api-sharing-editing.md",
            )

    def test_allowlisted_skills_have_a_reason(self):
        for skill, reason in self.ALLOWLIST.items():
            self.assertTrue((SKILLS_DIR / skill / "SKILL.md").is_file())
            self.assertTrue(reason.strip())

    def test_allowlist_reasons_do_not_cite_helper_mediation(self):
        """A write performed through pipeline_common is still a write -
        this is exactly the reasoning this correction pass rejected for
        m2-status-meeting-intake, so no future entry may reuse it."""
        for skill, reason in self.ALLOWLIST.items():
            lowered = reason.lower()
            for banned in self.BANNED_REASON_SUBSTRINGS:
                self.assertNotIn(
                    banned, lowered,
                    f"{skill}'s allowlist reason cites helper-mediation "
                    f"({banned!r}), which is not a valid exemption",
                )


class DocumentGraphSourceTypeOwnerTests(unittest.TestCase):
    def test_document_graph_names_operational_registries_as_owner(self):
        graph_text = (REPO_ROOT / ".agents" / "document_graph.yaml").read_text(encoding="utf-8")
        self.assertIn("operational-registries.md", graph_text)
        self.assertNotIn("google-workspace-rules.md", graph_text)


if __name__ == "__main__":
    unittest.main()
