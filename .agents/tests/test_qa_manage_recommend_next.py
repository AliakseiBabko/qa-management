"""Unit tests for qa_manage.py's read-only `recommend-next --project <Project>
[--lane ...] [--focus ...]` command (Phase 15A).

recommend-next ranks discovered/needs_scope 00_Inbox sources for one
project - a convenience shortlist, never a decision. It reuses
compute_classify_preview() (the same signal/candidate-route logic
`classify` calls) and must never write the queue, start a run, touch
Drive/mirror beyond the same read-only file access classify/pack already
perform, or record telemetry. Covers project-prefix filtering for
discovered rows, declared-Project filtering for needs_scope rows,
--lane filtering via candidate-route/Source-type lane resolution
(never a 30_Project_Knowledge path check), --focus as a ranking-only
hint, deterministic scoring/tie-breaking, and read-only enforcement.

All fixture text is synthetic placeholders - no real names/projects.

Run:  python -m unittest discover -s .agents/tests
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import qa_manage


PROJECT_A = "Project_A"
GRAPH = {
    "lanes": {
        "m2_project_management": {"root_folder": "20_M2_Project_Management"},
        "project_knowledge": {"root_folder": "30_Project_Knowledge"},
        "m1_people_management": {"root_folder": "10_M1_People_Management"},
    },
    "sources": {
        "meeting_transcript": {
            "routes": {
                "multi_project": {"skills": ["m2-status-meeting-intake"], "entry": ["m2_input_doc"]},
                "single_project": {"skills": ["shared-rules"], "entry": ["m2_input_doc"]},
            }
        },
        "qa_1to1": {
            "routes": {
                "m1": {"skills": ["m1-skill"], "entry": ["m1_doc"]},
                "m2": {"skills": ["m2-skill"], "entry": ["m2_doc"]},
                "mixed": {"skills": ["m1-skill", "m2-skill"], "entry": ["m1_doc", "m2_doc"]},
            }
        },
        "project_knowledge_transcript": {
            "lane": "project_knowledge",
            "skills": ["pk-skill"], "entry": ["pk_doc"], "scope_required": ["project"],
        },
        "m1_history": {"skills": ["m1-history-skill"], "entry": ["m1_doc"], "scope_required": ["person"]},
        "admin_note": {"skills": ["admin-skill"], "entry": ["people_registry_doc"]},
    },
    "documents": {
        "m1_doc": {"scope": "person", "downstream": []},
        "m2_doc": {"scope": "project", "downstream": []},
        "m2_input_doc": {"scope": "project", "downstream": []},
        "pk_doc": {"scope": "project", "downstream": []},
        "people_registry_doc": {"scope": "workspace", "downstream": []},
    },
}

TRANSCRIPT_TWO_SPEAKERS = (
    "<Person1>:\n"
    "Hello, how are things going on <Project1>?\n\n"
    "<Person2>:\n"
    "Going well, thanks.\n"
)

TRANSCRIPT_THREE_SPEAKERS = (
    "[Speaker 1]\nWelcome everyone.\n\n"
    "[Speaker 2]\nThanks for having us.\n\n"
    "[Speaker 3]\nLet's get started.\n\n"
    "[Speaker 1]\nSounds good.\n\n"
)

PLAIN_NOTE = "A short reference note with no speaker turns at all, just prose.\n"


def row(run_id, **extra) -> dict:
    base = {
        "Run ID": run_id, "Source": f"00_Inbox/{run_id}.txt",
        "Current source": f"00_Inbox/{run_id}.txt", "Source disposition": "inbox",
        "Source type": "", "Route variant": "",
        "Project": "", "Person": "", "Scopes": "",
        "Status": "discovered", "Stage": "", "Skills": "", "Entries": "",
        "Discovered": "2026-01-01 00:00", "Started": "", "Last mutation": "2026-01-01 00:00",
        "Completed": "", "Snapshot": "", "Reason": "", "Summary": "", "Source text version": "",
    }
    base.update(extra)
    return base


PEOPLE_REGISTRY_HEADER = [
    "Name (RU)", "Name (EN)", "Email", "Side", "Worker ID", "M1",
    "Role", "Internal rank", "Project(s)", "Дата трудоустройства",
    "Дата последнего PR", "Первый коммерческий проект", "Aliases / spelling variants", "Notes",
]


def people_row(name_ru="", name_en="", project="", aliases="") -> list[str]:
    """One `_people_registry` row, placeholder-only, matching the real
    14-column schema (see pipeline_common.PEOPLE_REGISTRY_HEADER) - only
    the columns match_person_registry() actually reads (Name (RU)/(EN),
    Project(s), Aliases) are ever non-blank in these fixtures."""
    return [name_ru, name_en, "", "", "", "", "", "", project, "", "", "", aliases, ""]


def people_rows(*rows: list[str]) -> list[list[str]]:
    return [PEOPLE_REGISTRY_HEADER, *rows]


def write_file(root: Path, relative_path: str, content: str) -> None:
    full = root / relative_path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content, encoding="utf-8")


class Args:
    def __init__(self, project, json=True, debug=False, lane="", focus="", limit=None):
        self.project = project
        self.json = json
        self.debug = debug
        self.lane = lane
        self.focus = focus
        self.limit = limit


def run_recommend_next(rows, data_root, people_rows=None, **kwargs):
    mock_drive = MagicMock()
    mock_services = {"drive": mock_drive, "sheets": MagicMock()}
    # fetch_people_registry_rows is patched directly (not left to fall
    # through to the real Drive-backed lookup) because the real path pages
    # through drive.files().list() results via a nextPageToken loop - a
    # bare MagicMock's .get("nextPageToken") never returns a falsy value,
    # so that loop never terminates against these fixtures. Tests that
    # care about the person-alias signal pass `people_rows` explicitly;
    # everything else gets [] (no signal), matching prior behavior before
    # this fetch existed.
    with patch("qa_manage.get_services_cached", return_value=mock_services), \
         patch("qa_manage.find_queue", return_value={"id": "sheet_id"}), \
         patch("qa_manage.read_queue", return_value=rows), \
         patch("qa_manage.write_queue") as write_queue_mock, \
         patch("qa_manage.load_graph", return_value=GRAPH), \
         patch("qa_manage.fetch_people_registry_rows", return_value=people_rows or []), \
         patch("qa_manage.DATA_ROOT", data_root):
        res = qa_manage.cmd_recommend_next(Args(**kwargs))
    return res, mock_services, write_queue_mock


# ---------------------------------------------------------------------------
# Pure helpers - direct unit tests
# ---------------------------------------------------------------------------

class DiscoveredProjectPathMatchTests(unittest.TestCase):
    def test_matches_project_subfolder_prefix(self):
        r = row("r1", **{"Current source": "00_Inbox/Project_A/05 nfr.txt"})
        self.assertTrue(qa_manage.discovered_row_matches_project_path(r, PROJECT_A))

    def test_case_insensitive(self):
        r = row("r1", **{"Current source": f"00_Inbox/{PROJECT_A.lower()}/05 nfr.txt"})
        self.assertTrue(qa_manage.discovered_row_matches_project_path(r, PROJECT_A))

    def test_bare_inbox_file_never_matches_any_project(self):
        r = row("r1", **{"Current source": "00_Inbox/some file.txt"})
        self.assertFalse(qa_manage.discovered_row_matches_project_path(r, PROJECT_A))

    def test_different_project_subfolder_does_not_match(self):
        r = row("r1", **{"Current source": "00_Inbox/OtherProject/file.txt"})
        self.assertFalse(qa_manage.discovered_row_matches_project_path(r, PROJECT_A))

    def test_backslash_paths_normalized(self):
        r = row("r1", **{"Current source": "00_Inbox\\Project_A\\file.txt"})
        self.assertTrue(qa_manage.discovered_row_matches_project_path(r, PROJECT_A))

    def test_falls_back_to_source_when_current_source_blank(self):
        r = row("r1", Source="00_Inbox/Project_A/file.txt", **{"Current source": ""})
        self.assertTrue(qa_manage.discovered_row_matches_project_path(r, PROJECT_A))

    def test_never_matches_canonical_lane_path(self):
        # Discovered rows live in 00_Inbox, never 30_Project_Knowledge -
        # a row whose Current source somehow pointed at the canonical lane
        # path must NOT match via this path-prefix check (it isn't the
        # convention this function implements).
        r = row("r1", **{"Current source": "30_Project_Knowledge/Project_A/file.txt"})
        self.assertFalse(qa_manage.discovered_row_matches_project_path(r, PROJECT_A))


class LaneResolutionTests(unittest.TestCase):
    def test_explicit_lane_wins(self):
        candidate = {"source_type": "project_knowledge_transcript", "required_scope": ["project"]}
        self.assertEqual(qa_manage.lane_for_candidate(GRAPH, candidate), "project_knowledge")

    def test_project_scope_defaults_to_m2(self):
        candidate = {"source_type": "meeting_transcript", "required_scope": ["project"]}
        self.assertEqual(qa_manage.lane_for_candidate(GRAPH, candidate), "m2_project_management")

    def test_person_scope_defaults_to_m1(self):
        candidate = {"source_type": "m1_history", "required_scope": ["person"]}
        self.assertEqual(qa_manage.lane_for_candidate(GRAPH, candidate), "m1_people_management")

    def test_workspace_scope_has_no_lane(self):
        candidate = {"source_type": "admin_note", "required_scope": []}
        self.assertIsNone(qa_manage.lane_for_candidate(GRAPH, candidate))

    def test_row_source_type_resolution_for_needs_scope(self):
        self.assertEqual(
            qa_manage.lane_for_row_source_type(GRAPH, "project_knowledge_transcript", ""),
            "project_knowledge")
        self.assertEqual(
            qa_manage.lane_for_row_source_type(GRAPH, "qa_1to1", "m1"),
            "m1_people_management")
        self.assertEqual(
            qa_manage.lane_for_row_source_type(GRAPH, "qa_1to1", "m2"),
            "m2_project_management")

    def test_blank_source_type_has_no_lane(self):
        self.assertIsNone(qa_manage.lane_for_row_source_type(GRAPH, "", ""))

    def test_unknown_source_type_has_no_lane(self):
        self.assertIsNone(qa_manage.lane_for_row_source_type(GRAPH, "not_a_real_type", ""))


class FocusMatchTests(unittest.TestCase):
    def test_no_keywords_never_matches(self):
        result = qa_manage.compute_focus_match("00_Inbox/x.txt", "some text", [], [])
        self.assertEqual(result, {"matched": False, "keywords_found": []})

    def test_matches_filename(self):
        result = qa_manage.compute_focus_match("00_Inbox/Project_A/performance-notes.txt", "", [], ["performance"])
        self.assertTrue(result["matched"])
        self.assertIn("performance", result["keywords_found"])

    def test_matches_preview_text_case_insensitive(self):
        result = qa_manage.compute_focus_match("00_Inbox/x.txt", "discussion of LOAD testing", [], ["load"])
        self.assertTrue(result["matched"])

    def test_matches_candidate_reason_text(self):
        candidates = [{"reason": "mentions throughput and latency budgets"}]
        result = qa_manage.compute_focus_match("00_Inbox/x.txt", "", candidates, ["throughput"])
        self.assertTrue(result["matched"])

    def test_no_match_when_keyword_absent_everywhere(self):
        result = qa_manage.compute_focus_match("00_Inbox/x.txt", "unrelated text", [], ["performance"])
        self.assertFalse(result["matched"])


class RecencyBonusTests(unittest.TestCase):
    def test_oldest_gets_max_bonus_newest_gets_zero(self):
        bonus = qa_manage.compute_recency_bonus_by_run_id({
            "old": "2026-01-01 00:00",
            "new": "2026-01-03 00:00",
        })
        self.assertEqual(bonus["old"], qa_manage.RECOMMEND_NEXT_RECENCY_MAX_BONUS)
        self.assertEqual(bonus["new"], 0.0)

    def test_single_candidate_gets_max_bonus(self):
        bonus = qa_manage.compute_recency_bonus_by_run_id({"only": "2026-01-01 00:00"})
        self.assertEqual(bonus["only"], qa_manage.RECOMMEND_NEXT_RECENCY_MAX_BONUS)

    def test_empty_input_returns_empty(self):
        self.assertEqual(qa_manage.compute_recency_bonus_by_run_id({}), {})

    def test_never_depends_on_wall_clock_now(self):
        # Same relative order -> same bonuses, regardless of absolute dates
        # (no dependency on datetime.now() anywhere in the function).
        bonus_a = qa_manage.compute_recency_bonus_by_run_id({
            "old": "2020-01-01 00:00", "new": "2020-01-03 00:00",
        })
        bonus_b = qa_manage.compute_recency_bonus_by_run_id({
            "old": "2030-06-01 00:00", "new": "2030-06-03 00:00",
        })
        self.assertEqual(bonus_a["old"], bonus_b["old"])
        self.assertEqual(bonus_a["new"], bonus_b["new"])


class PersonRegistryMatchTests(unittest.TestCase):
    """match_person_registry() is a ranking *hint* only - never a scope
    decision (see its own docstring and recommend-next's guardrails). All
    fixtures use placeholder names, matching this file's own convention."""

    def test_exact_name_match(self):
        rows = people_rows(
            people_row(name_ru="<Имя1> <Фамилия1>", name_en="<Name1> <Surname1>", project="<Project1>"),
        )
        matches = qa_manage.match_person_registry("00_Inbox/<Name1> <Surname1> case.txt", rows)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["name"], "<Имя1> <Фамилия1>")
        self.assertIn("name", matches[0]["matched_via"])

    def test_alias_transliteration_match(self):
        # Filename uses ONLY the alias's own distinctive token ("Kolesny"),
        # never the tokens shared with the real Name (RU)/(EN) cells
        # ("Person2"/"Kalesny") - isolates the match to the Aliases column
        # specifically, not just an incidental overlap with the real name.
        rows = people_rows(
            people_row(
                name_ru="<Имя2> <Фамилия2>", name_en="Person2 Kalesny",
                aliases="Person2X Kolesny (transliteration variant used in one recording)",
            ),
        )
        matches = qa_manage.match_person_registry("00_Inbox/Kolesny notes.txt", rows)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["matched_via"], ["alias"])
        self.assertIn("kolesny", matches[0]["matched_tokens"])

    def test_no_match(self):
        rows = people_rows(
            people_row(name_ru="<Имя3> <Фамилия3>", name_en="<Name3> <Surname3>", project="<Project1>"),
        )
        matches = qa_manage.match_person_registry("00_Inbox/completely-unrelated-file.txt", rows)
        self.assertEqual(matches, [])

    def test_no_match_on_empty_registry(self):
        self.assertEqual(qa_manage.match_person_registry("00_Inbox/<Name1>.txt", people_rows()), [])
        self.assertEqual(qa_manage.match_person_registry("00_Inbox/<Name1>.txt", []), [])

    def test_multiple_possible_matches(self):
        rows = people_rows(
            people_row(name_ru="<Имя1> <Фамилия1>", name_en="<Name1> <Surname1>", project="<Project1>"),
            people_row(name_ru="<Имя4> <Фамилия4>", name_en="<Name4> <Surname1>", project=""),
        )
        # Filename token "Surname1" is shared by both registry rows (a
        # deliberately ambiguous fixture - a shared/common surname).
        matches = qa_manage.match_person_registry("00_Inbox/<Surname1> family case.txt", rows)
        self.assertEqual(len(matches), 2)
        names = {m["name"] for m in matches}
        self.assertEqual(names, {"<Имя1> <Фамилия1>", "<Имя4> <Фамилия4>"})

    def test_active_project_person_sorts_first_among_multiple_matches(self):
        rows = people_rows(
            # Row without a current Project(s) association comes first in
            # the input to prove sorting isn't just input order.
            people_row(name_ru="<Имя4> <Фамилия4>", name_en="<Name4> <Surname1>", project=""),
            people_row(name_ru="<Имя1> <Фамилия1>", name_en="<Name1> <Surname1>", project="<Project1>"),
        )
        matches = qa_manage.match_person_registry("00_Inbox/<Surname1> family case.txt", rows)
        self.assertEqual(matches[0]["name"], "<Имя1> <Фамилия1>")
        self.assertTrue(matches[0]["has_active_project"])
        self.assertFalse(matches[1]["has_active_project"])

    def test_short_tokens_are_not_matched(self):
        # A short/common token (below RECOMMEND_NEXT_PERSON_TOKEN_MIN_LEN)
        # must not produce a match on its own - it would false-positive on
        # too much incidental text otherwise.
        rows = people_rows(people_row(name_ru="<Аб>", name_en="Al"))
        matches = qa_manage.match_person_registry("00_Inbox/Al report.txt", rows)
        self.assertEqual(matches, [])

    def test_transliterated_first_name_alone_does_not_match(self):
        # A nickname sharing no distinctive token with the formal given
        # name on record is exactly the case this function does NOT claim
        # to solve - a shared surname token is required, not a fuzzy
        # first-name guess.
        rows = people_rows(people_row(name_ru="<Имя5>", name_en="Formalname5 <Surname5>"))
        matches = qa_manage.match_person_registry("00_Inbox/Nickname5 case.txt", rows)
        self.assertEqual(matches, [])

    def test_does_not_call_any_drive_api(self):
        # Pure function - takes already-read rows, makes no API calls of
        # its own (a prerequisite for it being safely unit-testable).
        import inspect
        source = inspect.getsource(qa_manage.match_person_registry)
        for forbidden in ("drive.", ".execute(", "read_sheet_values", "get_people_registry_sheet"):
            self.assertNotIn(forbidden, source)


