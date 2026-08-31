"""Project-local adapter for the shared private management coordinator."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


SHARED_COORDINATOR = Path(__file__).resolve().parents[3] / "ai-skills" / "scripts" / "management_dialogue.py"


if __name__ == "__main__":
    raise SystemExit(subprocess.call([sys.executable, str(SHARED_COORDINATOR), *sys.argv[1:]]))
