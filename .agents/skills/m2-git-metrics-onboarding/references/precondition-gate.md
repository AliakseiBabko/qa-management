# Precondition Gate

Scope: the three items that must be recorded in a person's
`_metrics_collector_registry` row **before** a metrics key is issued for
that (person, project) pair. Load this module on every issue pass, and
re-check items 1 and 3 on any project whose authorization basis is older
than the current engagement.

## Why There Is A Gate At All

Issuance is the irreversible step. The collector does not measure the
operator: every code path records **every contributor** it finds in the
repos it discovers, with no configuration switch to limit collection to
the operator's own commits. The app stores those contributors under their
real git display names; the anonymisation described in the collector's own
documentation applies only at the boundary with the app's LLM summariser,
not to storage or to the UI. So the moment a key is used, named activity
data about people who never opted in - including client-side contributors
- exists in a third-party system.

That is a legal/HR question, not a tooling one. This gate does not answer
it. It refuses to let it stay unanswered while keys go out, and it keeps
the answer attached to the row it justifies.

This reasoning is what item 1 protects against, and it is why the item is
about *third parties* rather than about paperwork. Where there is no third
party in the payload - an operator measuring only their own commits - the
item has nothing to protect and is replaced by the test that establishes
that fact. See "Which Variant Applies" below.

## Which Variant Applies

