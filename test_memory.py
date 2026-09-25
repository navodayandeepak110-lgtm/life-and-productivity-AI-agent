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

        # TEST 3: Exact ID matching in Task Completion (Fixing the indexing bug)
        # Find any pending task from the dataset
        pending_task = next((t for t in mem.tasks if t.get("status") == "pending"), None)
        assert pending_task is not None, "No pending tasks available for completion test"
        target_id = pending_task["id"]

        completed_t = mem.complete_task(target_id)
        assert completed_t is not None
        assert completed_t["id"] == target_id
        assert completed_t["status"] == "completed"
        assert "completed_at" in completed_t

        # Reload memory to verify disk persistence
        mem_reloaded = MemoryManager(data_dir=str(test_dir))
        t_reloaded = next((t for t in mem_reloaded.tasks if t["id"] == target_id), None)
        assert t_reloaded["status"] == "completed"
        print(f"✅ TEST 3 PASSED: ID-based task completion & persistence verified for Task #{target_id}.")

        # TEST 4: Task CRUD (Add, Update, Search, Delete)
        new_task = mem.add_task(
            title="Test Task Priority",
            description="Testing memory",
            priority="urgent",
            deadline="Tomorrow"
        )
        assert new_task["id"] > 11
        assert new_task["priority"] == "urgent"

        updated_task = mem.update_task(new_task["id"], priority="low", title="Updated Test Title")
        assert updated_task["priority"] == "low"
        assert updated_task["title"] == "Updated Test Title"

        search_res = mem.search_tasks(query="Updated Test")
        assert len(search_res) == 1
        assert search_res[0]["id"] == new_task["id"]

        del_ok = mem.delete_task(new_task["id"])
        assert del_ok is True
        assert next((t for t in mem.tasks if t["id"] == new_task["id"]), None) is None
        print("✅ TEST 4 PASSED: Task CRUD and search verified.")
