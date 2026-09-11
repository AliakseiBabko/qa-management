# AI Adoption Knowledge Base Contract

The three-tier structure of the `55_AI_Adoption` knowledge base, and the rules
for adding a source to it. Read before touching any of the three documents.

The tiering exists so raw detail and traceability stay separate from
readability. Do not collapse the tiers: the store must not become a copy of the
notes, and the wiki must not become a copy of the store.

## The three documents

| Document | Tier | Shape | Grows with |
|---|---|---|---|
| `ai_adoption_source_notes` | 1 | One section per processed source, append-only | Every processed source |
| `ai_adoption_knowledge_store` | 2 | Topic-organised, upsert in place, every entry cites its source | Most sources |
| `ai_in_qa_best_practices` | 3 | Compressed, readable synthesis | Only when understanding changes |

Raw transcripts are **not** part of the knowledge base. They stay next to the
original recording on the local machine; the source note records the path.

## Tier 1 - source notes

Append a new section. Never rewrite an existing one; if a later source
corrects it, the correction goes in the new section and in the store's
contradiction handling, not by editing history.

Required per source: an ID (`S<n>`, sequential), source name, date, duration,
format, recording and transcript paths, participants with roles, project shape,
then **Durable facts**, **Uncertainties and gaps**, and **Relevance**.

Every fact carries a confidence tag:

- **confirmed** - stated plainly by a participant with direct knowledge.
- **inferred** - a reading of what was said, not stated.
- **uncertain** - the speaker hedged, or accounts conflicted.
- **unverified** - asserted, not corroborated, not checkable from the source.

An opinion offered as opinion is tagged **confirmed as opinion** or **confirmed
as experience**, not promoted to fact. This matters: several of the most useful
claims in this knowledge base are one experienced person's judgment, and the
wiki has to keep saying so.

**Scope exclusion is recorded, not silently applied.** Where a source contains
material that does not belong in this lane - compensation, staffing, a person's
future on the project, a competence judgment - the note states that the
material exists, that it was excluded, and where it routes. It never states
what the material said.

## Tier 2 - knowledge store

Organised by topic, not by source. A new source **upserts**: it updates the
matching entry in place and appends its citation. It does not add a second,
competing entry on the same topic.

Every entry cites the source IDs behind it. An entry supported by more than one
source says so - corroboration across projects is the thing that lets a
practice reach the wiki as a recommendation rather than as one person's
experience.

### Contradictions

Never silently overwrite an older fact with a newer conflicting one. Record
both, their sources, and which evidence is stronger if that is determinable.
Keep them in the `Contradictions on record` section as well as in the topical
entry.

Before recording a contradiction, check whether it is one. The commonest case
here turned out not to be: two projects reporting opposite outcomes from the
same technique, where the real discriminator was a project property (how
expensive a wrong test case is to discard) rather than the technique. Both
accounts stood, and the resolution was more useful than either. Look for the
discriminator before concluding that two people disagree.

### Supersession by primary data

A later source is sometimes not new evidence but the *primary data behind* an
earlier one - the repository behind a presentation, the spreadsheet behind a
status claim. Handle it as supersession, not contradiction:

- Log it as its own source with its own ID. Do not edit the earlier note; the
  contract's append-only rule holds even when the earlier note is now known to
  be loose.
- State the relationship explicitly in the new note: which source it supersedes,
  on which claims, and what the earlier source remains the only evidence for.
  A presentation usually keeps the narrative, the incidents and the reasoning
  even after its numbers are replaced.
- Record the supersession in `Contradictions on record` too, labelled as
  supersession, so a reader who lands on the earlier entry is warned.
- Prefer the primary data for every quantitative claim, and prefer the recounted
  figure over the remembered one. A verbal figure from a presentation is a
  recollection mid-study; the data is the study.
- Watch for confounding the earlier source could not see. An aggregate that
  looked decisive in the talk may rest on an unbalanced sample once the rows are
  visible; where that happens, carry the matched-pair or per-cell reading and
  attach the sample size to the claim.

### Open questions

Carried forward at the end of the store, and cleared only when a source
actually answers them - not when they stop being interesting. A question that
has been open across several sources is itself a finding.

## Tier 3 - best-practices wiki