Establish the lane first (see SKILL.md's "Two Lanes"):

| Lane | Item 1 | Item 2 | Item 3 |
| :--- | :--- | :--- | :--- |
| **IC self-report** | Replaced by the self-only scope test below | Applies, and carries the whole weight | Applies (recorded, non-blocking) |
| **M2 issuance** | Applies in full | Applies in full | Applies (recorded, non-blocking) |

## Item 1, IC Variant - The Self-Only Scope Test

On the IC self-report lane there is no third party to authorize, so there
is no authorization question. What there is instead is a factual claim -
"this submission is about me only" - which the tool does not enforce and
which the scope either satisfies or does not. Test it rather than assert
it, and test it with **the collector's own dry run**, which is the only
authority on what it will actually send:

```bash
python collect.py --config config.toml --dry-run
```

Read the `contributors[]` list in the printed payload. Every entry must be
the operator. One extra name means the submission is not a self-report,
and the pass moves to the M2 variant below - not because a rule says so,
but because other people's named data is genuinely in the payload.

> [!CAUTION]
> **Do not reimplement this test in git, and do not scope it to a branch.**
> Contributor discovery runs `git log --all`, walking **every ref in the
> repository** - not the graded branch. The graded branch only governs
> review hygiene, churn and PR counting; it has no effect on *whose* data
> is submitted. A branch-scoped check therefore returns a self-only answer
> that the collector then contradicts: on a real repository, a check
> against the graded branch found one contributor while the dry run sent
> twelve. Choosing a different branch cannot make a submission self-only.
> The only lever on the contributor set is **which repositories are in
> scope**, and a single repository is routinely enough to pull in a dozen
> people.

Re-run the dry run whenever the scope or the team changes. A repository
that is self-only this month stops being self-only the moment anyone else
pushes any branch, and nothing in the tool will announce that.

Where the dry run shows other contributors and the scope cannot be
narrowed further, there is no self-only configuration available for that
project. That is an answer, not an obstacle: it means the honest options
are the M2 variant's authorization route, or not submitting that project.

Record in `Auth basis`: `IC self-report - self-only scope verified
YYYY-MM-DD (<n> contributors: operator only)`.

Two things the IC lane does **not** relax:

- **Item 2 still applies, and matters more here, not less.** On this lane
  the scoped root is the *only* thing keeping a self-report self-only. A
  root one level too wide turns "measuring myself" into submitting a
  team's profiles under the operator's own key.
- **The validity caveats still apply.** Self-reported numbers still get
  read - by the operator, by the app's org-wide table, possibly by a
  future self-review. A checkout-dependent commit count or a false
  direct-to-main chip is just as wrong when it is about the operator as
  when it is about someone else.

## Item 1, M2 Variant - Authorization Basis

**Record**: `YYYY-MM-DD - <role who authorized> - <scope authorized>` in
the row's `Auth basis` column.

The question to get answered, per project, is narrow: *is there
authorization to collect and store named per-contributor activity for the
contributors visible in `<Project>`'s repositories, including
contributors who are not our employees?* An answer needs a named
authorizing role (department head, HR, legal, or the client contact who
can speak for the client's own staff), a date, and a scope - most
usefully whether it covers only our own staffed engineers or also
client-side and third-party-vendor contributors.

- Unanswered, or answered only as an informal "should be fine": record
  `Не подтверждено` and stop. The row is `Blocked (gate)`.
- Answered for our own staff only: that is a real answer, and it
  constrains item 2 - the collector root must resolve only to
  repositories where our own engineers are the contributors, which in
  practice is rarely a client repo.
- Answered in full: record it, and note the review date if the
  authorization is time-bounded.

Route an unanswered item as a question into the project's `m2_input`
round (never straight into `project_risk`) plus a dated follow-up in
`action_items`. It is M2's own open item, not a chase against the person
waiting for a key.

## Item 2 - Scoped Collector Root Confirmed

**Record**: `Y (<n> repos)` or `N` in `Scoped root confirmed`, and the
enumerated repos' facts per `collector-bugs.md`.

The collector auto-discovers every git repository beneath its configured
root, several levels deep. A developer's top-level code folder is
routinely a flat tree of dozens of repositories spanning several
unrelated clients; pointing one project's key at it sweeps every one of
those clients' contributors into that single project's submission. This
is the single most likely way the rollout causes a real incident, and it
is silent - the submission succeeds and looks normal.

So: the root is scoped **per client**, the discovered repository list is
enumerated and read before the first submission, and it is confirmed that
every repository on it belongs to `<Project>`. Anything unexpected on the
list means the root is wrong; fix the root, do not exclude repositories
one by one.

An unconfirmed scope is a `Blocked (gate)` row even when item 1 is
answered - authorization for `<Project>` is not authorization for
whatever else happens to sit in the same folder.

## Item 3 - Downstream Use Of The Data

**Record**: the answer, and its date, in `Notes`.

**This is now answered, and the answer is yes.** The app's bonus model
declares an activity-source enum whose values include `metrics_collection`
alongside `weekly_report`, `onboarding`, `offboarding` and `manual`, and
its manager-bonus payload carries per-activity bonus lines with
coefficients, counts and amounts. So metrics collection is a
compensation-relevant activity, and on the manager side rather than the
engineer's: the person issuing keys and chasing submissions has a
financial interest in the submission count going up.

That does not make the rollout improper, but it changes two things
permanently:

- **Disclosure stops being a courtesy.** An engineer asked to install a
  collector by someone whose bonus is affected by their compliance is
  entitled to know that before agreeing, not after. The install handoff
  says it plainly, in the operator's own words.
- **The engineer-side question stays open.** The enum establishes a
  manager-side link; it does not establish whether an engineer's own
  figures affect the engineer's own compensation or evaluation. That
  remains a question for the app owner, and until answered:

- Treat collector output as **non-compensating**, and say so plainly in
  the install handoff. A person agreeing to run a measurement tool is not
  the same as a person agreeing to be paid according to it.
- Do not use collector output in `salary-review-prep`, `m-self-review`
  team scoring, or any other compensation-adjacent artifact.

This item does not block issuance on its own the way items 1 and 2 do -
but the disclosure in the handoff is not optional, the manager-side
compensation link is always disclosed, and any part of item 3 still
unresolved must appear in the handoff too.

## Gate Output

| Lane | State | Result |
| :--- | :--- | :--- |
| Either | Items 1 and 2 recorded, item 3 recorded or explicitly pending | Proceed to issuance; carry item 3's state into the handoff |
| IC | Self-only test shows another contributor | Not a self-report - re-run the pass on the M2 variant |
| M2 | Item 1 or 2 open | `Blocked (gate)` row, `m2_input` question, `action_items` follow-up, no key |

Never issue a key on the M2 lane with a `Blocked (gate)` row on the
promise of closing the gate afterwards. On the IC lane, never record a
self-only claim that was asserted rather than tested - the test is one
command.
