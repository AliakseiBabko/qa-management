# Search Strategy And Source Extraction

Scope: how to search the workspace without brute-force grepping the Drive
mirror, and how to reuse already-extracted `.docx`/`.xlsx` source content.
Load this module for any skill that searches broadly across the workspace
or analyzes a binary source document.

## Search Strategy

Do not grep recursively across the whole `G:\My Drive\QA_Management` mirror
to find mentions of a person or topic. This reads every file's raw bytes,
including multi-MB `.docx`/`.xlsx` source binaries and `.gdoc`/`.gsheet`
placeholder files whose real content lives in the cloud, not the local
pointer file (grepping them finds nothing anyway, since the local file is
just a JSON stub) — a real attempt at this timed out well before finishing
on a single-name search.

Instead:

1. Check `_people_registry` first — its `Project(s)`/`Notes` columns
   usually already point at the person's project and known source docs.
2. Then look directly in the conventional location this repo already
   documents: `<Person> case chat.txt` / `<Person> case at <Project>.txt`
   under `00_Inbox`, that project's
   `<Project>_strategy.txt`, or `01_Meeting_Transcripts` — the naming
   convention already tells you where to look; don't blind-search first.
3. If a genuinely broad text search across Drive is still needed, use the
   Drive API's `fullText contains` query (server-side indexed, and it
   covers native Google Docs/Sheets content) instead of a local filesystem
   grep over the mirror.
4. Don't introduce a new tagging/indexing layer to solve this — the
   existing naming conventions and registries already serve that purpose.

## Source Extraction

Source extraction writes Markdown, CSV, JSON, and manifests under `90_Storage\_System\extracts\source`. Those files are intermediate analysis artifacts, not final business documents.

When asked to analyze a `.docx` or `.xlsx` source file, use
`.agents\scripts\qa_source_extract.py` (its `extract_docx`/`extract_xlsx`
functions can be imported and called directly on a single file, without
running the full CLI) rather than reaching for a separate library — it
reads `.xlsx`/`.docx` straight from the zip/XML package with no external
dependencies, which is what already made analyzing an internal assessment
matrix workbook and a project's source docs work without needing to
install anything.

Before extracting, check whether the file has already been processed:
look for its path (and `sha256`, via `sha256_file()`) in an existing
`manifest.csv`/`manifest.json` under `90_Storage\_System\extracts\source\*`. A
matching `source_file` + `sha256` means the extraction is already
available at that row's `extract_file` — reuse it instead of
re-extracting. A matching path with a different `sha256` means the file
changed since the last extraction and should be re-extracted.
