# Document Contract

Primary final output is a Google Doc in `10_M1_People_Management\<Person>`,
with local Markdown fallback. This is a staging copy of the person's OKR —
the real record of truth is the Jira OKR card (see `okr-process-rules.md`);
this Doc is what gets drafted here first and then operationalized/pasted
into Jira, and kept as the readable, evidence-linked version for M1.

## Purpose

Use this reference for the individual OKR / development-plan document
family.

## Template

`<repo-root>\Templates\okr_m1.md`

Use this as the section skeleton for every individual OKR. It encodes the
Confluence-mandated fields (Критерии для оценки / Результат / deadline /
status per Key Result) plus the four standing objective categories this
skill defaults to: Техническое развитие, ИИ, Soft skills / командная
работа, Департамент.

## Expected Output

One OKR Google Doc per person, per Performance Review cycle.

Suggested target folder:

`G:\My Drive\QA_Management\10_M1_People_Management\<Person>`

Doc title (Drive file name): `OKR к Perfomance review <DD.MM.YY>` — the
review date this OKR was drafted for, matching the Jira naming convention
in `okr-process-rules.md`.

Local Markdown fallback naming pattern (only when Google API access is
unavailable): `okr_<Person>_<DD.MM.YY>.md`.

## Versioning

- A new OKR Doc is a new file per Performance Review cycle — do not
  overwrite the prior cycle's Doc. This differs from
  `m2-individual-development-plan`, which updates one living Doc in place;
  OKR is explicitly period-scoped by the company process, so each cycle's
  Doc is its own dated record.
- Within one cycle, update the current cycle's Doc in place (e.g. status
  updates, KR results as they land) rather than creating `_vN` copies.
- When closing a cycle (see SKILL.md, Workflow step 5), record final
  status/result on every KR in that cycle's Doc before drafting the next
  cycle's Doc.
- Append source traceability to the project `evidence_log` Sheet only when
  the person is on a project; there is no project-level evidence_log for
  bench people, so note sourcing inline in the Doc instead.

## Scope

- one QA engineer
- may reference project context, but does not produce project-level OKR
  content

## Source Priority

1. Existing OKR Doc for this person (current or most recent prior cycle).
2. Person's `<Person> 1to1` Sheet (`m1-people-1to1-file`) — for soft-skill
   evidence and any development-direction mentions.
3. Person's row in the latest people-risk traffic-light Sheet
   (`m1-people-risk-report`) — for soft-skill/risk-driven KRs.
4. If the person is on a project: that project's context (tech stack,
   tools, `individual_metrics`, project development plan) — for the
   Техническое развитие objective.
5. If the person is on bench: explicit user-provided market direction. Ask
   rather than invent one if it's missing.
6. Explicit manager (M1) notes given in conversation.

## Normalization

- Keep every objective's Key Results to 2-3; keep the whole Doc to 3-4
  objectives. This is a deliberate ceiling — the company process requires
  a minimum of 3, not a maximum, but this skill defaults to staying near
  that minimum unless the user asks for more.
- Every KR needs all four fields: action, Критерии для оценки, Результат,
  deadline, plus a status once the cycle is underway. Do not compress these
  into a single sentence — keep them as separate, scannable lines, matching
  the real OKR examples this template was built from.
- Do not restate the same project/role context paragraph before every KR;
  state it once at the objective level, then let each KR stay concrete.
- A KR tied to project technology must name the actual technology/tool in
  question, not a generic phrase like "improve technical skills."
- A soft-skill KR must trace to a specific 1:1/risk-report episode; if none
  exists, say so and leave the KR general rather than fabricating one.
- Preserve links (courses, docs, repos) inline in the "Результат" field
  when the source material provides them — matches how the real OKR
  examples this template is based on cite evidence links directly.
