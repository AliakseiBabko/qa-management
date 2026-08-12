# Live/Interactive Source Access Rules

Scope: the general judgment call for reaching a source that isn't a file
already sitting in `00_Inbox` - a live console, a wiki space, a repo
browser, an external doc, an API-backed system. This is operational
judgment, not an artifact-producing workflow, so it lives here as a
shared reference rather than as its own skill - any intake/investigation
skill points to this file instead of restating the rule.

This reference does not replace a lane's own investigation gotchas (Drive
export quirks, frame-click workarounds, source-classification rules) -
those stay in the skill that owns that lane. This file holds only the
cross-lane decision rule and the current map of known access paths.

## The Decision Rule

1. **A credentialed structured API/client/script already exists for the
   domain → use it, not browser/DOM scraping.** Check the known-paths
   table below and this repo's `.agents/scripts/` before opening a
   browser tool at all. Scraping a rendered page for content an API
   already serves as structured data is strictly worse: slower, more
   fragile (DOM/renderer changes break it, a browser fallback here once
   silently doubled the round-trips a session needed), and it discards
   structure (real links, IDs, table shape) the API response keeps.
2. **No script exists yet, but the source has a real API and this access
   pattern is likely to recur → set up the API/client once**, rather than
   re-scraping the same kind of source by browser every time it comes up
   again. A one-time credential/script setup (an OAuth client, an API
   token + a thin client script mirroring this repo's existing
   `pipeline_common.py`/`confluence_client.py` pattern) pays for itself
   after the second use. A genuine one-off read of a source with no
   reuse case does not need this investment - use the browser for it and
   move on.
3. **Use Playwright/browser when:** no suitable API exists for the
   source; the source is a genuine external interactive UI (a form flow,
   a dashboard whose state depends on live interaction); setting up
   auth/API access isn't justified for a one-off read; or the rendered/
   visual state itself is the evidence being captured (a UI bug, a
   layout, a live dashboard reading at a point in time) - not just a
   means of reaching text that a structured source could otherwise
   provide directly.
4. **Browser extraction is investigation, not a record, unless the
   workflow explicitly says otherwise.** Treat what a browser session
   surfaces as something to read and act on now, not something to store
   as-is - screenshots/DOM dumps aren't a substitute for the structured
   write a skill actually owns, unless that skill's own contract calls
   for preserving the rendered source as evidence (e.g.
   `visual-evidence-intake`'s screenshots, or a UI-bug report where the
   rendered state *is* the finding).
5. **Do not default to browser automation for a source that already has
   a stable API path** (Drive/Sheets/Docs, Confluence/Jira once
   credentialed) just because a browser session happens to be open or
   already authenticated - convenience in the moment is not a reason to
   skip a faster, more reliable, already-available path.

## Known Access Paths

| Source | Preferred path | Notes |
| --- | --- | --- |
| Google Drive / Docs / Sheets | Existing Google API services (`pipeline_common.get_services()`, `read_google_doc.py`, etc.) | This repo's default write/read path for every canonical document; never scrape a Drive UI for content the API already serves. |
| Local Drive-mirror path ending `.gdoc`/`.gsheet`/`.gslides` | Resolve to the real Drive file via `resolve_drive_path.py`, then read/export through the Docs/Sheets API | Not a real file locally (Drive for Desktop keeps no bytes for Google-native types) - an I/O error here means "resolve it," not "fall back to a browser." See `google-workspace/api-sharing-editing.md`, "Resolving A Local Drive-Mirror Path." |
| Atlassian (Confluence / Jira) | `.agents/scripts/confluence_client.py` (Basic Auth, `.local/atlassian/credentials.json`) | Set up once (see AGENTS.md's `.local/` exception); reuse across sessions - no repeated interactive login. A Jira-specific client can be added on the same credential file when needed. |
| External rendered website/page with no API (tabs, accordions, JS-gated content) | Playwright/browser | The genuine fallback case - no structured path exists. |
| Browser-opened Google Sheet/Doc under a genuinely different (non-workspace) account, gated behind its own separate login | Playwright/browser, narrowly | Only when the content is truly unreachable by this workspace's own OAuth client - not a general fallback for anything under `G:\My Drive\QA_Management\...`, which always has an API path (see the Drive-mirror row above). |

## Guardrails

- Don't treat "I already have a browser tool open" as a reason to prefer
  it over a documented API path - check the table first.
- Don't invest in a one-time API/client setup for a source that's
  genuinely a single, non-recurring read - that's the browser's actual
  use case.
- Don't let a lane's own investigation gotchas (export quirks, frame
  clicks, source classification) migrate into this file - they stay
  owned by the skill that hit them; this file stays the general rule
  plus the access-path map.
