"""Create the machine-local skill-discovery adapter for Claude Code.

`.agents/skills/` is the single canonical skill source in this repo (see
AGENTS.md, Skill Location). Codex and Antigravity read it directly and need
no adapter. Claude Code looks for skills under `.claude/skills/`, so this
script creates `.claude/skills` as a *link* to `.agents/skills` - a Windows
directory junction, or a POSIX relative symlink. Nothing is ever copied or
mirrored: one canonical tree, one pointer at it.

The adapter is machine-local and intentionally untracked (`.gitignore`), so a
clean clone works without it - `validate_repo.py` does not require it. Only
Claude Code's skill discovery does.

Modes:
  (default)  create the adapter if missing; succeed silently if it is already
             correct. Never deletes, replaces, or overwrites an existing path.
  --check    report whether the adapter resolves to the canonical directory.
             Creates and modifies nothing. Exit 0 only when correct.

Usage:
  python .agents/scripts/setup_agent_adapters.py
  python .agents/scripts/setup_agent_adapters.py --check
"""

from __future__ import annotations

import argparse
import io
import os
import subprocess
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parents[2]

CANONICAL_PARTS = (".agents", "skills")
ADAPTER_PARTS = (".claude", "skills")

# Relative POSIX symlink target, resolved from inside `.claude/`.
POSIX_LINK_TARGET = "../.agents/skills"

CANONICAL_LABEL = "/".join(CANONICAL_PARTS)
ADAPTER_LABEL = "/".join(ADAPTER_PARTS)

# Adapter states. Only OK is a success; every other state is a refusal that
# names its own remediation rather than touching the existing path.
OK = "ok"
MISSING = "missing"
DANGLING = "dangling"
MISDIRECTED = "misdirected"
REAL_DIRECTORY = "real_directory"
REAL_FILE = "real_file"


class AdapterError(RuntimeError):
    """A refusal or a failed creation, already phrased for the operator."""


def canonical_dir(repo: Path) -> Path:
    return repo.joinpath(*CANONICAL_PARTS)


def adapter_path(repo: Path) -> Path:
    return repo.joinpath(*ADAPTER_PARTS)


def _is_windows() -> bool:
    """Seam so both platform branches stay testable on either OS."""
    return os.name == "nt"


def _link_destination(path: Path) -> Path | None:
    """Absolute destination of the link at `path`, or None if it is not a link.

    Covers POSIX symlinks and Windows directory junctions (which
    `os.path.islink` reports as False). A dangling link still returns a
    destination; existence is judged separately by the caller.
    """
    is_link = os.path.islink(path)
    if not is_link and hasattr(Path, "is_junction"):
        try:
            is_link = path.is_junction()
        except OSError:
            is_link = False
    if not is_link:
        return None
    try:
        raw = os.readlink(path)
    except OSError:
        return None
    # Windows junctions read back in extended-length form (\\?\C:\...);
    # strip the prefix so the destination compares equal to a normal path.
    if raw.startswith("\\\\?\\"):
        raw = raw[4:]
    target = Path(raw)
    if not target.is_absolute():
        target = path.parent / target
    return Path(os.path.normpath(target))


def classify_adapter(adapter: Path, canonical: Path) -> str:
    """Return one of the module's state constants for the adapter path."""
    if not os.path.lexists(adapter):
        return MISSING
    destination = _link_destination(adapter)
    if destination is None:
        return REAL_DIRECTORY if adapter.is_dir() else REAL_FILE
    if not adapter.exists():
        return DANGLING
    if destination.resolve() != canonical.resolve():
        return MISDIRECTED
    return OK


