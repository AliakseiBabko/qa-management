---
name: gitlab-pipeline-dashboard-ops
description: Trigger and troubleshoot a self-hosted GitLab CI pipeline via its REST API (parent/child bridge pipelines, manual jobs, runner tag and protected-branch diagnosis), set up a secure local credential store for repeated API calls, and audit a Grafana+Prometheus monitoring stack by cross-checking dashboard JSON against live metric data to tell a real gap from a cosmetic one. Use when the user needs to run or debug a GitLab CI pipeline from the API instead of the UI, figure out why a triggered job won't start, or check whether a Grafana dashboard is actually returning data rather than just rendering.
---

# GitLab Pipeline + Dashboard Ops

Reusable operational method for driving a self-hosted GitLab CI pipeline
and a Prometheus/Grafana stack from the API, and for diagnosing the
handful of non-obvious failure modes both surfaces produce. This is
methodology only — no project's real hostnames, credentials, project
paths, runner names, or personal names belong in this file. Get the
non-secret facts (URLs, project path, runner tags, dashboard inventory)
from that project's own ops-runbook / project-knowledge document in
Drive; get tokens/passwords from the local secret store — **never from a
Drive document**, even one otherwise dedicated to this project's
operational facts. See "Credential Setup" below for where a token
actually belongs.

## Required Start

1. Identify the project's own ops-runbook or project-knowledge document
   (a Drive doc under `30_Project_Knowledge/<Project>/`, distinct from
   its `pk_performance_test_plan`-style test-planning document) and read
   it for the actual GitLab URL, project path, Grafana/Prometheus URLs,
   runner tags, and dashboard inventory. That document holds durable,
   non-secret facts only — it is project data this skill consumes, not
   a second skill, and it must never contain a token or password. Do not
   invent or reuse an example value from this file.
2. Resolve the actual credential via the local secret store (see
   "Credential Setup") — if nothing is stored yet, set it up before
   attempting any API call. A credential found written into a Drive
   document is a policy violation to flag and fix (move it to the secret
   store, scrub the document), not a value to use as-is.

## Credential Setup (PowerShell SecretManagement/SecretStore)

For repeated API calls across a session, store the token once instead of
re-pasting it:

```powershell
Install-PackageProvider -Name NuGet -MinimumVersion 2.8.5.201 -Force -Scope CurrentUser
Set-PSRepository -Name PSGallery -InstallationPolicy Trusted
Install-Module Microsoft.PowerShell.SecretManagement -Scope CurrentUser -Force
Install-Module Microsoft.PowerShell.SecretStore -Scope CurrentUser -Force
```

**Gotcha:** a single `Install-Module A, B` call can silently install `A`
and drop `B` if a prompt interrupts it partway — install each module
separately and verify with `Get-Module -ListAvailable Microsoft.PowerShell.Secret*`
before continuing, rather than trusting the first command's exit code.

