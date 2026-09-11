"""Publish this M2's per-project artifacts into the department's shared folder.

The QA department keeps every M2/DC's artifacts in one place so Head, RM, M5
and peers can find them without asking: the shared drive **QA Common**, folder
**"M2 / DC Projects AQA"**, one folder per project named `<Project>_<Surname>`.

What lands there are Drive **shortcuts**, never moves or copies. The whole
pipeline resolves these documents by their path under
`20_M2_Project_Management/<Project>/`, so moving them would break every script
and skill that walks that tree, and copies would go stale the moment a skill
rewrites the original. A shortcut keeps one live document with one owner.

A shortcut alone is not enough: it opens only if the *target* is shared, and
these documents are private to the M2 by default. So every published target is
also granted `reader` to the department groups that hold the shared drive.
Publishing is those two steps together; `--unpublish` reverses both.

Only the *safe* artifact types go out. The audience here is the entire QA and
AQA department, far wider than the M2 workspace's own audience, so anything
carrying personal judgments, compensation, or client-escalation detail
(`project_risk`, `individual_risk`, `individual_metrics`,
`individual_development_plan`, `m2_input`, `evidence_log`) is deliberately not
published. Widening `ARTIFACTS` is a disclosure decision, not a config tweak.

Closed projects are excluded by reading each project's own
`private/project_metrics` `Статус проекта` row, the canonical binary field
(`Активен` / `Не активен`) that `refresh_project_registry.py` already gates on.
`_project_registry` is deliberately not the source: it carries an `Engagement
outlook` prose cell, not a status column. The read fails closed - if the sheet
or the row cannot be read, the project is treated as closed and skipped, since
wrongly publishing a closed project department-wide is the costlier error.

The M2 surname used in the `<Project>_<Surname>` folder name comes from the
`QA_DEPT_SURNAME` environment variable; it is a real person's name and so is
never hardcoded here (see AGENTS.md, "No Sensitive Data In This Repository").

Every Drive call needs `supportsAllDrives`/`includeItemsFromAllDrives`: the
destination is a shared drive, and a plain `files().create()` against it fails
with a bare 404 that looks like a wrong folder id.

Usage:
    python publish_department_artifacts.py                  # dry run: what would change
    python publish_department_artifacts.py --apply
    python publish_department_artifacts.py --verify         # audit what is published now
    python publish_department_artifacts.py --unpublish Mondia --apply
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pipeline_common  # noqa: E402

DEPARTMENT_FOLDER_ID = "1c9XmjoqN9ajURJot4bHnrgHeJJYyyzAJ"  # "M2 / DC Projects AQA" on QA Common
DEPARTMENT_GROUPS = ("qa@innowise.com", "aqa@innowise.com")
SURNAME = os.environ.get("QA_DEPT_SURNAME", "").strip()

FOLDER_MIME = "application/vnd.google-apps.folder"
SHORTCUT_MIME = "application/vnd.google-apps.shortcut"

M2_LANE = "20_M2_Project_Management"
# (subfolder under the project, document name) - read the docstring before adding to this.
ARTIFACTS = (
    ("private", "project_development_plan"),
    ("private", "project_metrics"),
    ("team_shared", "qa_process_metrics"),
)
# Not a project folder: the M2's own cross-project workspace.
NOT_A_PROJECT = frozenset({"M2"})
PROJECT_METRICS_STATUS_ROW = "Статус проекта"
INACTIVE_STATUS = "Не активен"


def children(drive: Any, parent: str, name: str = "") -> list[dict[str, Any]]:
    q = "'%s' in parents and trashed=false" % parent
    if name:
        q += " and name='%s'" % name.replace("'", "\\'")
    return drive.files().list(
        q=q, pageSize=200, fields="files(id,name,mimeType,shortcutDetails)",
        supportsAllDrives=True, includeItemsFromAllDrives=True,
    ).execute().get("files", [])


def child(drive: Any, parent: str, name: str) -> dict[str, Any] | None:
    found = children(drive, parent, name)
    return found[0] if found else None


def workspace_projects(drive: Any) -> list[dict[str, Any]]:
    root = drive.files().list(
        q="name='QA_Management' and mimeType='%s' and trashed=false" % FOLDER_MIME,
        fields="files(id,name)", supportsAllDrives=True, includeItemsFromAllDrives=True,
    ).execute()["files"][0]["id"]
    lane = child(drive, root, M2_LANE)
    if not lane:
        raise SystemExit("no %s under the workspace root" % M2_LANE)
    return sorted(
        (f for f in children(drive, lane["id"])
         if f["mimeType"] == FOLDER_MIME and f["name"] not in NOT_A_PROJECT),
        key=lambda f: f["name"],
    )


def project_artifacts(drive: Any, project_id: str) -> list[dict[str, Any]]:
    found = []
    for sub, name in ARTIFACTS:
        folder = child(drive, project_id, sub)
        if not folder:
            continue
        doc = child(drive, folder["id"], name)
        if doc:
            found.append(doc)
    return found


def grant_reader(drive: Any, file_id: str, apply: bool, label: str) -> int:
    """Give the department groups read access to one shortcut target."""
    current = {p.get("emailAddress"): p for p in drive.permissions().list(
        fileId=file_id,
        fields="permissions(id,emailAddress,role)").execute().get("permissions", [])}
    granted = 0
    for group in DEPARTMENT_GROUPS:
        if current.get(group, {}).get("role") == "reader":
            continue
        print("   share %s -> %s%s" % (label, group, "" if apply else " (dry-run)"))
        if apply:
            drive.permissions().create(
                fileId=file_id, sendNotificationEmail=False, fields="id",
                body={"type": "group", "role": "reader", "emailAddress": group},
            ).execute()
        granted += 1
    return granted


def revoke_reader(drive: Any, file_id: str, apply: bool, label: str) -> None:
    for perm in drive.permissions().list(
            fileId=file_id,
            fields="permissions(id,emailAddress)").execute().get("permissions", []):
        if perm.get("emailAddress") in DEPARTMENT_GROUPS:
            print("   revoke %s <- %s%s"
                  % (label, perm["emailAddress"], "" if apply else " (dry-run)"))
            if apply:
                drive.permissions().delete(fileId=file_id, permissionId=perm["id"]).execute()


def is_closed(services: dict[str, Any], project: dict[str, Any]) -> bool:
    """True when the project's own project_metrics says it is inactive.

    An absent row (or an absent sheet) means active, the same default
    `refresh_project_registry.py` applies - most projects simply never set
    the row, and treating that as closed would silently drop live projects.
    An API/permission error is different: the status is genuinely unknown,
    so it fails closed, because publishing a closed project department-wide
    is the costlier mistake.
    """
    try:
        private = child(services["drive"], project["id"], "private")
        if not private:
            return False
        sheet = child(services["drive"], private["id"], "project_metrics")
        if not sheet:
            return False
        rows = services["sheets"].spreadsheets().values().get(
            spreadsheetId=sheet["id"], range="A1:Z200").execute().get("values", [])
        for row in rows:
            if len(row) > 3 and row[2].strip() == PROJECT_METRICS_STATUS_ROW:
                return row[3].strip() == INACTIVE_STATUS
        return False
    except Exception as exc:  # noqa: BLE001 - deliberate fail-closed
        print("[status?] %s - could not read %s (%s), treating as closed"
              % (project["name"], PROJECT_METRICS_STATUS_ROW, exc))
        return True


def publish(services: dict[str, Any], apply: bool, only: set[str]) -> None:
    drive = services["drive"]
    for project in workspace_projects(drive):
        name = project["name"]
        if only and name not in only:
            continue
        if not only and is_closed(services, project):
            print("[closed] %s - not published" % name)
            continue
        folder_name = "%s_%s" % (name, SURNAME)
        artifacts = project_artifacts(drive, project["id"])
        if not artifacts:
            print("[empty] %s - no publishable artifacts" % folder_name)
            continue

        dest = child(drive, DEPARTMENT_FOLDER_ID, folder_name)
        if dest and dest["mimeType"] != FOLDER_MIME:
            dest = None
        if not dest:
            print("[create] %s%s" % (folder_name, "" if apply else " (dry-run)"))
            if apply:
                dest = drive.files().create(
                    body={"name": folder_name, "mimeType": FOLDER_MIME,
                          "parents": [DEPARTMENT_FOLDER_ID]},
                    fields="id,name,mimeType", supportsAllDrives=True).execute()
            else:
                dest = {"id": ""}
        else:
            print("[ok] %s" % folder_name)

        linked = {c.get("shortcutDetails", {}).get("targetId")
                  for c in (children(drive, dest["id"]) if dest["id"] else [])}
        for doc in artifacts:
            label = "%s/%s" % (folder_name, doc["name"])
            if doc["id"] not in linked:
                print("   link %s%s" % (label, "" if apply else " (dry-run)"))
                if apply:
                    drive.files().create(
                        body={"name": doc["name"], "parents": [dest["id"]],
                              "mimeType": SHORTCUT_MIME,
                              "shortcutDetails": {"targetId": doc["id"]}},
                        fields="id", supportsAllDrives=True).execute()
            grant_reader(drive, doc["id"], apply, label)


def unpublish(drive: Any, apply: bool, names: set[str]) -> None:
    """Trash a project's department folder and revoke the access publishing granted.

    Trash rather than delete: the folder holds only shortcuts, but a wrong name
    on the command line should still be recoverable from the shared drive's trash.
    """
    wanted = {"%s_%s" % (n, SURNAME) for n in names}
    seen = set()
    for folder in children(drive, DEPARTMENT_FOLDER_ID):
        if folder["name"] not in wanted:
            continue
        seen.add(folder["name"])
        for shortcut in children(drive, folder["id"]):
            label = "%s/%s" % (folder["name"], shortcut["name"])
            target = shortcut.get("shortcutDetails", {}).get("targetId")
            if target:
                revoke_reader(drive, target, apply, label)
            print("   trash %s%s" % (label, "" if apply else " (dry-run)"))
            if apply:
                drive.files().update(fileId=shortcut["id"], body={"trashed": True},
                                     supportsAllDrives=True).execute()
        print("[trash] %s%s" % (folder["name"], "" if apply else " (dry-run)"))
        if apply:
            drive.files().update(fileId=folder["id"], body={"trashed": True},
                                 supportsAllDrives=True).execute()
    for missing in sorted(wanted - seen):
        print("[absent] %s - nothing published under that name" % missing)


def verify(drive: Any) -> int:
    """Audit every published folder: does each shortcut resolve, and can the department open it?"""
    problems = 0
    for folder in sorted(children(drive, DEPARTMENT_FOLDER_ID), key=lambda f: f["name"]):
        if not folder["name"].endswith("_%s" % SURNAME):
            continue
        print(folder["name"])
        for shortcut in sorted(children(drive, folder["id"]), key=lambda f: f["name"]):
            target = shortcut.get("shortcutDetails", {}).get("targetId")
            if not target:
                print("   BAD  %s - not a shortcut" % shortcut["name"])
                problems += 1
                continue
            meta = drive.files().get(
                fileId=target,
                fields="name,webViewLink,permissions(emailAddress,role)").execute()
            roles = {p.get("emailAddress"): p.get("role") for p in meta.get("permissions", [])}
            ok = all(roles.get(g) == "reader" for g in DEPARTMENT_GROUPS)
            problems += 0 if ok else 1
            print("   %s %s -> %s"
                  % ("OK  " if ok else "BAD ", shortcut["name"], meta["webViewLink"]))
    print("\nproblems: %d" % problems)
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--apply", action="store_true",
                    help="actually write; without it every action is a dry run")
    ap.add_argument("--verify", action="store_true",
                    help="audit what is published now and exit non-zero on any broken entry")
    ap.add_argument("--only", nargs="+", metavar="PROJECT", default=[],
                    help="publish just these projects (overrides the closed-project skip)")
    ap.add_argument("--unpublish", nargs="+", metavar="PROJECT", default=[],
                    help="trash these projects' department folders and revoke their group access")
    args = ap.parse_args()

    services = pipeline_common.get_services()
    drive = services["drive"]
    if not SURNAME:
        raise SystemExit(
            "QA_DEPT_SURNAME is not set - it supplies the <Project>_<Surname> "
            "folder name and is deliberately not hardcoded in this repository.")
    if args.verify:
        return 1 if verify(drive) else 0
    if args.unpublish:
        unpublish(drive, args.apply, set(args.unpublish))
        return 0
    publish(services, args.apply, set(args.only))
    if not args.apply:
        print("\ndry run - nothing written; rerun with --apply")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
