# QA Management - Workspace Agent Policy

This file is the workspace-level policy for AI agents working in this
repository. It is a **compact startup router**, not a detailed manual:
README.md, `.agents/skills/`, and this repo's own executable validation
(`validate_repo.py`, `check_sensitive_data.py`) are canonical for anything
not stated as a rule below. When in doubt, read the owning skill or
README section rather than expecting the answer here.

## Purpose

Model-agnostic agent infrastructure for:

- `M1` people-management workflows
- `M2` project-management workflows
- Project Knowledge (`30_Project_Knowledge`) - project
  understanding/onboarding, distinct from M1/M2 management reporting

## No Sensitive Data In This Repository

This repository is **public**. It holds abstract skill logic, templates,
and scripts only - never real business data. Before writing or editing
any file here (skills, references, templates, scripts, README/AGENTS
content, **commit messages**), check it contains none of: a real person's
name, a real company name, a real client/project codename, a real
contact detail, or verbatim content copied from a real transcript, chat,
1:1, or risk narrative - even as an "example."

Use a placeholder instead (`<Person>`, `<Project>`, `<email>`), in file
content and commit messages alike. Real names and business data belong
**only** in the Google Drive workspace (`_people_registry`, each
project's own folder); skills read/write that data via the Drive API at
runtime, never hardcode it here.

If you find real data that leaked into this repo, flag it rather than
just deleting it going forward - it may need scrubbing from git history
too (`git log --all -p` still exposes a value after the current tree is
fixed).

The Drive workspace itself does **not** carry this repo's restriction:
it's internal, and real names, judgments, and reliability assessments
about named colleagues are exactly what `project_risk`, `individual_*`,
and the department tracker are for. Don't over-redact real, sourced Drive
output just because the same detail would be unsafe here in the repo.

**Company context**: skills assume a QA department inside an outsource
software company staffing engineers onto client projects. `Side` values
are `Internal`/`Client`, never a literal company name.

Development-tool and API-provider names/domains (e.g. Google, Codex,
Claude Code, Antigravity) are allowed when technically necessary,
including `Co-Authored-By` commit trailers - the prohibition is on real
employer/client/engagement/business identities, personal contact details,
and any other detail that identifies a specific real person, team, or
engagement.

## `.local/` Is A Narrow Exception, Not A Staging Area

`.local/` is gitignored, but it exists for exactly one thing: the
credential/token cache for external services this repo authenticates to
programmatically - the Google OAuth client/token
(`.local/google/credentials.json` and its token file) and the Confluence
API credentials (`.local/atlassian/credentials.json`, email + API token,
see `.agents/scripts/confluence_client.py`). It is **not** a general place for audit exports, derived business
data, transcripts, replacement mappings, or any other temporary sensitive
output - gitignored means "not committed," not "safe to accumulate real
data here." Transient sensitive processing (an in-memory watch list, a
one-off scan) stays in process memory or an OS temp location that gets
cleaned automatically; it never gets written to `.local/`.

## Start Here

- Skills live in `.agents/skills/`. Each `SKILL.md`'s frontmatter
  `description` is the router - **load only the skill needed** for the
  current outcome, and treat the directory plus frontmatter as the
  canonical skill inventory (not a table in this file).
- Claude Code discovers skills through a machine-local adapter. If
  `/skills` looks empty, run
  `.agents/scripts/setup_agent_adapters.py --check`: if it reports the
  adapter missing, run the script again without `--check` to create it;
  if it reports a collision or misdirected link, follow its printed
  remediation by hand - setup never replaces an existing path
  automatically.
- Any structural change to this repo (a new/changed skill, script,
  template, document type, or dependency) - load `repo-maintenance`
  before editing.
- Working the intake queue? Start with
  `.agents/scripts/qa_manage.py dashboard` - it names the next run and
  the exact next command. Use `guide <run-id>` for what to do on a
  specific run, `classify`/`pack` when `guide` points there.
