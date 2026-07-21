# Search Cookbook (Phase 12)

Recipes for finding things without re-deriving `search_workspace.py`/
`show_project_state.py` flag syntax from scratch each time. Every recipe
below is read-only. Placeholders (`<Person>`, `<Project>`, `<topic>`,
`<date>`, `<run-id>`) stand in for real values - never write a real
name/project into a committed file, only into a live command you run
locally.

All examples assume you're at the repo root and Google API access is
already set up (see README.md, Google API Smoke Test).

## "Where was `<Person>` last mentioned?"

```sh
python .agents/scripts/search_workspace.py search "<Person>" --json
```

Searches current canonical `.md`/`.csv` content across the whole workspace
mirror (`HEAD`). If you need to know *when* they were first mentioned, or
want the full history of mentions rather than just the current state, use
`history` instead (walks first-parent commits):

```sh
python .agents/scripts/search_workspace.py history "<Person>" --json
```

## "What changed for `<Project>` since `<date>`?"

```sh
python .agents/scripts/search_workspace.py history "<Project>" --since <date> --json
```

`--since`/`--until` filter by commit date along the first-parent history.
Pair with `--path` to narrow to one document if you already know which one
changed (e.g. `--path project_risk`).

## "Find all open risks mentioning `<topic>`."

```sh
python .agents/scripts/search_workspace.py search "<topic>" --path project_risk --json
```

`--path` is repeatable and matches canonical document names/paths
literally (`--literal-pathspecs` under the hood) - pass it multiple times
to search several document types in one call
(`--path project_risk --path project_development_plan`). For a broader
sweep of *pending* (not yet risk-concluded) open questions on the same
topic, also check `qa_manage.py gates` (see below) rather than assuming
`project_risk` already has the full picture - a topic can be sitting in an
unanswered `m2_input` round instead.

## "Find processed transcripts mentioning `<topic>`."

```sh
python .agents/scripts/search_workspace.py search "<topic>" --kind source --json
```

`--kind source` restricts to the exported source-text blobs
(`_source_text/blobs/v1/*.txt` - the exact text of processed transcripts/
chats), as opposed to canonical documents. Combine with `--run-id <id>` if
you already know which intake run produced the transcript you're thinking
of.

## "Search only canonical docs."

```sh
python .agents/scripts/search_workspace.py search "<topic>" --kind canonical --json
```

`--kind` accepts `source`, `canonical`, or `all` (default). Canonical means
the `.md`/`.csv` mirror of Sheets/Docs content - never source transcript
text.

## "Search only processed source text."

Same as "find processed transcripts" above - `--kind source`. Use this when
you specifically want to know what was *said* in a source, not what M2
*concluded* from it (the canonical documents are the conclusions; the
source text is the raw evidence).

## "Search one run by run-id."

```sh
python .agents/scripts/search_workspace.py search "<topic>" --run-id <run-id> --json
```

Narrows matches to files/blobs tied to one specific intake run - useful
when you already have the run id from `qa_manage.py dashboard`/`pack` and
just want everything that run touched.

## "Use `show_project_state.py` for live Drive state when the mirror may be stale."

`search_workspace.py` reads the **private mirror** (last `commit_workspace_state.py`
snapshot), not live Drive - if a pass hasn't been committed yet, the mirror
is behind. When you need the actual current state of a project (not "as of
the last snapshot"), read Drive directly instead:

```sh
python .agents/scripts/show_project_state.py --project <Project> --json
```

or a targeted read of one document:

```sh
python .agents/scripts/show_project_state.py --project <Project> --document m2_input --json
```

Rule of thumb: `search_workspace.py` for **breadth** (across projects/time,
git-history-aware); `show_project_state.py` for **freshness** (this one
project, right now, guaranteed live).

## Unprocessed inbox inspection

`search_workspace.py` only sees what's already in the private mirror -
a source still sitting unprocessed in `00_Inbox` won't show up there at
all (it hasn't been committed yet). For that case:

**Unprocessed inbox inspection: use `triage` / `triage-one` / `classify` /
`pack` before `search_workspace.py`.**

```sh
python .agents/scripts/qa_manage.py triage --json
python .agents/scripts/qa_manage.py triage-one <run-id> --json
python .agents/scripts/qa_manage.py classify <run-id> --json
python .agents/scripts/qa_manage.py pack <run-id> --json
```

`triage` gives a backlog overview; `triage-one`/`classify` inspect one
discovered source (format signals, candidate routes, a capped preview);
`pack` is the full handoff packet once a run is further along. None of
these four write anything.

## Related read-only commands

- `qa_manage.py gates [--project <Project>] [--min-age-days N] [--json]` -
  every project with a currently pending `m2_input` round (an open
  question gate blocking `project_risk`/`project_development_plan`), sorted
  oldest first with a recommended next action. Read-only; never answers a
  question or writes a document. See README.md, "Current pipeline scripts".
- `qa_manage.py dashboard` - the default operator entry point for "what
  needs attention in the intake queue" (distinct from `gates`, which is
  about M2's own pending decisions, not intake processing).
- `scan_open_questions.py` - cross-project scan that also surfaces
  `project_metrics` "Неизвестно" clarification gaps and `project_risk`
  action-plan follow-ups, not just `m2_input` rounds; `gates` is the
  narrower, m2_input-specific view.
