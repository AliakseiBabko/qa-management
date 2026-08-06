---
name: m2-project-status-report
description: Create a short chat-ready M2 project status report for a requested period - posted into the project's own strategy chat (the most common real destination), saved as a Google Doc under status_reports, or returned on-demand in conversation. Use when the user asks for current status, last-week status, project status update, or a text ready to copy into a chat based on available QA/project evidence.
---

# M2 Project Status Report

Use this skill for one output family only:

- short project status report text, matched to how real weekly reports on
  these projects actually get delivered (see Destination below) - not a
  long analytical document

This skill and `m2-strategy-chat-analysis` are two directions of the same
loop: a status written here often gets posted into the project's own
`_strategy` chat, and a later batch of that same chat is exactly what
`m2-strategy-chat-analysis` reads back in. Writing a clear, evidence-backed
status now is also writing next month's raw material for that skill.

## Required Start

1. Read `references/document-contract.md`.
2. Read `../qa-management-roles/references/google-workspace/workspace-basics.md`, `../qa-management-roles/references/google-workspace/m2-layout.md`, `../qa-management-roles/references/google-workspace/artifact-conventions.md`, `../qa-management-roles/references/google-workspace/search-source-extraction.md`, and `../qa-management-roles/references/google-workspace/api-sharing-editing.md`.
3. Read `../qa-management-roles/references/m2-role/m2-role-basics.md`
   (business-value framing) and
   `../qa-management-roles/references/m2-role/m2-communication-visibility.md`.
4. Read `../qa-management-roles/references/presale-upsell-rules.md` when the project has any expansion/upsell signal to report (see Content Rules, Расширение / Upsell).
5. Identify project, audience, report type, and period:
   - regular report
   - on-demand report
   - requested project, or all projects if explicitly requested
   - absolute start/end dates for relative periods such as "last week"
6. If the project is not specified and cannot be inferred from context, ask for the project unless the user clearly wants a multi-project status.
7. Run `.agents\scripts\show_project_state.py --project <Project> --summary` (or a full dump if you need more) to see current People count — a project with more than one QA needs the per-person/per-stream breakdown (see Chat Text Shape); a single-QA project doesn't.
8. Review available evidence for the requested period first, then use older artifacts only for context.

## Source Order

1. Existing status reports for the same project.
2. Project development plans and plan-progress notes.
3. Project QA metrics and individual QA metrics that affect the project picture.
4. Project risk summaries.
5. Workbook status rows, strategy-chat notes, 1to1 analysis findings, transcripts, or source extracts.
6. Pending sources under `00_Inbox`, durable references under `90_Storage/Reference`, and extracted copies under `90_Storage/_System/extracts/source`.

For DOCX/XLSX sources, prefer existing extracted files under `G:\My Drive\QA_Management\90_Storage\_System\extracts\source\YYYY-MM-DD\<Project>\...`. If no suitable extract exists, use `.agents/scripts/qa_source_extract.py`.

## Workflow

1. Build a short evidence-backed status for the requested period.
2. Decide the shape: flat (single QA) or per-person/per-stream (more than
   one) — see Chat Text Shape. Don't force a breakdown that the evidence
   doesn't support (e.g. one QA doing two unrelated task types isn't two
   streams).
3. Focus on what changed, what matters now, and what happens next.
4. Include metrics or risk levels only when they add useful management signal.
5. Separate current facts from plans, risks, and missing evidence.
6. Keep the report concise enough to paste into a chat without editing.
7. Decide the destination (see Destination) and deliver there.

## Destination

Real weekly reports on these projects are posted directly into the
project's own strategy chat — that's the default for a regular report,
not a saved Doc. Ask if genuinely unclear, but default to:

- **Regular weekly/status update** → chat-ready text for the project's
  strategy chat (paste-ready, per Chat Text Shape). Only also save it as a
  Doc under `status_reports` if the user asks for a kept copy, or if the
  project has no active strategy-chat channel to post into.
- **On-demand / ad hoc status** ("what's the status right now") → returned
  in conversation, per the existing default. Save only if asked.
- **Explicitly requested as a saved/archival report** → Google Doc under
  `status_reports`, per `document-contract.md`'s naming/versioning rules.

## Chat Text Shape

Default structure (single QA / flat project):

```text
<Project> status, <period>

Done / changed:
- ...

Risks / blockers:
- ...

Next steps:
- ...
```