- Finished a real pass (queue-backed intake run, or a no-queue
  direct-note/conversational rollup)? Record its mandatory closing
  telemetry - `.agents\scripts\closeout_telemetry.py` for a queue-backed
  run (unchanged). For a no-queue pass, TWO rows are involved, not one:
  the LOCAL row is still mandatory and still comes from
  `.agents\scripts\record_agent_session.py --append-csv` - this has not
  changed and `.agents\scripts\record_telemetry.py current-session` does
  NOT write to it. For the SEPARATE, equivalent CENTRAL row, use
  `.agents\scripts\record_telemetry.py current-session` (Phase 17B - a
  small wrapper that forwards to the central ai-telemetry project's own
  auto-detecting recorder, resolving project/runtime/session with no
  extra flags in the common case). Do NOT also pass
  `--dual-write-central` on the local command above for this same pass -
  the two are alternative paths to the same central row, not additive
  steps, and each performs its own independent live-log extraction:
  using both produces two inconsistent `source_system='native'` central
  rows for one session (different token totals, since the two
  extractions run minutes apart) instead of one confirmed row. This is
  not a hypothetical risk - it happened in production on 2026-08-12/13
  (a PKF performance-testing follow-up pass), producing 3 central rows
  for one session once ai-telemetry's own CSV-import step (a separate,
  sibling-repo script, not one of this repo's own) added its own copy on
  top. `--dual-write-central` stays correct on paths that never
  pair it with `current-session` for the same pass - e.g.
  `closeout_telemetry.py`'s own queue-backed default, unaffected by this
  rule. Not optional instrumentation - see
  `.agents\telemetry\README.md`. (This bullet was cut from an earlier,
  more detailed AGENTS.md during this file's own July 2026 compaction
  into a router; telemetry recording silently stopped the same week and
  stayed stopped for 2+ weeks until caught by a direct user review - the
  bullet is back specifically because removing it from startup context
  was enough on its own to stop the practice, even though the README
  still documented it as mandatory.) `.agents/telemetry` is this repo's
  own local record and stays mandatory as documented above - it is not
  being removed. A separate, sibling repo,
  `C:\Users\User\Documents\ai-telemetry`, is the newer central,
  cross-project store; `closeout_telemetry.py` best-effort-dual-writes
  into it automatically now - see `.agents\telemetry\README.md`'s "This
  is legacy/local telemetry" section for exactly what is/isn't covered
  yet.
- About to write an ad hoc Drive/Sheets/Docs script? Read README's
  **Current pipeline scripts** section first - most tasks already map to
  an existing one.
- If a Drive/Sheets/Docs-backed script fails with `WinError 10013`, socket
  permission errors, DNS/host resolution, or another sandbox-style network
  block, immediately rerun the same command with network/escalated
  permissions. Do not treat that first sandbox failure as evidence that
  Drive access is unavailable.
- If PowerShell SecretStore commands fail with a
  `SecureStoreFile`/`FileSystemWatcher` initialization error, rerun the
  same SecretStore read with escalated permissions. The vault may be
  healthy while the sandbox blocks access to the Windows profile-backed
  store; never print secret values while checking this.

## Canonical Data Boundary

Google Drive is the business-data source of truth:

- Drive root folder ID: `1QtIOTEd0fVi4eAhCo_I0xqDSIUiEITRc`
- Local mirror/fallback: `G:\My Drive\QA_Management`

Full folder layout and per-document detail are canonical in README's
**M1 Person Layout**, **M2 Project Layout**, and **Project Knowledge
Layout** sections, and in `qa-management-roles`'s role references - not
duplicated here. Keep these four distinct:

- **M1** people data (`10_M1_People_Management`) is person-based,
  people-management-owned.
- **M2** project data (`20_M2_Project_Management`) splits `private/`
  (M2-only) from `people/<Person>/shared/` (employee-visible) - never
  share the project root or `private/`.
- **Project Knowledge** (`30_Project_Knowledge`) is project
  understanding/onboarding, private by default. It is not a universal
  intermediate store for M1/M2 material: a source whose purpose is M1 or
  M2 management routes to its appropriate M1/M2 lane, never into Project
  Knowledge merely for convenience.