**Gotcha:** the vault-registration cmdlet is `Register-SecretVault`, not
`Register-SecretStore` (that name doesn't exist) — `Register-SecretStore`
lives inside the `SecretStore` module itself and only *configures* an
already-registered vault:

```powershell
Register-SecretVault -Name SecretStore -ModuleName Microsoft.PowerShell.SecretStore -DefaultVault
```

**Gotcha:** setting `-Authentication None` (no master-password prompts —
appropriate for a low-sensitivity token, a real security tradeoff the
user should explicitly choose, not something to default to silently) on
a brand-new vault still requires a one-time bootstrap password on first
creation, even though the target config has no password. In a
non-interactive session, `Set-SecretStoreConfiguration -Authentication None`
alone fails asking for a password it can't prompt for; pass a throwaway
one explicitly:

```powershell
$bootstrap = ConvertTo-SecureString ([System.Guid]::NewGuid().ToString()) -AsPlainText -Force
Set-SecretStoreConfiguration -Authentication None -Interaction None -Password $bootstrap -Confirm:$false
```

After that, `Set-Secret -Name <Name> -Secret "<token>"` and
`Get-Secret -Name <Name> -AsPlainText` work with no further prompts.

**Never** have the agent handle the real token value — ask the user to
run the `Set-Secret` line themselves in their own terminal so the secret
never enters the conversation transcript.

## Triggering And Following A Pipeline Via API

```powershell
$Headers = @{ "PRIVATE-TOKEN" = (Get-Secret -Name <Name> -AsPlainText) }
```

1. **Resolve the project ID** from its path (`GET /projects/<url-encoded-path>`) rather than
   guessing it — cache the numeric ID for the rest of the session.
2. **Confirm the actual default branch** (`GET /projects/:id` → `default_branch`,
   or list branches) before triggering — don't assume `main`; many repos
   use `develop` or another name, and a wrong ref fails with a plain
   "Reference not found" that gives no other clue.
3. **Create the pipeline**: `POST /projects/:id/pipeline` with `{"ref": "<branch>"}`.
4. **Manual/trigger ("bridge") jobs**: a root `.gitlab-ci.yml` that fans
   out into child pipelines via `trigger: include: ...` shows those as
   bridge jobs in the parent pipeline's `stage: trigger`. List them with
   `GET /projects/:id/pipelines/:id/bridges`, then `POST
   /projects/:id/jobs/:bridge_id/play`.
5. **Gotcha — bridge jobs are not regular jobs.** `GET
   /projects/:id/jobs/:bridge_id` 404s for a bridge job; re-fetch via
   `/pipelines/:id/bridges` instead to read its `downstream_pipeline`.
6. **Gotcha — an all-manual child pipeline reads as a bridge failure,
   and this is normal, not a bug.** If every job in the triggered child
   pipeline is `when: manual`, none run automatically, so the child
   pipeline immediately settles into `status: skipped`. A parent bridge
   job using `strategy: depend` then reports `status: failed` because it
   waited for a real completion and got "skipped" instead. The child
   pipeline and its manual jobs still exist and are fully playable — do
   not treat the bridge's "failed" status as blocking; go straight to
   listing and playing the child pipeline's own jobs
   (`GET /projects/:id/pipelines/:child_id/jobs?scope[]=manual`, then
   `POST /projects/:id/jobs/:job_id/play`).
7. **Poll for completion**: `GET /projects/:id/jobs/:job_id` in a loop
   until `status` leaves `pending`/`running`/`created`. Run this as a
   background task with a sane attempt cap rather than blocking — a slow
   or stuck runner can take minutes.

## Diagnosing A Job Stuck In `pending`

Work through these in order — each rules out one specific cause before
moving to the next, and the later ones need access the API alone may not
grant:

1. **Tag match, not just tag presence.** A GitLab runner needs *every*
   tag the job requests, not just one — a job tagged `dev, tools` will
   not run on a runner tagged only `dev`. Compare `GET
   /projects/:id/jobs/:job_id` → `tag_list` against each candidate
   runner's own `tag_list` (`GET /runners/:id`) — an exact superset, not
   an overlap.
2. **`online` + `active` is necessary but not sufficient** — also check
   `locked` (project-locked runners can't serve other projects) and,
   for jobs on a protected branch, `access_level`. Counter-intuitively,
   `access_level: not_protected` does **not** exclude protected
   branches — it means the runner isn't *restricted to* protected-only;
   it can still serve them. Don't chase this as the cause unless a
   runner is explicitly `protected: true`-restricted the other way.
3. **Read the exact UI wording on the job's own page** — it disambiguates
   two very different situations that look identical from the API's bare
   `status: pending`:
   - *"This job is in pending state and is waiting to be picked by a
     runner"* — GitLab believes an eligible runner exists; this points to
     **queue congestion** (the runner is likely busy on another
     project's job, especially if someone recently lowered its
     concurrency limit).
   - *"This job is stuck, because you don't have any active runners
     online with any of these tags assigned to them"* — no eligible
     runner exists at all; re-check tags/status, this is a
     configuration problem, not a queue problem.
4. **Cross-project runner load needs instance-admin access, not project
   access.** `GET /runners/:id/jobs` (what's actually running on a
   shared runner across every project it serves) 403s for a
   project-scoped token even when that same token can trigger pipelines
   fine. The UI equivalent (`/admin/runners`) 404s for a non-admin
   account too — this is a real permission boundary, not a bug to work
   around. If congestion is suspected, this is the point to hand off to
   whoever actually has admin rights, with the specific runner name and
   job ID already identified — don't keep guessing past this point.

## Auditing A Grafana + Prometheus Dashboard Set

The point of this pass is that **a dashboard rendering correctly in the
UI proves nothing about whether its panels return data** — query syntax
can be valid-looking and still be silently wrong for the bound
datasource, and a panel can be perfectly correct but simply idle. Only a
live cross-check tells them apart.

1. List every dashboard: `GET /api/search?type=dash-db` (Grafana API,
   basic auth) — gives title, UID, and folder for each.
2. Fetch each dashboard's full JSON: `GET /api/dashboards/uid/:uid`.
   **Gotcha:** a dashboard that returns `500 Internal Server Error` with
   an empty body at this step (not just a bad query result) is broken at
   the storage/metadata level, not the query level — that needs a
   Grafana admin, not a query fix.
3. For every panel, extract its `datasource.type` and every target's
   query (`expr` for Prometheus, `query`/`rawSql` for others).
   **Gotcha:** a legacy dashboard schema stores panels under a top-level
   `rows[].panels[]` array instead of `panels[]` directly — check for
   `rows` before concluding a dashboard has zero panels.
4. **Flag a datasource/query-language mismatch immediately** — e.g. a
   query using `SHOW TAG VALUES ...` or other `SELECT ... FROM ... WHERE`
   syntax bound to a Prometheus datasource errors with a
   language-specific parse error (Prometheus's error names an
   "unexpected identifier" from the foreign syntax). This is the
   signature of a dashboard built for a different backend (e.g. InfluxDB)
   and never ported — confirmed broken, not a live-data question at all.
5. For every syntactically-plausible Prometheus query, extract the base
   metric name(s) and query Prometheus directly:
   `GET /api/v1/query?query=<metric_name>` (URL-encode the query).
   Classify each: **zero series** = either a genuinely idle
   metric (no current traffic to report) or a real exporter/collector
   gap — state which you believe and why, don't leave it ambiguous;
   **non-zero series** = confirmed live.
6. Report as a table per dashboard (panel, metric(s), verdict, note) plus
   a short summary of anything RED (broken) or worth a second look — not
   a wall of raw query output.

## Guardrails

- Never write a real hostname, IP, credential, project path, runner
  name, or person's name into this file — see the workspace's own
  sensitive-data policy for where that belongs instead (the project's
  Drive-hosted knowledge document).
- Never write a token or password into any Drive document, including the
  project's own ops-runbook doc — that doc is durable project *data*
  (URLs, paths, tags, inventory, procedures, history), not a secret
  store. Tokens/passwords live only in the local secret store (see
  "Credential Setup"). If a credential is ever found already sitting in
  a Drive document, treat it as compromised the same way a
  conversation-leaked token is: get it rotated, move the replacement to
  the secret store, and scrub the document.
- Don't guess a project's default branch, GitLab project path, or
  Grafana/Prometheus URLs — resolve or read them, every time.
- Don't treat a bridge job's "failed" status as pipeline failure without
  checking its downstream pipeline first — see the all-manual-child
  gotcha above.
- Don't keep polling or retrying past the point where the cause requires
  access you've confirmed you don't have (cross-project runner load,
  admin-only views) — hand off with the specific diagnostic facts
  instead of continuing to guess.
