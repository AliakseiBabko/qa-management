# Scoring Calibration

What each score on the 0-4 scale in `Templates/ai_adoption_review.md` actually
requires, per dimension, and the mis-scores that keep happening. Read before
scoring a session.

## The scale, restated precisely

| Score | Test it must pass |
|---|---|
| 0 | Absent and not considered. |
| 1 | Happens, by hand, per person, differently each time. No artifact. |
| 2 | A written artifact exists. Not enforced, not shared, possibly not current. |
| 3 | Relied on daily, and would survive its author being away for two weeks. |
| 4 | As 3, plus a mechanism that *proves* it held - a hook, a scoped permission, a run log, a quarantine step. |

The jump from 2 to 3 is durability. The jump from 3 to 4 is proof. Most
projects sit at 2 and describe themselves as being at 3.

## Recurring mis-scores

**Comparing configurations by consumption per attempt.** The measured result
inverts the naive reading: a configuration with less context is cheaper per
cycle but produces more cycles that fix nothing - 22% of all tokens in the
benchmark bought no fix. Anywhere a project justifies a choice on cost, check
whether the denominator is attempts or completions.

**Accepting a price per test on a subscription.** On a fixed subscription an
engineer meets a limit, not a per-request charge, so a dollars-per-test figure
is derived from assumptions about allowance size rather than measured. Score
the consumption question on tokens and on seat/allowance facts; treat a
confident per-test price on subscription billing as a sign the project has not
actually measured anything.

**Scoring the prompt, not the artifact.** A very good prompt re-typed into a
chat is 1. The question is whether an artifact exists that survives the
session, not how well the person prompts. Fifteen prompt variants tried against
a problem is evidence of 1, not of effort worth crediting.

**Scoring intention as implementation.** "We're planning hooks" is the current
score plus an entry in §L. This is the single most common inflation.

**Crediting a demonstration as a practice.** A skill that works when
demonstrated but that nobody else has run, and that the author last touched
months ago, is 2. Ask when it was last changed and on what trigger.

**Treating instruction text as enforcement (§E).** A written prohibition is 2 at
best. A project that has watched a prohibition be ignored and responded by
writing it in more places is still 2 - the response did not change the
mechanism. A hook, an approval mode, or a read-only connector is what reaches 4.

**Averaging a governance finding away.** Not a scoring error but the most
consequential one. §B findings are never scores, and a project with an open
finding cannot be tiered above *Individual practice* however strong §C-§K look.

**Penalising a correct decline (§C).** An automation target assessed and
declined because the task is already cheap, or has no stable repeating shape, is
not a coverage gap. Score coverage against routines worth covering. Only "not
considered" is a gap.

**Penalising an environment constraint (§H, §E).** A restricted project that
exports requirements by hand is at its permitted ceiling. Record the constraint
and score against what §B permits. The converse also holds: being at the
ceiling is not a 4.

**Scoring §I from the individual's answer alone.** "I shared it" is not
diffusion. Ask how a teammate would *discover* it exists, and whether a new
joiner would inherit a working setup or start over. A valuable setup nobody else
knows about is 0-1 on this dimension no matter how good it is - and that is
usually the highest-return recommendation available.

**Reading self-review as verification (§G).** An agent reviewing its own output
is not a verification loop. If the only check is the authoring agent's own
review pass, §G is 1.

## Per-dimension anchors

### C - Task coverage
- **1** AI used somewhere, ad hoc, no inventory of what it touches.
- **2** The team can name which routines it is in and which it is not.
- **3** Each uncovered routine has a stated reason from the four in the template.
- **4** As 3, and the reasons have been revisited since the last review.

### D - Reusable artifacts
- **1** Chat with re-pasted context; prompts kept in a personal note.
- **2** Artifacts exist. One growing file, or several with duplicated content.
- **3** Narrow, single-purpose, cross-referencing, revised on a cadence.
- **4** As 3, under version control, and demonstrably authored from real work
  rather than written speculatively.

### E - Enforcement
- **1** Nothing written; relies on the operator watching.
- **2** Prohibitions written in an instruction file or skill.
- **3** Approval mode set deliberately, integration permissions scoped read-only
  where possible, cross-chat memory disabled.
- **4** As 3, plus a hook or equivalent that fires deterministically on the
  thing that must not happen, and a case where it demonstrably caught something.

### F - Delegation
- **1** Delegation decided per task by feel.
- **2** The person can state the boundary consistently when asked.
- **3** The boundary is written in the root instruction file, three-way.
- **4** As 3, and a case exists where the boundary stopped something.

Ask what the largest single delegation was and how it ended. A project that has
never had the characteristic failure - output that looked good while coverage
was poor and existing logic was cut - has either been careful or has not looked.

### G - Verification
- **1** Human reads the output; the agent checks nothing.
- **2** A review pass exists, by the same agent.
- **3** A different model reviews, or output lands in a quarantine before
  reaching a shared system.
- **4** The agent runs the code it wrote against a real environment and proves
  it before a human looks.

### H - Context grounding
- **1** Everything pasted by hand.
- **2** Repository rules written down somewhere the agent reads.
- **3** The agent fetches its own requirements and locates its own commits/diffs.
- **4** As 3, plus an accumulating record of the project's own gotchas that a
  skill consults before re-deriving, and repetitive pre-processing pushed into
  deterministic scripts.

### I - Team diffusion
- **1** One person's setup, undiscoverable.
- **2** Shared on request; a teammate would have to know to ask.
- **3** More than one person uses it; a new joiner inherits it.
- **4** As 3, presented at team level, and the client's own shared assets are
  used where they exist.

### J - Cost discipline
- **1** Default model and effort for everything; limits hit without a response.
  Cannot say what the project spends.
- **2** Aware of cost; manages it by using the tool less.
- **3** Model and effort matched to task class; sessions started fresh per task;
  an escalation gate so the expensive tier is reached deliberately; a stopping
  rule wherever an agent runs in a loop. A project paying for a top tier while
  having no reusable instruction artifact has this backwards: measured, context
  is worth about +35 points of fix rate and the tier premium is worth nothing
  measurable at ~2.5x the consumption.
- **4** As 3, and something expensive was measured and replaced with a cheaper
  mechanism (a script, a lower effort tier, a transcript instead of a video),
  or consumption per successful outcome is actually tracked.

Two questions decide most of this dimension, and both are easy to skip. Ask
which tier the project is on, who pays, and whether the allowance runs out
before the period ends - no review so far has asked anything about consumption,
which is why the department has no picture of it. And ask what stops a loop: an
agent given a repeating loop and no exit condition ran until it had consumed an
entire five-hour token window with no result. A permanently-available browser
MCP is among the largest consumption drivers on record and should be gated, not
removed.

### K - Outcome evidence
- **1** Impression only, and no answer to "what got worse".
- **2** A clear account of where output needs the most correction.
- **3** As 2, plus a named upstream effect, in either direction.
- **4** As 3, with a measurement and a baseline behind it.

§K rarely reaches 3 and almost never reaches 4, which is itself the finding
worth writing down.

## Tiering

From the profile, not the average:

- **Ad hoc** - D<=1.
- **Individual practice** - D>=2, I<=1.
- **Team practice** - D>=3, I>=2.
- **Guarded practice** - Team practice plus E>=3 and G>=3.

Governance gate: no tier above *Individual practice* while §B carries an open
finding.
