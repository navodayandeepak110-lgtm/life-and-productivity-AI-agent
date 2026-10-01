#!/usr/bin/env python3
"""
Temporal Intelligence Engine — Verification Tests
Tests: deadline alerts, effective priority boost, adaptive habit coaching,
       morning briefing integration, and /tasks deadline-aware sorting.
"""
import sys
sys.stdout.reconfigure(encoding="utf-8")

import ast
from datetime import date, timedelta
from memory_manager import MemoryManager

print("=" * 60)
print("TEMPORAL INTELLIGENCE ENGINE — VERIFICATION TESTS")
print("=" * 60)

# ── Syntax check ──────────────────────────────────────────────
for fname in ["memory_manager.py", "productivity_agent.py"]:
    with open(fname, "r", encoding="utf-8") as f:
        ast.parse(f.read())
    print(f"SYNTAX OK: {fname}")

import os
import shutil
from pathlib import Path

# Use temporary data dir to keep agent_data clean
test_dir = Path("test_temporal_data")
if test_dir.exists():
    shutil.rmtree(test_dir)
shutil.copytree("agent_data", test_dir)

try:
    m = MemoryManager(data_dir=str(test_dir))

    d_today      = date.today().isoformat()
    d_tomorrow   = (date.today() + timedelta(days=1)).isoformat()
    d_in_5       = (date.today() + timedelta(days=5)).isoformat()
    d_in_6       = (date.today() + timedelta(days=6)).isoformat()
    d_overdue    = (date.today() - timedelta(days=2)).isoformat()

    # Add temp test tasks
    t1 = m.add_task("Test CRITICAL task - due tomorrow",  priority="low",    deadline=d_tomorrow)
    t2 = m.add_task("Test OVERDUE task - 2 days late",    priority="low",    deadline=d_overdue)
    t3 = m.add_task("Test WARNING task - due in 6 days",  priority="medium", deadline=d_in_6)
    t4 = m.add_task("Test LOW no deadline",               priority="low",    deadline=None)

    print(f"\nAdded test tasks: #{t1['id']}, #{t2['id']}, #{t3['id']}, #{t4['id']}")

    # ── TEST 1: _days_until ───────────────────────────────────────
    assert m._days_until(d_tomorrow) == 1,  "_days_until(tomorrow) should be 1"
    assert m._days_until(d_overdue)  == -2, "_days_until(2 days ago) should be -2"
    assert m._days_until(d_today)    == 0,  "_days_until(today) should be 0"
    assert m._days_until(None)       is None
    print("PASS TEST 1: _days_until()")

    # ── TEST 2: _get_effective_priority ──────────────────────────
    p_low_tomorrow   = m._get_effective_priority({"priority": "low",    "deadline": d_tomorrow})
    p_high_no_dl     = m._get_effective_priority({"priority": "high",   "deadline": None})
    p_overdue_any    = m._get_effective_priority({"priority": "low",    "deadline": d_overdue})
    p_medium_in5     = m._get_effective_priority({"priority": "medium", "deadline": d_in_5})
    p_medium_in6     = m._get_effective_priority({"priority": "medium", "deadline": d_in_6})

    # low+tomorrow (1+3=4) > high+no_deadline (3)
    assert p_low_tomorrow > p_high_no_dl, (
        f"LOW+tomorrow({p_low_tomorrow}) should beat HIGH+no_deadline({p_high_no_dl})"
    )
    # overdue is always max (10)
    assert p_overdue_any == 10, f"Overdue should be 10, got {p_overdue_any}"
    # in-5-days gets +2 boost, in-6-days gets +1 boost
    assert p_medium_in5 > p_medium_in6, (
        f"medium+5d({p_medium_in5}) should beat medium+6d({p_medium_in6})"
    )
    print(f"PASS TEST 2: _get_effective_priority()  "
          f"low+tomorrow={p_low_tomorrow}  high+no_dl={p_high_no_dl}  overdue={p_overdue_any}")
