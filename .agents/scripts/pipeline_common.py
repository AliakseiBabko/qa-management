"""Shared one-line service setup for the M2/M1 Google API pipeline scripts.

Every script under .agents/scripts that talks to Drive/Sheets/Docs repeats the
same load_credentials + build_services boilerplate. This is the shared
version - new scripts should use get_services() instead of re-inlining it.
Existing scripts are not required to migrate; this just stops the pattern
from being copy-pasted again going forward.

Also holds append_doc_round() and get_last_round_status() - the m2_input
round-append logic that got hand-rolled separately for <Project> and
<Project> (character-offset tracking + paragraph-style requests
duplicated each time, a real bug risk). New strategy-chat processing should
call these instead of rewriting the index math.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any

from google_api_smoke_test import build_services, load_credentials

DEFAULT_CREDENTIALS = Path(".local/google/credentials.json")
DEFAULT_TOKEN = Path(".local/google/token.json")

ANSWER_HEADING = "Ответ и общие соображения M2"


def get_services(
    credentials_path: Path | str = DEFAULT_CREDENTIALS,
    token_path: Path | str = DEFAULT_TOKEN,
) -> dict[str, Any]:
    creds = load_credentials(Path(credentials_path), Path(token_path))
    return build_services(creds)


def _insert_blocks(docs_service: Any, doc_id: str, insert_at: int, blocks: list[tuple[str, str]]) -> None:
    """Shared insert logic: build insertText + paragraph-style requests for
    a (kind, text) block list starting at a given index, and apply them.

    Inserted text inherits the paragraph style of whatever's AT the
    insertion point (e.g. an empty "Ответ и общие соображения M2" HEADING_2
    paragraph) until explicitly overridden. Every block's range is
    therefore explicitly (re)set to NORMAL_TEXT first, then HEADING_2 is
    applied on top for heading2-kind blocks - never rely on inheritance
    defaulting to normal text (it doesn't when the insertion point happens
    to be a heading, which is exactly the append_to_pending_round case)."""
    text_parts: list[str] = []
    heading2: list[tuple[int, int]] = []
    bullets: list[tuple[int, int]] = []
    cursor = insert_at
    for kind, text in blocks:
        content = text + "\n"
        start = cursor
        end = start + len(content)
        if kind == "heading2":
            heading2.append((start, end))
        elif kind == "bullet":
            bullets.append((start, end))
        text_parts.append(content)
        cursor = end
    inserted_end = cursor

    requests: list[dict[str, Any]] = [
        {"insertText": {"location": {"index": insert_at}, "text": "".join(text_parts)}},
        {
            "updateParagraphStyle": {
                "range": {"startIndex": insert_at, "endIndex": inserted_end},
                "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"},
                "fields": "namedStyleType",
            }
        },
    ]
    for start, end in heading2:
        requests.append({
            "updateParagraphStyle": {
                "range": {"startIndex": start, "endIndex": end},
                "paragraphStyle": {"namedStyleType": "HEADING_2"},
                "fields": "namedStyleType",
            }
        })
    for start, end in bullets:
        requests.append({
            "createParagraphBullets": {
                "range": {"startIndex": start, "endIndex": end},
                "bulletPreset": "BULLET_DISC_CIRCLE_SQUARE",
            }
        })
    docs_service.documents().batchUpdate(documentId=doc_id, body={"requests": requests}).execute()


def _find_answer_heading_start(docs_service: Any, doc_id: str) -> tuple[dict[str, Any], int | None]:
    doc = docs_service.documents().get(documentId=doc_id).execute()
    for element in doc["body"]["content"]:
        if "paragraph" not in element:
            continue
        text = "".join(run.get("textRun", {}).get("content", "") for run in element["paragraph"]["elements"])
        if text.strip() == ANSWER_HEADING:
            return doc, element["startIndex"]
    return doc, None


def append_doc_round(docs_service: Any, doc_id: str, blocks: list[tuple[str, str]]) -> None:
    """Append a brand-new dated round to the end of a Doc (e.g. m2_input).

    blocks is a list of (kind, text) pairs, kind one of "heading2", "bullet",
    "normal". Inserts before the Doc's trailing empty paragraph so a blank
    line is preserved at the very end, matching the existing m2_input
    convention of one dated section per round.

    Use this only to open a NEW round. To add content to an ALREADY-pending
    round (see get_last_round_status), use append_to_pending_round instead -
    appending here would land after the empty "Ответ и общие соображения M2"
    heading and make get_last_round_status wrongly read the round as
    answered (this happened once; see <Project> m2_input history/evidence_log
    2026-07-13 for the fix).
    """
    doc = docs_service.documents().get(documentId=doc_id).execute()
    end_index = doc["body"]["content"][-1]["endIndex"]
    _insert_blocks(docs_service, doc_id, end_index - 1, blocks)


def append_to_pending_round(docs_service: Any, doc_id: str, blocks: list[tuple[str, str]]) -> None:
    """Add an addendum to the CURRENT round while it's still pending, by
    inserting right before the "Ответ и общие соображения M2" heading -
    keeping that heading's answer section genuinely empty so
    get_last_round_status still reads the round as pending.

    Raises ValueError if the doc has no answer heading (call
    get_last_round_status first and use append_doc_round instead if the doc
    doesn't have the expected shape, or the round is already answered and a
    new one should be opened).
    """
    doc, answer_start = _find_answer_heading_start(docs_service, doc_id)
    if answer_start is None:
        raise ValueError(
            f"No '{ANSWER_HEADING}' heading found in doc {doc_id} - can't locate the pending round to "
            "extend. Use append_doc_round to open a new round instead."
        )
    _insert_blocks(docs_service, doc_id, answer_start, blocks)


def add_questions(
    docs_service: Any,
    doc_id: str,
    blocks: list[tuple[str, str]],
    round_date: str | None = None,
) -> dict[str, Any]:
    """Add new question/context content to an m2_input Doc - the entry point
    to use instead of picking between append_doc_round and
    append_to_pending_round yourself (that choice was made wrong once; see
    <Project> m2_input history/evidence_log 2026-07-13).

    Auto-routes on the doc's current state (via get_last_round_status):
    - a round is pending -> appended as an addendum before the answer
      heading (append_to_pending_round), so the round stays correctly
      pending.
    - no round is pending (answered, or the doc has no round yet) -> a
      fresh round is opened with today's date (or round_date if given),
      wrapping `blocks` in the full heading scaffold, via append_doc_round.

    blocks is just the question/context content itself - (kind, text)
    pairs, kind one of "heading2" (for a labeled sub-section within the
    round), "bullet", "normal". Do not include the "Раунд:"/"Вопросы от
    предварительного анализа"/answer headings yourself; they're added
    automatically when a new round needs to be opened.

    Returns the status dict (see get_last_round_status) after the write.
    """
    status = get_last_round_status(docs_service, doc_id)
    if status["pending"]:
        append_to_pending_round(docs_service, doc_id, blocks)
    else:
        date = round_date or dt.date.today().isoformat()
        scaffold: list[tuple[str, str]] = [
            ("heading2", f"Раунд: {date}"),
            ("heading2", "Вопросы от предварительного анализа"),
            *blocks,
            ("heading2", ANSWER_HEADING),
            ("normal", ""),
        ]
        append_doc_round(docs_service, doc_id, scaffold)
    return get_last_round_status(docs_service, doc_id)


def add_answer(docs_service: Any, doc_id: str, blocks: list[tuple[str, str]]) -> dict[str, Any]:
    """Write answer content into the CURRENT pending round of an m2_input
    Doc. Requires a round to actually be pending - raises ValueError
    otherwise, since answering a round that's already answered (or doesn't
    exist) is not a valid action; open one with add_questions first.

    blocks is the answer content - (kind, text) pairs. Inserted at the
    Doc's end, which lands right after the empty answer heading, filling it
    in and making the round read as answered afterward.

    Returns the status dict (see get_last_round_status) after the write.
    """
    status = get_last_round_status(docs_service, doc_id)
    if not status["pending"]:
        raise ValueError(
            f"No pending round in doc {doc_id} to answer (status={status}). "
            "Use add_questions to open a new round first."
        )
    append_doc_round(docs_service, doc_id, blocks)
    return get_last_round_status(docs_service, doc_id)


QUESTIONS_HEADING = "Вопросы от предварительного анализа"


def get_pending_round_questions(docs_service: Any, doc_id: str) -> str:
    """Return the question text of the CURRENT pending round (everything
    between the last 'Вопросы от предварительного анализа' heading and the
    last 'Ответ и общие соображения M2' heading), or "" if no round is
    pending or the doc has no round yet.

    Used by scan_open_questions.py to surface what's still waiting on an M2
    answer without requiring a full doc dump - a pending round with no
    answer is itself an open item.
    """
    doc = docs_service.documents().get(documentId=doc_id).execute()
    paragraphs: list[tuple[str, str]] = []
    for element in doc["body"]["content"]:
        if "paragraph" not in element:
            continue
        style = element["paragraph"].get("paragraphStyle", {}).get("namedStyleType", "NORMAL_TEXT")
        text = "".join(run.get("textRun", {}).get("content", "") for run in element["paragraph"]["elements"])
        paragraphs.append((style, text))

    questions_idx = answer_idx = None
    for i, (style, text) in enumerate(paragraphs):
        if style != "HEADING_2":
            continue
        stripped = text.strip()
        if stripped == QUESTIONS_HEADING:
            questions_idx = i
        elif stripped == ANSWER_HEADING:
            answer_idx = i

    if questions_idx is None or answer_idx is None or answer_idx <= questions_idx:
        return ""
    after_answer = "".join(text for _, text in paragraphs[answer_idx + 1 :]).strip()
    if after_answer:
        return ""  # round already answered, nothing pending
    return "".join(text for _, text in paragraphs[questions_idx + 1 : answer_idx]).strip()


def get_last_round_status(docs_service: Any, doc_id: str) -> dict[str, Any]:
    """Read an m2_input Doc and report the most recent round's date and
    whether it's still waiting on an answer (the text after the last
    "Ответ и общие соображения M2" heading is empty).

    Returns {"round_date": str | None, "pending": bool | None} - pending is
    None if the doc has no answer-section heading at all (unexpected/older
    format), so a caller can distinguish "no signal" from "answered".
    """
    doc = docs_service.documents().get(documentId=doc_id).execute()
    paragraphs: list[tuple[str, str]] = []
    for element in doc["body"]["content"]:
        if "paragraph" not in element:
            continue
        style = element["paragraph"].get("paragraphStyle", {}).get("namedStyleType", "NORMAL_TEXT")
        text = "".join(run.get("textRun", {}).get("content", "") for run in element["paragraph"]["elements"])
        paragraphs.append((style, text))

    round_date = None
    for style, text in paragraphs:
        stripped = text.strip()
        if style == "HEADING_2" and stripped.startswith("Раунд:"):
            round_date = stripped.split(":", 1)[1].strip()

    answer_idx = None
    for i, (style, text) in enumerate(paragraphs):
        if style == "HEADING_2" and text.strip() == ANSWER_HEADING:
            answer_idx = i

    if answer_idx is None:
        return {"round_date": round_date, "pending": None}

    after = "".join(text for _, text in paragraphs[answer_idx + 1 :]).strip()
    return {"round_date": round_date, "pending": not bool(after)}
