"""Warm the openFDA cache for the demo drug set. Thin wrapper over `pharos build-cache`.

    python scripts/build_cache.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pharos.cli import app  # noqa: E402

if __name__ == "__main__":
    sys.argv = [sys.argv[0], "build-cache", *sys.argv[1:]]
    app()
