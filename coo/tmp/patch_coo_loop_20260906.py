"""Patch coo-loop-v3.sh / coo-loop-v4.sh do_execute (2026-09-06), take 2.

Small line-level fragments instead of one giant block:
1. Executor launched without --auto -> num_turns:0 permission-gate exits
   (sessions 5634a6ec / 514c7e4b on 20260905-ntreis-fm23).
2. Session-continuity grepped "sessionId" but droid JSON emits "session_id",
   so executor_session: was never persisted.

Each replace asserts exactly-1 occurrence (or already-applied); backup first.
"""
from __future__ import annotations

import shutil
from pathlib import Path

REPO = Path(r"C:\Users\lkmot\factory-context\code\fleet-triage\coo")
STAMP = "20260906"

REPLACES = [
    # anchor: add EXEC_AUTO right after "local rc=0" in do_execute
    (
        '  local rc=0\n  if [ -n "$sid" ]',
        '  local rc=0\n'
        '  # executor needs explicit --auto or it exits num_turns:0 at the permission gate\n'
        '  # (2026-09-06: two FM23 verify cycles died on "insufficient permission")\n'
        '  local EXEC_AUTO="${COO_EXECUTE_AUTO:-medium}"\n'
        '  if [ -n "$sid" ]',
    ),
    # RELOOP branch launch
    (
        'run_droid execute exec -o json -s "$sid"',
        'run_droid execute exec -o json --auto "$EXEC_AUTO" -s "$sid"',
    ),
    # fresh-run branch launch
    (
        'run_droid execute exec -o json -f "$f"',
        'run_droid execute exec -o json --auto "$EXEC_AUTO" -f "$f"',
    ),
    # session_id capture: snake_case first
    (
        r'''newsid=$(grep -o '"sessionId"[[:space:]]*:[[:space:]]*"[^"]*"' ''',
        r'''newsid=$(grep -o '"session_id"[[:space:]]*:[[:space:]]*"[^"]*"' ''',
    ),
    # fallback line for older droid builds emitting camelCase
    (
        r"""| sed 's/.*:\s*"//;s/"$//')
  if [ -n "$newsid" ]; then""",
        r"""| sed 's/.*:\s*"//;s/"$//')
  [ -z "$newsid" ] && newsid=$(grep -o '"sessionId"[[:space:]]*:[[:space:]]*"[^"]*"' coo/tmp/"$id".exec.log 2>/dev/null | head -1 | sed 's/.*:\s*"//;s/"$//')
  if [ -n "$newsid" ]; then""",
    ),
]

for name in ("coo-loop-v4.sh", "coo-loop-v3.sh"):
    path = REPO / name
    data = path.read_text(encoding="utf-8")
    original = data
    for i, (old, new) in enumerate(REPLACES):
        c_old, c_new = data.count(old), data.count(new)
        if c_old == 0 and c_new >= 1:
            print(f"{name} R{i}: already applied")
            continue
        if c_old != 1:
            raise SystemExit(f"ABORT {name} R{i}: expected 1 old occurrence, found {c_old}")
        data = data.replace(old, new, 1)
        print(f"{name} R{i}: replaced")
    if data != original:
        backup = path.with_suffix(f".sh.bak-{STAMP}")
        shutil.copy2(path, backup)
        with open(path, "r+b") as fd:  # in-place write; rename is blocked by live loop
            fd.write(data.encode("utf-8"))
            fd.truncate()
        print(f"PATCHED {name} (backup: {backup.name})")
    else:
        print(f"NOCHANGE {name}")
