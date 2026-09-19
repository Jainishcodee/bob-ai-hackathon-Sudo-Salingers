"""Shared helpers for the Pharos Bob hooks. Standard library only; must never raise.

Hook contract (IBM Bob lifecycle hooks): the event arrives as JSON on stdin. Exit 0 = carry on.
Exit 2 = BLOCK (honoured for UserPromptSubmit and PreToolUse only). Any other non-zero exit is
logged by Bob and ignored — so a crash here can never break a session, it just stops protecting it.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent  # repo root (…/.bob/hooks/_common.py)
ENV_FILE = ROOT / "src" / ".env"

SECRET_PATTERNS = [
    # no leading \b: in "OPENFDA_API_KEY" the underscore before "API" is a word character
    (re.compile(r"(?i)api[_-]?key\s*[=:]\s*['\"]?[A-Za-z0-9_\-]{20,}"), "an API key assignment"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "a private key"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"), "a GitHub token"),
    (re.compile(r"\bgithub_pat_[A-Za-z0-9_]{30,}\b"), "a GitHub fine-grained token"),
]


def read_event() -> dict:
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except Exception:
        return {}


def local_secret_values() -> list[str]:
    """Real secret values from src/.env, so we can catch them even with no 'api_key=' prefix.
    Read locally by the hook only — never printed, never sent to the model."""
    vals: list[str] = []
    try:
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            val = val.strip().strip("'\"")
            if len(val) >= 16 and any(t in key.upper() for t in ("KEY", "TOKEN", "SECRET", "PASSWORD")):
                vals.append(val)
    except Exception:
        pass
    return vals


def find_secret(text: str) -> str | None:
    """Return a human description of the first secret found in text, else None."""
    if not text:
        return None
    for val in local_secret_values():
        if val in text:
            return "the real value of a key from src/.env"
    for pattern, what in SECRET_PATTERNS:
        if pattern.search(text):
            return what
    return None


def redact(text: str) -> str:
    for val in local_secret_values():
        text = text.replace(val, "<redacted>")
    for pattern, _ in SECRET_PATTERNS:
        text = pattern.sub("<redacted>", text)
    return text


def strings_in(obj) -> list[str]:
    """Every string anywhere inside a JSON-like structure."""
    out: list[str] = []
    if isinstance(obj, str):
        out.append(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            out.extend(strings_in(v))
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            out.extend(strings_in(v))
    return out


def block(reason: str) -> None:
    msg = f"[pharos hook] BLOCKED: {reason}"
    print(msg)                    # some hosts surface stdout …
    print(msg, file=sys.stderr)   # … others stderr. Say it on both.
    sys.exit(2)
