---
name: m2-git-metrics-onboarding
description: Roll an external git-metrics collector out to the people on an M2 project - confirm the authorization/scope gate, register the person on the project team, issue and later revoke their per-(person, project) metrics key, hand them install instructions they can run themselves, and verify their submissions actually landed. Owns the workspace-wide `_metrics_collector_registry`. Use when onboarding or offboarding someone onto the collector, chasing an expected-vs-submitted submission gap, or deciding whether a collector-derived anomaly chip is trustworthy. Not for writing QA metrics documents - see m2-project-qa-metrics-report / m2-individual-qa-metrics-report.
---

# M2 Git Metrics Onboarding

Use this skill for one outcome family only: administering an **external**
git-metrics application (referred to here as the app, reachable at
`<app-host>`) for the people on M2's projects - roster, key lifecycle,
install handoff, and submission verification - plus the one workspace
document that records it, `_metrics_collector_registry`.

## Two Lanes, Two Rulesets

This skill covers two genuinely different situations, and applying one
lane's rules to the other is the main way it goes wrong.

- **IC self-report** - the operator measuring their **own** individual-
  contributor work on their own project. Their data, their consent. The
  authorization question that governs the other lane does not apply,
  because there is no third party to authorize. What replaces it is a
  *test*, not a waiver: see `references/precondition-gate.md`'s IC
  variant, which requires proving the scope submits nobody but the
  operator. "This is only about me" is a claim the scope either satisfies
  or does not, and it is cheap to check.
- **M2 issuance** - M2 issuing keys to the engineers on the projects in
  their own M2 folder. Other people's data, sometimes including
  client-side contributors. The full gate applies, unchanged, every time.

The same person routinely occupies both roles, on the same day, with the
same tool. Establish which lane a pass is in **before** reading the gate,
and record it in the registry row's `Lane` column. A project that belongs
to the operator's own IC work never becomes an M2-managed project just
because it has a collector key, and an M2 project never inherits the IC
lane's lighter gate because the operator happens to also commit to it.

## What This Is, And Isn't

- **Not** `m2-project-qa-metrics-report` or
  `m2-individual-qa-metrics-report`. Those two produce Drive Sheets
  (`project_metrics`, `individual_metrics`) from evidence M2 already
  holds. This skill produces no metrics content at all - it administers
  a third-party tool and records who has a key. Collector output is at
  most a *candidate input* to those two skills, and only after this
  skill has marked its `Metrics validity` as `Reliable` (see
  `references/collector-bugs.md`).
- **Not** an onboarding milestone report. `m2-onboarding-report` covers a
  new hire's Day-1 / final onboarding on a project. Issuing a tool
  credential is not a project onboarding milestone and does not belong in
  those reports.
- **Not** a wrapper that decides a person's risk level. The app computes
  its own risk level and per-employee anomaly chips. This skill's job
  around those is the opposite: to record which of them are known
  artifacts of collector bugs, so they do not get read as findings.

## Required Start

1. Establish the lane (IC self-report or M2 issuance) - see "Two Lanes"
   above. Then read `references/precondition-gate.md` **first** and apply
   that lane's variant of it; no key is issued until its items are
   recorded. Do not reorder this step.
