# Metrics Key Lifecycle

Scope: the app's key API surface and UI path, secret handling, and the
full issue / verify / rotate / revoke lifecycle with its triggers. Load
this module on any issue, verify or revoke pass.

## Identity Model

A key is scoped to a **(person, project) pair**, not to a person. The same
person on two projects has two keys, two key prefixes and two registry
rows, and revoking one leaves the other working. This matches the app's
submission model (one POST per project) and it is what makes a clean
project-exit revocation possible without cutting the person off from
projects they are still on.

A person must **already be on the project's Team** in the app before a key
can be issued. An Admin can issue directly; no project manager is
required, and a project with no manager assigned does not block issuance.

**Issuance is gated to the project's own manager (or an Admin), not to the
grade.** Verified 2026-09-03: reading or creating a key on a project the
caller does not manage returns `403 Not a manager of this project`, even
for an M2 who can see the project in the list. So an M2 asked to onboard
someone onto a project managed by a different person cannot issue that
key, and must either be added as a manager of that project or ask the
Admin to issue it. Record who actually issued the key in the registry
row - on a project M2 does not manage, the issuer is someone else, and
that also means someone else can read the secret back at any time.

A person on the `member` role cannot issue their own key and does not see
the metrics-keys panel at all: the app renders it only for a caller with
manage rights on the project. Any instruction telling the engineer to
generate their own key on the Team tab is wrong.

## API Surface

Issue and revoke are both project-scoped:

- **Issue** - POST to the project's metrics-keys collection
  (`/projects/{project_id}/metrics/keys`), body carrying the employee
  identifier and a label. The response is the only place the **secret**
  ever appears, alongside the key prefix, an active flag, and a last-used
  timestamp.
- **Revoke** - DELETE the specific key under the same collection
  (`/projects/{project_id}/metrics/keys/{key_id}`).
- **Submissions** use the key as a bearer token against the
  metrics-submission endpoint; the key's last-used timestamp is what moves
  when a run lands.

UI equivalent: project, then its Team tab, expand the person's row, then
Metrics keys, then Generate. Either route is fine; the API route is
preferable when issuing several keys in one pass, because it makes the
label consistent and leaves less room for issuing against the wrong row.

Give every key a **label that names the pair and the issue date**, so a
key list in the app is readable without the registry next to it. The key
prefix itself already encodes the person, but not the project or the
vintage.

## Secret Handling

**The secret is not write-once.** Verified 2026-09-03 against the app's
own API description: the key-listing response is documented as returning
the **decrypted secret** to managers and admins "so they can re-share it",
and the project's authorization is the only thing gating who reads it. So
the secret stays retrievable for the life of the key by anyone who manages
that project, and by every Admin.

Two consequences, both the opposite of what a write-once model would give:

- A lost secret does **not** require rotation - it can be read back from
  the key list. Rotate only for the triggers below.
- The blast radius of a key is wider than the person holding it. Every
  current and future manager of that project, plus every Admin, can read
  it at any time without leaving a trace in the registry. Treat "who could
  read this key" as a project-level answer, not a per-person one.

Handling, unchanged by that:

- It goes to the person over a channel they already use for credentials,
  and into their local collector config. Nowhere else.
- It never goes into `_metrics_collector_registry`, any other Drive
  document, this repository, a commit message, a status report, or chat
  scrollback. The registry stores the **prefix** only, which is enough to
  match a row to a key in the app and useless as a credential.
- A lost secret is re-read from the app's key list by whoever manages the
  project, and re-shared. Never write it down anywhere retrievable of our
  own making: the app is already the retrievable copy, and a second copy
  only adds a place to leak from.
- A secret that has been pasted anywhere shared is a leak, and a leak is a
  revoke trigger regardless of how unlikely misuse seems.

## Lifecycle

### Issue

Gate first (`precondition-gate.md`), team membership second, key third,
scope and validity fourth, handoff fifth, verification sixth. The order is
not cosmetic: the gate precedes the key because the key is the
irreversible step, and the scope work precedes the handoff because the
handoff has to state the caveats the scope work discovers.

Record on issue: person, project, employee identifier, key prefix, issue
date, issuer, and `Status = Issued`.

### Verify

Confirm the first submission actually landed - a submission exists for
that (person, project) and the key's last-used timestamp has moved.
Record `Last submission seen` and move `Status` to `Submitting`.

If nothing landed, record `Status = No submission` **with a named
reason**, not as a bare state. The reason is what makes the monthly gap
triage tractable; without it, a silent row is indistinguishable from an
unfinished handoff.

### Rotate

Rotation is a revoke plus an issue, and it keeps the same registry row -
update the key prefix and issue date, and note the rotation in `Notes`.
Rotate when:

- the secret may have been exposed (pasted into a shared channel, a
  ticket, a screenshot, a shared machine);
- the person's machine changed hands or was reimaged;
- a key's last-used timestamp has been stale long enough that nobody can
  say whether it is still in use anywhere.

### Revoke

Revoke, and record the date and reason, when:

- the person **rolls off the project**. Per-project scoping is what makes
  this precise: revoke that project's key only. This is the single most
  commonly forgotten trigger, because nothing in the app prompts for it.
- the person is **offboarded** - revoke every key they hold, across every
  project.
- a **leak** is suspected and rotation is not enough (for instance, the
  person no longer needs the collector at all).
- the project's **authorization basis has lapsed** - gate item 1 was
  time-bounded and its review date has passed without renewal. An expired
  basis is not a paperwork problem; the collector is still transmitting
  named third-party data under an authorization that no longer exists.
- the project **ends**, or its repositories move out of scope.

Keep the row after revocation, with `Status = Revoked`, the date and the
reason. The registry's value is partly historical: it answers who could
submit what, when, which is exactly the question that gets asked after the
fact and cannot be reconstructed from a row that was deleted.

## Offboarding Interaction

An offboarding or project replacement handled through
`m2-offboarding-report` / `m2-replacement-report` does **not**
automatically revoke anything - those skills produce reports, not tool
administration. Revocation is this skill's pass, and it needs to be
triggered explicitly. A leaver whose key still works is the failure mode
this section exists to prevent, so when an offboarding is in progress,
check the registry for that person's rows across every project rather than
only the project being reported on.
