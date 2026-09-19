"""Local self-test for the Pharos Bob hooks: feeds each hook the JSON Bob would send and checks the exit code.

    python .bob/hooks/_selftest.py

Exit code 0 = allow, 2 = block. This proves the scripts' logic; it does not prove Bob calls them —
that needs .bob/settings.json enabled inside Bob.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from _common import local_secret_values  # noqa: E402


def run(script: str, event: dict) -> int:
    p = subprocess.run([sys.executable, str(HERE / script)], input=json.dumps(event), capture_output=True, text=True, timeout=20)
    return p.returncode


real = local_secret_values()
CASES = [
    ("guard_prompt.py", {"prompt": "run a signal assessment for metformin"}, 0, "ordinary prompt"),
    ("guard_prompt.py", {"prompt": "use OPENFDA_API_KEY=abcdefghijklmnopqrstuvwxyz0123456789ABCD"}, 2, "prompt with an API key assignment"),
    ("guard_prompt.py", {"prompt": "token ghp_" + "a" * 36}, 2, "prompt with a GitHub token"),
    ("guard_prompt.py", {"prompt": "PHAROS_OFFLINE=1 please"}, 0, "harmless env var"),
    ("guard_tool.py", {"tool": "read_file", "input": {"path": "src/.env"}}, 2, "read src/.env"),
    ("guard_tool.py", {"tool": "read_file", "input": {"path": "src/.env.example"}}, 0, "read .env.example"),
    ("guard_tool.py", {"tool": "execute_command", "input": {"command": ".venv\\Scripts\\activate"}}, 0, ".venv is not .env"),
    ("guard_tool.py", {"tool": "execute_command", "input": {"command": "rm -rf src/pharos/faers/cache"}}, 2, "delete the cache"),
    ("guard_tool.py", {"tool": "execute_command", "input": {"command": "Remove-Item src\\pharos\\faers\\cache\\*.json"}}, 2, "delete the cache (PowerShell)"),
    ("guard_tool.py", {"tool": "execute_command", "input": {"command": "python -m pharos build-cache"}}, 0, "rebuild the cache"),
    ("guard_tool.py", {"tool": "execute_command", "input": {"command": "git push --force origin main"}}, 2, "force push"),
    ("guard_tool.py", {"tool": "execute_command", "input": {"command": "git reset --hard HEAD~3"}}, 2, "reset --hard"),
    ("guard_tool.py", {"tool": "execute_command", "input": {"command": "git push"}}, 0, "normal push"),
    ("guard_tool.py", {"tool": "write_to_file", "input": {"path": ".github/workflows/validate.yml", "content": "x"}}, 2, "edit the template validator"),
    ("guard_tool.py", {"tool": "read_file", "input": {"path": ".github/workflows/validate.yml"}}, 0, "read the validator"),
    ("guard_tool.py", {"tool": "use_mcp_tool", "input": {"server_name": "pharos", "tool_name": "scan_signals", "arguments": {"drug": "metformin"}}}, 0, "a pharos MCP call"),
    ("session_start.py", {"event": "SessionStart", "session_id": "t"}, 0, "session briefing"),
]
if real:
    CASES.append(("guard_prompt.py", {"prompt": "here it is: " + real[0]}, 2, "prompt containing the REAL key from src/.env (value not shown)"))

failed = 0
for script, event, want, label in CASES:
    got = run(script, event)
    ok = got == want
    failed += not ok
    print(f"{'ok  ' if ok else 'FAIL'}  {script:<17} exit {got} (want {want})  {label}")
print(f"\n{len(CASES) - failed}/{len(CASES)} passed")
sys.exit(1 if failed else 0)
