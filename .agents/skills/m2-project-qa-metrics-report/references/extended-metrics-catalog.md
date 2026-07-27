# M2 QA Process Extended Metrics Catalog

Scope: the optional/tooling-gated Extended `qa_process_metrics` catalog and DOCX/XLSX source-extraction strategy. Load only when adding an Extended-tier metric row or extracting a raw source document — not needed for the Core 6 metrics or routine reporting.

## Source Extraction Strategy

- Before reading an original DOCX/XLSX file, check whether the source was already extracted under `G:\My Drive\QA_Management\90_Storage\_System\extracts\source\YYYY-MM-DD\<Project>\`.
- For extracted workbooks, start from the workbook JSON file. Use sheet names, row counts, column counts, `document_role`, source path, and preview rows to decide which CSV sheet files matter.
- For extracted workbooks with many sheets or many rows, do not read all CSV files end to end. First inspect the JSON manifest, then search candidate CSV files for metric labels, dates, scorecard sections, owners, blockers, trend words, or project-specific keywords.
- For extracted DOCX files, search headings and key phrases before reading long sections. Prefer sections that mention metrics, scorecard, plan progress, QA process, automation, manual testing, feedback, risks, blockers, owners, and review dates.
- If no suitable extract exists, run `.agents/scripts/qa_source_extract.py` with the source root and an output root under `G:\My Drive\QA_Management\90_Storage\_System\extracts\source\YYYY-MM-DD`. Do not re-extract into a non-empty folder without `--overwrite` unless the user explicitly wants to refresh the extract.
- Preserve extracted source paths in `evidence_log`, not in `Пояснение` — neither table has an evidence/path column.
- If an extracted file is stale compared with the source document modified date, say so and decide whether the stale extract is sufficient or a refreshed extract is needed.

## Extended Metric Catalog (`qa_process_metrics`, optional tier)

Optional, menu not checklist. Add a row only when the project **already has**
a working data source for that specific metric (a configured TMS, a CI
dashboard, a prod/pre-release tag already in the bug tracker). Do not add a
blank placeholder row "in case" a tool gets set up later, and do not ask a
project to stand up new tooling just to populate a catalog row.

Not the Core 6 (see `qa-process-metrics-schema.md`'s Schema section and
`Templates\метрики_проекта_qa.md` §2 Core) — this is the optional menu.
Full definitions and "where to find it" guidance:
`Templates\метрики_проекта_qa.md` §2.

### Project improvement / plan progress

- Progress against the project development plan: planned actions completed, accepted by project stakeholders, blocked, or postponed.
- Automation development progress: new automated coverage, stabilized tests, CI/CD/reporting integration, useful automation results for release decisions.
- Risk/problem management: visible project problems identified, owner assigned, mitigation started, current blocker age, next review date.
- Accepted project improvements: process changes, reporting improvements, test management changes, documentation/readiness improvements, stakeholder-approved QA proposals.

### QA process speed and predictability

- QA cycle time for feature/regression/retest flow.
- Time from build readiness to QA result.
- Retest turnaround time.
- Blocker age and environment/data waiting time.
- Deadline fit: testing completed inside agreed window, or reason for miss.

### Automation

See `m2-role/m2-metrics-attribution.md`, Automation Metric Layering, for
the cascade-layer rule. When a source contains these facts, update
`qa_process_metrics` first, then `project_metrics`, then `_project_registry`
— `individual_metrics` is used only for the person-specific
contribution/ownership angle (owns the framework, contributes tests,
improves visibility/reporting, needs support presenting progress, lacks
autonomy maintaining the framework).

- Automation coverage by critical flow/module.
- Number of automated tests added or maintained.
- Automation execution time.
- Pass rate.
- Flaky test count/rate and trend.
- Failed-test triage time.
- CI/CD/report availability and usefulness for release decisions.

### Manual testing

- Manual test coverage by feature, requirement, flow, or risk area.
- Number/scope of tested features per iteration.
- Test execution speed for planned scope.
- Escaped defects / missed bugs by severity.
- Defect quality: duplicates, invalid bugs, not-a-bug, feature requests misclassified as bugs, unclear bug reports.
- Regression readiness and completion for release-critical scope.

### Client/team value and communication

- Stakeholder visibility: which decision-makers or key stakeholders receive QA status, risks, metrics, or proposals.
- Feedback from client, PM, DC, QA Lead, or team; mark whether feedback is direct or indirect.
- Accepted QA recommendations and their project impact.
- QA contribution to project value: reduced risk, faster release decision, better quality signal, improved trust, reduced support/rework.

### Individual-input metrics for project aggregation

Use individual metrics only when they explain project capacity, coverage, or role value. For person-level reporting, use the individual QA metrics skill.

- Tests created/executed by person or stream.
- Testing speed and scope per iteration.
- Deadline fit for assigned QA scope.
- Defect quality and escaped defects connected to the person's scope.
- Stakeholder interaction level and accepted improvements initiated by the person.
- Automation contribution by person or stream: tests added, maintained, stabilized, or connected to reporting/CI.
- Individual blockers, overload, access gaps, or unclear ownership that affect project delivery, QA speed, or continuity.
