"""UserPromptSubmit hook — stop a secret from ever reaching the model.

If the prompt contains an API key, a private key, a GitHub token, or the *actual* value of a key
stored in src/.env, exit 2: Bob refuses to send the prompt and shows the reason. The real key is
compared locally inside this process; it is never printed or logged.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import block, find_secret, read_event  # noqa: E402


def main() -> None:
    event = read_event()
    found = find_secret(str(event.get("prompt", "")))
    if found:
        block(f"your prompt contains {found}. Secrets belong in src/.env (git-ignored), never in a chat. "
              "Remove it and send again.")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        sys.exit(0)
    sys.exit(0)
