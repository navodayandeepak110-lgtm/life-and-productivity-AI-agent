#!/usr/bin/env python3
"""
Comprehensive Test Suite for Agent Memory System
Validates persistence, context injection, ID lookups, CRUD tools, journaling, and search.
"""

import os
import sys
import shutil
from pathlib import Path
from memory_manager import MemoryManager

# Reconfigure stdout for UTF-8 compatibility on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def run_tests():
    print("=" * 60)
    print("RUNNING AGENT MEMORY ENGINE TESTS")
    print("=" * 60)

    # Use a temporary test directory so we don't mess up live data
    test_dir = Path("test_agent_data")
    if test_dir.exists():
        shutil.rmtree(test_dir)

    # Copy existing files to test dir
    shutil.copytree("agent_data", test_dir)

    try:
        mem = MemoryManager(data_dir=str(test_dir))
        print("✓ MemoryManager initialized successfully.")

        # TEST 1: Check existing data loaded properly
        assert len(mem.goals) >= 2, "Goals failed to load"
        assert len(mem.tasks) >= 10, "Tasks failed to load"
        assert len(mem.projects) >= 1, "Projects failed to load"
        assert len(mem.habits) >= 2, "Habits failed to load"
        assert "Deepak" in mem.context.get("name", ""), "Context failed to load"
        print("✅ TEST 1 PASSED: Existing user data loaded correctly.")

        # TEST 2: Check context injection into prompt summary
        summary = mem.get_user_data_summary()
        assert "## USER PROFILE & PERSONAL CONTEXT" in summary, "Context section missing from summary"
        assert "Deepak" in summary, "User name missing from summary"
        assert "study_schedule" in summary.lower() or "study schedule" in summary.lower(), "Schedule missing from summary"
        assert "## ACTIVE GOALS" in summary, "Goals missing from summary"
        assert "## TASKS" in summary, "Tasks missing from summary"
        assert "## HABITS TRACKER" in summary, "Habits tracker missing from summary"
        print("✅ TEST 2 PASSED: Context and Profile properly injected into Prompt Summary.")
