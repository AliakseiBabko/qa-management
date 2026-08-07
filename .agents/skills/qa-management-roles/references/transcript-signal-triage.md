# Transcript Signal Triage

Shared first-pass filter for reading any transcript (1:1, strategy chat,
status meeting, PK source, or a peer conversation) before topic
classification or fact extraction begins - the same read-through
heuristic the user applies by hand, made explicit so every skill applies
it the same way instead of each one re-deriving its own version.

## The Two-Stage Filter

**Stage 1 - name recognition is only an attention cue, never sufficient
on its own.** A known project name or a known person's name appearing is
what makes a passage worth a second look - but plenty of genuinely
low-value chat mentions a project or a person in passing (a joke, a
scheduling aside, weekend plans) without containing anything worth
extracting. Don't stop at "this sentence names `<Project>`" and log it;
that's necessary, not sufficient.

**Stage 2 - the real test is narrative shape, not subject matter.** What
actually distinguishes an extraction-worthy passage from filler is
whether the speaker gives a **situation with structure**: what happened,
in what order, and why (the cause/reason) - a real narrated event, not a
vague generality, an opinion floated without detail, or small talk that
happens to touch a familiar name. "The client was difficult" is not
extraction-worthy on its own; "the client's DC told the team directly
they don't see what the QA engineer is doing, syncs about it stopped
because the client saw no point continuing, and the engineer admitted she
hadn't known what to prioritize early on" is - it has a sequence, a
cause, and a concrete claim someone could act on or learn from.

Practically: skim for the moment a speaker shifts from general/vague to
specific - that shift, not the name that triggered your attention, is
when to slow down and actually extract.

## This Is The Same Test Every Skill Already Applies Locally

This isn't a new rule so much as the general form of tests already
written into individual skills - recognize the pattern rather than
re-deriving it per skill:

- `project-knowledge-roles`: "distinguish durable project knowledge from
  one-off meeting remarks" - the durable/one-off line is this same
  structure test applied to project facts.
- `pm-case-knowledge-roles`: "a case needs real shape: situation,
  approach, outcome, takeaway" - the case-worthiness test applied to
  management situations.
- `qa-1to1-analysis`'s risk-signal calibration - a risk signal needs
  concrete evidence, not just a name or a mood, to be worth logging.

Applying this filter well is what makes those downstream tests easy to
pass or fail correctly - a passage that fails Stage 2 here will almost
always fail its skill-specific test too, and one that passes here is a
real candidate worth running through that test.

## Guardrails

- Don't manufacture structure that isn't there - if a passage only has a
  name and a vague claim, it stays filler; don't pad it into a fake
  situation to justify extracting it.
- Don't let Stage 1 substitute for Stage 2 - a passage about a real,
  familiar project/person that's still just chat (no what/why/order) is
  still filler, not an exception.
- A transcript can be genuinely all filler for one purpose and still
  contain real material for another (a 1:1 with nothing risk-worthy can
  still contain a real PM case, or vice versa) - apply this filter fresh
  per candidate destination, not once for the whole transcript.
