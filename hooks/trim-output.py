#!/usr/bin/env python3
"""Cuts noisy output: all error lines plus last N lines.
Called from wrapper set by hooks/trim-noisy-bash."""
import sys, re

TAIL = 30
ERR = re.compile(
    r"\b(error|ERROR|Error|FAIL|FAILED|failed|Traceback|Exception|"
    r"fatal|FATAL|panic:|npm ERR!|SyntaxError|TypeError|AssertionError|"
    r"warning:|WARN\b|E:\s|\berr\b)", re.I)

path = sys.argv[1]
try:
    lines = open(path, errors="replace").read().splitlines()
except OSError:
    sys.exit(0)

n = len(lines)
if n <= TAIL:
    print("\n".join(lines))
    sys.exit(0)

head_err = [(i, l) for i, l in enumerate(lines[:-TAIL]) if ERR.search(l)]
if head_err:
    print(f"[trimmed {n - TAIL - len(head_err)} lines · {len(head_err)} error/warn lines kept]")
    for i, l in head_err[:60]:
        print(f"{i+1}: {l}")
    if len(head_err) > 60:
        print(f"... +{len(head_err)-60} more error lines")
    print(f"--- last {TAIL} lines ---")
else:
    print(f"[trimmed {n - TAIL} lines, no errors found · last {TAIL}]")
print("\n".join(lines[-TAIL:]))
