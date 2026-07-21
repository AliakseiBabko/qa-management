"""Persisted per-edge cascade closure outcomes - the durable half of
check_cascade_closure.py.

The closure checker computes which graph edges an intake pass must
account for; until now the resolution ("updated" / "no change needed
because...") lived only in the agent's reply text. This module persists
each resolution as one row in the workspace-wide `_closure_outcomes`
Sheet at the Drive root (real project/person names - Drive, never the
repo), making closure machine-verifiable per run and scope-aware: the
same edge may legitimately resolve differently for two projects or
people within one intake run.

Valid outcomes are constrained by the edge's kind in document_graph.yaml:

    direct   -> updated
    judgment -> updated | no_change (reason required)
    gated    -> gated (reason required) | updated (once the gate is satisfied)
    script   -> regenerated

`run_id` is any stable string for the pass (until the intake queue mints
canonical ids in the next roadmap step, use `<date>-<source-slug>`, e.g.
`2026-07-19-aslan-1to1`). `actor` defaults to "agent"; use "m2"/"m1" when
the human made the call.

Usage:

    python closure_outcomes.py record --run-id R --source individual_metrics \
        --target project_metrics --outcome updated --project <Project> [--dry-run]
    python closure_outcomes.py record --run-id R --source m2_input \
        --target project_risk --outcome gated --reason "round 2026-07-19 pending"
    python closure_outcomes.py list --run-id R [--project P]

check_cascade_closure.py --run-id R reads these rows and treats an edge
as resolved only when a kind-valid outcome exists for it.
"""

from __future__ import annotations

import argparse
import datetime as dt
import io
import sys
from pathlib import Path

import yaml

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))

GRAPH_PATH = Path(__file__).resolve().parent.parent / "document_graph.yaml"
SHEET_NAME = "_closure_outcomes"
HEADER = ["Run ID", "Timestamp", "Project", "Person", "Route variant",
          "Source node", "Target node", "Edge kind", "Outcome", "Reason", "Actor"]

VALID_OUTCOMES = {
    "direct": {"updated"},
    "judgment": {"updated", "no_change"},
    "gated": {"gated", "updated"},
    "script": {"regenerated"},
}
REASON_REQUIRED = {"no_change", "gated"}


def load_docs() -> dict:
    graph = yaml.safe_load(GRAPH_PATH.read_text(encoding="utf-8"))
    return graph.get("documents") or {}


def edge_kind(source: str, target: str) -> str:
    for edge in (load_docs().get(source) or {}).get("downstream") or []:
        if edge.get("to") == target:
            return edge["kind"]
    raise SystemExit(f"No edge {source} -> {target} in document_graph.yaml - "
                     "outcomes attach to graph edges; add the edge first if it's real.")


def require_scope(source: str, target: str, project: str, person: str) -> None:
    """A record must carry the scope its edge endpoints have: an edge touching
    a project-scoped document is meaningless without knowing which project,
    likewise person. Workspace-scoped endpoints require nothing."""
    docs = load_docs()
    scopes = {(docs.get(n) or {}).get("scope") for n in (source, target)}
    if "project" in scopes and not project.strip():
        raise SystemExit(f"{source} -> {target} touches a project-scoped document - "
                         "--project is required.")
    if "person" in scopes and not person.strip():
        raise SystemExit(f"{source} -> {target} touches a person-scoped document - "
                         "--person is required.")


def validate(kind: str, outcome: str, reason: str) -> None:
    allowed = VALID_OUTCOMES[kind]
    if outcome not in allowed:
        raise SystemExit(f"Outcome {outcome!r} is not valid for a {kind!r} edge "
                         f"(allowed: {sorted(allowed)}).")
    if outcome in REASON_REQUIRED and not reason.strip():
        raise SystemExit(f"Outcome {outcome!r} requires --reason (why no change / what gate).")


def find_sheet(services):
    """Read-only resolution: None if the sheet doesn't exist yet."""
    from sync_m2_source_docs_to_sheets import ROOT_FOLDER_ID, find_sheet_in_folder
    return find_sheet_in_folder(services["drive"], ROOT_FOLDER_ID, SHEET_NAME)


def get_or_create_sheet(services):
    """Create-on-demand - used only by `record`; reads must never create."""
    from sync_m2_source_docs_to_sheets import ROOT_FOLDER_ID, create_sheet
    sheet = find_sheet(services)
    if sheet:
        return sheet
    return create_sheet(services, SHEET_NAME, ROOT_FOLDER_ID, [HEADER])


