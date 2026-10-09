---
name: m2-project-tool
description: Work with the company's internal project-management web app (the "project tool") as QA M2 - check that every active M2 project is set up there (M2 assigned as the QA Department Manager, strategy-chat link correct and the posting bot added), and publish the weekly QA status report or a project risk through its Activity Board / Risks tabs, which relay into the project's strategy chat. Use when the user asks to set up, check, or sync their projects in the project tool, or to post a weekly status/risk there. Not for drafting the status text itself (m2-project-status-report owns that) and not for Drive document updates.
---

# M2 Project Tool

The project tool is a company web app that collects project data from the
CRM (Salesforce) and the HR system once a day, and gives every role
(Sales, DC, PC, M2, M3) one shared project card. For M2 it replaces the
hand-written weekly status in the strategy chat: a status report or risk
created in the tool is relayed into that project's strategy chat by a
polling job, usually within a minute.

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
  client/Sales side). The link usually arrives from the CRM and is right in
  most cases; before the first post on a project, open the linked chat and
  confirm it is the internal strategy chat.

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

## Other Capabilities (use only when asked)

- Overview: project status / development potential / risk level selectors
  (each change asks for a reason and lands in the activity log),
  description, links (attach a Google Doc), intermediary chain.
- Team tab per person: health status, extension prospect, comment,
  1:1 summary, feedback (optionally visible to the employee), HR fields
  (level, upcoming vacation, visa). 1:1s are normally kept by M1 - do not
  duplicate the Drive 1:1 record here.
- Audits: questionnaire templates applied to projects (for example an AI
  usage survey). Read with `audit-templates`; fill only on request.
- Feedback button: bugs and ideas go to the tool's team.

## Guardrails

- No create, update, or delete call without the user's explicit approval
  of that exact item; read endpoints are free to use.
- Never call write endpoints directly with `fetch`; use the UI form so the
  tool's own validation and reason prompts run.
- Do not copy real names, project names, or tool URLs into this repo;
  audit output is reported in chat or written to Drive only.
- Playwright snapshots land in `.playwright-mcp/` (gitignored); never move
  them into a tracked path.
