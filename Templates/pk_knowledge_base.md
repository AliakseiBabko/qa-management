# Template: Project Knowledge Base

Output format — Google Doc, one living document per project under
`30_Project_Knowledge\<Project>\knowledge_base\`. Update sections in place
as new sources add or correct understanding; do not create a new document
per source — that is what `pk_summary` is for. Knowledge accumulates
gradually from fragments (1:1s, meetings, chats, presentations, documents,
owner notes) — a formal knowledge-transfer session is one possible input,
never a prerequisite. Leave a section blank/marked "unknown" rather than
guessing.

Once a section (H2) grows past roughly 800 words or ~3 distinct
sub-topics, split it with Heading 3 sub-headings keyed to how the content
actually clusters (a module, a workshop topic, a subsystem) — a periodic
housekeeping pass, not a per-intake requirement. Insert new content at
the end of the target section/sub-section, never at a heading's own start
index (Docs API heading-inheritance bug, see
`project-knowledge-roles/SKILL.md`, "Structural Format"). Change Log
entries are dated one-liners only — what changed and which section(s),
never the fact itself; if an entry runs past ~2 lines, that content
belongs in the topical section, not here.

## <Project> — Knowledge Base

### Overview

What the project is, in a few sentences — audience, product area, current
phase.

### Business Goals

Why the project exists / what outcome it's meant to produce, to the extent
known.

### Stakeholders/Roles

Who's involved and in what capacity (role, not necessarily name) — client
side and delivery side.

### System/Architecture

High-level structure: components, services, major technical decisions.

### Core Workflows

The main things the system/product actually does, end to end.

### Data/Integrations

Data sources, external systems, integration points.

### QA Scope

What is/isn't currently covered by testing, and by whom.

### Performance-Critical Scenarios

Flows or components where performance matters most, and why.

### Known Constraints

Technical, organizational, or business constraints that shape what's
possible.

### Glossary

Terms/acronyms specific to this project, defined once here.

### Open Questions

Unresolved gaps or contradictions between sources — do not silently drop
or silently resolve by guessing.

### Source Index

Link to `pk_source_index` (Sheet) rather than duplicating it here.

### Change Log

Dated one-line entries: what changed in this document and why.
