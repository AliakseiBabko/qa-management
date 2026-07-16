### Aliases

When reading a meeting transcript or chat export, project and person names
often don't match this workspace's canonical spelling exactly — voice
transcription (STT) mangles names, compound client/legal names get
truncated to just one word, and Cyrillic transliteration of the same person
varies between documents. Before treating an unfamiliar name in a
transcript as a new project or person, check it against known aliases
first.

**The actual alias dictionary (real names/projects) lives in Drive, not
here** — see `_aliases` in `20_M2_Project_Management`, alongside
`_project_registry`/`_m2_people_registry`. This repo file only documents the
*mechanism* and the recurring STT error patterns worth watching for; see
`AGENTS.md`, "No Sensitive Data In This Repository," for why real names
never get written into this repository's own tracked files.

#### Workflow

1. Before asking the user "is `<name heard in transcript>` a new
   project/person," check `_aliases` in Drive first.
2. If the transcript name isn't there and isn't a clean match to anything
   in `_project_registry`/`_m2_people_registry`, treat it as genuinely
   unresolved — ask, don't guess (per `m2-strategy-chat-analysis`'s
   UNCLASSIFIED handling).
3. Once an alias is confirmed in conversation, add a row to `_aliases` in
   Drive (Type: Project / Other M2's project / Person / Pattern; Canonical;
   known variants; a short Notes cell for how/when it was confirmed) so the
   same ambiguity doesn't need re-resolving from scratch next time.
4. A project name that resolves to a different M2's project (not this
   workspace's own `20_M2_Project_Management` scope) still belongs in
   `_aliases` for name-recognition — but never gets its own folder or
   registry row here.

#### Guardrails

- This file (and `_aliases` in Drive) is name-resolution only — "X is the
  same as Y," nothing more. Don't let it grow into a second registry: any
  fact beyond a name/spelling match (a risk, a role, a history) belongs in
  `_m2_people_registry`, `_project_registry`, or the project's own documents,
  not in a Notes cell here.

#### STT Error Patterns To Watch For

- **Compound name truncation**: a client's full compound/legal name gets
  heard and transcribed as only the more distinctive half of it.
- **Transliteration variance**: the same Cyrillic name can appear with more
  than one valid Latin transliteration across different source documents —
  don't treat spelling variants as two different people without checking.
- **Phonetic mangling**: uncommon or foreign-sounding project/company names
  can come out of STT as unrelated-looking Russian (or vice versa) words
  that only make sense once you already know the real name.
