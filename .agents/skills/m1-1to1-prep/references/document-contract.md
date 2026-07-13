# Document Contract

Primary output is chat text, not a file. This mirrors `m2-1to1-prep`: an
on-demand answer is text only; a copy is saved only when the user asks for
one.

## Purpose

Use this reference for M1's pre-1to1 question-prep output.

## Expected Output

Chat text, structured as:

```text
1to1 prep — <Person>, <date if given>

Открытые риски:
- ...

Последующие шаги:
- ...
```

Omit a section with nothing in it rather than leaving it with a placeholder
line.

## Versioning

- No default persistent artifact.
- If the user asks to save the prep, write it as a Google Doc named
  `1to1_prep_<YYYY-MM-DD>` in `10_M1_People_Management\<Person>\` (create
  the person subfolder if the existing layout doesn't already have one).
  Do not overwrite a prior date's prep.
- Do not write into the people-risk Sheet or the person's 1to1 Sheet from
  this skill — those get updated from what the 1to1 actually produces (via
  `qa-1to1-analysis`, `m1-people-risk-report`, `m1-people-1to1-file`), not
  from what was planned to be asked.

## Source Priority

See SKILL.md, Source Order — the person's current people-risk row is the
primary driver, followed by its own `План действий`, then the most recent
1to1 Sheet row's open follow-up, then any not-yet-folded-in transcript
findings.

## Normalization

- Every question must trace to a specific open risk item or unresolved
  follow-up — no generic "how are you doing" filler standing in for real
  content.
- Name the risk in evidence-based terms (what was actually observed),
  not a label ("не путать «риск с нашей стороны» с общим неудовлетворением
  — назвать конкретный наблюдаемый факт").
- If a risk item's evidence is weak or second-hand, note that in how the
  question is framed (open exploration, not a leading/accusatory question).

## Rule

Do not produce project-level content here. If the user actually wants
project-focused 1to1 prep instead, redirect to `m2-1to1-prep`.
