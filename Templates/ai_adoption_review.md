# Template: AI Adoption Review

Output format - Google Doc, one document per reviewed project under
`55_AI_Adoption\reviews\`, named `<Project>_ai_adoption_review_<YYYY-MM-DD>`.
One document per review session; a re-review of the same project creates a new
dated document and cites the previous one, so the trajectory stays visible.

This is a **review of a project's AI adoption**, not of a person. It records
what is implemented, how it is guarded, what it is measured against, and what
the project committed to next. It never records a verdict about a named
engineer's competence - that belongs to M1's `individual_risk`. A single
engineer's setup can be described; the assessment is of the project's practice.

Two things this template deliberately separates:

- **Scored dimensions** (§C-§K) - where a project sits on a maturity scale, and
  what would move it.
- **Findings** (§B and §M) - access-legitimacy problems and governance
  conflicts. These are never scored, never averaged away against a good
  tooling score, and are escalated rather than coached around.

Leave a field marked `unknown` rather than guessing. An `unknown` in §B is
itself a finding.

---

## How to run the review

1. **Pre-read.** The project's completed AI usage questionnaire, the client's
   own AI policy or approval matrix if one exists, and the previous review
   document if there is one. Fill §A and as much of §B as the paperwork
   answers, before the call.
2. **The call.** 45-60 minutes, with a screen share if the project's data
   sensitivity allows. Use the question bank in §N. Ask for the artifact, not
   the intention: "show me the skill" rather than "do you use skills".
3. **Score.** §C-§K, on the 0-4 scale below, immediately after the call while
   the demonstration is fresh.
4. **Commit.** §L, with a named metric, a baseline captured *now*, an owner and
   a date. A review that ends without a baseline cannot be followed up - fill
   §L or write down explicitly that no measurement was agreed and why.
5. **Send.** The follow-up message restating §L only. Recommendations without
   a commitment do not get implemented.
6. **Return.** On the §L date. Re-review creates a new dated document.

### Scoring scale

| Score | Meaning |
|---|---|
| 0 | Absent. Not present and not considered. |
| 1 | Ad hoc. Happens by hand, per person, differently each time. |
| 2 | Repeatable. A written artifact exists but is not enforced or shared. |
| 3 | Established. Artifact exists, is relied on daily, and survives a person's absence. |
| 4 | Verified. As 3, plus a mechanism that proves it held - a hook, a scoped permission, a run log. |

Score what was demonstrated, not what was described as planned. A planned item
scores at its current state and is listed in §L instead.

---

## A. Session record

| Field | Value |
|---|---|
| Project | |
| Review date | |
| Reviewers | |
| Participants and roles | |
| Streams / sub-teams covered | |
| Previous review | date + link, or `none` |
| Questionnaire received | yes / no / partial |
| Screen share | yes / no / declined (reason) |
| Recording | yes / no |

**Project context in one paragraph.** Product area, delivery model, team shape,
manual/automation split, and anything about the domain that bears on how well
generation works (documentation quality, business-logic complexity, how
expensive a wrong test case is to discard).

---

## B. Access legitimacy - gate, not a score

Complete this section before any other. It determines which of the patterns in
§C-§K are even reachable, and it is the section where a problem is a finding
rather than a low score.

| Question | Answer |
|---|---|
| What has the client approved, and where is that written down? | |
| Is there a client AI policy / approval matrix? Has the team read it? | |
| Which tools are in use, and which of those are covered by that approval? | |
| Does the client know which tools the team actually uses? | |
| Client's own AI tooling - exists? usable? actual quality under load? | |
| Where does project data go? What is deliberately never fed in, and by whose rule? | |
| Integration access (MCP/connectors) - approved, scoped read-only, or absent? | |
| Machine and network shape - client VDI, own machine over VPN, client-issued laptop? | |
| Is anything in use *because* it is untraceable rather than because it is permitted? | |

**Ecosystem class** - pick one, it drives the environment-specific expectations
in §O:

- [ ] **Open, client-endorsed.** Client supports AI, may have its own shared
      assets. Integration is available.
- [ ] **Restricted / client-owned.** Client's own model, external tools limited
      or unapproved, policy circulated. Manual export may be the honest ceiling.
- [ ] **Closed.** VDI or client-issued hardware, nothing installable, no
      external tooling reachable.
- [ ] **Negotiated autonomy.** Client has agreed to the enabling changes; the
      agent can own the loop end to end.

### Findings

Record any of the following verbatim, as a finding with an owner and an
escalation path. Do not score them, do not offset them against a strong
tooling score, and do not answer them with a workaround.

- Tooling in use that the client has not approved.
- Deliberate concealment: trace stripping, output edited to look hand-written,
  surfaces chosen so a screen share shows nothing, commit attribution removed
  to hide authorship rather than to satisfy a house style.
- Agent access to client systems under an individual's credentials where the
  client believes only that individual is acting.
- Authentication routed around a control the client put in place.
- Data fed to a tool the client's own policy excludes.
- A control bypassed rather than changed - a prerequisite skipped, a
  restriction routed around.

For each: what it is, who is exposed, what the alternative is (client's own
tooling, a declared and approved subscription, or a local store the agent works
against without touching client resources), and who is escalating it.

> Note for reviewers. The reviewer's job here is to record and escalate, not to
> resolve. Answering "how do I leave no trace" operationally puts the
> engagement and the company at risk and is inconsistent with the department's
> own advice to declare tooling to the client. If the honest answer is that the
> project cannot integrate, that is a legitimate finding and the ceiling to
> design against.

---

## C. Task inventory and coverage

The routine tasks the project actually performs, and whether AI is involved.

| Task | Frequency | AI involved | Artifact used | Assessment |
|---|---|---|---|---|
| Requirement / user story analysis | | | | |
| Checklist generation | | | | |
| Test case generation | | | | |
| Test plan authoring | | | | |
| Test code authoring | | | | |
| Test code review | | | | |
| Test failure triage | | | | |
| Log analysis | | | | |
| Bug report authoring | | | | |
| Duplicate checking before filing | | | | |
| Test data generation | | | | |
| Release / status reporting | | | | |
| Sprint scope planning | | | | |
| Coverage analysis | | | | |
| CI / infrastructure diagnosis | | | | |

**For failure-triage and self-healing work, also record the failure classes.**
The strongest measured predictor of whether AI fixes a failing test is not the
model or the tooling but the class of failure. Locator drift and spec/API drift
were fixed essentially every time (20/20 and 9/9 in the benchmark); subform
ownership 3 of 7; subform interaction and report-output event drift 0 of 4
between them. Ask which classes dominate this project's failures, and calibrate
the expectation - and any promise - to that mix. A project whose failures are
mostly structural and stateful should not be sold a self-healing loop on
another project's fix rate.

**For every uncovered task, record why.** There are three good reasons and one
bad one, and the review must distinguish them:

- *Already cheap.* The task is faster by hand than the setup would cost. A
  correct decision - record it as such, not as a gap. Reporting, bug filing and
  uniform data generation commonly fall here.
- *Not a repeating shape.* The task only occurs when something has gone wrong,
  so there is no stable prompt to write. Log analysis commonly falls here.
- *Blocked.* Access, approval or a permission would be needed. Cross-reference
  §B.
- *Not considered.* The only answer that is a gap.

**Score C:** ____ /4 - breadth of coverage against the routines that are worth
covering, not against all routines.

---

## D. Reusable instruction artifacts

Prompts re-typed into a chat are score 1, regardless of how good the prompt is.

| Question | Answer |
|---|---|
| What artifacts exist? (skills, gems, rules files, root instruction file) | |
| Are they narrow and single-purpose, or one growing file? | |
| Do they reference each other, or duplicate content? | |
| How was the first version authored? | |
| How often are they revised, and on what trigger? | |
| Are they under version control? | |
| Would they survive their author leaving the project? | |

**What good looks like.** One artifact per job, narrow by design and narrowing
further over time rather than accumulating. Cross-references instead of
duplication. First version generated by the agent from the engineer's own real
work history, then revised on a regular cadence. Short is fine - a few
sentences can be enough, and consumes less context.

**Anti-pattern to record.** A single chat carrying context by re-pasting. A
prompt library with no artifact. Fifteen prompt variants tried against a
problem that is not a prompt problem.

**Score D:** ____ /4

---

## E. Enforcement and guardrails

The dimension most projects score lowest on, and the one that separates a
demonstration from a practice.

| Question | Answer |
|---|---|
| What must the agent never do on this project? | |
| Where is that written? | |
| Has it ever been ignored? What happened? | |
| Are there hooks, or only instructions? | |
| What approval mode is in use? | |
| How are integration permissions scoped - read-only where possible? | |
| Are CI / system tokens minted with restricted rights? | |
| Is cross-chat memory / chat referencing disabled? | |
| Is there a sandbox or quarantine for writes into shared systems? | |

**What good looks like.** Anything that must hold is enforced by a mechanism,
not by instruction text - a hook fired on a trigger, an approval mode, a
read-only connector, a token minted with restricted rights, a quarantine
workspace whose contents are promoted by hand.

**Ask specifically whether a written prohibition has been ignored.** It is a
common and reproducible failure: instructions get dropped as context compacts,
and duplicating the rule in more places reduces but does not eliminate it.
A project that has seen this and responded with more instruction text scores 2;
one that responded with a hook or a scoped permission scores 4.

**Score E:** ____ /4

---

## F. Delegation discipline

| Question | Answer |
|---|---|
| What does the agent do unattended? | |
| What must always be reviewed by a human? | |
| What is never given to the agent at all? | |
| Where is that boundary written? | |
| What is the largest task ever delegated in one go? What happened? | |
| Has permission-bypass mode been used? On what? | |

**What good looks like.** An explicit three-way classification in the root
instruction file - delegable, must-review, never-delegate - where
never-delegate means either a human decision is mandatory or the task must be
split first. On a subscription agent the system prompt is unreachable, so the
root file is the only available lever, and its value is as much in interrupting
thoughtless delegation as in constraining the agent.

**Ask what happens when the first attempt fails.** The sharpest measured signal
available: every benchmark run whose first patch worked ended fixed (31 of 31),
while runs whose first patch failed fixed only 40%. Median token consumption was
the same either way, so this is about outcome probability, not saving allowance.
A project that treats a failed first attempt as a normal step toward a fix is
letting a coin flip run on. A project that stops, re-diagnoses, or widens the
evidence at that point has the better gate. Score F accordingly.

**Anti-pattern to record.** Large autonomous delegation with permissions
bypassed. The characteristic outcome is output that looks good - a large number
of tests produced quickly - where coverage is in fact poor *and* existing logic
has been simplified or removed, and where reviewer agents did not catch it. Ask
what was verified, not what was produced.

**Score F:** ____ /4

---

## G. Verification loop

| Question | Answer |
|---|---|
| What does the agent verify before a human sees the output? | |
| Can it run the code it wrote? Against what environment? | |
| Who reviews AI-written test code? | |
| Is review done by the same agent that wrote it? | |
| Is a second model used? | |
| What is reviewed by eye regardless? | |

**What good looks like.** The agent proves its own work before handing it over
- spinning up the services locally, running the tests, and only then opening a
PR. Where that is not possible: a quarantine workspace, and review by a
different model than the author.

**Anti-pattern to record.** Self-review. The agent's own review returns
"everything is fine" on work a second model finds problems in. Architecture in
particular needs a human eye, specifically for unnecessary abstraction.

**Score G:** ____ /4

---

## H. Context grounding

| Question | Answer |
|---|---|
| How do requirements reach the agent - connector, or copy-paste? | |
| Does the agent locate the commit or diff for a ticket itself? | |
| Are the repository's architecture rules written down for it? | |
| If the repository holds more than one architecture, is the intended one named? | |
| Is there an accumulating record of the project's own gotchas? | |
| Does any skill consult that record before re-deriving? | |
| Is anything pre-processed by deterministic script rather than by tokens? | |

**What good looks like.** The agent fetches its own context. Connector-level
access to the requirement source is the first integration worth building,
because requirement analysis and case authoring both fail on a partial picture.
An accumulating gotcha record - the agent writing down what turned out not to
work here and why, and consulting it later - is what separates the mature cases.
Repetitive pre-processing (unpacking CI archives, locating a failure point,
extracting the relevant fragment) belongs in a script, not in token spend.

**Note.** In a restricted ecosystem, manual export of requirements is a
legitimate ceiling, not a low score. Score against what §B permits, and record
the constraint.

**Score H:** ____ /4

---

## I. Team-level diffusion

The dimension a well-tooled project most often fails.

| Question | Answer |
|---|---|
| Who else on the team uses what this person built? | |
| How would a teammate discover it exists? | |
| Has anything been presented at a team sync? | |
| Does the client have shared assets of its own? Are we using them? | |
| Is anything shared *to* the client as process improvement? | |
| Would a new joiner inherit a working setup or start over? | |

**What good looks like.** Artifacts are discoverable and shared, adoption is
presented at team level, and the client's own shared assets are used where they
exist. Where the team proposes tooling to the client as process and team
development, that is the strongest form of this dimension.

**Anti-pattern to record.** A working, valuable individual setup that nobody
else on the team knows exists. This is common and easy to fix, and it is
usually the highest-return recommendation a review can make.

**Score I:** ____ /4

---

## J. Cost discipline

| Question | Answer |
|---|---|
| Which model and effort level for which class of task? | |
| Is the team paying for a top tier where context would do more? | |
| Has a usage limit been hit? On what? | |
| Is any artifact avoided because of what it consumes? | |
| Is context managed - new session per task, or one growing session? | |
| Is anything being fed in that a script should pre-process? | |

**Ask what it consumes and what the seat costs. Do not ask for a price per
test.** On a fixed subscription an engineer meets a **limit**, not a
per-request charge, so a dollars-per-test figure cannot be derived without
assuming an allowance size and tracking usage against it - assumptions that
quietly become the answer. Ask instead: which tier, who pays, does it run out
before the period ends, and what burns it. A price per test is a real number
only where billing is metered per request.

| Question | Answer |
|---|---|
| Which subscription tier, and who pays for it? | |
| Does the allowance run out before the period ends? How often? | |
| What burns it fastest, in the team's own view? | |
| Is billing metered per request anywhere? (If so, a per-test price is real) | |
| Is there an escalation gate, or does work start on the top tier? | |
| Where an agent runs in a loop, what stops it? | |
| Is a browser MCP permanently available, or gated? | |
| Is anything fed in that a deterministic script should pre-process? | |

**Reference figures.** The first block is measured over 46 runs of one
benchmark, in tokens, because that is the unit the study itself used. Roughly
57% of those totals are cache reads, which allowances weight far below fresh
input tokens, so the non-cache column is the more allowance-relevant one. The
figures come from one application and one task class - orders of magnitude, not
benchmarks.

| Measured consumption | Total tokens | Non-cache |
|---|---|---|
| Median run that fixed the test | 7.9M | 2.84M |
| Median run that fixed nothing | 10.1M | 4.09M |
| Share of consumption that bought no fix | 22% | 16% |
| Mid-tier model, same cases as top tier | 8.0M at 71% fixed | 2.97M |
| Top-tier model | 20.3M at 67% fixed | 6.30M |
| Mid-tier model with rules/context | 85% fixed | |
| Mid-tier model without them | 50% fixed (n=4) | |
| Hardest failure class (0 of 2 fixed) | 40.8M | 6.32M |

| Reported in money | Figure |
|---|---|
| Enterprise seat, one engineer | $500/month, exhausted before month end |
| Heavy agent sessions | $20-40/day, above $1000 per working month |
| Metered API billing, per run | $2-7, up to $10-15 for a long test |
| Prompt caching | One $13 fix reported as ~$80 without it |

**What good looks like.** Model and effort matched to task class rather than
defaulting to the most capable option; a mid-tier model for most work, the
lowest effort for simple retrieval. Sessions started fresh per task rather than
grown, both for cost and because a compacting context is where instruction
adherence degrades. An escalation gate so the expensive tier is reached
deliberately rather than by default. A stopping rule on any loop. Expensive
tools - a live browser above all - gated to the cases that need them rather
than left permanently on. Consumption reported in tokens rather than an imputed
price.

Note what *not* to conclude from a low-consumption setup: restricting an agent
to terminal logs only saved about 10% of tokens in the benchmark while halving
the share of its investigation steps that led anywhere. Cheap per token is not
cheap per outcome.

**Anti-pattern to record.** Attaching video for analysis (it becomes per-frame
image analysis and consumes enormous tokens - use a transcript). A large
context treated as an asset. An artifact built and then never used because it
is too expensive to run. A loop with no exit condition - one such run consumed
an entire five-hour token window with no result. A permanently-on browser MCP,
which is among the largest consumption drivers on record. And starting hard
work on the top model tier: measured like-for-like, it consumed ~2.5x the
tokens of the mid tier for no measurable gain in fix rate, while adding rules
and project context to a mid model was worth about +35 points.

**Score J:** ____ /4

---

## K. Outcome evidence

| Question | Answer |
|---|---|
| What is demonstrably faster or better than before? | |
| What got *worse*? | |
| Where does the AI's output need the most correction? | |
| What has it found that a human would not have? | |
| Is any of this measured, or is it impression? | |
| Is AI output arriving from upstream (developers, analysts) as extra QA load? | |

**Ask whether they measure how wastefully it worked, not only whether it
worked.** The benchmark keeps three numbers per run - the outcome, an
efficiency score against a fixed step budget, and an investigation-quality
score (the share of investigation steps that produced something actionable),
the last assigned by a human after the run rather than by the agent. A run can
be green having exhausted its entire step budget, and a pass/fail metric cannot
see it. Almost no project will have this; a project that has any version of it
is at the top of the K scale.

**Ask the "what got worse" question explicitly.** It is the question that
surfaces the highest-value findings, and it is not volunteered. The pattern to
watch for: upstream teams generating artifacts with AI - testing notes,
documentation, autotests - whose quality dropped, so that QA's investigation
time *increased*. That is an accountability problem rather than a prompt
problem, and it is not fixable inside QA. Record it, name the owner, and
escalate it; the local countermeasure (reading the diff instead of the notes) is
a symptom, not a fix.

Also watch for ownership evaporation: AI-generated tests reviewed by developers
rather than QA, with nobody able to say who set the generation up or who
maintains it.

**Score K:** ____ /4

---

## L. Follow-up commitment

A review without this section cannot be followed up. Fill it or record
explicitly that nothing was agreed, and why.

| Field | Value |
|---|---|
| Actions agreed, with owner | |
| Artifacts shared during the session, and by whom to whom | |
| Metric to be collected | |
| **Baseline, captured at this review** | |
| How the metric will be collected | |
| Who collects it | |
| Return date | |
| What would count as adoption having worked | |

**On metric choice - read this before writing one.** Do not commit to
collecting a metric that has not been defined. "Percentage of time saved" is
not a metric unless the baseline and the measurement method are written down
here, and self-reported time saving is an impression, not a measurement.

The measures currently collected at department level - tickets per sprint,
story points where they exist, and git push counts per repository from a
locally-run tool - are **activity** measures, not productivity measures. They
are reasonable to collect and a poor basis for a productivity conclusion. State
which of the two this review is doing.

Be honest about the ceiling in what the review promises. Used responsibly, AI
adoption does not produce a dramatic QA productivity gain, because upstream
delivery accelerated too: the realistic outcome is testing at the rate
developers now deliver, and the gain accrues as feature volume at business
level rather than as freed QA capacity. A review that promises a step change
will report a failure later on a target that was never achievable.

Better candidates than time saved, where a baseline can actually be taken:

- Proportion of a defined task class now produced with an artifact rather than
  by hand - countable, and it maps to §D.
- Rework rate on generated output - what fraction is discarded or corrected.
  Also the discriminator for whether generation-first suits this project at all.
- Cycle time for a named recurring flow with a clear start and end, e.g. nightly
  failure triage from run completion to a filed or dismissed result.
- Number of team members using a shared artifact - the §I dimension, and the
  one where movement is fastest.
- **Consumption per successful outcome** for a defined task class - tokens, not
  money, for the reason in §J. This is the measure that behaves correctly:
  comparing configurations by consumption per *attempt* systematically favours
  the weaker one, because the cheaper-per-cycle setup produces more cycles that
  achieve nothing. Measured on one project, 22% of all tokens went on runs that
  fixed nothing.

---

## M. Governance conflicts and escalations

Anything from §B, plus anything the review could not resolve and should not
have resolved locally. One row each: what it is, who is exposed, who owns the
decision, and what was escalated to whom on what date.

| Item | Exposure | Decision owner | Escalated to / date |
|---|---|---|---|

---

## N. Question bank

Working questions, grouped by dimension. Ask for the artifact rather than the
intention, and ask what went wrong rather than what is used.

**Opening.** Walk me through where AI sits in your flow. Which of your routine
tasks is the most time-consuming, and is AI in it? Can you show me?

**Access (§B).** How does the client feel about AI on this project - and how do
you know? Is there a policy document or an approval matrix? Which of the tools
you use are covered by it? Does the client know what you use? What do you
deliberately never feed in? Is anything working because nobody is checking?

**Artifacts (§D).** Show me the skill. How did the first version get written?
When did you last change it? What happens when it grows - do you split it? Does
one call another? Where does it live?

**Enforcement (§E).** What must it never do? Where is that written? Has it ever
done it anyway? What did you change afterwards? Do you have hooks, or
instructions? What did you grant the connector - read, or write?

**Delegation (§F).** What do you let it do without watching? What do you always
check? What would you never hand it? What is the biggest thing you ever handed
it in one go, and how did that end?

**Verification (§G).** Before you look at the output, what has already been
checked? Can it run what it wrote? Who reviews AI-written tests? Does it review
its own work? Does that catch anything?

**Grounding (§H).** How do requirements reach it? Does it find the commit for a
ticket itself? Where are your repository's rules written? Does it remember what
didn't work here last time?

**Diffusion (§I).** Who else uses this? How would a teammate find out it
exists? Have you shown the team? Does the client have anything of their own we
could be using?

**Cost (§J).** Which model for which task? Have you hit a limit? Is there
anything you built and then stopped using because it costs too much?

**Outcome (§K).** What is genuinely faster now? What got worse? Where does its
output need the most fixing? Has it found anything you wouldn't have? Is anyone
upstream generating things with AI that land on you?

**Closing.** What would you want that does not exist yet? What did you try that
did not work?

---

## O. Expectations by scenario

The scored dimensions are the same everywhere. What a good answer looks like is
not. Use the ecosystem class from §B and the starting point below.

### Starting from scratch

The order matters, and the common failure is starting at the wrong end.

1. **Resolve §B first.** What is approved determines everything downstream.
   Designing an integration-heavy setup and then discovering it is not
   permitted wastes the effort and creates pressure to hide it.
2. **The delegation boundary, before any tooling choice.** Root instruction file
   with the three-way classification. It is the cheapest artifact and the one
   that prevents the expensive failure.
3. **The surface choice is not important.** Desktop, terminal client and IDE
   plugin are close enough that it should not be debated; plugins are the
   weakest, and a plugin is also the surface most visible in a shared screen.
   Do not let this become the decision the rollout is organised around.
4. **A small baseline artifact set,** covering commits, review, debugging and
   ticket creation, with the rules worth having regardless - duplicate check
   before filing, required fields, correct markup.
5. **One real task end to end,** with the artifact generated from that real
   work rather than written speculatively.
6. **A guarantee mechanism** for whatever turns out to matter - hook, approval
   mode, or scoped permission.
7. **Then integration**, requirement source first.

Do not begin by reaching for the most capable model. Buy the context instead.
Measured, rules and accumulated project context took a mid model from 50% to
85% fixed, while moving up a tier bought nothing measurable: on the cases both
tiers ran, mid fixed 71% and the frontier tier 67%, at about 2.5x the tokens.
Inside the frontier tier, vendor mattered more than tier. (The stronger claim,
that a weak model with context equals a strong model without it, is untested -
that configuration was never run.) The escalation ladder that the evidence supports is: widen the
evidence available to the agent, then try a different vendor at the same tier,
and treat the top tier as a last resort rather than the answer to difficulty.

Do not begin by restricting what the agent may look at, either. Confining it to
terminal logs halved investigation quality in the benchmark to save about 10% of
tokens. Gate the one genuinely expensive tool (a live browser session) behind a
trigger; leave the cheap evidence open.

Do not begin with a codebase index or RAG. On subscription models it pollutes
context faster than it helps, goes stale within minutes, needs a background
re-indexer, and has to be switched by hand between projects, while the model's
own search is more targeted. It has a legitimate niche - production pipelines
on small local models - which is not this.

Do not begin with agent swarms. For QA and documentation work the sub-agents
are weaker models, the orchestrator cannot verify what they return, verifying
doubles cost and runtime, and not verifying means paying a premium for weaker
output with gaps nobody can see. One agent, single-threaded, with a reviewer
after each action, and a fresh session per task.

### Improving an existing framework

The project already has automation and wants AI to extend it. The questions are
different: what is the *current* bottleneck, and is it a generation problem or
an access problem?

- **Reading tickets and requirements automatically.** Usually the highest-value
  first integration, and usually gated by §B rather than by capability.
- **Statistics and digests.** Worth building for what people forget, not for
  what they already see - a digest of incoming work helps a lead more than the
  engineer whose own queue it is. Operational caveats: a scheduled task may
  require the client application to be running, and connector tokens expire and
  break the run silently.
- **Failure triage and self-healing.** Works well on local and
  application-level failures. It does *not* work on infrastructure - expect
  confident wrong answers about CI configuration when the real cause is a
  service being down. Keep a human in that path. Where a project wants the full
  self-healing loop, the measured shape is: a deterministic script to extract
  the failure context from the CI report; a cheap or mid model with a rules
  artifact; the agent runs the test itself and iterates; a stopping rule (same
  error three times without movement); escalation to a wider data source or a
  better model only on failure; a live browser gated to locator and
  race-condition symptoms; then a linter pass and a human review. Ask which of
  those stages exist - the loop is the easy part, and the exit conditions are
  what projects skip.
- **Coverage extension.** The strongest pattern in this area is to negotiate
  the enabling change rather than engineer around it. Where an agent may add
  test IDs to the product repository, the whole locator-debugging cycle
  disappears; where it may not, budget for that cycle explicitly rather than
  pretending it is not there.
- **Test case generation.** Assess before recommending. Where implementation
  details are unknowable until the feature exists and per-case cost is low, mass
  generation is genuine relief even at a high discard rate. Where business logic
  is complex and documentation is thin, it fails regardless of the prompt, and
  no number of prompt variants will fix it. The discriminator is what a wrong
  case costs, not the technique. Recommend accordingly, and do not send a
  generic generation skill to a project of the second kind.

### Open, client-endorsed ecosystem

Expect high scores in §C, §D, §H and low in §I. Tooling is not the constraint;
diffusion is. The highest-return recommendations are sharing mechanics, team-level
artifacts, and adoption of the client's own shared assets. Watch §K closely - a
project where AI is endorsed everywhere is where upstream AI output most often
starts arriving as QA load, and where ownership of generated tests evaporates.

### Restricted or client-owned ecosystem

Score §H against what §B permits. Manual export is a legitimate ceiling. The
client's own model may be genuinely weaker - usable for small tasks, degrading
under load - and saying so is part of the review. The honest options are the
client's tooling, a declared and approved subscription, or a local store the
agent works against without touching client resources. Covert use is not a
fourth option, whatever the local monitoring gap permits, and §B is where that
gets recorded.

### Closed ecosystem

Most of §E through §H is unreachable. Review what is: artifact quality within
the permitted tool, cost discipline, and diffusion. Do not score a project down
for constraints it does not control - record the constraint and assess against
it.

### Negotiated autonomy

The highest-scoring shape, and the one to calibrate against: narrow per-scope
artifacts, cross-artifact memory of the project's own gotchas, local
run-and-verify before a human looks, and PRs into the product repository under
an arrangement the client agreed to. When reviewing a project that looks like
this, check how much credit belongs to the method and how much to an
easy-to-automate application - the answer changes what transfers elsewhere.

---

## P. Summary

| Dimension | Score |
|---|---|
| C - Task coverage | /4 |
| D - Reusable artifacts | /4 |
| E - Enforcement | /4 |
| F - Delegation | /4 |
| G - Verification | /4 |
| H - Context grounding | /4 |
| I - Team diffusion | /4 |
| J - Cost discipline | /4 |
| K - Outcome evidence | /4 |

**Maturity tier** - from the profile, not the average:

- **Ad hoc** - chat-based, no artifact. Typically D≤1.
- **Individual practice** - artifacts exist and work for one person. D≥2, I≤1.
- **Team practice** - artifacts shared and relied on. D≥3, I≥2.
- **Guarded practice** - as above, plus enforcement and self-verification.
  E≥3 and G≥3.

A project cannot be rated above **Individual practice** while §B carries an
open finding, whatever its scores. Governance is a gate, not a weighted
dimension.

**Three sentences on where this project actually stands**, what the single
highest-return change would be, and what to look at first on the return visit.
