# Template: Internal Assessment Feedback

Output format — Google Doc, one document per session, at
`60_Assessments_And_Interviews\internal_assessments\<Person>\<YYYY-MM-DD>_assessment_feedback - <Person>`.
Internal-only, so real names, real verdicts, and named process criticism are
fine here — the repo copy of this template stays abstract.

Written for two readers at once: the assessor team and the lead who publishes
the final text in the tracker, and the candidate's own M-manager who has to
turn the gaps into a development plan. So the verdict section must be
publishable as-is, and the sections after it carry the working detail behind
it.

**Language** — write the document in the language the session was conducted
in. Grade/level labels, competency-matrix topic names, and rating vocabulary
stay in their original form (`T1`..`T4`, `Excellent / OK / Minor Gaps / N/A`)
even in a non-English document; translating them breaks the match with the
matrix and the ratings table.

Insert a new section at the **end** of its parent section, never at a
heading's own start index — see `project-knowledge-roles/SKILL.md`,
"Structural Format", for the Docs API heading-inheritance bug this avoids.

---

## Header block

Plain paragraphs, one fact per line, before the first heading:

> **Candidate:** `<Person>` (`<email>`)
> **Target grade:** `<grade>` (expected level per topic: `<Tn>` theory / `<Tn>` practice)
> **Format:** `<which assessment format, its scope, its agreed duration and assessor count>`
> **Session date:** `<YYYY-MM-DD>, <time/timezone>`
> **Interviewer(s):** `<names and roles (R1/R2) where the format defines them>`
> **Candidate's M-manager:** `<name from the matrix>`
> **Candidate profile:** `<manual QA / AQA / other, since it calibrates block weight>`
> **Project:** `<project, domain, tenure, whether it is the candidate's first project>`
> **Sources:** `<transcript; self-assessment matrix; the governing process pages by id>`

Then a status note, as its own paragraph, whenever the session deviates from
the fullest form of the process **or** deliberately uses a lighter one: say
which format this was and that the lighter shape was the agreed design, so a
later reader does not misread it as a procedural failure. If the governing
documentation is still being written, say that too.

## 1. Summary

Three short paragraphs, no lists:

1. Whether each in-scope block clears the target grade's bar, and where the
   candidate answered above or below their own self-assessment.
2. The single most consequential gap, stated as what the candidate could not
   do unaided — not as a topic name.
3. **Recommendation:** one sentence. Whether the blocks are cleared, and
   whether the gap is a development-plan item or a re-sit condition. Never
   leave those two conflated.

## 2. Feedback draft (tracker publication structure)

Mirror whatever structure the process requires for the published feedback,
so this section can be copied out without rewriting. The common shape:

### Verdict

`<Approve / Not Approve>` on `<grade>` for `<blocks in scope>`. No hedging,
no second condition smuggled into the sentence.

### Strengths

One bolded lead-in per strength, then the evidence. Every entry must name
what the candidate actually said — the product's monetization model, the
architecture layers they listed, the incident they walked through. A
strength with no quotable evidence behind it is an impression, and
impressions do not belong in a competency verdict.

### Gaps

Same shape, and the same evidence rule, plus one extra distinction that is
easy to lose: separate **what the candidate did not know** from **what the
candidate reached only after being led there**. Both are gaps, they are not
the same gap, and only the first is a knowledge gap. Where an answer was
led, say who supplied the frame.

Mark explicitly anything that was not probed, and why (out of scope for the
format, no time, or expected to be light for this candidate profile) — an
unprobed topic is not a gap and must never read as one.

### Recommendations

Numbered, each one an action the candidate or their manager can start:
what to study, what access to request, what to practise, what to correct in
the matrix. Cite the department's own reference pages where they exist.

## 3. Per-topic assessment against the competency matrix

One table per in-scope block, columns:

| Topic | Expected for `<grade>` | Assessed from session | Confirmed |
|---|---|---|---|

`Topic` uses the matrix's own topic names verbatim. `Assessed` may exceed or
fall short of the expectation, and may differ from the candidate's own
self-rating — that difference is a finding, so state it rather than
smoothing it. `Confirmed` answers only whether the target grade's bar is
met.

## 4. Ratings for the shared evaluation table

One table with the rating vocabulary the shared evaluation table uses:

| Column | Rating | Basis |
|---|---|---|

Fill only columns this session actually touched. Everything else is `N/A`,
with the reason — `not in scope for this format`, `no time` — because the
next assessor reads this table to decide what to focus on, and a blank cell
and a deliberately-skipped cell mean opposite things to them.

## 5. Process notes

Split in two, and keep the halves visibly separate:

- **Not a deviation:** every lighter-than-maximal aspect of this session
  that was the agreed design (assessor count, duration, relative weight of
  the blocks for this candidate profile). State it plainly so it is not
  re-litigated later.
- **Worth acting on:** real process observations — interviewer airtime
  crowding out the candidate's own answers, unfilled matrix fields, a
  contradiction between two governing pages, anything the format's own
  documentation should absorb while it is still being written.

Never put candidate assessment in this section, and never put process
criticism in the feedback draft.
