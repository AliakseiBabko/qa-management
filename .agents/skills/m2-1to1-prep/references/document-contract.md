# Document Contract

Primary output is chat text, not a file. This mirrors
`m2-project-status-report`: an on-demand answer is text only; a copy is
saved only when the user asks for one.

## Purpose

Use this reference for M2's pre-1to1 question-prep output.

## Expected Output

Chat text, structured as:

```text
1to1 prep — <Person> (<Project>), <date if given>

Метрики/факты:
- ...

Развитие:
- ...

Проект (только если применимо):
- ...
```

Omit a section with nothing in it rather than leaving it with a placeholder
line.

## Versioning

- No default persistent artifact.
- If the user asks to save the prep, write it as a Google Doc named
  `1to1_prep_<YYYY-MM-DD>` in
  `20_M2_Project_Management\<Project>\people\<Person>\`. Do not overwrite a
  prior date's prep — each date is its own file, since the whole point is
  what was still open going into that specific conversation.
- Do not append prep questions into `individual_development_plan` or
  `individual_metrics` — those get updated from what the 1to1 actually
  produces (via `qa-1to1-analysis` and the relevant M2 skill), not from
  what was planned to be asked.

## Source Priority

See SKILL.md, Source Order — the priority there is the actual contract:
`individual_metrics` blanks first, then `individual_development_plan` open
items, then `project_metrics` contribution-row caveats, then open
`m2_input` questions this person can answer, then `individual_metrics_internal`
(reframed, never quoted), then `qa_process_metrics` gaps owned by them.

## Normalization

- Every question must trace to a specific gap in a specific source — no
  generic "how's it going" filler.
- Keep questions open-ended enough to actually get information ("what's
  blocking X" beats "is X blocked?").
- Do not merge two unrelated gaps into one compound question; keep each
  question answerable on its own.
- If a source's data is stale (e.g. `individual_metrics` snapshot is from
  over a month ago), say so — the freshness gap is itself worth asking
  about.

## Rule

Do not produce project-level status or risk content here. If the user
actually wants project-status prep instead of person-1to1 prep, redirect to
`m2-project-status-report` or `m2-project-risk-report` rather than blending
the two into one output.
