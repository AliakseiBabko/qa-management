"""Phase 14B: given a run_id, compute the minimal set of mirror paths a
scoped `commit_workspace_state.py --scoped` export must cover.

Pure queue/graph logic only - no Drive folder mechanics here (that's
`commit_workspace_state.py`'s job, since it owns the mirror/Drive-facing
export code already). This module answers "what does this run's scope
mean", not "where does that live in Drive".

Rules (see AGENTS.md / README.md Phase 14B section):

- Scopes come from the same `enumerate_run_scopes()` helper
  `qa_manage.py review`/`complete` already trust - a scoped export's notion
  of "this run's scope" is never allowed to diverge from what completion
  verification considers the run's scope.
- A project-scoped tuple resolves to its source_type's declared graph lane
  (`sources.<type>.lane`, e.g. `project_knowledge`), defaulting to
  `m2_project_management` when the source type declares no lane of its own
  (true today for every M1/M2 source type - only the Project Knowledge
  lane's types self-declare `lane: project_knowledge`).
- A person-scoped tuple always resolves to the `m1_people_management` lane
  (the only person-shaped lane).
- A single run can need both (e.g. `qa_1to1`'s `mixed` variant has one
  scope tuple with both project and person set) - both lanes are included.
- No declared scope anywhere (a pure workspace-scoped source, e.g.
  `admin_note`) resolves to no subtrees at all - only the fixed
  workspace-root file set.
- Any lane a resolved scope needs that document_graph.yaml can't supply a
  `root_folder` for is a **fail-closed refusal**, never a silent narrowing.
"""

from __future__ import annotations

from dataclasses import dataclass, field

ALWAYS_INCLUDE_NAMES: tuple[str, ...] = ("_intake_queue", "_skill_invocations", "_closure_outcomes")

MULTI_SCOPE_WARNING_THRESHOLD = 4

DEFAULT_PROJECT_LANE = "m2_project_management"
PERSON_LANE = "m1_people_management"


@dataclass
class ScopeResolution:
    ok: bool
    reason: str = ""
    warnings: list[str] = field(default_factory=list)
    always_include_names: tuple[str, ...] = ALWAYS_INCLUDE_NAMES
    # Lane root folder names (e.g. "20_M2_Project_Management") whose DIRECT
    # file children (non-recursive) must be exported.
    lane_root_prefixes: set[str] = field(default_factory=set)
    # "<lane_root>/<project_or_person>" prefixes to export RECURSIVELY.
    subtree_prefixes: set[str] = field(default_factory=set)


def _lane_for_source(graph: dict, source_type: str) -> str | None:
    spec = (graph.get("sources") or {}).get(source_type) or {}
    return spec.get("lane")


def _lane_root_or_none(graph: dict, lane_key: str) -> str | None:
    lane_spec = (graph.get("lanes") or {}).get(lane_key)
    root = (lane_spec or {}).get("root_folder")
    return str(root).strip() if root and str(root).strip() else None


def resolve_scope(services, run_id: str) -> ScopeResolution:
    """Fails closed (ok=False, reason set) rather than ever returning a
    resolution that would cause a scoped export to silently miss something
    its own run's completion verification would consider in-scope."""
    import qa_manage
    from closure_outcomes import fetch_outcomes

    try:
        sheet = qa_manage.find_queue(services)
        if not sheet:
            return ScopeResolution(ok=False, reason="No _intake_queue sheet yet - run scan first.")
        rows = qa_manage.read_queue(services, sheet)
        row = qa_manage.get_run(rows, run_id)
        graph = qa_manage.load_graph()

        outcome_rows = fetch_outcomes(services, run_id, all_scopes=True)
        scopes = qa_manage.parse_scopes_cell(row.get("Scopes", ""))
        entries = qa_manage.parse_entries_cell(row.get("Entries", ""))
        variant = row.get("Route variant", "")
        enumerated = qa_manage.enumerate_run_scopes(outcome_rows, scopes, entries, variant)
    except SystemExit as exc:
        return ScopeResolution(ok=False, reason=str(exc))
    except Exception as exc:  # malformed Scopes/Entries JSON, graph parse error, etc.
        return ScopeResolution(ok=False, reason=f"Could not resolve scope for {run_id!r}: {exc}")

    source_type = row.get("Source type", "")
    default_project_lane = _lane_for_source(graph, source_type) or DEFAULT_PROJECT_LANE

    lane_root_prefixes: set[str] = set()
    subtree_prefixes: set[str] = set()
    distinct_project_person: set[tuple[str, str]] = set()

    for project, person, _variant in enumerated:
        project, person = project.strip(), person.strip()
        if not project and not person:
            continue
        distinct_project_person.add((project, person))

        if project:
            root = _lane_root_or_none(graph, default_project_lane)
            if not root:
                return ScopeResolution(
                    ok=False,
                    reason=f"Run {run_id!r} needs lane {default_project_lane!r} for its project "
                           "scope, but document_graph.yaml has no root_folder for it - "
                           "re-run with full export instead."
                )
            lane_root_prefixes.add(root)
            subtree_prefixes.add(f"{root}/{project}")

        if person:
            root = _lane_root_or_none(graph, PERSON_LANE)
            if not root:
                return ScopeResolution(
                    ok=False,
                    reason=f"Run {run_id!r} needs lane {PERSON_LANE!r} for its person scope, "
                           "but document_graph.yaml has no root_folder for it - "
                           "re-run with full export instead."
                )
            lane_root_prefixes.add(root)
            subtree_prefixes.add(f"{root}/{person}")

    warnings: list[str] = []
    if len(distinct_project_person) > MULTI_SCOPE_WARNING_THRESHOLD:
        warnings.append(
            f"run {run_id!r} touches {len(distinct_project_person)} distinct project/person "
            "scopes - scoped mode saves little here; full export is likely a better fit."
        )

    return ScopeResolution(
        ok=True,
        warnings=warnings,
        lane_root_prefixes=lane_root_prefixes,
        subtree_prefixes=subtree_prefixes,
    )
