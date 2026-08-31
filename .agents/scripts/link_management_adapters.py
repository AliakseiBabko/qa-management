"""Project-local adapter for the shared management-skill linker."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


SHARED_LINKER = Path(__file__).resolve().parents[3] / "ai-skills" / "scripts" / "link_management_adapters.py"


if __name__ == "__main__":
    raise SystemExit(subprocess.call([sys.executable, str(SHARED_LINKER), *sys.argv[1:]]))
