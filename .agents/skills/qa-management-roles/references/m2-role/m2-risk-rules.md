# M2 Risk Rules

Scope: Risk classification, feedback-confidence weighing, and topology/staffing risk signals.

## Risk Rules

Classify risks by perspective:

- business risks
- project/product risks
- development risks
- QA/process risks
- staffing/continuity risks
- our-role risks

For each risk, state:

- what can happen
- why it matters
- impact on business/project/role
- early signals
- mitigation/action
- owner

Do not list current problems as risks without stating what future harm they can cause.

Do not conflate "at least one named risk is serious" with "the project's
overall risk level is high." Individual risks can and should be classified
by severity on their own (see
`m2-project-risk-report/references/risk-evidence-rules.md` for the full definition) — but the project-wide level is a separate, stricter
judgment about whether something concretely threatens the engagement's
continuation or trust right now, not a maximum over the individual items.
Nearly every active project has at least one serious individual risk;
treating that as sufficient for a high overall level makes most projects
read as high-risk and defeats the point of having the field.

Assess evidence strength for feedback and risk signals. Mark whether feedback is direct client feedback, intermediary feedback, DC/QA Lead feedback, team feedback, or employee self-report. Multi-hop or indirect feedback can still be useful, but it lowers confidence and should be named in the evidence.

A source's category (DC/QA Lead, self-report, etc.) sets a baseline
confidence, but it is not the whole picture — weigh it further by the
source's position/seniority/domain expertise relative to the *specific
claim*, and by whether their incentives align with an accurate answer or
push them toward a distorted one. A senior DC/QA Lead's concrete, checkable
technical assessment (e.g. a specific code-quality or comprehension gap)
carries real weight, particularly when they have no incentive to make the
project look worse than it is. A newcomer's self-report on their own
performance — especially on their first commercial project — should be
read through the onboarding-fragility lens (`newcomer-support-rules.md`),
not treated as an equally authoritative counter-claim just because it
disagrees with someone more senior.

Do not let a reliability concern on one axis discount a source's claims on
an unrelated axis. Whether someone is honest/consistent in what they tell
a person directly versus what they say about that person to a third party
(a communication/diplomacy axis) is a different question from whether
their technical assessment of that person's work is accurate (a
judgment/expertise axis). A source shown to be inconsistent on the first
does not become unreliable on the second — name which axis is actually in
question rather than applying a blanket "this source is unreliable" label
to everything they say. Independent verification (code review, direct
metrics) is still the right closing step for any single-source claim
regardless of how credible the source already is — not because the source
is under suspicion, but because that is the standard bar before this
document treats a conclusion as settled.

The premise "a source shown to be inconsistent" needs the same evidence bar
as any other claim before it gets asserted — do not skip that step just
because the claim is *about* reliability rather than about a technical
fact. A report that "X said one thing to me and something different to
someone else" is very often just one party's own interpretation of an
ambiguous exchange — different phrasing of the question, timing, tone, or
a simple account relayed secondhand through a third party — not a
transcript-confirmed contradiction. Without the actual transcript or
direct corroboration from both sides, do not write it up as an
established fact about that person's reliability, and do not let it anchor
an ongoing characterization in later documents ("already showed himself
unreliable"). Two people holding conflicting impressions of the same
interaction is the normal case, not evidence one of them is lying — record
it, if at all, as an unverified single-party account, not a settled
judgment about the source.

Treat hidden or unclear project topology as a risk signal: unknown streams, unknown DC/PM ownership, unclear vendor chain, missing client path, or incomplete staffing visibility can cause wrong escalations, duplicated communication, missed stakeholders, or loss of project scope.

Separate individual performance risk from project/stake risk. A person may perform well while the project is still high risk because of vendor-chain issues, client dissatisfaction, role value doubts, weak processes, or contract horizon.

The reverse also happens: sometimes an individual's own performance/position genuinely is the primary driver of a project risk (e.g. a client explicitly requests a more experienced replacement, reinforced by real performance history). When that's the case, say so directly and put it first in the risk narrative — do not default to splitting it into parallel, co-equal sub-risks (like "continuity risk" vs. "process maturity risk") just to keep individual and project risk visually separate. Secondary/background factors (process immaturity, documentation gaps) still belong in the writeup, but as subordinate to the actual primary cause, not sitting next to it as an alternative explanation.
