# Document Contract

Primary output is chat text, not a file. This mirrors `m2-1to1-prep` and
`m2-project-status-report`: the reply is text only, returned in
conversation, ready to paste — a copy is saved only when the user asks
for one.

## Purpose

Use this reference for M2's replies to a specific incoming chat question,
produced by this skill.

## Expected Output

Plain chat text in the reply's own language (Russian by default). No fixed
section headers — unlike a status report, a reply to a specific question
should read like a message, not a template with labeled blocks. Length
should match what the incoming question actually needs answered, not a
fixed shape.

## Versioning

- No default persistent artifact.
- If the user asks to keep a copy, save it as a Google Doc under
  `20_M2_Project_Management\<Project>\private\` (or the relevant person's
  folder if the reply is person-specific), named
  `chat_reply_<YYYY-MM-DD>_<short-topic-slug>`. Do not overwrite a prior
  date's reply — each is its own record of what was said when.
- Do not append reply content into `individual_development_plan`,
  `individual_metrics`, `project_metrics`, or `m2_input` automatically —
  those get updated from the source evidence a reply draws on (via the
  relevant intake skill), not from the reply text itself. If the reply
  articulates a genuinely new decision or plan not yet recorded anywhere,
  flag that to the user as a separate, explicit follow-up — don't fold it
  into this skill's output silently.

## Source Priority

See SKILL.md, Source Order — recent 1:1/evidence_log first (the actual new
information), then `m2_input`, then `project_metrics`/`project_risk`, then
`action_items`, then the user's own stated plan for this session.

## Rule

Do not produce project-level status or risk content unprompted, and do not
produce a 1:1 question list here. If the user actually wants a periodic
status update or 1:1 prep instead of a reply to a specific message,
redirect to `m2-project-status-report` or `m2-1to1-prep` rather than
blending the two into one output.
