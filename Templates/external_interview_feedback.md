# Template: External Interview Feedback

Output format — Google Doc, one document per interview, at
`60_Assessments_And_Interviews\external_interviews\<Person>\<YYYY-MM-DD>_interview_feedback - <Person>`.
Internal-only; real names and real judgments are fine here.

Different question from an internal assessment, and the difference drives the
whole document. An internal assessment asks *does this engineer hold this
grade*. An external interview asks *did this engineer win this seat, and what
would make the next one land* — the audience is a client whose criteria are
their own, partly unstated, and not necessarily fair. So the assessment is
against the client's actual questions and the candidate's own CV, not against
an internal competency matrix.

**Inputs** — the candidate's CV (what was promised to the client) and the
interview transcript (what the client asked and what the candidate delivered).
Where a CV claim and the transcript diverge, that divergence is the single
most useful finding in the document: it is what will sink the next interview
too if nobody names it.

**Language** — write in the language the debrief will be read in. Quote the
client's own questions in the language they were asked, since phrasing is
part of what the candidate has to prepare for.

Insert a new section at the **end** of its parent section, never at a
heading's own start index — see `project-knowledge-roles/SKILL.md`,
"Structural Format".

---

## Header block

Plain paragraphs before the first heading:

> **Candidate:** `<Person>` (`<email>`)
> **Position / seat:** `<role the client is interviewing for, seniority, rate band if known>`
> **Client / project:** `<client-side context, domain, stack as stated>`
> **Interview date:** `<YYYY-MM-DD>, <time/timezone>`
> **Client-side participants:** `<names/roles as they appear, or "unnamed" — never guessed>`
> **Internal participants:** `<who from our side attended, and in what role>`
> **Round:** `<screening / technical / final / repeat>`
> **Sources:** `<CV version; transcript; the seat's requirements if we hold them>`

## 1. Outcome and read

Three short paragraphs:

1. What the client actually seemed to be testing for, inferred from what they
   spent their time on rather than from the job description. If the transcript
   does not support an inference, say so — do not manufacture a read.
2. How the candidate landed on that: where they were convincing, where they
   lost the room, and at which specific question the interview turned if it
   turned.
3. **Read:** likely outcome and confidence, stated as an assessment with its
   basis, not as a prediction dressed up as fact. If the result is already
   known, state the result instead and skip the guess.

## 2. Against the CV

The section that only this document can produce. A table:

| CV claim | How it held up in the interview | Risk |
|---|---|---|

One row per claim the client actually probed. `Risk` is what happens if the
same claim is probed harder next time — no risk, needs rehearsal, or
overstated and should be reworded on the CV. Say "overstated" plainly when it
is; softening it here is what causes the same failure at the next interview.

Claims the client never touched are not findings. List them, at most as a
short note, under "not probed" — they are what to expect next time.

## 3. Question-by-question

Grouped by theme, not in strict chronological order. For each theme:

- **The client's questions**, quoted or closely paraphrased.
- **What the candidate answered** — the substance, briefly.
- **What a winning answer needed** — concretely, at this seat's level. This
  is the reusable part of the document; a theme with no such line is just a
  transcript summary.

Cover the non-technical themes with the same seriousness as the technical
ones: self-presentation and the legend's coherence, business/value framing,
AI-usage questions, English, reaction to pressure or to an unexpected
question, and whether the candidate asked the client anything at all.

## 4. Gaps to close before the next interview

Numbered, each one actionable and owned:

1. What to fix — a knowledge gap, a rehearsal gap, a CV wording gap, or a
   delivery/communication gap. Name which kind it is; they need different
   remedies and get confused constantly.
2. Who does it: the candidate, their M-manager, or whoever prepares
   candidates for this client.

Keep the honest total: if the seat was simply above the candidate's current
level, say so here rather than distributing that verdict across a list of
small fixes.

## 5. Signals about the client and the seat

Reusable beyond this one candidate, and the reason these documents are worth
keeping: what this client asks, in what order, how hard, what they visibly
care about, what they let slide, which of our standard preparation materials
matched and which did not.

A recurring client-side pattern worth applying across projects belongs in the
PM Case Library as well — see `pm-case-knowledge-intake`. A department-wide
preparation requirement this surfaces belongs in
`qa_department_standards` — see `qa-department-standards-intake`. Log it
there too rather than leaving it only in one candidate's debrief.

## 6. Process notes

Optional, and only for real observations about how the interview was set up
or supported on our side — a missing brief, a CV sent in a version the
candidate had not rehearsed, a scheduling or tooling failure. Never put
candidate assessment here.
