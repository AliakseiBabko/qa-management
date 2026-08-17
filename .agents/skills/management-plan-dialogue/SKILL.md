---
name: management-plan-dialogue
description: Run a structured multi-model dialogue around a large implementation plan by maintaining one canonical plan, attributable review files, and explicit response/synthesis records. Use when one model must review, challenge, extend, or respond to another model's management or architecture plan.
---

# Management Plan Dialogue

Use this skill when two or more models are iterating on a large generic
implementation plan stored under `management/`.

## Required working model

The models are co-designers. Do not assume that one model is permanently the
planner and the other is permanently the implementer. Every model may:

- identify defects or omissions;
- disagree with a recommendation and explain why;
- propose an alternative;
- add independent ideas that were not requested by the previous review;
- ask for evidence or a decision before changing the plan.

The canonical plan remains the current source of truth, but it is updated only
after the receiving model exercises its own judgment.

## Files and naming

Use one canonical plan:

```text
management/<TOPIC>_IMPLEMENTATION_PLAN.md
```

Store reviews here:

```text
management/reviews/<TOPIC>_<MODEL>_ROUND-<NN>_<YYYY-MM-DD>.md
```

Store responses or synthesis decisions here when they are substantial:

```text
management/responses/<TOPIC>_<MODEL>_RESPONSE-<NN>_<YYYY-MM-DD>.md
```

Use repository-safe model labels such as `CODEX`, `GEMINI`, or `MODEL-B`.
Use placeholders for all business data. Never put real project, company, or
person information in this public repository.

## Review procedure

1. Read the canonical plan and identify its revision or date.
2. Read the latest related reviews and responses when they exist.
3. Inspect relevant repository rules or source files before making claims.
4. Write a review file containing:
   - scope and revision reviewed;
   - strengths confirmed;
   - corrections and risks;
   - disagreements and rationale;
   - new ideas introduced by this model;
   - questions or decisions needed;
   - disposition for each item: accept, reject, defer, or investigate.
5. Return the review file link to the other model or user.

Do not silently edit the canonical plan while acting as a reviewer unless the
user explicitly asks for direct implementation in the same turn.

## Response and synthesis procedure

When responding to another model's review:

1. Read the exact review file and the current canonical plan.
2. Evaluate every recommendation independently; do not accept all items by
   default.
3. Write a response/synthesis file when the reasoning is substantial. It must
   identify accepted, rejected, deferred, and investigation items.
4. Explicitly record independent additions made by the responding model.
5. Update the canonical plan with the accepted changes and justified new ideas.
6. Add or update a short revision-history section in the canonical plan with
   links to the relevant review and response files.
7. Return the canonical-plan link and response link.

## Completion rule

The dialogue is ready to stop when the canonical plan has:

- no unacknowledged critical review items;
- documented unresolved questions and assumptions;
- clear implementation status;
- traceable review/response history;
- a defined validation and migration plan.

“Approved” must not mean that the plan was merely read. Use a status such as
`Merged design proposal — pending implementation validation` until the
repository changes and tests actually exist and pass.

## Coordinator audit contract

Use `.agents/scripts/management_dialogue.py` as the state machine. A dialogue
state records the current phase, acceptance criteria, unresolved items,
decision-register entries, verification results, and a SHA-256 revision hash of
the canonical plan.

Every `complete-turn` call should include `--changed-file` for each relevant
file, `--validation` for each exact check and result, and `--unresolved` for
each remaining question. The artifact itself must be saved under
`management/responses/` or `management/reviews/` and must contain the changed
files, exact validation results, unresolved items, and recommended next step.
The generated next-turn brief includes the plan hash, acceptance criteria,
unresolved items, open decisions, and the latest artifact so the next model
can verify the previous turn from the repository rather than from pasted chat
text.

Before continuing implementation, the receiving model independently checks
the saved artifact against the actual files and focused tests. A completion
message without a saved artifact is not a completed dialogue turn.

Use these control commands:

```powershell
python .agents\scripts\management_dialogue.py decision ...
python .agents\scripts\management_dialogue.py user-input ...
python .agents\scripts\management_dialogue.py verify ...
python .agents\scripts\management_dialogue.py close ...
```

`close` is the only normal way to stop the dialogue. A phase is not accepted
until its focused validation is recorded with `verify --result pass`. A third
model is optional and should be introduced only for a material disagreement,
security/migration audit, or disputed validation failure.
