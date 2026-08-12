"""Headless Confluence Cloud REST API client - no browser, no interactive
login. Mirrors pipeline_common.py's credential-loading conventions
(.local/<provider>/credentials.json, gitignored, same error-message shape
as the Google OAuth loader) but uses simple HTTP Basic Auth with an
Atlassian API token instead of an OAuth flow - Confluence Cloud's REST API
accepts `email:api_token` as Basic Auth directly, no refresh/expiry to
manage.

Setup (one-time):
1. Generate a token at https://id.atlassian.com/manage-profile/security/api-tokens
2. Create `.local/atlassian/credentials.json`:
   {"email": "you@example.com", "api_token": "...", "base_url": "https://<site>.atlassian.net"}
   (.local/ is gitignored - same trust boundary as .local/google/.)

Usage as a library:
    from confluence_client import get_session, get_page, get_children, storage_to_text
    session, base_url = get_session()
    page = get_page(session, base_url, "5203329112", expand="body.storage,version")
    print(storage_to_text(page["body"]["storage"]["value"]))

CLI:
    python confluence_client.py --page-id 5203329112
    python confluence_client.py --children 4564713491
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

DEFAULT_CREDENTIALS = Path(".local/atlassian/credentials.json")

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


def load_credentials(path: Path | str = DEFAULT_CREDENTIALS) -> dict[str, str]:
    path = Path(path)
    if not path.exists():
        raise SystemExit(
            f"Atlassian API credentials not found: {path}\n"
            "Generate a token at "
            "https://id.atlassian.com/manage-profile/security/api-tokens "
            "and create this file:\n"
            '  {"email": "you@example.com", "api_token": "...", '
            '"base_url": "https://<site>.atlassian.net"}'
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    missing = [k for k in ("email", "api_token", "base_url") if not data.get(k)]
    if missing:
        raise SystemExit(f"{path} is missing required field(s): {', '.join(missing)}")
    return data


def get_session(credentials_path: Path | str = DEFAULT_CREDENTIALS) -> tuple[requests.Session, str]:
    """Returns (authenticated session, base_url). base_url has no trailing slash."""
    creds = load_credentials(credentials_path)
    session = requests.Session()
    session.auth = (creds["email"], creds["api_token"])
    session.headers.update({"Accept": "application/json"})
    return session, creds["base_url"].rstrip("/")


def _check(response: requests.Response) -> Any:
    if response.status_code == 401:
        raise SystemExit(
            "Confluence API returned 401 Unauthorized - the API token is "
            "invalid, revoked, or the email doesn't match the token's "
            "owner. Regenerate at "
            "https://id.atlassian.com/manage-profile/security/api-tokens."
        )
    response.raise_for_status()
    return response.json()


def get_page(
    session: requests.Session,
    base_url: str,
    page_id: str,
    expand: str = "body.storage,version,ancestors",
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


def page_url(base_url: str, page: dict[str, Any]) -> str:
    webui = page.get("_links", {}).get("webui", "")
    return f"{base_url}/wiki{webui}" if webui else ""


def _main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--page-id", help="Fetch one page's title + body text")
    parser.add_argument("--children", metavar="PAGE_ID", help="List direct child pages")
    parser.add_argument("--cql", help="Run a CQL search (e.g. 'ancestor=4564713491')")
    parser.add_argument("--credentials", default=str(DEFAULT_CREDENTIALS))
    args = parser.parse_args()

    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")

    session, base_url = get_session(args.credentials)

    if args.page_id:
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
