"""Headless Confluence Cloud REST API client - no browser, no interactive
login. Mirrors pipeline_common.py's credential-loading conventions
(.local/<provider>/<profile>_credentials.json, gitignored) but uses simple
HTTP Basic Auth with an Atlassian API token instead of an OAuth flow -
Confluence Cloud's REST API accepts `email:api_token` as Basic Auth directly,
no refresh/expiry to manage.

Setup (per site / project profile):
1. Generate a token at https://id.atlassian.com/manage-profile/security/api-tokens
2. Create `.local/atlassian/<profile>_credentials.json` (e.g. `innowise_credentials.json` or `pkf_credentials.json`):
   {"email": "you@example.com", "api_token": "...", "base_url": "https://<site>.atlassian.net"}
   (.local/ is gitignored - same trust boundary as .local/google/.)

Usage as a library:
    from confluence_client import get_session, get_page, create_page, update_page, storage_to_text
    session, base_url = get_session(profile="pkf")
    page = get_page(session, base_url, "1601339413", expand="body.storage,version")
    print(storage_to_text(page["body"]["storage"]["value"]))

CLI examples:
    python confluence_client.py --profile pkf --page-id 1601339413
    python confluence_client.py --profile pkf --update-page 1601339413 --file update.html --comment "Update test strategy"
    python confluence_client.py --profile pkf --create-page --space TB --title "New Plan" --file plan.html --parent-id 1601339413
    python confluence_client.py --profile innowise --children 4564713491
    python confluence_client.py --cql "ancestor=4564713491"
"""

from __future__ import annotations

import argparse
import json
import sys
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import requests

ATLASSIAN_DIR = Path(".local/atlassian")
DEFAULT_CREDENTIALS = ATLASSIAN_DIR / "credentials.json"

BLOCK_TAGS = {
    "p", "div", "table", "tr", "h1", "h2", "h3", "h4", "h5", "h6",
    "li", "br", "ac:structured-macro", "ac:rich-text-body",
}
HEADING_TAGS = {"h1": "#", "h2": "##", "h3": "###", "h4": "####"}


class _StorageTextExtractor(HTMLParser):
    """Minimal storage-format (XHTML + Confluence ac:* macros) -> plain
    text extractor. Deliberately stdlib-only (no bs4/html2text dependency)
    - good enough for reading content, not a faithful renderer. Table
    cells/list items get line breaks; headings get a Markdown-style
    prefix; everything else is just text with block-level line breaks."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._heading_prefix: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in HEADING_TAGS:
            self._heading_prefix = HEADING_TAGS[tag]
            self.parts.append("\n" + HEADING_TAGS[tag] + " ")
        elif tag == "li":
            self.parts.append("\n- ")
        elif tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in HEADING_TAGS:
            self._heading_prefix = None
            self.parts.append("\n")
        elif tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        text = data.strip("\n")
        if text.strip():
            self.parts.append(text)

    def get_text(self) -> str:
        raw = "".join(self.parts)
        lines = [line.strip() for line in raw.splitlines()]
        out: list[str] = []
        blank = False
        for line in lines:
            if not line:
                if not blank:
                    out.append("")
                blank = True
                continue
            blank = False
            out.append(line)
        return "\n".join(out).strip()


def storage_to_text(storage_html: str) -> str:
    """Convert a Confluence `body.storage.value` XHTML string to readable
    plain text. Loses table-grid/macro-parameter structure - read the raw
    storage value directly (or `body.view.value` for closer-to-rendered
    HTML) if that's needed instead of prose content."""
    parser = _StorageTextExtractor()
    parser.feed(storage_html)
    return parser.get_text()


def resolve_credentials_path(path: Path | str | None = None, profile: str | None = None) -> Path:
    if path:
        return Path(path)

    if profile:
        profile_candidates = [
            ATLASSIAN_DIR / f"{profile}_credentials.json",
            ATLASSIAN_DIR / f"{profile}.json",
            ATLASSIAN_DIR / f"credentials_{profile}.json",
            Path(profile),
        ]
        for candidate in profile_candidates:
            if candidate.exists():
                return candidate
        raise SystemExit(
            f"Atlassian credentials for profile '{profile}' not found.\n"
            f"Expected file at: {ATLASSIAN_DIR / f'{profile}_credentials.json'}\n"
            "Format:\n"
            '  {"email": "you@example.com", "api_token": "...", "base_url": "https://<site>.atlassian.net"}'
        )

    # Default lookup: credentials.json -> innowise_credentials.json -> single available config
    if DEFAULT_CREDENTIALS.exists():
        return DEFAULT_CREDENTIALS

    innowise = ATLASSIAN_DIR / "innowise_credentials.json"
    if innowise.exists():
        return innowise

    if ATLASSIAN_DIR.exists():
        configs = list(ATLASSIAN_DIR.glob("*credentials*.json")) + list(ATLASSIAN_DIR.glob("*.json"))
        configs = sorted(set(configs))
        if len(configs) == 1:
            return configs[0]
        if configs:
            names = [c.stem.replace("_credentials", "").replace("credentials_", "") for c in configs]
            raise SystemExit(
                f"Multiple Atlassian credential profiles found in {ATLASSIAN_DIR}: {', '.join(names)}\n"
                "Please specify one using --profile <name> or --credentials <path>."
            )

    return DEFAULT_CREDENTIALS


