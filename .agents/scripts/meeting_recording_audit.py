"""Audit scheduled meetings against the recordings that actually exist.

Answers a question the document graph structurally cannot: *did every
meeting that was scheduled actually produce a record?* Every other check in
this repo starts from a source that exists - a transcript in the inbox, a
row in `evidence_log`. A meeting that happened and produced no artifact at
all is invisible to all of them, because there is nothing to notice. The
calendar is the only place it leaves a trace.

A real audit found exactly that: two per-person syncs on one project, eight
weeks apart, both held, neither recorded, neither written up. The person's
1:1 record simply stopped, and nothing in the workspace flagged it.

Recording lookup, in order:

1. **Attached to the calendar event.** A Google Meet recording attaches
   itself to its event as a `video/*` attachment carrying a Drive `fileId`.
   Meet often attaches its transcript Doc the same way - `--json` reports
   both, so a caller can prefer the ready-made transcript over transcribing
   the video again.
2. **Recorded locally.** OBS-style captures are named by wall-clock start
   (`2026-09-15 16-00-51.mkv`) with no hint of the meeting, so they are
   matched by timestamp against the event window. Derivative artefacts this
   workflow itself produces (`_audio`, `_trimmed`, `_stt`, `_partN`) are
   never treated as primary recordings.
3. **Neither** - reported as `missing`, meaning the meeting happened with no
   recording anywhere.

Identity comes from the event, never from the filename: `summary` names the
meeting and `attendees` name the participants, which is what makes a bare
`2026-09-15 16-00-51.mkv` attributable to a person and a project at all.

A local match is a *candidate*, not proof. Overlapping meetings share a
window, and a recording starting inside a slot may belong to something else
entirely - in the audit above, a file sitting squarely inside a per-person
sync slot turned out to be a six-person department meeting that had taken
the slot over. Confirm identity from content before processing, and treat
`confidence: low` as "check this one by hand".

Read-only: queries Calendar, stats local files, writes nothing.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import pipeline_common  # noqa: E402
from google_api_smoke_test import ensure_utf8_stdout  # noqa: E402

DEFAULT_RECORDINGS_DIR = pathlib.Path.home() / "Videos"
MEDIA_EXTENSIONS = {".mkv", ".mp4", ".mp3", ".m4a", ".wav", ".webm"}

# Artefacts this workflow generates beside a source recording. They carry the
# source's timestamp, so without this they double-match every event.
DERIVATIVE_SUFFIX = re.compile(r"(_audio|_trimmed|_stt|_part\d+)", re.IGNORECASE)

# OBS writes "2026-09-15 16-00-51.mkv"; Meet exports "... 2026_09_11 12_30 CEST ...".
OBS_STAMP = re.compile(r"(20\d\d)-(\d\d)-(\d\d)[ _](\d\d)-(\d\d)-(\d\d)")
MEET_STAMP = re.compile(r"(20\d\d)[_-](\d\d)[_-](\d\d)[ _](\d\d)[_-](\d\d)")
# Meet names its artefacts "<event> - 2026/09/11 12:30 CEST - Recording".
ATTACHMENT_STAMP = re.compile(r"(20\d\d)/(\d\d)/(\d\d)\s+(\d\d):(\d\d)")

# Per-person conversations, which is what has a longitudinal record to keep.
DEFAULT_PATTERN = r"m2\s*sync|1\s*to\s*1|1x1|1:1|1-2-1|one\s*to\s*one"

# Recurring all-hands and team syncs match the pattern but have no per-person
# record, so they are noise in this audit unless explicitly asked for.
DEFAULT_EXCLUDE = r"daily|standup|all\s*hands|department"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--calendar-id",
        default="primary",
        help="Calendar to audit. Default: the authenticated user's primary.",
    )
    parser.add_argument("--since", required=True, help="Start date, YYYY-MM-DD.")
    parser.add_argument(
        "--until",
        help="End date, YYYY-MM-DD, exclusive. Default: today.",
    )
    parser.add_argument(
        "--pattern",
        default=DEFAULT_PATTERN,
        help="Case-insensitive regex an event summary must match.",
    )
    parser.add_argument(
        "--exclude",
        default=DEFAULT_EXCLUDE,
        help="Case-insensitive regex that drops an otherwise-matching event. "
             "Pass an empty string to keep everything the pattern matched.",
    )
    parser.add_argument(
        "--recordings-dir",
        type=pathlib.Path,
        default=DEFAULT_RECORDINGS_DIR,
        help=f"Local capture folder. Default: {DEFAULT_RECORDINGS_DIR}",
    )
    parser.add_argument(
        "--lead-minutes",
        type=int,
        default=20,
        help="How long before an event a local recording may start and still "
             "match - a capture is often started late, or a prior meeting "
             "runs over. Default: 20.",
    )
    parser.add_argument(
        "--trail-minutes",
        type=int,
        default=10,
        help="How long after an event ends a local recording may start and "
             "still match. Default: 10.",
    )
    parser.add_argument(
        "--missing-only",
        action="store_true",
        help="Report only meetings with no recording anywhere - the gaps.",
    )
    parser.add_argument("--json", action="store_true", help="Emit a JSON report.")
    parser.add_argument("--credentials", help="Path to the OAuth client JSON.")
    parser.add_argument("--token", help="Path to the cached OAuth token JSON.")
    return parser.parse_args(argv)


def filename_timestamps(name: str) -> list[dt.datetime]:
    """Every wall-clock start time readable out of a filename."""
    found: list[dt.datetime] = []
    for match in OBS_STAMP.finditer(name):
        year, month, day, hour, minute, second = (int(g) for g in match.groups())
        found.append(dt.datetime(year, month, day, hour, minute, second))
    for match in MEET_STAMP.finditer(name):
        year, month, day, hour, minute = (int(g) for g in match.groups())
        found.append(dt.datetime(year, month, day, hour, minute))
    return found


def index_local_recordings(directory: pathlib.Path) -> list[tuple[dt.datetime, pathlib.Path]]:
    """Local media files paired with their best-known start time.

    Falls back to mtime for a file whose name carries no timestamp, so a
    hand-renamed recording still participates instead of vanishing.
    """
    if not directory.is_dir():
        return []
    indexed: list[tuple[dt.datetime, pathlib.Path]] = []
    for path in directory.iterdir():
        if not path.is_file() or path.suffix.lower() not in MEDIA_EXTENSIONS:
            continue
        if DERIVATIVE_SUFFIX.search(path.stem):
            continue
        stamps = filename_timestamps(path.name)
        if stamps:
            indexed.extend((stamp, path) for stamp in stamps)
        else:
            indexed.append((dt.datetime.fromtimestamp(path.stat().st_mtime), path))
    return indexed


def fetch_events(service, calendar_id: str, since: str, until: str) -> list[dict]:
    """Timed events in the window, recurrences expanded to real instances."""
    events: list[dict] = []
    page_token = None
    while True:
        response = (
            service.events()
            .list(
                calendarId=calendar_id,
                timeMin=f"{since}T00:00:00Z",
                timeMax=f"{until}T00:00:00Z",
                singleEvents=True,
                orderBy="startTime",
                pageToken=page_token,
                maxResults=2500,
            )
            .execute()
        )
        events.extend(response.get("items", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break
    # All-day entries carry no start time, so they cannot be matched to a
    # recording window and are not meetings in the sense this audit means.
    return [event for event in events if event.get("start", {}).get("dateTime")]


def attachment_belongs_to(title: str, start: dt.datetime, end: dt.datetime) -> bool:
    """Is this attachment this instance's own recording?

    Expanding a recurring series copies the series-level attachment onto
    every instance, so a weekly sync recorded once in May reports that same
    May recording against every later week - a meeting with no recording of
    its own looks recorded. Meet stamps its own title with the session's
    date and time, so compare that against this instance's window. An
    attachment whose title carries no timestamp cannot be adjudicated and is
    kept, on the reasoning that a false gap is cheaper than a silent drop.
    """
    match = ATTACHMENT_STAMP.search(title)
    if not match:
        return True
    year, month, day, hour, minute = (int(g) for g in match.groups())
    stamp = dt.datetime(year, month, day, hour, minute)
    # Meet starts its artefact clock when recording begins, which can trail
    # the scheduled start and outlast the scheduled end.
    return start - dt.timedelta(hours=1) <= stamp <= end + dt.timedelta(hours=1)


def attached_media(
    event: dict, start: dt.datetime, end: dt.datetime
) -> tuple[list[dict], list[dict], list[dict]]:
    """Split attachments into this meeting's recordings, companions, and
    artefacts whose own timestamp puts them outside this meeting.

    Meet attaches its recording as a video and, when enabled, its transcript
    as a Doc. The second is worth surfacing: a ready transcript means the
    caller can skip transcribing the video entirely.
    """
    recordings, companions, inherited = [], [], []
    for attachment in event.get("attachments", []) or []:
        entry = {
            "title": attachment.get("title", ""),
            "file_id": attachment.get("fileId", ""),
            "mime_type": attachment.get("mimeType", ""),
            "url": attachment.get("fileUrl", ""),
        }
        if not attachment_belongs_to(entry["title"], start, end):
            inherited.append(entry)
        elif entry["mime_type"].startswith(("video/", "audio/")):
            recordings.append(entry)
        else:
            companions.append(entry)
    return recordings, companions, inherited


def audit(args: argparse.Namespace) -> list[dict]:
    overrides = {}
    if args.credentials:
        overrides["credentials_path"] = args.credentials
    if args.token:
        overrides["token_path"] = args.token
    calendar = pipeline_common.get_services(**overrides)["calendar"]

    until = args.until or dt.date.today().isoformat()
    events = fetch_events(calendar, args.calendar_id, args.since, until)

    keep = re.compile(args.pattern, re.IGNORECASE)
    drop = re.compile(args.exclude, re.IGNORECASE) if args.exclude else None
    local = index_local_recordings(args.recordings_dir)

    report: list[dict] = []
    for event in events:
        summary = event.get("summary") or ""
        if not keep.search(summary):
            continue
        if drop and drop.search(summary):
            continue

        start = dt.datetime.fromisoformat(event["start"]["dateTime"]).replace(tzinfo=None)
        end = dt.datetime.fromisoformat(event["end"]["dateTime"]).replace(tzinfo=None)
        window_start = start - dt.timedelta(minutes=args.lead_minutes)
        window_end = end + dt.timedelta(minutes=args.trail_minutes)

        recordings, companions, inherited = attached_media(event, start, end)
        candidates = sorted(
            {str(path) for stamp, path in local if window_start <= stamp <= window_end}
        )

        if recordings:
            source, confidence = "calendar_attachment", "high"
        elif len(candidates) == 1:
            source, confidence = "local_capture", "medium"
        elif candidates:
            # Several files share the slot; at most one is this meeting.
            source, confidence = "local_capture", "low"
        else:
            source, confidence = "missing", "high"

        entry = {
            "start": start.isoformat(timespec="minutes"),
            "end": end.isoformat(timespec="minutes"),
            "duration_minutes": int((end - start).total_seconds() // 60),
            "summary": summary,
            "attendees": [a.get("email", "") for a in event.get("attendees", []) or []],
            "source": source,
            "confidence": confidence,
            "attached_recordings": recordings,
            "attached_companions": companions,
            "foreign_attachments": inherited,
            "local_candidates": candidates,
            "event_link": event.get("htmlLink", ""),
        }
        if args.missing_only and source != "missing":
            continue
        report.append(entry)
    return report


def print_report(report: list[dict]) -> None:
    marker = {"calendar_attachment": "REC ", "local_capture": "LOCAL", "missing": "GAP "}
    for entry in report:
        flag = marker[entry["source"]]
        low = "  (low confidence - several recordings share this slot)" if entry["confidence"] == "low" else ""
        print(f"{flag} {entry['start']}  {entry['duration_minutes']:>3}m  {entry['summary']}{low}")
        if entry["attendees"]:
            print(f"        participants: {', '.join(entry['attendees'])}")
        for rec in entry["attached_recordings"]:
            print(f"        attached recording: {rec['title']} (fileId={rec['file_id']})")
        for comp in entry["attached_companions"]:
            print(f"        also attached: {comp['title']} ({comp['mime_type']})")
        for old_att in entry["foreign_attachments"]:
            print(f"        ignored (timestamped outside this meeting): {old_att['title']}")
        for candidate in entry["local_candidates"]:
            print(f"        local candidate: {candidate}")
    gaps = sum(1 for e in report if e["source"] == "missing")
    unsure = sum(1 for e in report if e["confidence"] == "low")
    print(f"\n{len(report)} meeting(s): {gaps} with no recording, {unsure} needing manual identification.")


def main(argv: list[str] | None = None) -> int:
    ensure_utf8_stdout()
    args = parse_args(argv)
    report = audit(args)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_report(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
