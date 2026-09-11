# `_metrics_collector_registry` Contract

Scope: the location, ACL, identity model and column schema of the one
document this skill owns. Load this module on any pass that reads or
writes it.

## Location And Visibility

`20_M2_Project_Management\_metrics_collector_registry` - a single
workspace-wide Google Sheet at the M2 lane root, alongside
`_project_registry`, with a CSV fallback.

**Unshared - M2/M3 only**, the same ACL class as the optional
`_m2_risk_registry`. It is never shared with the people it has rows
about, and never with a project team: it carries per-person validity
judgments, authorization notes, and the reasons individual chips are
being disregarded. Sharing it would also put one project's authorization
basis in front of another project's team.

Cross-project by design. The alternative - a roster inside each
`<Project>/private/` - was considered and rejected: the question this
document exists to answer ("who is expected to submit, who has, and why
not") is inherently cross-project, and fanning it out across a dozen
project folders makes the monthly gap triage a dozen reads that can each
go stale independently.

## Identity Model

**One row per (Person, Project) pair.** Living, updated in place - not an
append-only log. A person on two projects has two rows; a revoked key
keeps its row rather than being deleted (see `key-lifecycle.md`).

This follows the current-state table default for new M2 per-person tables:
a row is the present truth about that pair, with history carried in the
dated columns (`Issued`, `Last submission seen`, `Revoked`) and in `Notes`,
not in extra rows.

## Columns

| # | Column | Content |
| :--- | :--- | :--- |
| 1 | `Person` | Name as in `_people_registry`, so the two cross-reference cleanly |
| 2 | `Project` | Project name as in `_project_registry` |
| 3 | `Lane` | `IC` (operator's own self-report) or `M2` (issued to someone else). Decides which gate variant applies and must never be changed to widen a row's permissions retroactively |
| 4 | `App employee id` | The app's own identifier for this person |
| 5 | `Key prefix` | Prefix only. **Never the secret** |
| 6 | `Issued` | `YYYY-MM-DD` |
| 7 | `Issued by` | Who issued it (an Admin acted; record which) |
| 8 | `Status` | `Blocked (gate)` / `Issued` / `Submitting` / `No submission` / `Stuck` / `Revoked` |
| 9 | `Auth basis` | `YYYY-MM-DD - <who> - <scope>`, or `Не подтверждено`. Gate item 1 |
| 10 | `Scoped root confirmed` | `Y (<n> repos)` / `N`. Gate item 2 |
| 11 | `Repos in scope` | The discovered repository list, or its count with the list in `Notes` |
| 12 | `Trunk branch` | Per repo: `<repo-a>: develop; <repo-b>: main` |
| 13 | `Trunk auto-detected` | `Y` / `N (graded on checkout)` |
| 14 | `Squash-merge` | `Y` / `N` / `Unknown` |
| 15 | `Review markers present` | `Y` / `N` |
| 16 | `Metrics validity` | `Reliable` / `Branch-dependent` / `Direct-to-main unreliable` / `Both` |
| 17 | `Person informed` | `YYYY-MM-DD` the disclosure was actually delivered |
| 18 | `Last submission seen` | `YYYY-MM-DD`, or blank |
| 19 | `Key last used` | The app's last-used timestamp for the key |
| 20 | `Revoked` | `YYYY-MM-DD - <reason>`, or blank |
| 21 | `Notes` | Gate item 3's answer and date, rotation history, per-repo detail too long for columns 11-15 |

Column 3 sets the lane; columns 9-10 are the gate; 12-16 are the validity
record; 17 is the disclosure record. None of the three groups is optional, and a row with a
key prefix but an empty column 17 is an incomplete onboarding regardless
of whether submissions are arriving. An `IC` row needs no separate
disclosure date - the operator is the person being informed - but its
self-only scope test date belongs in `Auth basis` all the same.

## Reading The Registry

- **`Status` answers "is data flowing".** `Metrics validity` answers "does
  the data mean anything". They are independent: a `Submitting` row with
  `Metrics validity = Both` is a person whose numbers arrive reliably and
  should not be used.
- **Gap triage** (SKILL.md workflow step 7) is a `Status` breakdown, and
  it distinguishes M2's own unfinished work (`Blocked (gate)`, or `Issued`
  with no `Person informed` date) from work waiting on the person
  (`Issued` and informed but never run) from tool failures (`Stuck`).
- **A validity caveat overrides the app.** When the app shows a chip or a
  risk level for a person whose row is not `Reliable`, the row is the
  answer given to anyone who asks, including the person.

## Maintenance

Recomputed by hand, on each pass, not by a script. There is deliberately
no refresh script: the columns that matter most (8, 9, 15, 16) are
judgment and disclosure records that cannot be derived from either the app
or the repositories, and a script that refreshed only the mechanical
columns would make the row look freshly verified when its judgment half
had gone stale.

Re-check on a project's normal review cadence, and always when: a person
joins or leaves a project, a project's repository set changes, a
repository's trunk or merge strategy changes, the authorization basis
reaches its review date, or the app's own behaviour changes (it is a
proof-of-concept build; the defects in `collector-bugs.md` may be fixed,
and a fixed defect is a reason to re-derive `Metrics validity` upward).
