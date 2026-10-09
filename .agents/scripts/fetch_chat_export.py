"""Pull a Google Chat space's messages from its link into a `00_Inbox` text
file, so a strategy chat no longer has to be copy-pasted by hand.

The file is written in the same shape as a manual copy-paste from Google
Chat - one header line per message ("Name, Mon D, H:MM AM/PM[, Edited]")
followed by the message text - so `detect_strategy_chats.py` and the
`m2-strategy-chat-analysis` skill read it unchanged. The file name follows
that skill's New-File Convention: `<Project>_<label>_<YYYY-MM-DD>.txt`, a
new file per batch, never appended to an already-logged one.

Read-only against Google Chat (chat.messages.readonly). Dry-run by default:
prints the message count, date range and the first lines; `--apply` writes
the file. Refuses to overwrite an existing file.

Limits:
- Sender names come from the space's current membership; a person who has
  left the space prints as their `users/<id>`.
- Headers carry no year (same as a real paste), so detection resolves dates
  against the file's mtime; keep one batch within twelve months.
- Message text only: attachments and Drive links are listed by name, not
  downloaded.

A thread link (`.../room/<space>/<thread>`) limits the fetch to that
thread. `--print` writes the text to stdout instead of a file - the mode
for drafting a reply (`m2-chat-reply`), which must not create inbox files.

Usage:
  fetch_chat_export.py --url https://chat.google.com/room/<id> --project <Project> --since 2026-09-25
  fetch_chat_export.py --url <link> --project <Project> --days 14 --apply
  fetch_chat_export.py --url https://chat.google.com/room/<id>/<thread> --print
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from google_api_smoke_test import ensure_utf8_stdout, import_google_libs, load_credentials
from pipeline_common import DEFAULT_CREDENTIALS, DEFAULT_TOKEN

DEFAULT_INBOX = Path(r"G:\My Drive\QA_Management\00_Inbox")
SPACE_ID_RE = re.compile(r"(?:room|space|dm)/([A-Za-z0-9_-]{8,})(?:/([A-Za-z0-9_-]{6,}))?")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", required=True, help="Chat or thread link (chat.google.com/room/<id>[/<thread>]) or a bare space id.")
    parser.add_argument("--project", help="Project name as in _project_registry; becomes the file prefix (file mode).")
    parser.add_argument("--label", default="strategy", help="File-name label after the project (default: strategy).")
    parser.add_argument("--print", dest="to_stdout", action="store_true",
                        help="Print the messages instead of writing a file (reply drafting).")
    window = parser.add_mutually_exclusive_group()
    window.add_argument("--since", help="Start date YYYY-MM-DD (inclusive, local time).")
    window.add_argument("--days", type=int, help="Fetch the last N days.")
    parser.add_argument("--until", help="End date YYYY-MM-DD (inclusive, local time); default now.")
    parser.add_argument("--inbox", default=str(DEFAULT_INBOX))
    parser.add_argument("--credentials", default=str(DEFAULT_CREDENTIALS))
    parser.add_argument("--token", default=str(DEFAULT_TOKEN))
    parser.add_argument("--apply", action="store_true", help="Write the file (default: dry run).")
    return parser.parse_args()


def ids_from(url: str) -> tuple[str, str | None]:
    """Return (space id, thread id or None) from a chat/thread link or a bare space id."""
    match = SPACE_ID_RE.search(url)
    if match:
        return match.group(1), match.group(2)
    if re.fullmatch(r"[A-Za-z0-9_-]{8,}", url):
        return url, None
    raise SystemExit(f"Cannot find a space id in: {url}")


def local_bounds(args: argparse.Namespace) -> tuple[dt.datetime | None, dt.datetime]:
    now = dt.datetime.now().astimezone()
    if args.days is not None:
        start = (now - dt.timedelta(days=args.days)).replace(hour=0, minute=0, second=0, microsecond=0)
    elif args.since:
        start = dt.datetime.fromisoformat(args.since).astimezone()
    else:
        start = None  # whole thread
    end = now
    if args.until:
        end = (dt.datetime.fromisoformat(args.until) + dt.timedelta(days=1)).astimezone()
    if start and (end - start).days > 330 and not args.to_stdout:
        raise SystemExit("Window longer than ~11 months: headers carry no year, split it into smaller batches.")
    return start, end


def rfc3339(value: dt.datetime) -> str:
    return value.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def member_names(chat, space: str) -> dict[str, str]:
    names: dict[str, str] = {}
    token = None
    while True:
        resp = chat.spaces().members().list(parent=space, pageSize=1000, pageToken=token).execute()
        for membership in resp.get("memberships", []):
            member = membership.get("member", {})
            if member.get("name") and member.get("displayName"):
                names[member["name"]] = member["displayName"]
        token = resp.get("nextPageToken")
        if not token:
            return names


def fetch_messages(chat, space: str, start: dt.datetime | None, end: dt.datetime, thread: str | None) -> list[dict]:
    parts = [f'createTime < "{rfc3339(end)}"']
    if start:
        parts.insert(0, f'createTime > "{rfc3339(start)}"')
    if thread:
        parts.append(f"thread.name = {space}/threads/{thread}")
    query = " AND ".join(parts)
    messages: list[dict] = []
    token = None
    while True:
        resp = chat.spaces().messages().list(
            parent=space, pageSize=1000, pageToken=token, filter=query, orderBy="createTime asc"
        ).execute()
        messages.extend(resp.get("messages", []))
        token = resp.get("nextPageToken")
        if not token:
            return messages


def header(sender: str, created: dt.datetime, edited: bool) -> str:
    # detect_strategy_chats.py splits the header on commas, so a name may not contain one.
    name = sender.replace(",", " ").strip()
    hour = created.strftime("%I").lstrip("0") or "12"
    line = f"{name}, {created.strftime('%b')} {created.day}, {hour}:{created.strftime('%M %p')}"
    return line + (", Edited" if edited else "")


def render(messages: list[dict], names: dict[str, str]) -> str:
    blocks = []
    for message in messages:
        if message.get("deletionMetadata"):
            continue
        sender = message.get("sender", {})
        who = sender.get("displayName") or names.get(sender.get("name", ""), sender.get("name", "unknown"))
        created = dt.datetime.fromisoformat(message["createTime"].replace("Z", "+00:00")).astimezone()
        edited = bool(message.get("lastUpdateTime")) and message.get("lastUpdateTime") != message.get("createTime")
        body = (message.get("text") or "").strip()
        attachments = [a.get("contentName") or a.get("name", "") for a in message.get("attachment", [])]
        if attachments:
            body = (body + "\n" if body else "") + "\n".join(f"[attachment: {a}]" for a in attachments)
        blocks.append(f"{header(who, created, edited)}\n{body}\n")
    return "\n".join(blocks)


def main() -> int:
    ensure_utf8_stdout()
    args = parse_args()
    space_id, thread = ids_from(args.url)
    space = f"spaces/{space_id}"
    if not args.to_stdout and not args.project:
        raise SystemExit("--project is required unless --print is used.")
    if not thread and not (args.since or args.days is not None):
        raise SystemExit("Give --since or --days (only a thread link may omit the window).")
    start, end = local_bounds(args)

    _, _, _, build = import_google_libs()
    chat = build("chat", "v1", credentials=load_credentials(Path(args.credentials), Path(args.token)))
    info = chat.spaces().get(name=space).execute()
    messages = fetch_messages(chat, space, start, end, thread)
    text = render(messages, member_names(chat, space))

    print(f"Space: {info.get('displayName')} ({space})" + (f", thread {thread}" if thread else ""))
    window = f"{start:%Y-%m-%d %H:%M}" if start else "thread start"
    print(f"Window: {window} .. {end:%Y-%m-%d %H:%M}, messages: {len(messages)}")
    if not messages:
        print("Nothing found.")
        return 0
    if args.to_stdout:
        print("\n" + text)
        return 0

    out = Path(args.inbox) / f"{args.project}_{args.label}_{dt.date.today().isoformat()}.txt"
    first = messages[0]["createTime"][:10]
    last = messages[-1]["createTime"][:10]
    print(f"Message dates: {first} .. {last}")
    print(f"Target file: {out}")
    if not args.apply:
        print("\n--- preview (dry run, nothing written; add --apply) ---")
        print("\n".join(text.splitlines()[:20]))
        return 0
    if out.exists():
        raise SystemExit(f"Refusing to overwrite {out}; use another --label or move the existing file.")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(f"Wrote {out}. Next: detect_strategy_chats.py, then m2-strategy-chat-analysis.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
