# Template: Business Focus / Architecture Feedback Form

The department's own published-feedback form for a Business Focus / Architecture
assessment — the text that goes into the tracker and is read by the candidate,
their M-manager, and the assessor lead. It is **not** the working assessment
document: `Templates/internal_assessment_feedback.md` owns that, and this form
is what its "Feedback draft" section must mirror so the draft can be copied out
without rewriting.

Source: the department's canonical form, referenced by the calibration and
feedback-publication process page as «Шаблон фидбека для ассесмента по бизнес
фокусу». Re-read the live form before each write — it changes, and the copy
here is a shape reference, not the authority.

**Language** — Russian, matching the form. Grade labels (`Junior`/`Middle`/
`Senior`), matrix topic names and level codes (`T1`..`T4`) stay in their
original form.

**Scope** — this form covers the Business Focus and Architecture blocks only.
A full grade assessment that also covered the technical base uses the manual-QA
or AQA feedback template instead, per the same process page.

---

## Header block

A two-column field list, one fact per row, before the first section:

> **ФИО сотрудника:** `<Имя Фамилия>`
> **Целевой грейд:** `<Junior / Middle / Senior QA>`
> **Дата ассесмента:** `<ДД.ММ.ГГГГ>`
> **Ассессор(ы):** `<ФИО ассессора(ов)>`
> **Статус / Вердикт:** `<Ассессмент сдан / Требуется повторный ассесмент / Не сдан>`

**The verdict vocabulary is this form's own, and it is three-valued** — do not
substitute the `Approve / Not Approve` pair the general calibration page uses
for a full grade session. `Требуется повторный ассесмент` is the value that
exists precisely so a re-sit condition never has to be smuggled into a passing
verdict as a caveat. Pick one value and leave it unqualified: a development-plan
item never turns `Ассессмент сдан` into something conditional, and if a block
genuinely cannot be decided from the session, say so in the closing section
rather than inventing a fourth status.

## Оценка компетенций и сильные стороны

Prose, not a list of topic names. Describe the areas and topics where the
engineer was strongest, and which concepts, frameworks and practical approaches
they use freely and unaided.

Every strength names what the candidate actually said — the product's
monetization model, the layers they listed, the incident they walked through.
A strength with no quotable evidence behind it is an impression, and impressions
do not belong in a published verdict. Where an answer arrived only after the
interviewer supplied the frame, it is not a strength; it belongs in the next
section, marked as led.

Shape of a good entry, per block:

- Business Focus — separates business flow from user flow, applies risk-based
  testing against the domain's own risks, translates a defect into its
  consequence for the user and for revenue.
- Architecture — moves confidently around the project's architecture, knows its
  integration points and API styles, and can say how the architecture changes
  where a defect is looked for and how it is reported.

## Зоны роста

The topics where the actual level came out below the target, or where the depth
or the independence of the argument was missing.

Keep two distinctions visible, because the reader acts on them differently:

- **Did not know** versus **was led there** — both are gaps, only the first is a
  knowledge gap. Where an answer was led, say who supplied the frame.
- **Development-plan item** versus **re-sit condition** — state which one each
  gap is. Conflating them is the most consequential error this document can
  make: one goes to the candidate's manager, the other blocks a grade, and the
  header's status field has to match whichever this section concludes.

Anything not probed is marked as not probed, with the reason (out of scope for
this format, no time, expected light for this candidate profile). A blank and a
deliberate skip mean opposite things to the next assessor.

## Рекомендации по развитию

Numbered directions, typically two or three, each an action the candidate or
their manager can start — what to study, what access to request, what to
practise, what to correct in the matrix. Cite the department's own reference
pages where they exist.

> **`<Направление 1>`:** `<конкретный шаг или тема для самостоятельного изучения>`
> **`<Направление 2>`:** `<второй совет по углублению знаний>`
> **`<Направление 3>`:** `<третий совет при необходимости>`

## Итоговое решение

One short closing paragraph, written so it can stand alone if quoted: whether
the level of understanding of business context, risk and the role of QA in
protecting the product's business value is sufficient for the target grade, and
which single capability is recommended as the main focus of further growth.

It restates the header's status in prose; it never introduces a new condition
the status field does not carry.
