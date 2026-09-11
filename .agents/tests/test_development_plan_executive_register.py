"""Tests for the repo-maintenance pass that made `project_development_plan`
an executive-facing synthesis document (2026-09-07):

A real plan (<Project>) was reviewed and found to be a working file rather
than a finished one. It pointed the reader at internal artifacts they cannot
open (`см. action_items`, `см. evidence_log`, `30_Project_Knowledge/...`
paths, chat export filenames), narrated its own revision history in its body
("исправлено по чату X", "устаревшая характеристика заменена этим
обновлением", "нуждается в переподтверждении"), carried an `Источники`
section that told an M3 reader nothing, answered two whole sections with
"нет данных" because the client had never stated a business goal, listed
facts that belonged in the 1:1 records they came from, and carried a
`Следующий review` date earlier than its own `Обновлено` date.

The contract now says: this document is written for management above M2, for
a reader with no access to the workspace and no memory of a previous
version. Facts live upstream; the reading of them lives here. A silent
client is the normal case and is answered with an inference marked
`(гипотеза M2)` that names the signal it rests on, never with "нет данных".

Separately, that same plan had a mangled block appended to it twice, whose
paragraph breaks were literal backslash-n sequences rather than real
newlines - a caller mistake that `docs_editing.py` now refuses instead of
inserting.

Run:  python -m unittest discover -s .agents/tests
"""

from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SKILLS_DIR = REPO_ROOT / ".agents" / "skills"
SCRIPTS_DIR = REPO_ROOT / ".agents" / "scripts"
PLAN_SKILL = SKILLS_DIR / "m2-project-development-plan"

SKILL_PATH = PLAN_SKILL / "SKILL.md"
SCHEMA_PATH = PLAN_SKILL / "references" / "plan-schema.md"
NORMALIZATION_PATH = PLAN_SKILL / "references" / "plan-sources-normalization.md"
INDEX_PATH = PLAN_SKILL / "references" / "document-contract.md"
TEMPLATE_PATH = REPO_ROOT / "Templates" / "план_развития_проекта.md"

# The exact pointer shapes found in the reviewed plan. None of these may be
# reachable for a reader outside the M2 workspace, so none may appear in the
# document - the contract has to name them to forbid them.
BANNED_POINTER_SHAPES = (
    "см. action_items",
    "см. evidence_log",
    "см. m2_input",
    "30_Project_Knowledge/",
)

