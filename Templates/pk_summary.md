# Template: Project Knowledge Source Summary

Output format — Google Doc, one per processed source, under
`30_Project_Knowledge\<Project>\summaries\`, named `<source-slug>_summary`.
Captures what the source actually said before any judgment about what's
durable enough for the knowledge base — see `project-knowledge-roles` for
the durable-vs-one-off distinction.

## <Source> — Summary

### Source

File/link and where it came from.

### Date

When the source event/document occurred (not the processing date).

### Source Type

One of `project_knowledge_transcript` / `project_knowledge_document` /
`project_knowledge_chat` / `project_knowledge_notes`.

### Context

Why this source exists / what prompted it.

### Key Topics

The main subjects covered, as a short list.

### Extracted Facts

Concrete, attributable facts found in the source.

### Decisions/Constraints

Any decisions made or constraints stated in the source.

### Open Questions

Anything left unclear or contradicting other sources.

### Knowledge Base Sections Updated

Which `pk_knowledge_base` sections this summary fed, or "none" if the
source added nothing durable (a valid outcome, not a gap).