Update **only** when the new source changes the synthesised understanding. A
source that corroborates what the wiki already says updates the store and
leaves the wiki alone.

Rules:

- Every actionable claim must be traceable back through the store to a source
  note. The wiki does not carry per-claim citations inline, so it must not carry
  a claim the store does not hold.
- Preserve uncertainty. Where a practice rests on one person's experience rather
  than corroboration across projects, the wiki says so in the sentence, not in a
  footnote.
- Never invent. Do not fill a gap with general knowledge or a plausible default.
  If external enrichment is explicitly requested for a pass, mark that content's
  provenance as external.
- Keep the honest-ceiling section current. It is the section most likely to be
  quietly dropped and the one most likely to prevent a bad commitment.
- Structural sections that must survive any edit: what determines whether it
  works; best practices; bad practices; environment patterns; what can honestly
  be claimed; open questions.

## Derived language editions

`ai_in_qa_best_practices_ru` is a Russian-language generic rules digest derived
from the tier-3 wiki. It is **not** a translation, and treating it as one
produces exactly the document nobody wants.

Two rules govern it, and they are separate.

### It states rules, not evidence

The English wiki is the traceable synthesis: it names the projects, the
sessions and the situations behind each claim, because that is what makes it
auditable. The Russian edition is the opposite genre. It says once, at the
top, what body of material it rests on, and then states only rules and
conclusions.

Strip on the way across:

- project, product, client and person names, and anything that identifies them
- "on that call", "the expert said", "one engineer reported", "the reference
  case" and every other attribution to a specific session or speaker
- narrated incidents where a rule already carries the lesson
- named model, vendor and tool versions where a role word does the job better:
  prefer "средняя модель", "топовая модель", "браузерный MCP". Version names
  age out within months, the rule does not

Keep: every measured figure, every sample size, every hedge, and the failure
mechanisms themselves (what breaks, and why). A rule without its mechanism is
not shorter, it is weaker, and a figure without its sample size is a claim the
data does not support.

The genre test: a reader should be able to act on any paragraph without
knowing which project it came from. If a paragraph only makes sense once you
know whose project it was, it belongs in the store, not here.

### It has to read as Russian

Not as translated English. This is the failure mode to watch for, because it
is easy to produce and hard to notice once written.

- Write from the substance, not from the English sentence. Transposing clause
  order produces text that is grammatical and unreadable.
- Short sentences. Verbs over nominalisations. Russian carries an instruction
  in a verb where English uses a noun phrase.
- Use the borrowed vocabulary engineers actually say out loud: скиллы, хуки,
  промпт, токены, коннекторы, локаторы, фикс, прогон, ревью, дифф. Do not
  invent calques for them, and do not translate them into formal Russian
  nobody uses.
- Watch the dash rule specifically. The house style avoids long dashes, but
  Russian needs a dash in "X - это Y" constructions, and replacing it with a
  comma produces a splice that reads as broken. Rewrite the sentence so no
  dash is required (add a verb, use a colon, restructure) rather than leaving
  the comma. Check for this deliberately after writing: a comma followed by
  `это`, `не`, `скорее` or a bare noun predicate is the tell.
- Verify mechanically what can be verified: heading counts per level, table
  count, and that every figure in the source appears in the edition. Read for
  register by eye afterwards, because no check catches unnatural phrasing.

### Keeping it current

A change to the English wiki leaves the derived edition stale.
`ai_adoption_workspace_layout.DERIVED_EDITIONS` maps each edition to its
source. Regenerate the edition whole rather than patching both documents: they
have different content by design, so a patch applied to each will not converge.
If you change the source and do not regenerate, say so plainly in the handoff.

Metric names (EQA, IRR), file names, code identifiers and technical terms with
no accepted Russian form stay as they are.

## When a source produces nothing

Some sessions add nothing. A source note is still written - the fact that a
session was processed and yielded nothing durable is worth recording, and it
stops the same source being reprocessed later. The store and wiki are left
alone.

## Publishing

All three are Google Docs under `55_AI_Adoption`. Publish with
`publish_markdown_doc.py --folder-path "55_AI_Adoption"`, or `--doc-id` to
replace an existing document's body. Review documents go to
`55_AI_Adoption\reviews\`.

Do not create the root folder or any of the three documents speculatively -
only when a real processed source justifies it.
