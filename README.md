# qa-management

Repository for QA-management agent infrastructure.

This repo stores:

- shared skill definitions under `.agents/skills/`
- canonical CSV templates under `Templates/`
- shared 1to1 analysis rules under `.agents/skills/qa-1to1-analysis/references/`

Operational data and generated report files stay in:

`G:\My Drive\QA_Management`

Current Drive layout:

- `00_Source_Docs/`: durable source documents and reference materials
- `01_Recordings/`: raw meeting recordings
- `02_Transcripts_Inbox/`: raw transcript intake
- `03_Transcripts_Processed/`: processed transcripts
- `10_M1_People_Management/`: M1 person files and people risk snapshots
- `20_M2_Project_Management/`: M2 project-management outputs
- `80_Exports/`: export packages and external copies
- `90_Archive/`: archived legacy folders and backups

## Source extraction

Use the dependency-free extractor when Office source documents need to be converted into
analysis-friendly Markdown, CSV, and JSON files:

```powershell
python .agents\scripts\qa_source_extract.py
```

Default input:

`G:\My Drive\QA_Management\00_Source_Docs`

Default output:

`G:\My Drive\QA_Management\80_Exports\source_extracts\YYYY-MM-DD`

The extractor does not modify source documents. It writes a `manifest.csv` and project-level
subfolders with DOCX text as Markdown and XLSX sheets as CSV.

## M2 batch generation

After extraction, generate first-pass M2 CSV outputs with:

```powershell
python .agents\scripts\generate_m2_outputs.py
```

Default input:

`G:\My Drive\QA_Management\80_Exports\source_extracts\YYYY-MM-DD`

Default output:

`G:\My Drive\QA_Management\20_M2_Project_Management\generated_from_source_YYYY-MM-DD`

The generator preserves source evidence and writes draft CSVs for project risks, project metrics,
individual QA metrics, project development plans, and individual development plans.