def row_matches_scope(rec: dict, project: str, person: str, variant: str) -> bool:
    """Strict scope matching for closure checking. An empty row scope field
    (workspace-scoped edge) is a wildcard and matches any filter - but a
    *scoped* row requires the corresponding explicit filter: an omitted
    filter never means "all scopes", or outcomes from different scopes
    would merge under one run again. Pure - unit-tested."""
    for field, wanted in (("Project", project), ("Person", person), ("Route variant", variant)):
        have = rec.get(field, "").strip()
        wanted = (wanted or "").strip()
        if have and not wanted:
            return False
        if have and have.casefold() != wanted.casefold():
            return False
    return True


def fetch_outcomes(services, run_id: str, project: str = "", person: str = "",
                   variant: str = "", all_scopes: bool = False) -> list[dict]:
    """All rows for a run, as dicts keyed by HEADER, in sheet (append)
    order. By default strict single-scope matching (row_matches_scope);
    `all_scopes=True` is the unfiltered listing mode for humans - the
    strict closure checker must never use it. Read-only: a missing sheet
    is just an empty result, never created here."""
    from sync_m2_source_docs_to_sheets import read_sheet_values
    sheet = find_sheet(services)
    if not sheet:
        return []
    rows = read_sheet_values(services, sheet["id"])
    out = []
    for row in rows[1:]:
        padded = list(row) + [""] * (len(HEADER) - len(row))
        rec = dict(zip(HEADER, padded))
        if rec["Run ID"] != run_id:
            continue
        if not all_scopes and not row_matches_scope(rec, project, person, variant):
            continue
        out.append(rec)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)

    rec = sub.add_parser("record", help="record one edge outcome")
    rec.add_argument("--run-id", required=True)
    rec.add_argument("--source", required=True, help="graph source node of the edge")
    rec.add_argument("--target", required=True, help="graph target node of the edge")
    rec.add_argument("--outcome", required=True,
                     choices=sorted({o for v in VALID_OUTCOMES.values() for o in v}))
    rec.add_argument("--reason", default="", help="required for no_change/gated")
    rec.add_argument("--project", default="")
    rec.add_argument("--person", default="")
    rec.add_argument("--variant", default="", help="source route variant (m1/m2/mixed/...)")
    rec.add_argument("--actor", default="agent")
    rec.add_argument("--dry-run", action="store_true", help="validate and print, write nothing")

    lst = sub.add_parser("list", help="list a run's outcomes")
    lst.add_argument("--run-id", required=True)
    lst.add_argument("--project", default="")
    lst.add_argument("--person", default="")
    lst.add_argument("--variant", default="")

    args = parser.parse_args()

    if args.cmd == "record":
        kind = edge_kind(args.source, args.target)
        validate(kind, args.outcome, args.reason)
        require_scope(args.source, args.target, args.project, args.person)
        row = [args.run_id, dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
               args.project, args.person, args.variant,
               args.source, args.target, kind, args.outcome, args.reason, args.actor]
        if args.dry_run:
            print("VALID (dry run, not written):")
            for key, val in zip(HEADER, row):
                if val:
                    print(f"  {key}: {val}")
            return 0
        from pipeline_common import get_services
        services = get_services()
        sheet = get_or_create_sheet(services)
        services["sheets"].spreadsheets().values().append(
            spreadsheetId=sheet["id"], range="A1", valueInputOption="RAW",
            body={"values": [row]}).execute()
        print(f"Recorded: {args.source} -> {args.target} [{kind}] = {args.outcome}"
              + (f" ({args.reason})" if args.reason else ""))
        return 0

    from pipeline_common import get_services
    services = get_services()
    # Listing is for humans: with no scope args, show every scope of the run
    # (unfiltered mode); with scope args, apply the same strict matcher the
    # checker uses so what you list is what the checker would see.
    unfiltered = not (args.project or args.person or args.variant)
    rows = fetch_outcomes(services, args.run_id, args.project, args.person,
                          args.variant, all_scopes=unfiltered)
    if not rows:
        print(f"No outcomes recorded for run {args.run_id!r}.")
        return 1
    for rec_ in rows:
        scope = " / ".join(x for x in (rec_["Project"], rec_["Person"]) if x)
        print(f"  {rec_['Source node']} -> {rec_['Target node']:28s} "
              f"[{rec_['Edge kind']}] {rec_['Outcome']}"
              + (f"  ({rec_['Reason']})" if rec_["Reason"] else "")
              + (f"  @{scope}" if scope else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
