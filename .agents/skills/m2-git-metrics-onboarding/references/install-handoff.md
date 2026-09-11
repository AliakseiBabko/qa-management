# Per-Person Install Handoff

Scope: how to produce the instructions `<Person>` follows on their own
machine, and the disclosure that goes with them. Load this module on an
issue pass only (SKILL.md workflow step 5), not on a verify, triage or
revoke pass.

The handoff is one message, written in the language the person actually
works in. It has to survive being read once, on a busy day, by someone
who will not come back to ask questions - which means the caveats go in
the body, not in a footnote.

## Before Writing It

Three things must already be true, or the handoff is premature:

1. The gate is closed (`precondition-gate.md`) and the key is issued.
2. The scoped collector root is fixed and its discovered repository list
   has been read.
3. The per-repository trunk and merge-strategy checks from
   `collector-bugs.md` are done, and the row's `Metrics validity` is set.

Item 3 is what the handoff's caveat section is built from. Writing the
handoff first and checking the repositories afterwards produces the one
outcome this skill exists to prevent: a person running the collector and
reading their own red chip before anyone has told them it is an artifact.

## Structure

**1. What this is, in two sentences.** A git activity collector run
locally that submits aggregated per-contributor statistics to an internal
app at `<app-host>`, for `<Project>`. Name the cadence expected of them.

**2. Disclosure - what it transmits.** Not a link to the collector's
README; the README understates it in four places (see
`collector-behavior.md`). State plainly:

- It collects **every contributor** in the repositories in scope, not just
  them. There is no setting to limit it to their own commits.
- Contributors are stored and displayed **under their real git names**.
  The anonymisation the README mentions applies only where the app sends
  data to its LLM summariser, not to storage or the UI.
- What per-contributor fields go: commits, insertions/deletions, PR counts
  and sizes, file extensions touched, a 24-hour work-hour distribution,
  weekly/daily commit counts, cycle times, a review-hygiene split, churn.
- **That the manager asking has a stake in their compliance.** The app
  counts metrics collection as a bonus-bearing activity on the manager
  side, so the person requesting the install benefits from the request
  being honoured. Say so in the operator's own voice. It is awkward and it
  is exactly the thing an engineer is entitled to know before agreeing;
  omitting it is what would make the rollout improper rather than merely
  uncomfortable.
- Whether the engineer's **own** figures feed their own compensation or
  evaluation: state gate item 3's current answer, and where it is still
  unresolved, say that it is unresolved and that the data is being treated
  as non-compensating for them until answered.

Record the date this was delivered in the registry's `Person informed`
column. That column is the evidence the disclosure happened; an undated
row means it did not.

**3. Prerequisites.** Python 3.11 or newer on PATH (3.14 has been
verified); no package installation needed. The collector source, from
`<collector-source-dir>`, kept **outside** any client repository - and
give the real reason, which is that a metrics tool has no business in a
client's version control, not the collector guide's framing about hiding
it. Do not reproduce the guide's advice about dropping the client VPN
before submitting; if the submission cannot reach `<app-host>` from the
project's normal network, that is a question for the gate, not a step for
the person.

**4. Configuration.** Their key (delivered over a credential channel, not
in this message), and their **scoped collector root** - given as the exact
path, per client, already decided in step 5 of the workflow. Tell them
explicitly not to point it at their whole code folder, and why: it
auto-discovers every repository several levels down and would attribute
other clients' contributors to `<Project>`. If they later reorganise their
checkouts, they come back to M2 rather than re-pointing it themselves.

**5. Run and confirm.** How to run it, and what a successful submission
looks like. Ask them to tell M2 when the first run completes, so
verification (workflow step 6) is not a guess.

**6. Caveats that apply to them specifically.** Only the ones their own
repositories actually trigger, from `Metrics validity`:

- **`Branch-dependent`** - name the repositories whose trunk the collector
  cannot detect, and what it grades instead. If they have to keep the
  trunk checked out before each run, say so as a step, not as background.
- **`Direct-to-main unreliable`** - tell them, in advance, that the app
  will probably show a high "direct to main" figure and a red chip for
  them, that it is a known defect in how the tool detects squash merges,
  that M2 has it recorded, and that it will not be used to assess them.
  A person who sees that chip first, unwarned, is entitled to conclude
  the whole exercise is being run against them.
- **`Reliable`** - say that too. It is short, and it means the caveats
  section is meaningful rather than boilerplate.

**7. Who to come back to.** M2, by name, for anything: a lost key, a
changed repository set, a number that looks wrong, or a decision to stop.

## Guardrails

- **Never put the secret in this message.** Separate channel, always.
- **Never present the collector guide's VPN or parent-level-`.gitignore`
  advice as neutral setup.** See `collector-behavior.md`'s closing
  section; one of the two has a real technical reason and the other is a
  gate question.
- **Never omit the caveat section because the person is senior**, or
  because the chip "will probably be obvious". The registry's
  `Person informed` date is a claim that they were told everything in
  sections 2 and 6.
- **Never write the handoff for someone whose row is `Blocked (gate)`.**
  There is nothing to hand off; the open item is M2's.
- Keep it short and direct, one message, no separate onboarding document -
  the caveats are the length, not the surrounding prose.