class PersonMatchRankingIntegrationTests(unittest.TestCase):
    """Integration-level: the person-alias signal moves score_breakdown/
    score but never touches project filtering, scope fields, or which
    candidates are eligible."""

    def test_match_increases_score_but_never_mutates_project_or_scope(self):
        # Filenames/paths below are plain identifiers (no angle brackets) -
        # unlike this file's transcript-content placeholders, these become
        # real files on disk (write_file), and '<'/'>' are illegal in
        # Windows filenames.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_file(root, "00_Inbox/Project1/Name1 Surname1 case.txt", TRANSCRIPT_THREE_SPEAKERS)
            write_file(root, "00_Inbox/Project1/unrelated.txt", TRANSCRIPT_THREE_SPEAKERS)
            rows = [
                row("r1", Discovered="2026-01-01 00:00",
                   **{"Current source": "00_Inbox/Project1/Name1 Surname1 case.txt"}),
                row("r2", Discovered="2026-01-01 00:00",
                   **{"Current source": "00_Inbox/Project1/unrelated.txt"}),
            ]
            fixture_people = people_rows(
                people_row(name_ru="<Имя1> <Фамилия1>", name_en="Name1 Surname1", project="Project1"),
            )
            # Force equal recency/size/focus so the person-match bonus is
            # the only thing that can break the tie between r1 and r2.
            with patch("qa_manage.compute_recency_bonus_by_run_id", return_value={"r1": 0.0, "r2": 0.0}):
                res, _, write_mock = run_recommend_next(
                    rows, root, people_rows=fixture_people, project="Project1")

            by_id = {c["run_id"]: c for c in res.data["candidates"]}
            self.assertTrue(by_id["r1"]["person_alias_matches"])
            self.assertFalse(by_id["r2"]["person_alias_matches"])
            self.assertGreater(by_id["r1"]["score"], by_id["r2"]["score"])
            self.assertEqual(res.data["recommended"], "r1")
            self.assertGreater(
                by_id["r1"]["score_breakdown"]["person_alias_match"],
                by_id["r2"]["score_breakdown"]["person_alias_match"],
            )

            # The signal never mutates project/scope: the command's own
            # declared project is exactly what was passed in, still a hard
            # filter (both candidates matched it independently of the
            # person hint), and nothing writes to the queue.
            self.assertEqual(res.data["project"], "Project1")
            write_mock.assert_not_called()

    def test_no_registry_rows_means_no_signal_and_no_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_file(root, "00_Inbox/Project1/a.txt", TRANSCRIPT_THREE_SPEAKERS)
            rows = [row("r1", **{"Current source": "00_Inbox/Project1/a.txt"})]
            res, _, _ = run_recommend_next(rows, root, people_rows=[], project="Project1")
            self.assertTrue(res.ok)
            self.assertEqual(res.data["candidates"][0]["person_alias_matches"], [])
            self.assertEqual(res.data["candidates"][0]["score_breakdown"]["person_alias_match"], 0.0)

    def test_fetch_people_registry_rows_failure_degrades_gracefully(self):
        # fetch_people_registry_rows() itself (not the recommend-next test
        # helper's patch) must swallow a real lookup failure rather than
        # propagating it - simulate that failure directly.
        with patch("pipeline_common.get_people_registry_sheet", side_effect=SystemExit("not found")):
            self.assertEqual(qa_manage.fetch_people_registry_rows({"drive": MagicMock()}), [])


