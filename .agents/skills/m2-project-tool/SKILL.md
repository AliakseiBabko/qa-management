---
name: m2-project-tool
description: Work with the company's internal project-management web app (the "project tool", expected to become the department standard for M2 project management) as QA M2 - check that every active M2 project is set up there (M2 assigned as the QA Department Manager, strategy-chat link correct and the posting bot added), publish the weekly QA status report or a project risk through its Activity Board / Risks tabs (both relay into the project's strategy chat), and answer what an M2 can and cannot do in the tool. Use when the user asks to set up, check, or sync their projects in the project tool, to post a weekly status/risk there, or what the tool offers. Not for drafting the status text itself (m2-project-status-report owns that) and not for Drive document updates.
---

# M2 Project Tool

The project tool is a company web app that collects project data from the
CRM (Salesforce) and the HR system once a day, and gives every role
(Sales, DC, PC, M2, M3) one shared project card. For M2 it replaces the
hand-written weekly status in the strategy chat: a status report or risk
created in the tool is relayed into that project's strategy chat by a
polling job, usually within a minute. It is expected to become the
department standard for M2 project management, so treat it as the default
destination for the regular weekly status once a project is connected.

The tool's URL and product name identify the employer, so they are never
written in this repository. Read the URL at runtime from the `Tools`
section of `50_QA_Department_Standards/qa_department_standards` (Drive);
if it is not there, ask the user once and suggest logging it through
`qa-department-standards-intake`.

## Facts That Shape Every Run

- **M2 never creates projects.** Projects appear automatically from the
  CRM the day after the deal is opened. "Adding our projects" means:
  find each active M2 project in the tool and confirm M2 is assigned to it.
- **Edit rights come only from assignment.** An M2 sees every project the
  QA department works on (the `All` tab) but can change nothing until the
  M3 sets them as `Department Manager` for `Quality Assurance` on the
  project's Team tab. The user cannot self-assign; a missing assignment is
  a request to the M3, not something to work around.
- **Team composition comes from the CRM.** A person shown as active who has
  actually left (or a missing person) is fixed by asking the RM to close it
  in the CRM; it refreshes the next day. Never "correct" it in the tool.
- **Publishing is outward-facing.** A status report, a risk, a risk action
  plan, and an action-taken entry are each posted into the strategy chat,
  which Sales, DC, and other departments read. Treat every create as a sent
  message: the user approves the exact text and the target project first.
- **Two strategy chats can exist** (an internal one and one with the
  client/Sales side), and one client can also have several "(strategy)"
  spaces that are really different engagements. The link usually arrives
  from the CRM and is right in most cases; before the first post on a
  project, confirm the linked space is that project's internal strategy
  chat. Check its name and members through the Chat API (the
  `chat.spaces`/`chat.memberships` read scopes, as `fetch_chat_export.py`
  uses) rather than opening Google Chat in the browser.
- **Scope is the projects where M2 is the QA Department Manager.** A project
  in the user's `Mine` tab where they are only a Project Employee (their
  own individual-contributor work, managed by another M2) is not theirs to
  set up or post for; leave it out of audits.

## Required Start

1. Read `references/tool-reference.md` (navigation, data model, read API,
   form fields, setup-audit snippet).
2. When publishing a status report, also load `../m2-project-status-report/SKILL.md`
   and follow its content rules; this skill only adds the tool's form
   mapping on top.
3. Get the active M2 project list from Drive `20_M2_Project_Management/_project_registry`
   (and `_aliases` for name variants). The tool's project names come from
   the CRM and often differ (client prefix/suffix, different spelling), so
   match by search plus the QA person on the project, never by exact name.
4. Use the Playwright MCP browser. The tool uses company SSO: if a page
   redirects to `/login`, stop and ask the user to log in in the open
   browser window, then continue.

## Workflow A - Setup Audit ("add/check our projects")

Read-only. Run the audit snippet from `references/tool-reference.md` in the
page (it uses the logged-in session; no credentials are handled), then
report one row per registry project:

| Registry project | Tool project (id) | Tool status | QA manager | QA people in tool | Edit rights | Strategy chat |

Flag, do not fix:

- registry project not found in the tool (spelling, not yet synced, or
  not a CRM project at all - for example an individual-contributor
  engagement);
- found but M2 is not the QA `Department Manager` -> list for the M3;
- QA people in the tool differ from the registry `People` column ->
  either the registry is stale or the CRM is; say which evidence is newer
  and route a CRM fix to the RM;
- a project in the tool's `Mine` tab that is not an active registry
  project (ended engagement, or an assignment as plain employee);
