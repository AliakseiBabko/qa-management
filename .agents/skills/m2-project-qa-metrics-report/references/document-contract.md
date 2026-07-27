# Document Contract — Module Index

This file is a **routing index only** — it carries no schema rules of its
own. Load only the module(s) your task actually needs.

| Module | Load it for |
|---|---|
| [project-metrics-schema.md](project-metrics-schema.md) | `project_metrics` Sheet purpose, templates, expected output, versioning, and row schema — read this every time |
| [qa-process-metrics-schema.md](qa-process-metrics-schema.md) | `qa_process_metrics` Sheet schema, Core (6-metric) discipline, and source priority — read this every time |
| [extended-metrics-catalog.md](extended-metrics-catalog.md) | the optional/tooling-gated Extended `qa_process_metrics` catalog and DOCX/XLSX source-extraction strategy — load only when adding an Extended-tier row or extracting a raw source document |

The two schema modules are needed for every invocation; the catalog module
only when the situation above applies.
