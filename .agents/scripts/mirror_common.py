import subprocess
import sys
from pathlib import Path

def mirror_git(mirror: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(mirror), *args],
                          capture_output=True, text=True, encoding="utf-8")

def mirror_git_bytes(mirror: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(mirror), *args],
                          capture_output=True)

def assert_private_mirror(mirror: Path, data_root: Path, init_allowed: bool = False):
    """
    Enforces the private mirror safety boundary:
    1. Resolves junctions/symlinks.
    2. Rejects remotes.
    3. Rejects if located at/inside the public skills repository.
    4. Rejects if located inside the synchronized Drive workspace.
    5. Before initialization: validates the resolved candidate and existing parent boundaries.
    6. After initialization: requires `git rev-parse --show-toplevel` to equal the requested mirror.
    """
    try:
        mirror_resolved = mirror.resolve()
    except Exception as e:
        sys.exit(f"Mirror guard failed: cannot resolve mirror path {mirror}: {e}")

    skills_repo = Path(__file__).resolve().parents[2]

    if mirror_resolved == skills_repo or skills_repo in mirror_resolved.parents:
        sys.exit(f"Mirror guard failed: mirror {mirror_resolved} is inside the public skills repository {skills_repo}")

    try:
        data_root_resolved = data_root.resolve()
        if mirror_resolved == data_root_resolved or data_root_resolved in mirror_resolved.parents:
            sys.exit(f"Mirror guard failed: mirror {mirror_resolved} is inside the synchronized Drive workspace {data_root_resolved}")
    except Exception:
        pass

    if not (mirror_resolved / ".git").exists():
        if not init_allowed:
            sys.exit(f"Mirror guard failed: mirror {mirror_resolved} is not initialized and init_allowed is False")

        if mirror_resolved.exists() and any(mirror_resolved.iterdir()):
            sys.exit(f"Mirror guard failed: requested mirror path {mirror_resolved} exists and is not empty before initialization")
        return

    # Check toplevel
    toplevel_res = mirror_git(mirror_resolved, "rev-parse", "--show-toplevel")
    if toplevel_res.returncode != 0:
        sys.exit(f"Mirror guard failed: git rev-parse failed for {mirror_resolved}:\n{toplevel_res.stderr}")

    toplevel = Path(toplevel_res.stdout.strip()).resolve()
    if toplevel != mirror_resolved:
        sys.exit(f"Mirror guard failed: git toplevel {toplevel} does not match requested mirror {mirror_resolved}")

    # Check remotes
    remotes_res = mirror_git(mirror_resolved, "remote", "-v")
    if remotes_res.stdout.strip():
        sys.exit(f"Mirror guard failed: remotes found in {mirror_resolved}. "
                 "If this is a disaster-recovery clone from a bundle, run 'git remote remove origin'.")
