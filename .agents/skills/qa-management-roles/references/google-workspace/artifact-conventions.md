# Artifact Conventions

Scope: naming/versioning, Sheet-specific rules, Doc-specific rules, and the
prose language rules for final business-facing output. Load this module
for any skill that writes a final Sheet, Doc, or business-facing prose.

## Naming And Versioning

- Preserve existing skill naming patterns, but use Google file titles instead of local filenames.
- For tabular outputs, omit `.csv` from the Google Sheet title unless the user explicitly wants the suffix preserved.
- For Google Docs outputs, omit `.md` from the title.
- Do not overwrite existing final dated/monthly documents by default.
- If a same-title final document exists in the target Drive folder, create the next `_vN` title, for example `_v2` or `_v3`.
- Personal 1to1 Sheets are append-only longitudinal records. Update the existing person Sheet by appending a row unless the user explicitly asks for correction.

## Sheet Rules

- Preserve the template column order and meaning exactly.
- For 2D monthly report templates, preserve the workbook-like layout rather than normalizing into a database table.
- Prefer one Google Sheet per final report artifact unless the user asks for a consolidated workbook.
- When updating an existing Sheet, read the header/layout first and validate that it matches the expected template before writing.
- If the layout does not match the expected template, stop and ask whether to migrate, append anyway, or create a new version.

## Docs Rules

- Use Google Docs for saved regular status reports, development plans, and other narrative documents.
- Keep the body concise and business-facing; do not include internal evidence paths unless the user asks for evidence, except for development plans, which keep a short "Источники / Evidence" section for traceability (matching how the real source plans are already written).
- Update the living Doc in place for development plans; Google Docs version history preserves prior revisions, so do not create a new dated Doc for routine updates.
- Reviewer feedback on a plan belongs in native Google Docs comments anchored to the relevant paragraph, not as an appended text block or a separate column.
- Preserve versioning behavior by title.

## Language Rules

Apply this to any prose written into a final output (development plans,
status reports, risk narratives, summaries) or into a chat message drafted
for the user to send to a colleague/stakeholder (see
`chat-message-style-rules.md` for that case specifically) — not to code,
file paths, or literal evidence citations.

- Do not use an em dash / long dash ("—") as word-joining punctuation in
  any generated prose. It reads as AI-generated and undermines text meant
  to sound natural, especially colleague-facing chat messages. Use a
  comma, period, semicolon, parentheses, or restructure the sentence
  instead.
- Base language is Russian. Write full sentences in Russian; do not build a
  clause out of one Russian verb followed by an English noun phrase.
  - Bad: "Ввести lightweight bug tracking rule." / "Подготовить account-level
    quality summary."
  - Good: "Ввести лёгкое правило учёта багов." / "Подготовить сводку качества
    на уровне аккаунта."
- Keep English only for things that do not have a natural standalone Russian
  name: tool/platform names (Jira, Confluence, Playwright, Cucumber, Allure,
  ReportPortal, AWS, Node.js), acronyms (QA, AQA, CI/CD, API, MVP, OKR, KPI,
  SLA, TMS, DoR, DoD, PM, BA, M1/M2/M3), and proper nouns (project names,
  stream names, product names, people's names).
- Do not use English for ordinary words that have a normal Russian
  equivalent, even if the word is common in spoken IT English: quality,
  value, risk, gap, state/status, summary, readiness, coverage (покрытие),
  bug (баг), sprint (спринт), regression (регрессия), checklist (чек-лист),
  framework (фреймворк), onboarding (онбординг), feedback (обратная связь),
  escalation (эскалация). Prefer the settled Russian IT loanword
  (баг/спринт/фреймворк/чек-лист/онбординг/эскалация/пайплайн) over the raw
  English word when one is already standard in this corpus.
- When rewriting or normalizing an existing document, preserve meaning,
  owners, dates, and numbers exactly; only change the wording style.
