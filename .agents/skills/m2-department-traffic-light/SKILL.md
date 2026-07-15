---
name: m2-department-traffic-light
description: Fill in M2's own project rows on the department's shared "Auto staff. Светофор проектов" traffic-light tracker (a foreign Google Sheet owned by the department head/other M2s, not one of this workspace's generated artifacts) - extract genuine project-level facts from real source documents, keep entries short and analytical, and leave out personal HR content and internal data-quality commentary. Use when M2 needs to update their block on that shared tracker, usually via a personal copy they made for editing before copy-pasting back.
---

# M2 Department Traffic Light

Use this skill when M2 is filling in their block of rows on the
department-wide outstaff/staffing traffic-light tracker
(`00_Source_Docs\03_Source_Documents\Auto staff. Светофор проектов.xlsx`,
tab `Outstaff`) - not a Sheet this workspace generates or owns. M2 typically
makes their own copy of the department original, edits their rows there,
then copy-pastes the result back into the shared table by hand.

## What This Is, And Isn't

- Not `_project_registry`: that's this workspace's own generated rollup,
  mechanically derived from `project_metrics` and never hand-edited. This
  tracker is the department's own artifact with its own column shape
  (`M2/DC`, `Project`, `QA team`, `Strategy chat`, `From - To`, `Status`,
  `Risks/comments`, `Action Plan`, `FTE`, `Project roadmap`, `Personal
  development plan`, `Upsale opportunity`, `Upsale comment`) - match its
  existing structure and formatting, don't impose this workspace's schema
  or run `format_all_sheets.py` on it.
- Not a status report: `m2-project-status-report` produces a period-scoped
  update for a project's own strategy chat. This skill produces a
  point-in-time row in someone else's cross-project dashboard.

## Required Start

1. Confirm which file is M2's own editable copy before touching anything.
   The department original and M2's copy often have near-identical names
   (e.g. `Auto staff. Светофор проектов` vs `Copy of Auto staff. Светофор
   проектов`) - resolve by checking the Drive `owners` field (must be M2
   themselves), not just a name match from search results. If genuinely
   unclear which file the user means, ask; do not guess on a spreadsheet
   this size with other people's data in it.
2. In the sheet, find M2's own block: rows are grouped by manager, with the
   `M2/DC` name only on the first row of each person's block and blank on
   the rows below it (matching each person's project count). Read a wide
   enough range to find the surrounding blocks and confirm the boundary
   before editing anything - the sheet may have unused reserved rows with
   only a leftover `Status` placeholder value and nothing else, which are
   not real data and can be trimmed or overwritten freely.

## Workflow

1. Get M2's current project list from `_project_registry` (this
   workspace's own source of truth) rather than trusting whatever was
   previously in the department tracker.
2. Trim or extend M2's row block to match the actual project count. Deleting
   rows belonging to *other* M2/DCs, or deleting a large row range, is a
   destructive action on a file that isn't fully M2's own artifact even
   when it's their copy - confirm the target file and scope with the user
   first if there's any doubt.
3. For each project, find real source documents under `00_Source_Docs` (and
   `90_Archive` for anything already archived) - look for a
   `<Name> case chat.txt` / `<Person> case at <Project>.txt`-style file
   under `02_Chats_and_Emails` first, then the project's own
   `<Project>_strategy.txt`. Do not source `Risks/comments`/`Action Plan`
   from this workspace's own `_people_registry`/`project_metrics` Notes -
   those often contain internal data-quality commentary (see Content
   Rules) rather than project facts, and pulling from there instead of the
   real source document was a mistake corrected mid-session.
4. Write `Risks/comments` and `Action Plan` short and analytical: lead with
   the actual risk and its trajectory (worsening / stabilizing / resolved,
   what's already been mobilized), not a chronological dump of every date
   and name found in the source chat. A department head reads many of
   these rows; each one needs to be skimmable.
5. Set `Status` (Green/Yellow/Red) from genuine evidence - a brand-new
   project with no metrics yet is not automatically Green (nothing
   confirmed good) or Red (nothing confirmed bad); say so in conversation
   and let the user pick the department's convention for "too new to
   assess" if it matters.
6. Leave `Strategy chat`, `From - To`, `FTE`, `Project roadmap`, `Personal
   development plan`, `Upsale opportunity/comment` blank rather than
   guessing - only fill what's actually known (e.g. a confirmed contract
   end date belongs in `From - To`, not invented for every row to fill the
   column).

## Content Rules — What Belongs In A Cell, What Doesn't

- **Personal HR content stays out**, even when it shares a source document
  with a real project fact: compensation-negotiation drama, retention-risk/
  flight-risk assessment, health details, discipline history, contract
  non-renewal or "parting ways" planning. Extract only the project-facing
  kernel (e.g. "client is scaling the team and rotating the current QA
  out" is fine; "employee threatened to quit over salary, assessed as
  manipulative, considering not renewing her contract" is not). A single
  `02_Chats_and_Emails` thread can contain both an HR-only narrative and a
  genuine client/non-solicitation/staffing fact for the same person - use
  the latter, drop the former, rather than skipping the whole source or
  including it wholesale.
- **Internal data-quality commentary stays out.** A contradiction between
  this workspace's own tracking artifacts (an HR card says one grade/DC
  status, `individual_metrics` or a strategy chat implies another) is a gap
  in *our* records, not a fact about the project - it does not belong in a
  cross-department tracker at all. Leave the cell blank if the only
  available "comment" is this kind of internal disagreement; don't write
  "не устранено" about our own bookkeeping.
- **No placeholder filler.** A brand-new project with nothing to report yet
  gets a blank cell, not a sentence explaining that there's nothing to
  report yet (e.g. not "project_metrics только что создан placeholder-ом").
- **Flag stale data explicitly** when the newest available evidence is
  weeks old and nothing since - state the last known state and the date,
  don't imply it's current. If the situation was actively unresolved (e.g.
  "awaiting client reply") and there was previously no M2 on the QA side
  tracking it, say that plainly rather than pointing back at "M2" as if a
  third party should check - M2 filling in the row now *is* that check.

## Guardrails

- This tracker is not part of this workspace's generated-rollup family
  (`_project_registry`, `_timeline`, etc.) - there is no refresh script,
  and it should never be treated as a source of truth to read back into
  `_people_registry`/`project_metrics`. Data flows one way: from this
  workspace's real evidence into the department tracker, not back.
- Never edit rows outside M2's own block.
- Don't apply this workspace's Sheet-formatting conventions
  (`format_all_sheets.py`, wrap/align/column-width rules) to this file -
  it's the department's own template with its own existing formatting.