- strategy chat state: `NO_STRATEGY_CHAT_LINK` (add the link) or
  `BOT_NOT_IN_SPACE` (the user adds the tool's app once in that chat: space
  name menu -> Apps & integrations -> Add apps -> search the app by the
  tool's product name; not via Manage members). The status-report form
  shows these steps itself while the app is missing. If the user says the
  app is already in the space but the status stays `BOT_NOT_IN_SPACE`,
  compare room ids: the CRM-supplied link often points at a different
  space. Replace it (pencil next to Strategy Chat) with the link the user
  gives, and report the old room id so it can be restored. Both are one-time
  user actions in Google Chat; the agent does not do them.

## Workflow B - Weekly QA Status Report

1. Draft the text with `m2-project-status-report` (Outstaff Delivery weekly
   format where that standard applies), for an explicit absolute period.
2. Map it onto the tool's status-report form (`references/tool-reference.md`,
   Status Report Form): Department = `Quality Assurance` (this is what
   pulls the QA team names into the posted message), Title, Period from/to,
   colour 🟢/🟡/🔴, and the four rich-text sections Delivery, Updates, Risks,
   Upsales. Leave a section empty rather than pad it.
3. Show the user the filled form content per project and get an explicit
   go for that project. Check `chat-binding-status` is `connected` first;
   if not, publishing will not reach the chat - fix Workflow A first.
4. Fill the form in the browser and press `Create and publish`. Read the
   project's `strategies` list back to confirm the entry exists; mention
   that the chat message lands on the next polling cycle.
5. Never publish to try the form out. The tool's own author tests on a
   separate dev instance for exactly this reason.

## Workflow C - Project Risk

Only for a risk that meets the department definition (client-side threat,
capacity failure, retention) - not a process gap. A risk created here is
posted to the strategy chat and becomes visible to Sales, which is its
purpose; agree the wording with the user first. Fields: type, severity,
short reason, client escalation yes/no, target (a person on the project or
the whole project), responsible role-holder, description. The tool then
offers to change the project's overall risk level and requires a reason.
Action plans (owner + deadline) and action-taken notes post into the same
chat thread. Mirror any risk created here in Drive `project_risk` through
the normal M2 cascade; the tool does not replace that record.

## What M2 Can Do In The Tool

As QA `Department Manager` on a project (permissions confirmed through
`my-permissions`). Core M2 duties, in order of how often they matter:

1. **Weekly status report** (Workflow B) - the routine duty.
2. **Risks** (Workflow C) - raise, add an action plan, log actions taken,
   close as successful/unsuccessful; every step posts to the chat thread.
3. **Project indicators** - Status (active, pending, ...), Development
   potential, Risk level. Each change asks for a reason and lands in the
   activity log; keep Risk level consistent with the open risks.

Also available, use only when asked:

- Overview: description, links (for example a Google Doc), intermediary
  chain, Project/Strategy/Accounting chat links.
- Team tab per QA engineer: health status, extension prospect, comment,
  1:1 notes, feedback (for example from the client, optionally made visible
  to the employee); a generated Google Form can collect feedback from a
  client-side lead, but agree that with Sales first. HR fields are
  read-only context (level, upcoming vacation, visa, military status) and
  help with availability planning.
- Employee History: everyone who ever worked on the project and whether
  they did the work (`employee`) or were presented to the client
  (`declared`).
- Audits: questionnaires applied to projects (for example an AI-usage
  survey); M2 can also create a template for their own project.
- Cross-project views: `/risks` filtered by department, People, Departments.
- Feedback button: bugs and ideas go straight to the tool's team.

## What M2 Cannot Do

- Create projects (they come from the CRM daily).
- Assign roles or managers (the M3 does; every role shows `canAssign:
  false` for M2).
- Change the team list (the RM fixes it in the CRM; refreshes next day).

## Relation To Drive Records

The tool does not sync with Drive. Until the user decides otherwise:

- A risk raised in the tool is also kept in Drive `project_risk` through the
  normal M2 cascade (the tool is the visible, shared channel; Drive keeps
  the full M2 reasoning). Apply the department risk definition to both.
- A status report posted through the tool is the delivered weekly status;
  save a Drive copy under `status_reports` only if the user asks.
- 1:1s stay in the Drive 1:1 records (normally kept by M1); do not
  duplicate them in the tool's 1:1 notes.

## Announced Roadmap (walkthrough, 2026-10-01)

Not live yet; re-check before relying on any of it: a Delivery tab with
the full project and client description (migrated from the PC/PMO
system), a workload view of hours, sick days and vacations from the HR
system, stop requests sent to the RM for approval and synced back to the
CRM, onboarding checklists that announce a start in the strategy chat, a
per-role home page listing pending statuses and new risks, more frequent
CRM sync, and later the department metrics app's results. DC, PC/PMO and
delivery managers are being moved onto the tool, with section-level edit
rights split by role.

## Guardrails

- No create, update, or delete call without the user's explicit approval
  of that exact item; read endpoints are free to use.
- Never call write endpoints directly with `fetch`; use the UI form so the
  tool's own validation and reason prompts run.
- Do not copy real names, project names, or tool URLs into this repo;
  audit output is reported in chat or written to Drive only.
- Playwright snapshots land in `.playwright-mcp/` (gitignored); never move
  them into a tracked path.
