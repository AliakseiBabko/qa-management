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

## Resolving A Local Drive-Mirror Path (No Browser Needed)

The user's Google Drive for Desktop app mirrors this Drive account 1:1 at
`G:\My Drive\QA_Management` (`qa_manage.DATA_ROOT`), itself the Drive folder
`sync_m2_source_docs_to_sheets.ROOT_FOLDER_ID`. A `.gdoc`/`.gsheet`/
`.gslides` file in that mirror is a Google-native placeholder with no
readable bytes on disk - opening it with `Read`, `cat`, `Get-Content`, or
`[System.IO.File]::ReadAllBytes` fails with "Incorrect function" (or
similar), even though `Get-Item` reports a plausible size. This is expected
Google Drive for Desktop behavior, not a broken file or a sandboxing issue -
**do not** attempt to read it as a regular file, and do not fall back to
opening a live browser and clicking through Drive's search UI to find it.
Instead, resolve the local path straight to the real Drive file via the API:

```
python resolve_drive_path.py "G:\My Drive\QA_Management\00_Inbox\PKF\PKF - Perfomance Strategy v2.gdoc"
```

This walks the same folder tree by name via `drive.files().list` (the exact
technique `qa_manage.compute_source_file_hash` already uses internally for
Google-native placeholders) and returns the file's real `id`,
`mimeType`, and `webViewLink`. Once you have the `id`, read/write it
directly - `docs_service.documents().get(documentId=id)` for a Doc,
`sheets_service.spreadsheets().values().get(spreadsheetId=id, range=...)`
for a Sheet, or the export endpoints
(`https://docs.google.com/document/d/<id>/export?format=txt`,
`.../spreadsheets/d/<id>/export?format=xlsx`) if a plain-text/CSV dump is
more convenient than working with the structured API response. None of this
needs a browser tool at all. The same resolution also works the other
direction in miniature: if you already know the local folder path the user
is talking about, resolving it this way gives you the same "folder → Drive
URL" mapping the user would otherwise have to look up and paste by hand.

**Never reach for a live browser when the user hands you a local path under
this Drive mirror** (`G:\My Drive\QA_Management\...`), even a `.gdoc`/
`.gsheet` placeholder that looks unreadable, and even if `resolve_drive_path.py`
or the follow-up API call hits a snag - debug that (wrong path, stale OAuth
token, wrong scope) rather than falling back to a browser as a workaround.
The one legitimate use of a live browser in this workspace is a genuinely
different situation: an external system that isn't this Drive account at
all and sits behind its own separate login (the precedent being Unicard
project documents gated behind their own credentials, unreachable by any
Drive/Sheets/Docs API call this OAuth client has). That is a deliberate,
narrow exception for credential-gated external systems - it is not a general
fallback for "the API path was inconvenient" or "the local path didn't
resolve," and must not be broadened into one.

## Docs API Editing

- When updating an existing Doc's content in bulk, clear the whole body
  (`deleteContentRange` over the full range) and reinsert with fresh
  paragraph styles, rather than patching pieces in place.
- If you do patch just one heading's text via `deleteContentRange` +
  `insertText`, its paragraph style resets to normal text — you must reapply
  `updateParagraphStyle` (e.g. `HEADING_2`) afterward, or the heading silently
  stops looking like a heading.
- The same inheritance runs the other way too, and is easier to miss: `insertText`
  at a location that sits exactly at a heading paragraph's own `startIndex`
  (the common "insert new content right before this section's heading" move)
  makes every newly-inserted paragraph inherit that heading's style — the
  content silently becomes a run of fake `HEADING_2` paragraphs, not the
  `NORMAL_TEXT` you intended. This produced a real incident: several rounds of
  "append new facts before the next heading" on a `pk_knowledge_base` document
  quietly turned every appended paragraph into a heading, and it wasn't
  caught until a later pass dumped all `HEADING_2` paragraphs and found
  6–20-paragraph runs where only one real section heading should have been.
  The fix is generic and works even after the fact: fetch the document, find
  every run of *consecutive* `HEADING_2` paragraphs (`start` of one equals
  `end` of the previous), and reset every paragraph in the run except the
  last one (the real heading) to `NORMAL_TEXT` — a real heading is never
  immediately followed by another heading with zero content between them, so
  this is a safe, general repair. Better: avoid it going in by *always*
  appending an explicit `updateParagraphStyle: NORMAL_TEXT` request over the
  inserted range in the same `batchUpdate` as the `insertText`, exactly as
  `pipeline_common._insert_blocks` already does — don't skip that step just
  because the insertion point "looks like" plain body text; the paragraph
  mark you're inserting before is never guaranteed to be `NORMAL_TEXT`.
- When replacing one paragraph's text in place via `deleteContentRange` +
  `insertText`, get the paragraph's own `startIndex`/`endIndex` from a fresh
  `documents().get()` call and delete range `[startIndex, endIndex - 1)` -
  `endIndex` itself is exclusive and its last position is the paragraph's own
  trailing `\n`. Deleting one index too far in either direction (off by one
  on `startIndex` or using `endIndex` unadjusted) eats that newline and
  silently merges the paragraph into its neighbor - the two paragraphs read
  as one run-on block, invisible until you actually re-fetch and inspect
  paragraph boundaries afterward. When applying several such replacements
  (or heading-relative inserts) in one `batchUpdate`, process them in
  descending index order in the request list so an edit near the end of the
  document never invalidates the indices of an edit you computed earlier for
  content before it.