# The edit-history phrases the reviewed plan actually contained.
BANNED_CHANGELOG_PHRASES = (
    "исправлено по чату",
    "ранее ошибочно записано",
    "нуждается в переподтверждении",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(text: str) -> str:
    return " ".join(text.split())


class AudienceAndRegisterTests(unittest.TestCase):
    def setUp(self):
        self.text = _normalized(_read(SCHEMA_PATH))

    def test_has_audience_section(self):
        self.assertIn("## Audience And Register", self.text)

    def test_states_the_audience_is_above_m2(self):
        self.assertIn(
            "**This is a finished document written for management above M2**",
            self.text,
        )

    def test_reader_has_no_workspace_access_or_prior_version(self):
        self.assertIn(
            "a reader who has no access to the M2 workspace, has never seen a "
            "previous version",
            self.text,
        )

    def test_forbids_every_internal_pointer_shape_found_in_the_real_plan(self):
        for shape in BANNED_POINTER_SHAPES:
            self.assertIn(shape, self.text, f"contract does not name {shape!r} as banned")
        self.assertIn("No pointers to other internal artifacts", self.text)

    def test_forbids_edit_history_narration(self):
        self.assertIn("No edit-history narration", self.text)
        for phrase in BANNED_CHANGELOG_PHRASES:
            self.assertIn(phrase, self.text, f"contract does not name {phrase!r} as banned")

    def test_forbids_appended_dated_update_blocks(self):
        self.assertIn("No appended dated update blocks", self.text)

    def test_forbids_evidence_status_vocabulary_in_prose(self):
        self.assertIn("No evidence-status vocabulary in prose", self.text)


class SourcesSectionRemovedTests(unittest.TestCase):
    def test_schema_declares_the_section_prohibited(self):
        text = _normalized(_read(SCHEMA_PATH))
        self.assertIn("No `Источники` section", text)
        self.assertIn(
            "There is no `Источники` section. It was §12 until 2026-09-07 and "
            "is now prohibited outright",
            text,
        )

    def test_schema_no_longer_describes_it_as_optional(self):
        text = _normalized(_read(SCHEMA_PATH))
        self.assertNotIn("**Источники** — optional", text)

    def test_template_drops_the_section(self):
        text = _normalized(_read(TEMPLATE_PATH))
        self.assertNotIn("## 11. Источники", text)
        self.assertIn("Раздела «Источники» в этом шаблоне нет", text)

    def test_skill_forbids_writing_one(self):
        text = _normalized(_read(SKILL_PATH))
        self.assertIn("Do not write a `Источники` section", text)

    def test_routing_index_reflects_the_shorter_skeleton(self):
        text = _normalized(_read(INDEX_PATH))
        self.assertIn("11-item section skeleton", text)
        self.assertNotIn("12-item section skeleton", text)


class SilenceIsNotAnEmptySectionTests(unittest.TestCase):
    def setUp(self):
        self.text = _normalized(_read(SCHEMA_PATH))

    def test_has_the_section(self):
        self.assertIn("## Silence Is Not An Empty Section", self.text)

    def test_rejects_no_data_as_a_section_body(self):
        self.assertIn(
            'A section is **never** satisfied by "Открытый вопрос: в источниках '
            'нет данных"',
            self.text,
        )

    def test_treats_a_quiet_client_as_the_normal_case(self):
        self.assertIn(
            "that is the normal case, not a blocked one", self.text
        )

    def test_lists_indirect_signals_to_reason_from(self):
        for signal in (
            "What the client funds and staffs",
            "who they hire and where",
            "what they escalate versus quietly accept",
            "the contract or tender horizon",
            "the codebase itself",
        ):
            self.assertIn(signal, self.text)

    def test_inference_marker_reuses_existing_registry_vocabulary(self):
        self.assertIn("append `(гипотеза M2)` to the claim", self.text)
        self.assertIn(
            "the same wording `_project_registry`'s client-goal column already "
            "uses",
            self.text,
        )

    def test_inference_must_name_its_signal(self):
        self.assertIn("**Name the signal in the same sentence.**", self.text)

    def test_guards_against_overreach_too(self):
        self.assertIn("**Do not overreach either.**", self.text)
        self.assertIn(
            "a confident-sounding invented one is a worse failure", self.text
        )

    def test_unanswerable_items_become_one_line_questions(self):
        self.assertIn(
            "becomes one line in `Открытые вопросы`", self.text
        )


class SynthesisNotFactInventoryTests(unittest.TestCase):
    def setUp(self):
        self.text = _normalized(_read(SCHEMA_PATH))

    def test_has_the_section(self):
        self.assertIn("## Synthesis, Not A Fact Inventory", self.text)

    def test_places_the_document_at_the_end_of_the_pipeline(self):
        self.assertIn(
            "This document sits at the end of the pipeline, not the start",
            self.text,
        )

    def test_states_the_movability_test(self):
        self.assertIn(
            "if a sentence could be moved into a 1:1 record or a transcript "
            "summary without losing anything, it belongs there, not here",
            self.text,
        )

    def test_current_state_items_end_in_a_consequence(self):
        self.assertIn(
            "Every `Текущее состояние` item ends in a consequence for the "
            "project, not in a state",
            self.text,
        )


class SectionSkeletonTests(unittest.TestCase):
    def setUp(self):
        self.text = _normalized(_read(SCHEMA_PATH))

    def test_metadata_line_requires_a_future_review_date(self):
        self.assertIn(
            "check that `Следующий review` is later than `Обновлено`", self.text
        )

    def test_client_expectations_section_requires_an_inference_when_silent(self):
        self.assertIn(
            '"Клиент молчит" is not an acceptable body for this section',
            self.text,
        )

    def test_success_section_must_reach_a_verdict_without_client_criteria(self):
        self.assertIn(
            "the absence of a client scorecard does not excuse the section "
            "from reaching a verdict",
            self.text,
        )

    def test_no_section_may_read_no_data(self):
        self.assertIn(
            'never a section body reading "нет данных"', self.text
        )


class SkillGuardrailsTests(unittest.TestCase):
    def setUp(self):
        self.text = _normalized(_read(SKILL_PATH))

    def test_skill_frames_the_document_as_the_end_of_the_pipeline(self):
        self.assertIn(
            "It is also the **end of the pipeline, not a working file**",
            self.text,
        )

    def test_skill_points_at_the_two_new_schema_sections(self):
        self.assertIn('"Audience And Register" and "Synthesis, Not A Fact Inventory"', self.text)

    def test_skill_forbids_internal_pointers(self):
        self.assertIn("Do not point the reader at another internal artifact", self.text)

    def test_skill_forbids_revision_narration(self):
        self.assertIn(
            "Do not narrate the document's own revision history in its body",
            self.text,
        )

    def test_skill_forbids_no_data_sections(self):
        self.assertIn(
            'Do not leave a section reading "нет данных" because the client '
            "never said anything",
            self.text,
        )

    def test_skill_forbids_transcript_grade_facts(self):
        self.assertIn(
            "Do not list facts a reader could have got from a transcript",
            self.text,
        )

    def test_in_place_update_rule_bans_trailing_update_blocks(self):
        self.assertIn(
            'rather than appending a new dated copy or a trailing "Update '
            'YYYY-MM-DD" block',
            self.text,
        )

    def test_workflow_no_longer_lists_a_sources_step(self):
        self.assertIn("There is no sources section.", self.text)


class TemplateTests(unittest.TestCase):
    def setUp(self):
        self.text = _normalized(_read(TEMPLATE_PATH))

    def test_template_states_the_audience(self):
        self.assertIn(
            "**Это финальный документ для руководства выше M2**", self.text
        )

    def test_template_forbids_internal_pointers(self):
        self.assertIn("**Никаких отсылок к внутренним артефактам.**", self.text)

    def test_template_forbids_edit_history(self):
        self.assertIn("**Никакой истории правок в тексте.**", self.text)

    def test_template_requires_inference_over_no_data(self):
        self.assertIn("**Раздел не может состоять из «нет данных».**", self.text)
        self.assertIn("`(гипотеза M2)`", self.text)

    def test_template_requires_synthesis(self):
        self.assertIn("**Синтез, а не список фактов.**", self.text)

    def test_template_requires_a_future_review_date(self):
        self.assertIn(
            "`Следующий review` обязан быть позже, чем `Обновлено`", self.text
        )


class NormalizationTests(unittest.TestCase):
    def setUp(self):
        self.text = _normalized(_read(NORMALIZATION_PATH))

    def test_rejects_stopping_at_client_silence(self):
        self.assertIn('Do not stop at "the client never said."', self.text)

    def test_rejects_carrying_upstream_facts_verbatim(self):
        self.assertIn(
            "Do not carry a fact into this document just because it was "
            "recorded upstream",
            self.text,
        )

    def test_maintenance_notes_go_to_comments_or_evidence_log(self):
        self.assertIn(
            "they go in a Docs comment or `evidence_log`, never into the "
            "document's own prose",
            self.text,
        )


def _load_docs_editing():
    """Import docs_editing.py by path. It imports sibling scripts by bare
    module name, so the scripts directory has to be on sys.path first."""
    scripts = str(SCRIPTS_DIR)
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    spec = importlib.util.spec_from_file_location(
        "docs_editing", SCRIPTS_DIR / "docs_editing.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["docs_editing"] = module
    spec.loader.exec_module(module)
    return module


class LiteralNewlineGuardTests(unittest.TestCase):
    """The mangled block appended twice to the real plan had literal
    backslash-n where its paragraph breaks should have been."""

    @classmethod
    def setUpClass(cls):
        cls.module = _load_docs_editing()
        cls.tmp = tempfile.mkdtemp()

    def _write(self, name: str, content: str) -> str:
        path = os.path.join(self.tmp, name)
        Path(path).write_text(content, encoding="utf-8")
        return path

    def test_rejects_a_file_whose_breaks_are_literal_backslash_n(self):
        path = self._write("mangled.txt", "para one" + chr(92) + "npara two")
        with self.assertRaises(SystemExit) as caught:
            self.module._load_text_file(path)
        self.assertIn("literal backslash-n sequences", str(caught.exception))

    def test_accepts_real_newlines(self):
        path = self._write("clean.txt", "para one\npara two")
        self.assertEqual(self.module._load_text_file(path), "para one\npara two\n")

    def test_still_adds_the_trailing_newline(self):
        path = self._write("oneline.txt", "just one paragraph")
        self.assertEqual(self.module._load_text_file(path), "just one paragraph\n")

    def test_allows_a_backslash_n_that_is_not_the_whole_structure(self):
        """A file with real paragraph breaks may legitimately mention a
        backslash-n in its text (documentation about escaping, say)."""
        path = self._write(
            "mixed.txt", "line one mentions " + chr(92) + "n as a token\nline two\n"
        )
        result = self.module._load_text_file(path)
        self.assertIn("line two", result)


if __name__ == "__main__":
    unittest.main()