def load_credentials(path: Path | str | None = None, profile: str | None = None) -> dict[str, str]:
    resolved = resolve_credentials_path(path, profile)
    if not resolved.exists():
        raise SystemExit(
            f"Atlassian API credentials not found: {resolved}\n"
            "Generate a token at "
            "https://id.atlassian.com/manage-profile/security/api-tokens "
            "and create this file:\n"
            '  {"email": "you@example.com", "api_token": "...", '
            '"base_url": "https://<site>.atlassian.net"}'
        )
    data = json.loads(resolved.read_text(encoding="utf-8"))
    missing = [k for k in ("email", "api_token", "base_url") if not data.get(k)]
    if missing:
        raise SystemExit(f"{resolved} is missing required field(s): {', '.join(missing)}")
    return data


def get_session(
    credentials_path: Path | str | None = None,
    profile: str | None = None,
) -> tuple[requests.Session, str]:
    """Returns (authenticated session, base_url). base_url has no trailing slash."""
    creds = load_credentials(credentials_path, profile=profile)
    session = requests.Session()
    session.auth = (creds["email"], creds["api_token"])
    session.headers.update({
        "Accept": "application/json",
        "Content-Type": "application/json",
    })
    return session, creds["base_url"].rstrip("/")


def _check(response: requests.Response) -> Any:
    if response.status_code == 401:
        raise SystemExit(
            "Confluence API returned 401 Unauthorized - the API token is "
            "invalid, revoked, or the email doesn't match the token's "
            "owner. Regenerate at "
            "https://id.atlassian.com/manage-profile/security/api-tokens."
        )
    if not response.ok:
        try:
            err_json = response.json()
            message = err_json.get("message") or json.dumps(err_json)
        except Exception:
            message = response.text or f"HTTP {response.status_code}"
        raise SystemExit(f"Confluence API error ({response.status_code}): {message}")
    return response.json()


def get_page(
    session: requests.Session,
    base_url: str,
    page_id: str,
    expand: str = "body.storage,version,ancestors,space",
) -> dict[str, Any]:
    url = f"{base_url}/wiki/rest/api/content/{page_id}"
    return _check(session.get(url, params={"expand": expand}))


def get_children(
    session: requests.Session,
    base_url: str,
    page_id: str,
    expand: str = "version",
) -> list[dict[str, Any]]:
    """Direct children (one level) of a page or folder, via the
    dedicated child/page endpoint - use this over CQL for a simple
    "what's directly under this folder/page" listing."""
    url = f"{base_url}/wiki/rest/api/content/{page_id}/child/page"
    results: list[dict[str, Any]] = []
    params: dict[str, Any] = {"expand": expand, "limit": 100}
    while True:
        data = _check(session.get(url, params=params))
        results.extend(data.get("results", []))
        next_link = data.get("_links", {}).get("next")
        if not next_link:
            break
        # `next` is a relative URL with its own query string - follow it as-is.
        response = session.get(base_url + next_link)
        data = _check(response)
        results.extend(data.get("results", []))
        if not data.get("_links", {}).get("next"):
            break
    return results


