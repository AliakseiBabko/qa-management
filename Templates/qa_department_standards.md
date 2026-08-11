# Template: QA Department Standards

Output format — Google Doc, one single living document at
`50_QA_Department_Standards\qa_department_standards`. Personal reference
only (not shared), same visibility convention as `pm_case_library`. This
is the current, department-level answer to "what tools/process/approach
does the department expect right now" — the thing you check your own
projects' alignment against. It is **not** a per-project document (that's
`30_Project_Knowledge`) and **not** a log of management situations
(that's `40_PM_Case_Library`).

Organized by **topic**, not by project or by date. A requirement/tool
entry is current-state, not historical — when a requirement changes or is
superseded, update the entry in place (rewrite it) rather than appending
a new one; the Change Log captures the history of what changed and when,
the topic sections stay a clean current picture. This mirrors the
current-state-single-entry convention used for `project_metrics`/
`project_risk` (see `feedback_current_state_table_shape` in user memory),
applied to a topic-organized reference instead of a per-person/per-project
row.

Each entry, under its topic heading:

> **<Requirement/tool name>** — what it is, what's expected (which
> projects/situations it applies to, if not all), since when, source
> (who/what communicated it). One or two sentences; link out instead of
> pasting a long external doc's content here.

## QA Department Standards

### Tools

Required or standard tooling across the department — test management,
automation frameworks, reporting/CI tooling, AI-assisted QA tooling.
Entries land here once a real requirement/adoption decision exists, not
as a wishlist.

### Process Requirements

Concrete process expectations — Definition of Done, quality gates, bug
lifecycle, review/reporting cadence — stated at the department level
(distinct from a single project's own process, which belongs in that
project's `pk_test_strategy`/`аутсорс_чек_лист_qa` instead).

### Current Department Direction

Standing priorities/initiatives the department is currently pushing
(a quarter's focus area, a rollout in progress, a metric the department
is optimizing for). Update or retire an entry once the direction changes
or the initiative completes — don't leave a stale priority looking
current.

### Change Log

Dated one-line entries only — what changed and in which topic section,
never the full entry content itself. If an entry runs past ~2 lines, that
content belongs in the topic section, not here.