def remediation(state: str) -> str:
    """Precise, repository-relative remediation text for a non-OK state.

    Every message tells the operator to move or remove the offending path
    themselves - this script never does it for them.
    """
    if state == MISSING:
        return (
            f"{ADAPTER_LABEL} does not exist. "
            f"Run: python .agents/scripts/setup_agent_adapters.py"
        )
    if state == DANGLING:
        return (
            f"{ADAPTER_LABEL} is a dangling link (its target no longer exists). "
            f"Remove it manually, then re-run setup to point it at {CANONICAL_LABEL}."
        )
    if state == MISDIRECTED:
        return (
            f"{ADAPTER_LABEL} is a link to somewhere other than {CANONICAL_LABEL}. "
            f"Remove it manually, then re-run setup. Refusing to repoint an "
            f"adapter this script did not create."
        )
    if state == REAL_DIRECTORY:
        return (
            f"{ADAPTER_LABEL} is a real directory, not a link. It may hold skill "
            f"copies that would shadow the canonical {CANONICAL_LABEL}. Move its "
            f"contents into {CANONICAL_LABEL} if they are wanted, remove the "
            f"directory, then re-run setup."
        )
    if state == REAL_FILE:
        return (
            f"{ADAPTER_LABEL} is a file, not a link. Remove it manually, "
            f"then re-run setup."
        )
    raise ValueError(f"No remediation for state {state!r}")


def _create_windows_junction(adapter: Path, canonical: Path) -> None:
    """Directory junction via `mklink /J` - works without Administrator rights.

    A symlink would need elevation or Developer Mode; a junction does not,
    and resolves identically for skill discovery.
    """
    completed = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(adapter), str(canonical)],
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        # Deliberately not echoing mklink's output: it repeats absolute
        # local paths, and the state check below reports the real problem.
        raise AdapterError(
            f"Could not create the {ADAPTER_LABEL} directory junction "
            f"(mklink exit {completed.returncode})."
        )


def _create_link(adapter: Path, canonical: Path) -> None:
    adapter.parent.mkdir(parents=True, exist_ok=True)
    if _is_windows():
        _create_windows_junction(adapter, canonical)
    else:
        os.symlink(POSIX_LINK_TARGET, adapter, target_is_directory=True)


def setup_adapter(repo: Path) -> str:
    """Create the adapter if missing. Returns a short outcome label.

    Idempotent: an already-correct adapter is left untouched. Any other
    pre-existing path is a refusal, never an overwrite.
    """
    canonical = canonical_dir(repo)
    if not canonical.is_dir():
        raise AdapterError(
            f"Canonical skill directory {CANONICAL_LABEL} is missing. "
            f"Run this from a checkout of the repository."
        )
    adapter = adapter_path(repo)
    state = classify_adapter(adapter, canonical)
    if state == OK:
        return "already-correct"
    if state != MISSING:
        raise AdapterError(remediation(state))

    _create_link(adapter, canonical)

    verified = classify_adapter(adapter, canonical)
    if verified != OK:
        raise AdapterError(
            f"Created {ADAPTER_LABEL} but it does not resolve to "
            f"{CANONICAL_LABEL} (state: {verified})."
        )
    return "created"


def check_adapter(repo: Path) -> tuple[bool, str]:
    """Read-only adapter verification. Creates and modifies nothing."""
    canonical = canonical_dir(repo)
    if not canonical.is_dir():
        return False, f"Canonical skill directory {CANONICAL_LABEL} is missing."
    state = classify_adapter(adapter_path(repo), canonical)
    if state == OK:
        return True, f"{ADAPTER_LABEL} -> {CANONICAL_LABEL} (canonical)"
    return False, remediation(state)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Create or verify the machine-local Claude Code skill adapter "
            f"({ADAPTER_LABEL} -> {CANONICAL_LABEL})."
        )
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify the adapter without creating or modifying anything.",
    )
    args = parser.parse_args(argv)

    if args.check:
        ok, message = check_adapter(REPO)
        print(("OK: " if ok else "FAIL: ") + message)
        return 0 if ok else 1

    try:
        outcome = setup_adapter(REPO)
    except AdapterError as exc:
        print(f"FAIL: {exc}")
        return 1
    if outcome == "already-correct":
        print(f"OK: {ADAPTER_LABEL} already points at {CANONICAL_LABEL}.")
    else:
        print(f"OK: created {ADAPTER_LABEL} -> {CANONICAL_LABEL}.")
    print(
        f"{CANONICAL_LABEL} stays canonical; {ADAPTER_LABEL} is machine-local "
        f"and untracked."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