# ---------------------------------------------------------------------------
# cmd_recommend_next - integration-style, real fixture files
# ---------------------------------------------------------------------------

class ProjectFilteringTests(unittest.TestCase):
    def test_discovered_rows_filtered_by_path_prefix(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_file(root, "00_Inbox/Project_A/a.txt", TRANSCRIPT_THREE_SPEAKERS)
            write_file(root, "00_Inbox/OtherProject/b.txt", TRANSCRIPT_THREE_SPEAKERS)
            rows = [
                row("r1", **{"Current source": "00_Inbox/Project_A/a.txt"}),
                row("r2", **{"Current source": "00_Inbox/OtherProject/b.txt"}),
            ]
            res, _, write_mock = run_recommend_next(rows, root, project=PROJECT_A)
            self.assertTrue(res.ok)
            run_ids = {c["run_id"] for c in res.data["candidates"]}
            self.assertEqual(run_ids, {"r1"})
            write_mock.assert_not_called()

    def test_needs_scope_rows_filtered_by_declared_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_file(root, "00_Inbox/misc/a.txt", TRANSCRIPT_THREE_SPEAKERS)
            write_file(root, "00_Inbox/misc/b.txt", TRANSCRIPT_THREE_SPEAKERS)
            rows = [
                row("r1", Status="needs_scope", **{
                    "Current source": "00_Inbox/misc/a.txt",
                    "Source type": "meeting_transcript", "Route variant": "single_project",
                    "Project": PROJECT_A,
                }),
                row("r2", Status="needs_scope", **{
                    "Current source": "00_Inbox/misc/b.txt",
                    "Source type": "meeting_transcript", "Route variant": "single_project",
                    "Project": "OtherProject",
                }),
            ]
            res, _, _ = run_recommend_next(rows, root, project=PROJECT_A)
            run_ids = {c["run_id"] for c in res.data["candidates"]}
            self.assertEqual(run_ids, {"r1"})

    def test_needs_scope_row_with_no_declared_project_is_excluded(self):
        # A needs_scope row's Project field is blank when no --scope/--project
        # was given at start - it should not spuriously match every project.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_file(root, "00_Inbox/misc/a.txt", TRANSCRIPT_THREE_SPEAKERS)
            rows = [row("r1", Status="needs_scope", **{
                "Current source": "00_Inbox/misc/a.txt",
                "Source type": "meeting_transcript", "Route variant": "single_project",
                "Project": "",
            })]
            res, _, _ = run_recommend_next(rows, root, project=PROJECT_A)
            self.assertEqual(res.data["candidates"], [])

    def test_terminal_and_processing_rows_never_considered(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_file(root, "00_Inbox/Project_A/a.txt", TRANSCRIPT_THREE_SPEAKERS)
            rows = [
                row("r1", Status="completed", **{"Current source": "00_Inbox/Project_A/a.txt"}),
                row("r2", Status="processing", **{"Current source": "00_Inbox/Project_A/a.txt"}),
                row("r3", Status="blocked", **{"Current source": "00_Inbox/Project_A/a.txt"}),
                row("r4", Status="ignored", **{"Current source": "00_Inbox/Project_A/a.txt"}),
            ]
            res, _, _ = run_recommend_next(rows, root, project=PROJECT_A)
            self.assertEqual(res.data["candidates"], [])


class LaneFilteringTests(unittest.TestCase):
    def test_discovered_row_kept_when_a_candidate_route_maps_to_lane(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_file(root, "00_Inbox/Project_A/transcript.txt", TRANSCRIPT_THREE_SPEAKERS)
            rows = [row("r1", **{"Current source": "00_Inbox/Project_A/transcript.txt"})]
            res, _, _ = run_recommend_next(rows, root, project=PROJECT_A, lane="project_knowledge")
            run_ids = {c["run_id"] for c in res.data["candidates"]}
            self.assertEqual(run_ids, {"r1"})
            self.assertIn("project_knowledge", res.data["candidates"][0]["candidate_lanes"])

    def test_discovered_row_excluded_when_no_candidate_matches_lane(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_file(root, "00_Inbox/Project_A/note.txt", PLAIN_NOTE)
            rows = [row("r1", **{"Current source": "00_Inbox/Project_A/note.txt"})]
            # A short, signal-free note only yields project_knowledge_notes/
            # project_knowledge_document candidates (both project_knowledge
            # lane) - filtering for m1_people_management must exclude it.
            res, _, _ = run_recommend_next(rows, root, project=PROJECT_A, lane="m1_people_management")
            self.assertEqual(res.data["candidates"], [])

    def test_needs_scope_lane_resolved_from_source_type_not_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_file(root, "00_Inbox/misc/a.txt", TRANSCRIPT_TWO_SPEAKERS)
            rows = [row("r1", Status="needs_scope", **{
                "Current source": "00_Inbox/misc/a.txt",  # NOT under 30_Project_Knowledge
                "Source type": "project_knowledge_transcript", "Route variant": "",
                "Project": PROJECT_A,
            })]
            res, _, _ = run_recommend_next(rows, root, project=PROJECT_A, lane="project_knowledge")
            run_ids = {c["run_id"] for c in res.data["candidates"]}
            self.assertEqual(run_ids, {"r1"})

    def test_needs_scope_lane_mismatch_excludes_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_file(root, "00_Inbox/misc/a.txt", TRANSCRIPT_TWO_SPEAKERS)
            rows = [row("r1", Status="needs_scope", **{
                "Current source": "00_Inbox/misc/a.txt",
                "Source type": "qa_1to1", "Route variant": "m2",
                "Project": PROJECT_A,
            })]
            res, _, _ = run_recommend_next(rows, root, project=PROJECT_A, lane="m1_people_management")
            self.assertEqual(res.data["candidates"], [])


class FocusRankingTests(unittest.TestCase):
    def test_focus_never_bypasses_project_hard_filter(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_file(root, "00_Inbox/OtherProject/perf.txt", TRANSCRIPT_THREE_SPEAKERS)
            rows = [row("r1", **{"Current source": "00_Inbox/OtherProject/perf.txt"})]
            res, _, _ = run_recommend_next(rows, root, project=PROJECT_A, focus="perf")
            self.assertEqual(res.data["candidates"], [])

    def test_focus_never_bypasses_lane_hard_filter(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_file(root, "00_Inbox/Project_A/note.txt", PLAIN_NOTE)
            rows = [row("r1", **{"Current source": "00_Inbox/Project_A/note.txt"})]
            res, _, _ = run_recommend_next(
                rows, root, project=PROJECT_A, lane="m1_people_management", focus="note")
            self.assertEqual(res.data["candidates"], [])

    def test_focus_reorders_within_eligible_set(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_file(root, "00_Inbox/Project_A/a_first.txt", TRANSCRIPT_THREE_SPEAKERS)
            write_file(root, "00_Inbox/Project_A/b_second_performance.txt", TRANSCRIPT_THREE_SPEAKERS)
            rows = [
                row("r1", Discovered="2026-01-01 00:00", **{"Current source": "00_Inbox/Project_A/a_first.txt"}),
                row("r2", Discovered="2026-01-02 00:00",
                   **{"Current source": "00_Inbox/Project_A/b_second_performance.txt"}),
            ]
            # Without focus, r1 (older) ranks first on recency alone.
            res_no_focus, _, _ = run_recommend_next(rows, root, project=PROJECT_A)
            self.assertEqual(res_no_focus.data["recommended"], "r1")

            # With focus matching only r2's filename, r2 must outrank r1.
            res_focus, _, _ = run_recommend_next(rows, root, project=PROJECT_A, focus="performance")
            self.assertEqual(res_focus.data["recommended"], "r2")


class ScoringAndSortTests(unittest.TestCase):
    def test_score_breakdown_present_and_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_file(root, "00_Inbox/Project_A/a.txt", TRANSCRIPT_THREE_SPEAKERS)
            rows = [row("r1", **{"Current source": "00_Inbox/Project_A/a.txt"})]
            res1, _, _ = run_recommend_next(rows, root, project=PROJECT_A)
            res2, _, _ = run_recommend_next(rows, root, project=PROJECT_A)
            self.assertEqual(res1.data["candidates"][0]["score_breakdown"],
                            res2.data["candidates"][0]["score_breakdown"])
            breakdown = res1.data["candidates"][0]["score_breakdown"]
            for key in ("project_match", "lane_match", "focus_match", "recency", "size_penalty"):
                self.assertIn(key, breakdown)

    def test_tie_break_is_run_id_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_file(root, "00_Inbox/Project_A/a.txt", TRANSCRIPT_THREE_SPEAKERS)
            write_file(root, "00_Inbox/Project_A/b.txt", TRANSCRIPT_THREE_SPEAKERS)
            rows = [
                row("zzz_run", Discovered="2026-01-01 00:00", **{"Current source": "00_Inbox/Project_A/a.txt"}),
                row("aaa_run", Discovered="2026-01-02 00:00", **{"Current source": "00_Inbox/Project_A/b.txt"}),
            ]
            # Force a genuine total-score tie (recency is normally rank-based
            # and would otherwise differentiate even equal-timestamp rows -
            # see RecencyBonusTests) so the test isolates run_id tie-breaking
            # specifically, not the recency formula's own stable-sort effect.
            with patch("qa_manage.compute_recency_bonus_by_run_id",
                      return_value={"zzz_run": 0.05, "aaa_run": 0.05}):
                res, _, _ = run_recommend_next(rows, root, project=PROJECT_A)
            ordered_ids = [c["run_id"] for c in res.data["candidates"]]
            self.assertEqual(ordered_ids, sorted(ordered_ids))

    def test_limit_truncates_and_flags_truncated(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rows = []
            for i in range(3):
                write_file(root, f"00_Inbox/Project_A/f{i}.txt", TRANSCRIPT_THREE_SPEAKERS)
                rows.append(row(f"r{i}", **{"Current source": f"00_Inbox/Project_A/f{i}.txt"}))
            res, _, _ = run_recommend_next(rows, root, project=PROJECT_A, limit=2)
            self.assertEqual(len(res.data["candidates"]), 2)
            self.assertTrue(res.data["truncated"])

    def test_large_file_gets_size_penalty(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            big_text = TRANSCRIPT_THREE_SPEAKERS + ("padding line\n" * 1)
            write_file(root, "00_Inbox/Project_A/big.txt", big_text)
            big_path = root / "00_Inbox" / PROJECT_A / "big.txt"
            # Pad the file past the large-file threshold without changing
            # its transcript signal shape (append after real content).
            with open(big_path, "a", encoding="utf-8") as f:
                f.write("x" * (qa_manage.RECOMMEND_NEXT_LARGE_FILE_BYTES + 1))
            rows = [row("r1", **{"Current source": "00_Inbox/Project_A/big.txt"})]
            res, _, _ = run_recommend_next(rows, root, project=PROJECT_A)
            self.assertEqual(res.data["candidates"][0]["score_breakdown"]["size_penalty"],
                            qa_manage.RECOMMEND_NEXT_SIZE_PENALTY)


class ReadOnlyEnforcementTests(unittest.TestCase):
    def test_never_calls_write_queue(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_file(root, "00_Inbox/Project_A/a.txt", TRANSCRIPT_THREE_SPEAKERS)
            rows = [row("r1", **{"Current source": "00_Inbox/Project_A/a.txt"})]
            res, mock_services, write_mock = run_recommend_next(rows, root, project=PROJECT_A)
            self.assertTrue(res.ok)
            write_mock.assert_not_called()

    def test_never_calls_drive_mutating_methods(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_file(root, "00_Inbox/Project_A/a.txt", TRANSCRIPT_THREE_SPEAKERS)
            rows = [row("r1", **{"Current source": "00_Inbox/Project_A/a.txt"})]
            _, mock_services, _ = run_recommend_next(rows, root, project=PROJECT_A)
            drive_mock = mock_services["drive"]
            # No Drive method was ever invoked at all - recommend-next reads
            # the local Drive-sync-mounted file directly (same as classify),
            # never through the Drive API.
            drive_mock.files.assert_not_called()

    def test_never_imports_mutating_pipeline_modules(self):
        # commit_workspace_state.py / measure_operator_outputs.py / archive-
        # source / complete are never CALLED by cmd_recommend_next (checked
        # as call sites, "name(" - the docstring itself names some of these
        # in prose to say what it does NOT do, which would otherwise be a
        # false positive on a bare substring check).
        import inspect
        source = inspect.getsource(qa_manage.cmd_recommend_next)
        for forbidden_call in ("write_queue(", "cmd_start(", "cmd_archive_source(", "cmd_complete("):
            self.assertNotIn(forbidden_call, source)
        for forbidden_module in ("commit_workspace_state", "measure_operator_outputs"):
            self.assertNotIn(forbidden_module, source)


class JsonEnvelopeTests(unittest.TestCase):
    def test_json_envelope_matches_contract(self):
        import subprocess
        import json as jsonlib
        res = subprocess.run(
            [sys.executable, str(Path(__file__).resolve().parent.parent / "scripts" / "qa_manage.py"),
             "recommend-next", "--project", "NoSuchProjectAtAll", "--json"],
            capture_output=True, text=True, cwd=str(Path(__file__).resolve().parents[2]),
        )
        payload = jsonlib.loads(res.stdout)
        for key in ("schema_version", "ok", "command", "data", "warnings", "errors"):
            self.assertIn(key, payload)
        self.assertEqual(payload["command"], "recommend-next")

    def test_missing_project_flag_is_parser_error(self):
        import subprocess
        res = subprocess.run(
            [sys.executable, str(Path(__file__).resolve().parent.parent / "scripts" / "qa_manage.py"),
             "recommend-next", "--json"],
            capture_output=True, text=True,
        )
        self.assertNotEqual(res.returncode, 0)

    def test_guardrails_present_in_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rows = []
            res, _, _ = run_recommend_next(rows, root, project=PROJECT_A)
            self.assertTrue(res.data["guardrails"])
            joined = " ".join(res.data["guardrails"]).lower()
            self.assertIn("ranked", joined)
            self.assertIn("never", joined)

    def test_guardrails_warn_person_alias_match_is_a_hint_not_a_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            res, _, _ = run_recommend_next([], root, project=PROJECT_A)
            joined = " ".join(res.data["guardrails"])
            self.assertIn("person_alias_matches", joined)
            self.assertIn("never declares a person or project scope", joined)


class RecommendNextDocsTests(unittest.TestCase):
    """The person-alias-match feature must be discoverable from README.md,
    not just the command's own JSON output."""

    def test_readme_documents_person_alias_match(self):
        readme = (Path(__file__).resolve().parents[2] / "README.md").read_text(encoding="utf-8")
        normalized = " ".join(readme.split())
        self.assertIn("person_alias_matches", normalized)
        self.assertIn("match_person_registry()", normalized)
        self.assertIn("score_breakdown[\"person_alias_match\"]", normalized)
        self.assertIn("never a scope inference", normalized)


if __name__ == "__main__":
    unittest.main()