Per-person/per-stream structure (more than one QA on the project — see
`show_project_state.py --summary`'s People count): lead with a short
project-wide line if there's genuine cross-cutting news, then one block per
person/stream, then a shared closing section for anything that doesn't
belong to one person (contract, staffing, cross-project comms):

```text
<Project> status, <period>

<Person/stream 1>:
- done/changed, risks, next step - whatever's evidence-backed for them

<Person/stream 2>:
- ...

Прочее (contract/staffing/cross-cutting):
- ...
```

Optional sections when evidence supports them, in either shape:

- Metrics / quality
- Feedback / communication
- Help needed
- Расширение / Upsell — only when a real diagnostic signal or an actual
  conversation exists (see `presale-upsell-rules.md`); omit rather than
  padding with generic upsell language on a project with no such signal.

**Monthly narrative variant** — use instead of the bulleted shapes above
when the period is a full calendar month, or the user explicitly asks for
a monthly overview/narrative/paragraph form. Fixed four-part structure,
each part a short paragraph (not a bulleted digest, and not so short it
reads as thin — real substance from real evidence, "at least two
paragraphs" is a floor, not a target to undercut):

```text
<Project>, обзор за <месяц год>

<Introduction — one line: this is the regular QA overview for the
project. No "first post"/predecessor-M2 framing on any post, including
the actual first one - it reads as unnecessary throat-clearing every
month it's re-included and was explicitly rejected once already. This is
distinct from the one-time report-series intro below, which is a
different thing and does belong on the actual first occasion.>

<Current state — what QA actually has right now: framework/coverage/
automation maturity, what's working, genuine positive signal when there
is one.>

<Problems — the real QA-relevant gap(s): a visibility gap, an overload
risk, a missing metric/process, a broken feedback channel. Concrete, not
"there are some challenges.">

<Plans — what M2 will do about the problems just named, strictly on the
QA side (see Scope Boundary below).>
```

- Same evidence discipline as the bulleted shapes — no invented content,
  same "Data note" fallback for a weak period (see document-contract.md,
  Missing Evidence).
- Same M2 Focus content categories apply (staffing signals, risk/blocker
  movement, plan progress, client communication) — they land inside
  Current state/Problems/Plans instead of separate bulleted sections.
- For a multi-person project, name the people/streams naturally within
  the prose rather than switching to per-person blocks.
- No vague filler statements ("there are some issues," "we'll keep
  improving") - every sentence should name a concrete thing.
- A third or fourth short paragraph is fine if a section genuinely needs
  it - the four-part shape is the floor, not a rigid four-sentence limit;
  it should never grow into the long analytical report this skill
  explicitly avoids.

### QA-Only Scope And Tone (Monthly Narrative)

Real user feedback on this variant, condensed into standing rules — the
user spent significant time correcting wording across a first full batch
of these reports; treat every rule below as durable, not a one-off ask
for that batch.

- **QA-only content, no project status.** The audience already tracks
  project status day to day from being in the project's own chat. Every
  sentence in this report must be about the QA function specifically -
  what QA is doing, what's blocking QA, what QA plans to change. Never
  restate project status, business context, or client/product facts the
  audience already has independent of QA.
- **One-time report-series intro, not a per-report or per-project one.**
  The very first time this monthly-narrative format is produced at all
  (the document's actual debut), open the whole document with a short
  one-time paragraph naming the M2 role and mandate for QA on these
  projects - quality support, introducing best practices, client-facing
  visibility, improving engineer performance. Something like: "Здравствуй,
  это мой первый регулярный обзор QA по проекту. Как M2 со стороны QA я
  буду поддерживать качество QA-процессов, добиваться внедрения лучших
  практик, видимости для клиента и роста текущего QA-инженера на
  проекте." Write this once, at the top of the document, never per
  project and never repeated in later months - this is a different thing
  from the already-banned per-project "first post"/predecessor-M2
  framing above, which stays banned everywhere, including the first
  month.
- **Current state: collaborative credit, constructive landing.** When a
  review/audit was carried out together with the engineer, phrase it as
  work "carried out together with <name>, under my supervision," not "I
  personally reviewed." Land the paragraph on a constructive note - what's
  solid, what the next increment of work is - not a flat neutral
  description.
- **Problems: process-level, never person-level.**
  - Never attribute a negative assessment to one named individual by
    name/role ("Aslan said X," "the DC gave negative feedback") -
    describe it as client-side perception/estimation being mixed or
    uncertain, with no named source.
  - Never include a petty or gossip-shaped detail (one person giving two
    contradictory answers, minor interpersonal friction) - not
    informative for this report, drop it entirely.
  - Frame process gaps structurally, not personally: ticket quality (are
    there acceptance criteria?), bug lifecycle clarity, Definition of
    Done, CI/CD and quality gates, the client contact channel - these are
    QA-process facts, not blame on a person.
  - Never phrase a documentation/checklist gap as someone's fault
    ("written in a rush before leaving") - describe it as an improvement
    opportunity instead ("the checklist could be meaningfully improved").
  - Never mention a personal skill/background detail that could read as
    a knock (unfamiliar tech stack, lack of experience) - reframe as a
    growth direction the person is actively pursuing, and name the real
    limiting factor instead (e.g. a security policy restricting available
    tools).
  - Don't overstate duration/severity in a way that reads as project
    criticism ("hasn't worked in over two years") - state the underlying
    problem generally (lack of direct client feedback) without the harsh
    framing.
- **Plans: only what QA actually controls, collective voice, sequenced
  by urgency.**
  - Staffing/hiring (searching for a QA hire, headcount decisions) is
    never QA's plan - that's the client/PM/Sales's call, not something to
    mention in Plans at all, not even neutrally.
  - Building a direct client communication channel is not something QA
    can commit to as a plan - it may sit outside QA's own hierarchy/
    authority on the project. Rephrase any such intent as trying to
    better understand client/user needs "through other available means,"
    never as "we will establish direct contact with the client."
  - Voice: plans are QA's collective approach ("мы сконцентрируемся
    на..."), not M2's personal commitment ("I will..."). Mention the
    manager's personal involvement at most once per report, only if it
    adds real information - never as the default framing for every
    action.
  - When the immediate priority is an operational backlog/overload,
    sequence the plan accordingly: resolving current tickets/incidents
    efficiently comes first; automation/process improvement is what gets
    addressed "if/when time allows" afterward - don't lead with the
    aspirational item over the operational one.
  - Frame effort-dependent commitments as conditional, not firm
    promises: "если будет время, попробуем..." rather than a flat
    deliverable with an implied deadline.
  - The default toolbox for a Plans paragraph, absent more specific
    evidence: improving visibility (turning data QA already collects
    into a regular report, coverage/traceability metrics), trying to get
    more direct client/user feedback to understand needs better, and
    increasing use of AI tooling/test automation to raise QA output and
    value.
- **Language: plain, mostly Russian.** Avoid dense English-Russian jargon
  mashups translated term-by-term (e.g. "isolate mobile vs backend
  defects through direct requests via Postman"). Write natural Russian
  sentences; keep English only for terms genuinely standard as-is
  (CI/CD, Definition of Done, Page Object), not as scaffolding for an
  awkward literal translation.
- **Scope boundary on Plans: QA team only, never staffing/hiring
  decisions.** Growing or restaffing a project team is the client's call,
  executed through DC/delivery, not an M2 decision or an M2 plan - see
  the staffing bullet above; this is the same rule, restated because it's
  the single most repeated correction across the first batch of these
  reports.
- **Don't restate what the chat's own participants already know from
  being in it.** M2 is often one of several participants in a project's
  strategy chat, not the only source of truth for it - a fact the team
  discussed together in that same chat (an interview that happened, a
  decision already announced there) isn't news when M2 repeats it back.
  Only include something the audience wouldn't already have from being
  present - the QA-strategy synthesis, not a recap of shared events. When
  the user shares the actual chat history/context for a project, use it
  to check this directly rather than guessing what's already known.

## Guardrails

- Do not invent progress, blockers, feedback, dates, metrics, or ownership.
- Do not write a long analytical report; this skill produces a short status update.
- Do not expose sensitive internal details unless needed for the management action.
- Do not duplicate full risk, metrics, or development-plan reports. Summarize only what is useful for status.
- If available evidence for the requested period is weak, say that directly and state which sources were missing.
- Do not default to a saved Doc for a regular report without checking whether the project has an active strategy chat to post into instead — that's the more common real destination.
- Do not include a Расширение / Upsell section built from generic service-menu language with no project-specific evidence — see `presale-upsell-rules.md`, Rule.
