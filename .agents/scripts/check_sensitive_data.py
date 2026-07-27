"""Guard for AGENTS.md's "No Sensitive Data In This Repository" rule.

Scans the whole **commit candidate** - everything that would become public
if you committed and pushed right now - for real person/project names
pulled live from `_people_registry`/`_project_registry`:

- every tracked file as staged in the git index;
- every tracked file's working-tree version;
- untracked, non-gitignored files;
- the repository-relative **paths** themselves, not only file contents;
- anywhere in the repository, not only `.agents/`.

Scanning the index *and* the working tree separately matters: a value can
be staged and then removed from the working tree, so a working-tree-only
scan would call a dirty commit candidate clean. Never inspected: `.git/`,
gitignored paths (including `.local/`), binary files, and anything reached
by following a symlink/junction out of the repository.

Deletions are not a blanket exclusion, and the distinction matters: a
**staged** deletion has no index entry and no file on disk, so it
contributes no candidate blob at all; an **unstaged** deletion is still
staged in the index, so its index version is still scanned - that content
would ship if you committed right now.

Output is metadata only - repository-relative path, line number, and
whether the hit came from the index, the working tree, or an untracked
file. A **path** hit prints no path at all (the path is the sensitive
value), only an ordinal. Matched values and matching lines are never
printed, and no stable per-value id is emitted: against a registry of a
few hundred names, even a truncated hash is trivially dictionary-matched
back to the value.

**Fails closed.** Any git enumeration that errors, a non-git `--repo`, a
truncated `cat-file --batch` stream, or an empty watch list is a
non-zero exit - never silently "no findings". An unreadable repository
must never look like a clean one.

**This is a cheap net, not proof of safety.** It matches only strings
already registered in Drive, as literal substrings. It will not catch a
real company name, an email address, a phone number, an unregistered
project or person, or paraphrased first-party material that happens not to
match a registry string. A human read against AGENTS.md is still required
before committing. Not wired into a git hook.

Usage:
  python .agents/scripts/check_sensitive_data.py
  python .agents/scripts/check_sensitive_data.py --repo <path>
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

sys.path.insert(0, str(Path(__file__).parent))
from google_api_smoke_test import ensure_utf8_stdout
from operator_telemetry_common import contains_watch_string
from pipeline_common import PEOPLE_REGISTRY_FOLDER, PEOPLE_REGISTRY_SHEET

MIN_NAME_LEN = 4  # skip short tokens likely to false-positive (e.g. common words)

INDEX = "index"
WORKTREE = "worktree"
UNTRACKED = "untracked"


class RegistryLookupError(RuntimeError):
    """A required registry folder/Sheet is missing, or the watch list is empty.

    Raised instead of creating anything: this script is read-only by
    contract, and a missing or empty registry is a real problem to
    investigate, not something to silently work around with a watch list
    that would pass everything.
    """


class ScanError(RuntimeError):
    """The commit candidate could not be enumerated completely.

    Anything that leaves the scan partial - a failed git call, a non-git
    path, a truncated object stream - raises this. A partial scan reported
    as "no findings" is the worst possible outcome for a safety guard, so
    incompleteness is always an error, never an empty result.
    """


# ---------------------------------------------------------------------------
# Watch strings (live, read-only Drive lookup)
# ---------------------------------------------------------------------------

def load_watch_strings(services: dict[str, Any]) -> set[str]:
    """Real person/project names, fetched live. Never hardcoded here.

    Uses read-only finders exclusively - no folder-or-create helper, no
    Sheet creation, no Drive mutation of any kind.
    """
    from show_project_state import find_folder
    from sync_m2_source_docs_to_sheets import (
        ROOT_FOLDER_ID,
        find_sheet_in_folder,
        read_sheet_values,
    )

    drive = services["drive"]
    watch: set[str] = set()

    def require_folder(name: str) -> dict[str, Any]:
        folder = find_folder(drive, ROOT_FOLDER_ID, name)
        if not folder:
            raise RegistryLookupError(
                f"required registry folder {name!r} not found under the workspace "
                f"root; refusing to create it - investigate before committing"
            )
        return folder

    def require_sheet(folder: dict[str, Any], title: str) -> dict[str, Any]:
        sheet = find_sheet_in_folder(drive, folder["id"], title)
        if not sheet:
            raise RegistryLookupError(
                f"required registry Sheet {title!r} not found in {folder.get('name', '?')!r}; "
                f"refusing to create it - investigate before committing"
            )
        return sheet

    people_root = require_folder(PEOPLE_REGISTRY_FOLDER)
    people_sheet = require_sheet(people_root, PEOPLE_REGISTRY_SHEET)
    for row in read_sheet_values(services, people_sheet["id"])[1:]:
        for col in (0, 1):  # Name (RU), Name (EN)
            if len(row) > col and row[col].strip():
                watch.add(row[col].strip())

    m2_root = require_folder("20_M2_Project_Management")
    project_sheet = require_sheet(m2_root, "_project_registry")
    for row in read_sheet_values(services, project_sheet["id"])[1:]:
        if row and row[0].strip():
            watch.add(row[0].strip())

    usable = {s for s in watch if len(s) >= MIN_NAME_LEN}
    if not usable:
        raise RegistryLookupError(
            "registry lookup produced an empty watch list - every file would "
            "pass trivially; refusing to report a false all-clear"
        )
    return usable


# ---------------------------------------------------------------------------
# Commit-candidate enumeration (fails closed)
# ---------------------------------------------------------------------------

def _git(repo: Path, args: list[str]) -> bytes:
    """Run a git command, raising ScanError on any failure."""
    try:
        proc = subprocess.run(["git", "-C", str(repo), *args], capture_output=True)
    except OSError as exc:
        raise ScanError(f"could not run 'git {args[0]}': {exc}") from exc
    if proc.returncode != 0:
        detail = proc.stderr.decode("utf-8", "replace").strip().splitlines()
        raise ScanError(
            f"'git {' '.join(args)}' failed with exit {proc.returncode}"
            + (f": {detail[0]}" if detail else "")
        )
    return proc.stdout


def require_git_repo(repo: Path) -> None:
    if not repo.is_dir():
        raise ScanError(f"--repo path is not a directory: {repo}")
    inside = _git(repo, ["rev-parse", "--is-inside-work-tree"]).decode().strip()
    if inside != "true":
        raise ScanError(f"--repo path is not a git work tree: {repo}")


def _decode(data: bytes) -> str | None:
    """Decode as text, or None when the blob is binary.

    A NUL byte is git's own binary heuristic; undecodable bytes count too,
    since there is no text to scan.
    """
    if b"\0" in data:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        try:
            return data.decode("cp1251")
        except UnicodeDecodeError:
            return None


def _split_z(out: bytes) -> list[str]:
    return [p.decode("utf-8", "replace") for p in out.split(b"\0") if p]


def index_entries(repo: Path) -> list[tuple[str, str]]:
    """(blob_sha, path) for every entry staged in the index.

    A staged deletion has no index entry, so it contributes nothing here;
    an unstaged deletion is still staged, so its blob is still listed and
    scanned. A malformed entry is an error, not something to skip quietly.
    """
    entries: list[tuple[str, str]] = []
    for entry in _git(repo, ["ls-files", "-s", "-z"]).split(b"\0"):
        if not entry:
            continue
        meta, sep, path = entry.partition(b"\t")
        parts = meta.split()
        if not sep or len(parts) < 3:
            raise ScanError("malformed 'git ls-files -s' entry - index enumeration incomplete")
        entries.append((parts[1].decode(), path.decode("utf-8", "replace")))
    return entries


def iter_index_files(repo: Path) -> Iterator[tuple[str, str]]:
    """(path, text) for every staged blob.

    Read through one `cat-file --batch` process rather than a spawn per
    file. The stream is parsed strictly: a short read, a missing object, or
    a leftover tail means the index was not fully inspected, which is a
    ScanError rather than a partial result.
    """
    entries = index_entries(repo)
    if not entries:
        return

    try:
        proc = subprocess.run(
            ["git", "-C", str(repo), "cat-file", "--batch"],
            input="\n".join(sha for sha, _ in entries).encode() + b"\n",
            capture_output=True,
        )
    except OSError as exc:
        raise ScanError(f"could not run 'git cat-file --batch': {exc}") from exc
    if proc.returncode != 0:
        raise ScanError(f"'git cat-file --batch' failed with exit {proc.returncode}")

    buf, offset = proc.stdout, 0
    for _sha, rel in entries:
        header_end = buf.find(b"\n", offset)
        if header_end == -1:
            raise ScanError("truncated 'git cat-file --batch' output - index scan incomplete")
        header = buf[offset:header_end].split()
        if len(header) < 3:
            raise ScanError("unreadable object in 'git cat-file --batch' output")
        try:
            size = int(header[2])
        except ValueError as exc:
            raise ScanError("malformed size in 'git cat-file --batch' output") from exc
        start = header_end + 1
        data = buf[start:start + size]
        if len(data) != size:
            raise ScanError("short object body in 'git cat-file --batch' output")
        separator_at = start + size
        if buf[separator_at:separator_at + 1] != b"\n":
            raise ScanError("missing object separator in 'git cat-file --batch' output")
        offset = separator_at + 1
        text = _decode(data)
        if text is not None:
            yield rel, text

    if offset != len(buf):
        raise ScanError(
            "unexpected trailing output from 'git cat-file --batch' - "
            "the index stream did not end where the entry list did"
        )


def _is_safe_regular_file(repo: Path, full: Path) -> bool:
    """True only for a real file that is not reached through a link out.

    Symlinks/junctions are not followed: `is_symlink()` covers POSIX
    symlinks and Windows symlinks, `is_junction()` covers directory
    junctions, and the resolved-path containment check catches a link
    anywhere in the parent chain.
    """
    if full.is_symlink() or (hasattr(Path, "is_junction") and full.is_junction()):
        return False
    try:
        resolved = full.resolve()
        resolved.relative_to(repo.resolve())
    except (OSError, ValueError):
        return False
    return resolved.is_file()


def iter_worktree_files(repo: Path) -> Iterator[tuple[str, str]]:
    """(path, text) for tracked files present on disk, plus untracked ones.

    `--exclude-standard` applies .gitignore/.git/info/exclude/global
    excludes, so gitignored paths (`.local/`, `tmp/`, ...) are never read.
    Tracked files missing from disk are unstaged deletions - skipped here;
    their staged content is still covered by the index pass. Links are
    skipped rather than dereferenced; a staged symlink's blob is still
    scanned as index content, which reads its target as text without
    following it.
    """
    listing = _split_z(_git(repo, ["ls-files", "-z", "--cached", "--others", "--exclude-standard"]))
    seen: set[str] = set()
    for rel in listing:
        if rel in seen:
            continue
        seen.add(rel)
        full = repo / rel
        if not _is_safe_regular_file(repo, full):
            continue
        try:
            data = full.read_bytes()
        except OSError as exc:
            # An enumerated regular file that cannot be read leaves the scan
            # partial. The path may itself be sensitive, so it is withheld -
            # `git status` will show you which file is unreadable.
            raise ScanError(
                f"could not read an enumerated file (path withheld): "
                f"{type(exc).__name__} - run 'git status' to find it"
            ) from None
        text = _decode(data)
        if text is not None:
            yield rel, text


def tracked_paths(repo: Path) -> set[str]:
    return set(_split_z(_git(repo, ["ls-files", "-z"])))


def iter_commit_candidate(repo: Path) -> Iterator[tuple[str, str, str]]:
    """(source, path, text) over the whole commit candidate."""
    tracked = tracked_paths(repo)
    for path, text in iter_index_files(repo):
        yield INDEX, path, text
    for path, text in iter_worktree_files(repo):
        yield (WORKTREE if path in tracked else UNTRACKED), path, text


def iter_candidate_paths(repo: Path) -> Iterator[tuple[str, str]]:
    """(source, path) for every path in the commit candidate.

    Filenames leak too: a source archived as `<RealProject> notes.md` is a
    disclosure even when the file's bytes are clean.
    """
    tracked = tracked_paths(repo)
    for _sha, path in index_entries(repo):
        yield INDEX, path
    for rel in _split_z(_git(repo, ["ls-files", "-z", "--cached", "--others", "--exclude-standard"])):
        yield (WORKTREE if rel in tracked else UNTRACKED), rel


# ---------------------------------------------------------------------------
# Scanning
# ---------------------------------------------------------------------------

@dataclass
class Finding:
    """A content hit. Carries no value and no line text by construction.

    `path` is kept in memory for coordination but is only rendered when the
    path itself is clean. Once `path_ordinal` is set - meaning the path
    matched the watch list too - the path is withheld and the finding is
    tied to its path finding by ordinal instead.
    """
    path: str
    line_no: int
    sources: set[str] = field(default_factory=set)
    path_ordinal: int | None = None

    def render(self) -> str:
        where = "+".join(sorted(self.sources))
        if self.path_ordinal is not None:
            return (f"  sensitive path #{self.path_ordinal}, line {self.line_no} "
                    f"[{where}] (path withheld)")
        return f"  {self.path}:{self.line_no} [{where}]"


@dataclass
class PathFinding:
    """A hit in a path. The path itself is withheld - it *is* the value."""
    ordinal: int
    path: str = ""  # internal only; never rendered
    sources: set[str] = field(default_factory=set)

    def render(self) -> str:
        return f"  sensitive path detected #{self.ordinal} [{'+'.join(sorted(self.sources))}]"


def coordinate(findings: list[Finding], path_findings: list[PathFinding]) -> None:
    """Withhold the path of any content finding whose path is itself sensitive.

    Without this, a file named after a real project would leak that name
    through its own content diagnostics even though the path finding was
    careful to withhold it.
    """
    ordinals = {pf.path: pf.ordinal for pf in path_findings}
    for finding in findings:
        if finding.path in ordinals:
            finding.path_ordinal = ordinals[finding.path]


def scan(repo: Path, watch: set[str]) -> list[Finding]:
    """Content findings, deduplicated by path+line.

    An identical hit in the index and the working tree is one finding
    listing both sources, not two.
    """
    found: dict[tuple[str, int], Finding] = {}
    for source, path, text in iter_commit_candidate(repo):
        for line_no, line in enumerate(text.splitlines(), 1):
            if not contains_watch_string(line, watch):
                continue
            key = (path, line_no)
            found.setdefault(key, Finding(path=path, line_no=line_no)).sources.add(source)
    return [found[k] for k in sorted(found)]


def scan_paths(repo: Path, watch: set[str]) -> list[PathFinding]:
    """Path findings, ordinal-numbered so the path is never disclosed."""
    by_path: dict[str, set[str]] = {}
    for source, path in iter_candidate_paths(repo):
        if contains_watch_string(path, watch):
            by_path.setdefault(path, set()).add(source)
    return [
        PathFinding(ordinal=i, path=p, sources=srcs)
        for i, (p, srcs) in enumerate(sorted(by_path.items()), 1)
    ]


def main(argv: list[str] | None = None) -> int:
    ensure_utf8_stdout()
    parser = argparse.ArgumentParser(
        description="Scan the whole commit candidate for registered real names/projects."
    )
    parser.add_argument(
        "--repo", default=None,
        help="Repository to scan (default: the repository this script lives in).",
    )
    args = parser.parse_args(argv)
    repo = Path(args.repo).resolve() if args.repo else Path(__file__).resolve().parents[2]

    from pipeline_common import get_services
    try:
        watch = load_watch_strings(get_services())
    except RegistryLookupError as exc:
        print(f"FAIL: {exc}")
        return 2
    print(f"Loaded {len(watch)} known name(s)/project(s) to watch for.")

    try:
        require_git_repo(repo)
        findings = scan(repo, watch)
        path_findings = scan_paths(repo, watch)
        coordinate(findings, path_findings)
    except ScanError as exc:
        print(f"FAIL: incomplete scan - {exc}")
        print("Treating this as a failure, not a clean result.")
        return 2

    if not findings and not path_findings:
        print(
            "No known real names/projects found in the commit candidate "
            "(index, working tree, untracked; contents and paths). This does "
            "not prove the tree is clean - company names, contacts, "
            "unregistered identifiers, and paraphrased first-party material "
            "are not detectable this way. See AGENTS.md."
        )
        return 0

    total = len(findings) + len(path_findings)
    print(f"\n{total} potential sensitive-data hit(s) - values withheld by design:\n")
    for finding in findings:
        print(finding.render())
    for path_finding in path_findings:
        print(path_finding.render())
    print(
        "\nOpen each path/line yourself. Path hits print no path, because the "
        "path is the sensitive value; locate them with your own tooling."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