2. Read `references/collector-behavior.md` (what the collector actually
   transmits, and where its own documentation understates it) and
   `references/collector-bugs.md` (the three verified defects that change
   whether a person's numbers mean anything).
3. Read `references/key-lifecycle.md` and `references/registry-contract.md`.
4. Read `../qa-management-roles/references/google-workspace/workspace-basics.md`, `../qa-management-roles/references/google-workspace/m2-layout.md`, `../qa-management-roles/references/google-workspace/artifact-conventions.md`, and `../qa-management-roles/references/google-workspace/api-sharing-editing.md`.
5. Read `references/install-handoff.md` too when actually producing the
   per-person instructions (workflow step 5), not on a
   registry-read-only or gap-triage pass.
6. Identify which of the four passes is being asked for: **issue**
   (register + gate + key + handoff), **verify** (did a submission
   land), **gap triage** (expected vs submitted across projects), or
   **revoke/rotate**.

## Workflow

### 1. Confirm the pass and the target

Establish `<Person>` and `<Project>` explicitly. A key is scoped to the
**(person, project) pair** - the same person on two projects needs two
keys and gets two registry rows. Never reuse one key across projects; the
app's own submission model is one POST per project.

### 2. Run the precondition gate for this lane

Per `references/precondition-gate.md`, using the variant that matches the
lane. On the **M2 issuance** lane, all three items recorded in the
registry row, or the pass stops here with a `Blocked (gate)` row and a
follow-up in the project's `action_items` (via `m2-timeline`). Do not
issue a key "provisionally" while a gate item is open - a key that exists
is a key that submits.

On the **IC self-report** lane there is no authorization question to
answer, but the self-only scope test and the scope confirmation still run,
and a scope that turns out to submit other contributors moves the pass to
the M2 lane rather than proceeding.

### 3. Confirm the person is on the project team

The app requires a person to already be on the project's Team before a
key can be issued. Confirm (or create) the team membership, and capture
the app's employee identifier for the registry row. If the project has no
manager assigned in the app, note it - it does not block issuance for an
Admin, but it does mean nobody but M2 is watching that project's
submissions.

### 4. Issue the key

Per `references/key-lifecycle.md`. Record the key prefix, issue date and
issuer in the registry. **Never write the secret to the registry, to any
Drive document, to this repo, or into chat scrollback** - it is shown
once and belongs only in the person's own local collector config. If the
secret is lost, revoke and reissue rather than trying to recover it.

### 5. Establish scope and validity, then hand off

Before the person's first submission, and with them:

1. Fix a **per-client scoped collector root** - never their whole code
   folder. This is both a correctness requirement and half of the gate
   (see the scope trap in `references/collector-bugs.md`).
2. Enumerate the repos that scoped root actually discovers, and for each
   one record its **real trunk branch**, whether the collector can
   detect that trunk, whether the repo squash-merges, and whether it
   carries stray review markers.
3. Derive the row's `Metrics validity` from those facts.
4. Produce the install instructions from
   `references/install-handoff.md`, including the disclosure paragraph -
   the person is told what the collector transmits about them *and about
   their peers* before they run it, not after.

### 6. Verify the submission landed

A key issued is not a submission received. After the person's first run,
confirm on the app side that a submission exists for that (person,
project) and that the key's last-used timestamp moved. Record
`Last submission seen`. An issue pass is not complete until this is
either confirmed or recorded as `No submission` with a named reason.

### 7. Gap triage (expected vs submitted)

When the app's admin view shows an expected-vs-submitted gap, work it
from the registry, not from the app's table - the registry is the only
place that knows *why* a given person has no submission. Sort each
missing person into one cause and route it:

- `Blocked (gate)` - authorization or scope item still open. Not a
  chase; it is M2's own open item.
- `Issued`, never run - the handoff was delivered but not executed.
  Follow up with the person.
- `Issued`, no handoff - M2's own miss. Complete step 5.
- `Submitting` previously, now silent - check for a revoked/rotated key,
  a changed collector root, or a person who has rolled off the project.
- `Stuck` / failed on the app side - a tool problem; report it to the app
  owner rather than chasing the person.

Report the gap as counts per cause. "Expected N, submitted M" with no
cause breakdown is not a useful answer, and it hides the fact that part
of the gap is usually M2's own unfinished work.

### 8. Revoke or rotate

Per `references/key-lifecycle.md`'s trigger list. Revocation is a normal
part of this skill, not an exception: a person rolling off a project, an
offboarding, a suspected leak, a key whose last-used timestamp has gone
stale, or a project whose authorization basis has lapsed. Record the date
and the reason; keep the row rather than deleting it, so the history of
who could submit what, when, survives.

## Cascade

`_metrics_collector_registry` is a workspace-wide M2 document. After a
write, check the two judgment edges (see `.agents/document_graph.yaml`):

- **`individual_metrics`** - only when `Metrics validity` is `Reliable`
  and the app's figures add something the project does not already know.
  A collector figure never enters a person's metrics as a bare number:
  it enters as an observation with its window and its scope named.
- **`action_items`** - an open gate item, an unfinished handoff, a
  stale-key rotation, or a gap-triage follow-up becomes a dated action
  via `m2-timeline`.

Log the pass in `evidence_log` (`source_type: admin_note`, per
`../qa-management-roles/references/google-workspace/operational-registries.md`)
and in `_skill_invocations`, and record closing telemetry with
`.agents\scripts\record_agent_session.py --append-csv`. Do not invent a
new `source_type` for collector administration.

## Guardrails

- **No secret, ever, anywhere but the person's own local config.** Not in
  the registry, not in a Drive doc, not in this repo, not in chat.
- **No real identity in this repo.** This repo is public (see AGENTS.md).
  The app host, the person, the project, the client, the repo names and
  the collector's install path are `<app-host>`, `<Person>`,
  `<Project>`, `<repo>`, `<collector-source-dir>` here, and real only in
  the Drive registry - in file content and commit messages alike.
- **Do not treat an app-side anomaly chip or risk level as evidence**
  until the registry says the underlying numbers are reliable for that
  person. Two of the app's chips are known false-positive generators.
- **Do not issue a key to unblock a deadline with a gate item open.**
  The gate exists because issuance is the irreversible step: once the
  collector runs, named third-party contributor data is already
  transmitted and stored.
- **Do not point a key at a repository whose trunk the collector cannot
  detect** without recording the resulting validity caveat. Silently
  accepting checkout-dependent numbers is how a person gets graded on a
  feature branch.
- **Do not feed collector output into anything compensation-adjacent**
  (salary review, bonus input, `m-self-review` team scoring) while gate
  item 3 is unresolved.
- Read-only passes (registry read, gap triage) write nothing to Drive and
  record no telemetry beyond `_skill_invocations` unless the user asks to
  save the result.
