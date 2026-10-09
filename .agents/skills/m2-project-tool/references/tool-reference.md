# Project Tool Reference

Observed on the live tool (v1.2.x) and in the author's walkthrough for
M2s. Paths are relative to the tool's base URL (see SKILL.md for where the
URL lives). Re-check a path when a call returns 404 - the app is young and
changes often.

## Navigation

- `/projects` - list. Tabs `Mine` (projects where the user holds any role)
  and `All` (everything the user's department visibility allows). Search,
  configurable columns (Sales, DC, PC...), filters by department/role.
- `/projects/<id>` - Overview: description, details (company,
  intermediary, client location, domain, processes), main roles, chats
  (Project / Strategy / Accounting), links, Status / Development
  potential / Risk level with change history, Team management summary
  (department -> manager -> headcount), Activity log.
- `/projects/<id>/strategy` - Activity Board (status reports, meeting notes,
  strategies); `Add activity` opens the form in a side panel
  (`?mode=edit`).
- `/projects/<id>/history` - Employee History: everyone who ever worked on
  the project, department, role (`employee` = does the work, `declared` =
  the person presented to the client), start date, duration.
- `/projects/<id>/team` - current team by department; per-person card with
  1:1s and feedback.
- `/projects/<id>/risks`, `/projects/<id>/audits`
- `/risks` - cross-project risk register, filterable by department.
- `/audit-templates`, `/intermediaries`, `/people`, `/departments`.

## Enumerations

- Project status: `active`, `pending`, ... (shown upper-case).
- Development potential: `not_defined`, `low`, ...
- Risk level: `not_defined`, `all_good`, ...
- Status-report colour: `green` 🟢, `yellow` 🟡, `red` 🔴.
- Activity types: `status_meet` (UI "Status report", the one that relays
  to chat), meeting note, strategy (older types kept for history).
- Project roles: Project Employee, Department Manager, Sales Manager, DC,
  DC Manager, Sales Assistant, Account Manager, Project Manager, Delivery
  Manager, Project Coordinator, Tech Lead.
- QA department: `unitId` 6, name `Quality Assurance` (verify with
  `/api/auth/me` -> `units`).

## Read API (GET, session cookie, call from the page with `fetch`)

| Path | Returns |
|---|---|
| `/api/auth/me` | user id, units with role (`employee`/`manager`), global and project permission codes |
| `/api/projects?search=<text>` | paged list: id, name, status, company, departments, roleMembers |
| `/api/projects/<id>` | project fields incl. status, riskLevel, developmentPotential, start/end dates, links |
| `/api/projects/<id>/my-permissions` | `roles`, `permissions`, `isMember` |
| `/api/projects/<id>/departments` | per department: unitId, manager id/name, activeMemberCount, strategyCount |
| `/api/projects/<id>/chat-binding-status` | `connected`, `reason` (`BOT_NOT_IN_SPACE`, `NO_STRATEGY_CHAT_LINK`), strategyChatUrl |
| `/api/projects/<id>/team` | current members with unitName, status, healthStatus, extensionProspect, HR fields |
| `/api/projects/<id>/members?page=&limit=` | employee history |
| `/api/projects/<id>/strategies?page=&limit=` | Activity Board entries (title, period, status, rich-text sections, unit, author) |
| `/api/projects/<id>/risks` | project risks with open/closed counts |
| `/api/projects/<id>/activity-log?page=&limit=` | role/status/risk events |
| `/api/risks?page=&limit=` | cross-project risks (type, severity, target, status) |
| `/api/audit-templates` | questionnaire templates |

Edit rights on a project = `my-permissions.permissions` contains
`strategies:create` (granted with the QA `Department Manager` role).

## Status Report Form

Activity type `Status report`, then:

| Field | Control | Fill with |
|---|---|---|
| Department | combobox, default "No department" | `Quality Assurance` - pulls the QA team names into the chat message; with no department only a link to the whole team is attached |
| Title | textarea | one short headline of the week |
| Period | two date inputs | absolute from/to |
| Status | combobox | 🟢 Green / 🟡 Yellow / 🔴 Red |
| Delivery | rich text | delivery progress and blockers |
| Updates | rich text | team/process/communication changes |
| Risks | rich text | risk summary (a formal risk goes to the Risks tab) |
| Upsales | rich text | only with real evidence |

Buttons: `Cancel`, `Create and publish` (publishes immediately, relays to
the strategy chat on the next polling cycle). The editors support bold,
italic, strikethrough, bullet list, quote, link, inline code, code block.
Stored as ProseMirror JSON (`deliveryNotes`, `projectUpdates`, `risks`,
`upsales`).

## Setup-Audit Snippet

Run with the browser's evaluate tool on any tool page. Pass the candidate
names from `_project_registry` (and `_aliases`); it searches each, then
reports assignment, edit rights, QA team, and chat binding.

```js
async () => {
  const names = ['<Project A>', '<Project B>'];   // registry names / aliases
  const j = async u => { const r = await fetch(u); return r.ok ? r.json() : {error: r.status}; };
  const me = await j('/api/auth/me');
  const out = [];
  for (const n of names) {
    const hits = (await j(`/api/projects?search=${encodeURIComponent(n)}`)).data || [];
    if (!hits.length) { out.push(`${n} | NOT FOUND`); continue; }
    for (const p of hits) {
      const deps = await j(`/api/projects/${p.id}/departments`);
      const perm = await j(`/api/projects/${p.id}/my-permissions`);
      const chat = await j(`/api/projects/${p.id}/chat-binding-status`);
      const team = (await j(`/api/projects/${p.id}/team`)).data || [];
      const qa = Array.isArray(deps) ? deps.find(d => d.unitName === 'Quality Assurance') : null;
      const qaPeople = team.filter(m => m.unitName === 'Quality Assurance').map(m => m.fullname);
      out.push([n, `${p.name} (${p.id})`, p.status,
        qa ? `QA mgr: ${qa.departmentManagerId === me.id ? 'ME' : (qa.departmentManagerName || 'none')}` : 'no QA dept',
        `QA: ${qaPeople.join(', ') || '-'}`,
        (perm.permissions || []).includes('strategies:create') ? 'can edit' : 'read-only',
        chat.connected ? 'chat OK' : chat.reason].join(' | '));
    }
  }
  return out;
}
```
