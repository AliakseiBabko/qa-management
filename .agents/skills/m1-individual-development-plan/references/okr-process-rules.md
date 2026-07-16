# OKR Process Rules

Source: internal Confluence article on OKR requirements, cross-checked
against real OKRs actually used at this company. Kept here verbatim in
meaning (translated to rule form) because it defines cadence this skill
must not silently drop.

## Cadence and Scope

Full PR cadence table, participants, and meeting structure live in
`../../qa-management-roles/references/performance-review-rules.md` — read
that for the exact schedule. Summary relevant to OKR specifically:

- OKR is drafted at each Performance Review, for the period until the next
  one: 3 months during probation (one-time, anchored to hire date); 6
  months for every PR after that, for Junior, Middle, Senior, and M-level
  employees alike. The Intern→Junior transition PR is on individual
  timing, not this formula.
- At the Performance Review itself, the direction is agreed at a general
  level. After the review, the employee operationalizes it into concrete
  Objectives and Key Results together with their M-manager.
- OKR is mandatory for every employee **except unpaid interns**, who follow
  a separate internship program instead.
- OKR is created and tracked on a Jira board:
  - the correct issue type is selected at creation;
  - it is linked to a parent epic named after the person's full name (in
    Russian);
  - the title states the period it covers, e.g. "OKR к Perfomance review
    24.04.25" — the next OKR after that PR would be named counting forward
    to the following PR date (e.g. "OKR к Perfomance review 24.08.25" for a
    Junior on a 4-month notification-less cadence).
- Progress must be reflected on the Jira card at least every 2 weeks.

## Required Content

- At least 3 objectives.
- Each Key Result is one line - the concrete action itself, with a real
  deadline folded into the same line when one is known. Real OKRs at this
  company do not break a KR into separate "Критерии для оценки"/
  "Результат"/"Дедлайн"/"Статус" fields - an earlier version of this rule
  claimed that breakdown was Confluence-mandated; real examples reviewed
  2026-07 contradicted that, and the single-line format is what's actually
  used. Don't reintroduce the 4-field breakdown.
- OKR is drafted by the employee, with manager support — not written
  unilaterally by M1.
- OKR is approved by the manager after drafting, and accepted/closed by the
  manager at the end of the period.

## Closing an OKR

- Every OKR must be closed by the date of the next Performance Review.
- At closing, each KR gets a short one-line result appended (done / not
  done and why) - not a separate structured field, same one-line
  discipline as the KR itself.
- An unmet goal gets an explicit short result comment. If it should
  continue, it is carried forward into the next OKR rather than silently
  dropped.

## The Three Standing Purposes of OKR

Every OKR should serve at least one of these, and most objectives should
map cleanly onto one:

1. Improve the quality of work on the current project.
2. Deepen/broaden the person's expertise to increase their chances of
   landing or staying on a project.
3. Benefit the department (process help, upskilling in a new direction,
   knowledge sharing, teaching others).

## Best Practices

- OKR should correlate tightly with the person's actual current work.
  - On a project: build from the project's domain, technologies, tools,
    methodology, and process — objectives should target what actually
    helps that project.
  - On bench: build from market-relevant, broadly useful expertise that
    increases the number of project requests the person can be matched
    against.
- OKR is a manager tool, not just an employee artifact — M1 uses it to
  spot problems early and adjust support, so it needs to stay current, not
  be written once and forgotten.
- Ordinary work can legitimately be an OKR item: onboarding onto a new
  project, or picking up a testing type the project newly needs, are both
  valid KRs — they develop the person and give real signal about them.

## What OKR Affects

- Performance Review outcomes.
- Salary review and career progression decisions.
- Potential project rate reviews.