def search_cql(
    session: requests.Session,
    base_url: str,
    cql: str,
    expand: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """General-purpose search, e.g. `ancestor=<id>` for every descendant
    (not just direct children) under a folder/page, or `space=<KEY> and
    title~"<text>"` for a title search."""
    url = f"{base_url}/wiki/rest/api/content/search"
    params: dict[str, Any] = {"cql": cql, "limit": limit}
    if expand:
        params["expand"] = expand
    results: list[dict[str, Any]] = []
    while True:
        data = _check(session.get(url, params=params))
        results.extend(data.get("results", []))
        next_link = data.get("_links", {}).get("next")
        if not next_link:
            break
        data = _check(session.get(base_url + next_link))
        results.extend(data.get("results", []))
        if not data.get("_links", {}).get("next"):
            break
    return results


def create_page(
    session: requests.Session,
    base_url: str,
    space_key: str,
    title: str,
    body_storage: str,
    parent_id: str | None = None,
) -> dict[str, Any]:
    """Create a new page in the given space (optional parent page ancestor)."""
    url = f"{base_url}/wiki/rest/api/content"
    payload: dict[str, Any] = {
        "type": "page",
        "title": title,
        "space": {"key": space_key},
        "body": {
            "storage": {
                "value": body_storage,
                "representation": "storage",
            }
        },
    }
    if parent_id:
        payload["ancestors"] = [{"id": str(parent_id)}]
    return _check(session.post(url, json=payload))


def update_page(
    session: requests.Session,
    base_url: str,
    page_id: str,
    title: str | None = None,
    body_storage: str | None = None,
    minor_edit: bool = False,
    version_comment: str | None = None,
) -> dict[str, Any]:
    """Update an existing page by reading its current version and sending PUT."""
    current = get_page(session, base_url, page_id, expand="body.storage,version,space")
    current_version = current.get("version", {}).get("number", 1)
    space_key = current.get("space", {}).get("key")

    page_title = title if title is not None else current["title"]
    page_body = body_storage if body_storage is not None else current["body"]["storage"]["value"]

    url = f"{base_url}/wiki/rest/api/content/{page_id}"
    version_payload: dict[str, Any] = {
        "number": current_version + 1,
        "minorEdit": minor_edit,
    }
    if version_comment:
        version_payload["message"] = version_comment

    payload: dict[str, Any] = {
        "id": str(page_id),
        "type": "page",
        "title": page_title,
        "space": {"key": space_key},
        "body": {
            "storage": {
                "value": page_body,
                "representation": "storage",
            }
        },
        "version": version_payload,
    }
    return _check(session.put(url, json=payload))


def page_url(base_url: str, page: dict[str, Any]) -> str:
    webui = page.get("_links", {}).get("webui", "")
    return f"{base_url}/wiki{webui}" if webui else ""


def _main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--profile", "-p", help="Credential profile name (e.g. 'pkf', 'innowise')")
    parser.add_argument("--credentials", "-c", help="Path to credentials JSON file")

    # Read actions
    parser.add_argument("--page-id", help="Fetch one page's title + body text")
    parser.add_argument("--children", metavar="PAGE_ID", help="List direct child pages")
    parser.add_argument("--cql", help="Run a CQL search (e.g. 'ancestor=4564713491')")

    # Write actions
    parser.add_argument("--create-page", action="store_true", help="Create a new Confluence page")
    parser.add_argument("--update-page", metavar="PAGE_ID", help="Update an existing Confluence page ID")
    parser.add_argument("--space", help="Target space key for creating a page")
    parser.add_argument("--title", help="Page title for create or update")
    parser.add_argument("--parent-id", help="Parent page ID for create")
    parser.add_argument("--file", help="Path to file containing storage XHTML/HTML body")
    parser.add_argument("--minor-edit", action="store_true", help="Mark update as minor edit")
    parser.add_argument("--comment", help="Version comment message")

    args = parser.parse_args()

    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")

    session, base_url = get_session(credentials_path=args.credentials, profile=args.profile)

    if args.create_page:
        if not args.space or not args.title or not args.file:
            parser.error("--create-page requires --space, --title, and --file")
        body_content = Path(args.file).read_text(encoding="utf-8")
        created = create_page(
            session=session,
            base_url=base_url,
            space_key=args.space,
            title=args.title,
            body_storage=body_content,
            parent_id=args.parent_id,
        )
        print(f"Created page '{created['title']}' (ID: {created['id']})")
        print(page_url(base_url, created))
    elif args.update_page:
        if not args.file and not args.title:
            parser.error("--update-page requires at least --file or --title")
        body_content = Path(args.file).read_text(encoding="utf-8") if args.file else None
        updated = update_page(
            session=session,
            base_url=base_url,
            page_id=args.update_page,
            title=args.title,
            body_storage=body_content,
            minor_edit=args.minor_edit,
            version_comment=args.comment,
        )
        print(f"Updated page '{updated['title']}' (v{updated['version']['number']})")
        print(page_url(base_url, updated))
    elif args.page_id:
        page = get_page(session, base_url, args.page_id)
        print(f"# {page['title']}  (v{page['version']['number']})")
        print(page_url(base_url, page))
        print()
        print(storage_to_text(page["body"]["storage"]["value"]))
    elif args.children:
        for child in get_children(session, base_url, args.children):
            print(f"{child['id']}\t{child['title']}\t{page_url(base_url, child)}")
    elif args.cql:
        for item in search_cql(session, base_url, args.cql, expand="version"):
            print(f"{item['id']}\t{item['title']}\t{page_url(base_url, item)}")
    else:
        parser.print_help()


if __name__ == "__main__":
    _main()
