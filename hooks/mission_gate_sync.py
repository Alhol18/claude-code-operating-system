#!/usr/bin/env python3
"""Mission ↔ Gate drift check: SessionStart hook.

Compares missions (missions/*.md) with live gates (cadence/gates.json) by exact gate id
and goal states. Prints brief drift report only when there is something to show. Reads
local files directly: no server needed. Pure stdlib. Never fails the session (exit 0 always).

Drift detection:
  1. Gate CLOSED in gates.json, but active mission still holds it as blocker: update mission.
  2. Gate OPEN, but no active mission tracks it: add to mission (avoid losing it).
  3. Active mission where ALL goals are [DONE]: time to set status: done.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MISSIONS = ROOT / "missions"
GATES = ROOT / "cadence" / "gates.json"

GOAL_RE = re.compile(r"^##\s+(\d+)\.\s*(.*)$", re.MULTILINE)
STATE_RE = re.compile(r"^\[(DONE|IN PROGRESS|PAUSED|BLOCKED|BLOCKER)\]", re.IGNORECASE)
# Regex matching Ukrainian "gate X" references (гейт/гейти followed by gate id)
GATE_REF_RE = re.compile(r"гейт[иі]?\s+([a-z][a-z0-9-]+)", re.IGNORECASE)
FM_RE = re.compile(r"^(id|status|title):\s*(.+)$", re.MULTILINE)


DONE_RE = re.compile(r"\[DONE\]", re.IGNORECASE)


def scan_gate_refs(text):
    """Separates gate mentions into 'mission still holds' and 'just mentioned'.

    A mission that correctly closed a goal still names the gate in a line like
    "[DONE] ... (gate X, closed 2026-08-14)". Naive text search would count this
    as a blocker and remind forever: drift could not close without erasing history.
    So a ref is counted as held only when neither its line nor its section heading
    is marked [DONE].
    """
    held, mentioned = set(), set()
    section_done = False
    for line in text.splitlines():
        heading = GOAL_RE.match(line)
        if heading:
            section_done = bool(DONE_RE.search(line))
        line_done = section_done or bool(DONE_RE.search(line))
        for gid in GATE_REF_RE.findall(line):
            gid = gid.lower()
            mentioned.add(gid)
            if not line_done:
                held.add(gid)
    return held, mentioned


def parse_missions():
    out = []
    if not MISSIONS.exists():
        return out
    for p in sorted(MISSIONS.glob("*.md")):
        if p.name.startswith("_"):
            continue
        text = p.read_text(encoding="utf-8")
        fm = dict(FM_RE.findall(text[: text.find("\n---", 3) + 1] if "---" in text else text))
        goals = [(int(n), STATE_RE.match(rest.strip())) for n, rest in GOAL_RE.findall(text)]
        states = [(m.group(1).upper() if m else "TODO") for _, m in goals]
        held, mentioned = scan_gate_refs(text)
        out.append({
            "id": fm.get("id", p.stem).strip(),
            "status": fm.get("status", "active").strip(),
            "gates": held,
            "mentions": mentioned,
            "states": states,
        })
    return out


def load_gates():
    try:
        data = json.loads(GATES.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set(), set()
    # Schema v2: state in 'state' field, closed is exactly "closed". Old files may
    # still have binary 'status'. Read both so hook stays working during migration.
    def is_closed(g):
        if "state" in g:
            return g["state"] == "closed"
        return g.get("status") != "open"

    open_ids = {g["id"] for g in data.get("gates", []) if not is_closed(g)}
    closed_ids = {g["id"] for g in data.get("gates", []) if is_closed(g)}
    return open_ids, closed_ids


def main():
    missions = [m for m in parse_missions() if m["status"] == "active"]
    open_ids, closed_ids = load_gates()
    if not missions and not open_ids:
        return

    # Coverage counted by ALL mentions: open gate named in mission once, not lost,
    # even if adjacent goal is already done.
    referenced = set().union(*(m["mentions"] for m in missions)) if missions else set()

    # 1. closed gate still held by a mission
    stale = []
    for m in missions:
        for gid in sorted(m["gates"] & closed_ids):
            stale.append((m["id"], gid))
    # 2. open gate no mission tracks
    untracked = sorted(open_ids - referenced)
    # 3. mission all-DONE but still active
    complete = [m["id"] for m in missions if m["states"] and all(s == "DONE" for s in m["states"])]

    if not (stale or untracked or complete):
        print(f"🔄 Missions↔Gates: in sync ({len(open_ids)} open, all tracked, {len(missions)} missions)")
        return

    lines = ["🔄 MISSION↔GATE DRIFT: verify and update missions/*.md:"]
    for mid, gid in stale:
        lines.append(f"  ✅ gate '{gid}' CLOSED, but mission '{mid}' still holds it: mark goal done")
    for gid in untracked:
        lines.append(f"  ⚠️ gate '{gid}' OPEN, not in any mission: add to appropriate mission")
    for mid in complete:
        lines.append(f"  🏁 mission '{mid}': all goals DONE: set status: done")
    print("\n".join(lines))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # hook never fails the session
        print(f"(mission_gate_sync skipped: {e})", file=sys.stderr)
    sys.exit(0)
