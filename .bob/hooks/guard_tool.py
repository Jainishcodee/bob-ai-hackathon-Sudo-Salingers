"""PreToolUse hook — a seat-belt for demo day. Tool-name agnostic: it inspects the tool INPUT.

Blocks (exit 2) any tool call that would:
  * touch src/.env            — it holds a real API key; reading it would leak the key into the model's context
  * delete the offline cache  — src/pharos/faers/cache is the committed demo; losing it on stage is fatal
  * rewrite history           — git push --force, git reset --hard, git clean -fd
  * edit the template validator — .github/workflows/validate.yml must not change (hackathon rule)
  * carry a secret            — same detector as the prompt guard

Everything else passes untouched. To switch all hooks off: delete or rename .bob/settings.json.
"""

from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import block, find_secret, read_event, strings_in  # noqa: E402

# ".env" as a path component — but not ".env.example", ".venv", ".environment"
ENV_PATH = re.compile(r"(?<![\w.])\.env(?![\w.])")
CACHE_PATH = re.compile(r"faers[\\/]+cache", re.I)
DELETE_VERB = re.compile(r"(?i)(\brm\b|\bdel\b|\berase\b|\brmdir\b|\brd\b|remove-item|shutil\.rmtree|\bunlink\b|os\.remove)")
GIT_DANGER = re.compile(r"(?i)git\s+(push\s+.*(--force\b|-f\b|--force-with-lease)|reset\s+--hard|clean\s+-[a-z]*f)")
VALIDATOR = re.compile(r"\.github[\\/]+workflows[\\/]+validate\.yml", re.I)
WRITE_TOOL = re.compile(r"(?i)(write|edit|apply|replace|insert|create|delete|patch)")


def main() -> None:
    event = read_event()
    tool = str(event.get("tool", ""))
    texts = strings_in(event.get("input", {}))
    blob = "\n".join(texts)

    if ENV_PATH.search(blob):
        block("this action touches src/.env, which holds a real API key. Use src/.env.example as the template; "
              "a human edits .env by hand.")
    if CACHE_PATH.search(blob) and DELETE_VERB.search(blob):
        block("this would delete the committed offline cache (src/pharos/faers/cache). "
              "Regenerate it with `python -m pharos build-cache` instead; never remove it.")
    if GIT_DANGER.search(blob):
        block("history-rewriting git command (force-push / reset --hard / clean -f). A human runs these, deliberately.")
    if VALIDATOR.search(blob) and WRITE_TOOL.search(tool):
        block(".github/workflows/validate.yml is owned by the hackathon template and must not be modified.")
    found = find_secret(blob)
    if found:
        block(f"the tool input contains {found}.")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        sys.exit(0)
    sys.exit(0)
