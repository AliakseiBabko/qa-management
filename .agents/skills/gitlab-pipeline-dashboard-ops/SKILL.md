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

**Gotcha:** SecretStore data lives under the user's Windows profile, not
inside the repo workspace. If `Get-SecretInfo`, `Get-Secret`, or
`Get-SecretStoreConfiguration` fails with a
`SecureStoreFile`/`FileSystemWatcher` initialization error, rerun the same
read with escalated permissions instead of treating the vault as missing
or broken. Listing secret metadata is safe; never print the token itself.

**Gotcha:** when testing several candidate secret names in PowerShell,
capture loop output before formatting it. A direct loop followed by a
pipeline can parse as an empty pipe element in non-interactive shells.
Use this shape:

```powershell
$results = foreach ($name in @("<SecretName>", "<FallbackSecretName>")) {
  try {
    $Headers = @{ "PRIVATE-TOKEN" = (Get-Secret -Name $name -AsPlainText) }
    $user = Invoke-RestMethod -Uri "$GitLabApiBase/user" -Headers $Headers -Method Get -TimeoutSec 15
    [pscustomobject]@{
      SecretName = $name
      Auth = "OK"
      UserId = $user.id
      Username = $user.username
      Name = $user.name
    }
  } catch {
    [pscustomobject]@{
      SecretName = $name
      Auth = "FAILED"
      Error = $_.Exception.Message
    }
  }
}
$results | Format-List
```

To verify both token ownership and project access without exposing the
token, call `GET /user` first, then `GET /projects/:id` (or the resolved
URL-encoded project path) with the same headers. Report the returned user
identity and whether the project request succeeded; do not report or log
the token value.

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

## Building A CI Performance Evidence Pack From Prometheus

For a completed load-test job, distinguish three data sources before
asking DevOps for extra access:

- **GitLab artifacts** are the source of truth for JMeter's own results:
  `results.jtl`, generated HTML report files, and `statistics.json` if
  present.
- **Prometheus** is the source of truth for scraped infrastructure and
  application telemetry. It can answer historical queries for the test
  window as long as the window is still inside retention; this does not
  require SSH access to Kubernetes nodes.
- **Grafana dashboards** are only a visualization layer. A dashboard that
  uses InfluxQL-style queries (`SHOW TAG VALUES`, `SELECT ... FROM ...`)
  against a Prometheus datasource is an old/backend-mismatched dashboard,
  not proof that current metrics live in InfluxDB.

If Prometheus is reachable from the agent or CI job, collect the missing
bottleneck-analysis data by querying Prometheus directly:

1. Read the job metadata from GitLab: job name, status, runner, branch,
   `started_at`, `finished_at`, pipeline ID, commit, and artifact
   availability.
2. Download JMeter artifacts to an OS temp directory or CI artifact
   workspace, never into this public repo. Parse `statistics.json` first,
   then fall back to `results.jtl`.
3. Determine the actual test window from the JTL timestamps, not only
   GitLab's job timestamps. Include a baseline and cooldown query window:
   `[test_start - 5m, test_end + 2m]`.
4. If the job pushes JMeter metrics to Pushgateway, extract the
   Prometheus labels from the job trace or pipeline variables (usually
   labels such as environment/instance and profile/job name). Prometheus
   may scrape the final pushed values after the GitLab job finish time;
   query a short cooldown window or latest value before concluding the
   final Pushgateway sample is missing.
5. Query Prometheus with `/api/v1/query_range` for time-window data and
   `/api/v1/query` for end/latest snapshots. Report query expressions and
   time bounds in the evidence pack so the result is reproducible.

Minimum Prometheus metric groups for useful bottleneck analysis:

- JMeter pushed metrics: sample count, errors, error rate, throughput,
  response-time avg/p90/p95/p99/max by sampler.
- Node exporter: node CPU, memory, disk IO/filesystem, and network.
- Container/Kubernetes: pod CPU, memory working set, restart count,
  resource requests/limits, and CPU throttling
  (`container_cpu_cfs_*`).
- Ingress/service-mesh: request rate, response codes, request duration,
  retries, upstream latency, and circuit breaker/open-connection signals
  when present.
- JVM/Micrometer for tested services: heap/non-heap, GC pauses, thread
  pools, HTTP server request duration, process CPU, and connection-pool
  metrics such as HikariCP active/idle/pending/max.
- Database exporters used by the system under test: active connections,
  locks, slow/long queries if exposed, cache hit ratio, transaction rate,
  deadlocks, replication lag, disk/IO pressure, and exporter scrape
  errors.
- Queue/broker metrics when the scenario uses messaging: broker CPU/memory
  plus producer/consumer rates, lag, request latency, under-replicated
  partitions, and error counters where applicable.

Prometheus API access is usually enough to build the post-test report if
these metric families are already scraped. Ask DevOps for additional
access or changes only when one of these is true:

- the CI runner/container cannot resolve or reach the Prometheus API;
- Prometheus requires auth and no read-only CI secret exists;
- the needed metric family is absent from Prometheus;
- app pods do not expose metrics, or ServiceMonitor/PodMonitor/scrape
  config is missing;
- retention or scrape interval is too short/coarse for the test duration;
- logs/traces are needed because metrics show a symptom but not the
  failing request path.

Recommended CI flow:

1. Record test start timestamp immediately before running JMeter.
2. Run the load test and always save `results.jtl`.
3. Generate `statistics.json`/HTML from JMeter and push final JMeter
   metrics to Pushgateway, if that path exists.
4. Wait one or two Prometheus scrape intervals before querying final
   values, to avoid reporting stale pre-final Pushgateway data.
5. Query Prometheus for baseline, test, and cooldown windows.
6. Attach a single report artifact containing: JMeter summary, failed
   sample breakdown, Prometheus charts/tables, query expressions, time
   bounds, runner/container limits, and a short bottleneck hypothesis
   section.

Treat low node CPU/memory saturation as only one signal. If response
times are high while node resources are not saturated, investigate app
internals and dependencies first: CPU throttling, JVM GC/thread pools,
connection pools, database locks/IO, service-mesh retries, queue lag, and
test-client constraints.

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