- **PM Case Library** (`40_PM_Case_Library`) is a flat, cross-project,
  personal-reference collection of real management situations (client/
  team/stakeholder behavior, approach, outcome, takeaway) organized by
  pattern rather than by project - not a per-project store like the three
  above. It never substitutes for M1/M2's own current-state records
  (`individual_risk`, `project_risk`, `m2_input`, `evidence_log`) for an
  actively-managed project or person - see `pm-case-knowledge-roles`.

## Core Judgment Rules

- Start from the smallest relevant evidence source; do not invent
  unsupported facts.
- Keep business-facing output concrete and evidence-based.
- Russian is the default language for business-facing output unless the
  user asks otherwise; preserve English terms/citations that are already
  part of the source.
- Preserve established template schemas and filename conventions unless
  the user asks for a schema change.
- Google Sheets for final tabular output, Google Docs for final
  narrative/status output; local CSV/Markdown only as fallback or
  staging.
- Visibility/sharing (what's shared with whom) follows the owning
  skill/reference - see M2 Project Layout in README and
  `qa-management-roles`.
- Append-only vs. versioned-snapshot behavior (1to1 files never overwrite
  old rows; dated reports get `_vN`) is owned by each document's skill -
  follow it, don't improvise a new convention.

## Repository Validation

Before committing a structural change, run
`.agents/scripts/validate_repo.py` (must exit 0) and
`.agents/scripts/check_sensitive_data.py` (scans the whole commit
candidate, not just your diff). See `repo-maintenance` for the full
checklist.

On Windows, if `python` or `py` fails before script startup with
`ERROR_NO_SUCH_LOGON_SESSION` / "A specified logon session does not
exist", it is usually the Microsoft Store App Execution Alias shim, not
Python itself. Bypass the shim by calling the real interpreter directly,
currently `C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\python.exe`,
or put that directory ahead of `...\Microsoft\WindowsApps` in `PATH`.

**Never pass a Git-Bash-style POSIX path (`/tmp/foo.txt`, `/c/tmp/foo.txt`)
as a file argument to Python, even when launching Python from the Bash
tool.** Python here is a native Windows binary - it does not go through
Git Bash's path translation at all, and the two malformed-path shapes
fail in different, easy-to-misread ways:
- `/tmp/foo.txt` (no drive letter) does *not* error - Windows silently
  resolves a bare leading slash to "root of the current drive," so it
  writes/reads `C:\tmp\foo.txt` instead of Git Bash's own `/tmp` (which
  Git Bash maps elsewhere entirely). A write "succeeds" with no error at
  a location that isn't the one you meant, so a later `python ... read
  same posix path` can then fail (or silently read stale/unrelated
  content) while looking like a transient bug.
- `/c/tmp/foo.txt` (Git Bash's drive-letter mount syntax) fails outright
  with `FileNotFoundError` - Windows has no literal folder named `c` at
  any drive root; only Git Bash's own builtins understand that syntax.

Always use a native Windows path for any argument a Python script will
`open()`, e.g. `r'C:\tmp\foo.txt'` or `C:\Users\<user>\...`. The Bash
tool's own commands (`ls`, `cat`, `grep`, `find`) still take the `/c/...`
form as usual - only Python's (and other native-Windows-binaries')
argument parsing needs the native form; don't convert every path in a
mixed bash+python command, just the ones a Python `open()` call will see.

`check_sensitive_data.py` builds part of its watch list from Google Drive.
If it reaches Google API code and then fails with `WinError 10013` or a
socket/network permission error, rerun it with network/escalated
permissions; do not report the sandboxed failure as the final validation
result.

## Multi-Agent Convention

This repository is used by Codex, Antigravity, and Claude Code. Canonical
skill content is shared under `.agents/skills/` for all three - runtime
differences are limited to machine-local discovery adapters (see Start
Here) and genuinely necessary invocation notes inside a skill, never a
duplicated runtime-specific skill body.
