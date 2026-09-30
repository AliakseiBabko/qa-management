---
name: meeting-recording-audit
description: Find meetings that were scheduled but never turned into a record - reconcile calendar events against the recordings that actually exist (Google Meet recordings attached to the event, or local screen captures matched by timestamp), and identify an unnamed capture by the event that produced it. Use when checking whether every 1:1/sync in a period was processed, when a person's longitudinal record looks like it stopped, before a monthly/periodic report that depends on complete per-person history, or when a local recording filename gives no clue what meeting it was. Not for processing a transcript once identified - hand off to the owning intake skill.
---

# Meeting Recording Audit

Every other completeness check in this workspace starts from a source that
exists: a transcript in the inbox, a queue run, a `routed_to` list in
`evidence_log`. None of them can see a meeting that happened and produced
**no artifact at all**, because there is nothing to notice. The calendar is
the only place that leaves a trace.

This is not hypothetical. A real audit found two per-person syncs on one
project, eight weeks apart, both held, neither recorded, neither written up.
The person's 1:1 record simply stopped at July, and nothing in the workspace
flagged it - the documents were internally consistent, just missing two
conversations.

The second thing this solves: a local capture is named
`2026-09-15 16-00-51.mkv` and nothing else. The calendar event is what turns
that into "the M2 sync with a named engineer on a named project," via the
event `summary` and its `attendees`.

## When To Use

- Periodically, and before any report that assumes complete per-person
  history (a monthly report, a performance-review input, a risk review).
- When a person's 1:1 record has a suspicious gap.
- When a recording filename gives no clue what meeting it holds.
- After processing a batch of sources, to confirm nothing was scheduled that
  never arrived.

Not for turning an identified transcript into documents - that belongs to
the owning intake skill (`qa-1to1-analysis` plus `m2-1to1-apply` for an M2
1:1, `internal-assessment-feedback` for an assessment session, and so on).

## Required Start

1. Read `../qa-management-roles/references/live-source-access-rules.md` -
   this skill reads a live external source, and that file holds the
   API-versus-browser rule.
2. Confirm Calendar access works. The repo's own Google credentials already
   carry the Calendar scope (`google_api_smoke_test.py`'s `SCOPES`), so this
   needs no separate connector or browser session -
   `pipeline_common.get_services()["calendar"]` is the supported path.

## Workflow

Run the audit over the period in question:

```
python .agents\scripts\meeting_recording_audit.py --since 2026-08-01
python .agents\scripts\meeting_recording_audit.py --since 2026-08-01 --missing-only
python .agents\scripts\meeting_recording_audit.py --since 2026-08-01 --json
```

`--pattern` selects which event titles count (default covers `M2 sync`,
`1to1`, `1x1`, `1:1`, `1-2-1`); `--exclude` drops recurring team-wide
meetings that match the pattern but have no per-person record.
`--recordings-dir` points at the local capture folder.

Each meeting comes back as one of three states:

- **`REC`** - a recording is attached to the event itself (a Meet recording,
  with its Drive `fileId`). If Meet also attached a **transcript Doc** it is
  listed as a companion: read that instead of transcribing the video again.
- **`LOCAL`** - no attachment, but a local capture falls inside the event's
  time window. This is a *candidate*, never proof - see below.
- **`GAP`** - neither. The meeting happened and no recording exists anywhere.

Then, for each state:

1. **`GAP`** - decide whether it needs recovering from memory or notes, or
   whether the gap is simply recorded as a gap. Do not silently let a
   person's record skip a month; if the conversation happened, say so in the
   person's 1:1 file even when the only content available is "held, not
   recorded, no notes."
2. **`LOCAL`** - confirm identity from content before processing. The window
   match is circumstantial.
3. **`REC`** - cross-check against `evidence_log` for that project (the
   `source` column) before concluding it was processed. A recording existing
   is not the same as a record existing.

Once a source is identified, hand it to its owning intake skill. This skill
never processes content itself and never writes to a document.

## A Window Match Is Circumstantial

Meetings overlap, get moved, and take over each other's slots. In the real
audit, a capture sitting squarely inside a per-person sync slot turned out
to be a six-person department timesheet meeting that had taken the slot
over - processing it as that person's 1:1 would have written a fabricated
record. `confidence: low` (several captures share one slot) means check by
hand. Transcribing the first minute is usually enough to settle it.

Symmetrically, a per-person sync may be captured under a **different**
event's window when it runs long or starts late, so a `GAP` next to a busy
slot is worth a second look before being accepted.

## Recurring Events Inherit Attachments

Expanding a recurring series copies the **series-level** attachment onto
every instance. A weekly sync recorded once in May therefore reports that
same May recording against every later week, which would mark meetings with
no recording of their own as recorded - a false green, and the worst failure
mode for a completeness check.

The script defends against this by comparing the timestamp Meet writes into
the artefact's own title against the instance's window, and reports anything
outside it as `ignored (timestamped outside this meeting)` rather than
counting it. The same check catches an unrelated recording attached to the
wrong event. An attachment whose title carries no timestamp cannot be
adjudicated and is kept, on the reasoning that a false gap is cheaper than a
silent drop. When reading raw `--json`, apply the same scepticism: never
treat `attachments` as this meeting's recording without checking its stamp.

## Guardrails

- Read-only. This skill queries Calendar and stats local files; it writes no
  document, moves no file, and records no telemetry of its own. Findings are
  reported to the user, who decides what to process.
- Never infer a meeting's subject from a capture's filename - the filename
  is a timestamp. Identity comes from the event's `summary` and `attendees`.
- Never report a meeting as processed on the strength of a recording
  existing. Check `evidence_log` for the project before saying so.
- Attendee emails are real personal data: they belong in the conversation
  and in Drive documents, never in this repository or a commit message.
