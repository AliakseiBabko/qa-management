# API, Sharing, And Docs Editing Safety

Scope: Drive/Sheets/Docs API safety limits, the M2 folder-based sharing
boundary, and the Docs API bulk-editing technique. Load this module for any
skill that actually calls the Drive/Sheets/Docs API to write, or that
shares a folder with the project team or a named person.

## API Safety

- Use the smoke-test-proven Google APIs: Drive API, Sheets API, Docs API.
- Do not print credentials, token JSON, client secrets, or authorization URLs containing sensitive parameters unless needed for user action.
- Keep `.local\google\credentials.json` and `.local\google\token.json` out of git.
- Real data read from the Drive API (names, emails, project specifics)
  stays in conversation/generated Drive output — never write it back into
  this repository's own tracked files (skills, references, templates,
  scripts, commit messages) as an "example" or "for context." See
  `AGENTS.md`, "No Sensitive Data In This Repository."
- If Google API access fails, fall back to writing the established local CSV/Markdown artifact under `G:\My Drive\QA_Management` and state that the Google API write failed.
- The OAuth client only has `drive.file` scope: it can read metadata for any
  file (via `drive.metadata.readonly`), but can only rename/move/trash files
  it created itself through this API. Any file created another way — by hand
  in the Drive UI, by Drive Desktop sync, or by a different tool/OAuth
  client — will fail with `appNotAuthorizedToFile` on any write attempt. This
  is expected, not a bug to retry around: tell the user exactly which file
  and ask them to rename/move/delete it manually in the Drive UI instead.
- Always scope Drive `files.list` queries by parent (`'<parent_id>' in
  parents and name = '...'`). A bare `name = '...'` query with no parent
  filter matches same-named folders/files anywhere in the whole Drive, which
  can look like a duplicate-folder problem when the match is actually
  correctly nested somewhere else entirely (e.g. already filed under
  `90_Storage\Retired`).
- The Sheets API read-request quota is 60/min per user/project. Any script
  that iterates every Sheet in the workspace (`format_all_sheets.py`) costs
  at least 2 read calls per sheet (`spreadsheets().get` +
  `values().get`) and will exceed that quota well before finishing once the
  workspace has more than ~30 sheets — this is expected at current workspace
  size, not a sign something is broken. A 429 here is a rate limit, not a
  real failure: back off and retry (see `call_with_retry` in
  `format_all_sheets.py`) rather than treating the run as failed. If a
  one-off script or manual API call hits the same 429 without retry logic,
  just rerun it — formatting/read-only scripts are safe to rerun and pick up
  whatever didn't complete.

## Sharing Safety

The M2 tree uses folders as explicit permission boundaries:

- Share `team_shared\` only with the QA engineers assigned to that project.
  It contains team-editable project facts, currently `qa_process_metrics`.
- Share `people\<Person>\shared\` only with that person. It contains their
  `individual_development_plan` and `individual_metrics`.
- Never share the project root, `private\`, `people\<Person>\`, or any parent
  folder. `private\` contains M2 judgment, evidence, risks, internal metrics,
  1to1 history, and status drafts.
- Inherited access cannot be corrected by making a child look private. A
  private artifact found below a shared folder is a structural violation:
  move it to `private\` before continuing.
- Folder names are not a substitute for a permission audit. Sharing
  automation must verify the target folder, intended audience, and absence
  of private descendants before adding permissions.

## Docs API Editing

- When updating an existing Doc's content in bulk, clear the whole body
  (`deleteContentRange` over the full range) and reinsert with fresh
  paragraph styles, rather than patching pieces in place.
- If you do patch just one heading's text via `deleteContentRange` +
  `insertText`, its paragraph style resets to normal text — you must reapply
  `updateParagraphStyle` (e.g. `HEADING_2`) afterward, or the heading silently
  stops looking like a heading.
