"""SessionStart hook — whatever this prints is written into Bob's context.

Gives every new Bob session a 10-line briefing: where the project stands right now, and the three
rules that matter most. Fast by design (git only, no tests): budget < 1 second.
"""

from __future__ import annotations

import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import ROOT, read_event  # noqa: E402


def git(*args: str) -> str:
    try:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=3).stdout.strip()
    except Exception:
        return ""


def main() -> None:
    read_event()
    branch = git("rev-parse", "--abbrev-ref", "HEAD") or "?"
    last = git("log", "-1", "--format=%h %s (%cr)") or "?"
    dirty = len([l for l in git("status", "--short").splitlines() if l.strip()])
    cache = ROOT / "src" / "pharos" / "faers" / "cache"
    n_cache = len(list(cache.glob("*.json"))) if cache.exists() else 0
    n_tests = sum(1 for p in (ROOT / "src" / "tests").glob("test_*.py"))
    offline = os.environ.get("PHAROS_OFFLINE", "").strip().lower() in {"1", "true", "yes", "on"}

    print(
        "PHAROS PROJECT BRIEFING (from .bob/hooks/session_start.py)\n"
        f"- Repo: branch {branch}; last commit: {last}; uncommitted files: {dirty}\n"
        f"- Offline demo cache: {n_cache} openFDA responses; PHAROS_OFFLINE is {'ON' if offline else 'off'}\n"
        f"- Tests: {n_tests} test files in src/tests — run `python -m pytest tests -q` from src/ before calling anything done\n"
        "- Pharos = evidence layer (deterministic Python, MCP server `pharos`, 9 tools). You = reasoning layer.\n"
        "- Rule 1: every FAERS number you state must come from a pharos tool call in this conversation.\n"
        "- Rule 2: disproportionality is a reporting association — never say 'causes', never say 'safe'.\n"
        "- Rule 3: never read or edit src/.env; never delete src/pharos/faers/cache; statistics changes need a hand-computed test.\n"
        "- Custom modes: 'PV Analyst' (read-only + pharos tools), 'Regulatory Reviewer'. Commands: /signal /hidden /emerge /label /dossier /preflight /progress."
    )


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
