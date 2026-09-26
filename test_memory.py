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

        # TEST 5: Habit tracking & streak with exact ID
        habit_1 = mem.habits[0]
        initial_streak = habit_1.get("streak", 0)
        logged_habit = mem.log_habit(habit_1["id"], completed=True)
        assert logged_habit["streak"] == initial_streak + 1
        print("✅ TEST 5 PASSED: Habit streak and logging verified.")

        # TEST 6: Episodic Memory (Daily Journal)
        entry = mem.add_journal_entry(
            summary="Studied Java Collections & solved 3 LeetCode problems",
            wins=["Solved Two Sum in O(N)", "Understood HashMap internals"],
            blockers="Felt tired in the evening",
            hours_studied=5.5,
            focus_tomorrow="Revise Multithreading"
        )
        assert entry["id"] >= 1
        assert len(mem.get_recent_journal(7)) >= 1
        print("✅ TEST 6 PASSED: Episodic daily journal logging & retrieval verified.")

        # TEST 7: Semantic Memory / Notes
        note = mem.save_note(
            title="Java HashMap Time Complexity",
            content="get() and put() are O(1) average time, O(n) worst case with collisions, reduced to O(log n) with red-black trees in Java 8+.",
            category="java",
            tags=["java", "collections", "dsa"]
        )
        assert note["id"] >= 1

        found_notes = mem.search_notes(query="red-black", tag="java")
        assert len(found_notes) == 1
        assert "Java HashMap" in found_notes[0]["title"]
        print("✅ TEST 7 PASSED: Knowledge Base notes & search verified.")

        # TEST 8: Universal Memory Search
        global_res = mem.search_all_memory("GATE")
        assert "goals" in global_res or "tasks" in global_res or "context" in global_res
        print("✅ TEST 8 PASSED: Universal multi-store search verified.")

        # TEST 9: Session Persistence & Rolling History
        fake_history = [
            {"role": "user", "content": "Hello!"},
            {"role": "assistant", "content": "Hi Deepak! How can I help you today?"},
            {"role": "user", "content": "What are my priorities today?"},
            {"role": "assistant", "content": "Your top priority is Java OOP revision."}
        ]
        mem.save_session_history(fake_history)

        mem_session_reload = MemoryManager(data_dir=str(test_dir))
        latest_msgs = mem_session_reload.load_latest_session()
        assert len(latest_msgs) == 4
        assert latest_msgs[0]["content"] == "Hello!"
        print("✅ TEST 9 PASSED: Session history persistence verified.")

        # TEST 10: Proactive Morning Briefing & Fast CLI Formatters
        briefing = mem.get_morning_briefing()
        assert any(g in briefing.upper() for g in ["GOOD MORNING", "GOOD AFTERNOON", "GOOD EVENING"]) or "BRIEFING" in briefing.upper()
        assert "TOP PRIORITIES" in briefing.upper()
        assert "HABITS" in briefing.upper()
        tasks_fmt = mem.get_tasks_formatted("pending")
        assert "PENDING TASKS" in tasks_fmt
        habits_fmt = mem.get_habits_formatted()
        assert "HABIT TRACKER" in habits_fmt
        print("✅ TEST 10 PASSED: Proactive Morning Briefing & Fast CLI formatters verified.")

        # TEST 11: Smart Dynamic Context Pruning (Token Optimization)
        pruned_tasks = mem.get_pruned_context_summary("what are my tasks for today?")
        assert "PENDING TASKS" in pruned_tasks
        pruned_habits = mem.get_pruned_context_summary("show my habits streak")
        assert "HABITS" in pruned_habits
        pruned_notes = mem.get_pruned_context_summary("show youtube playlist links")
        assert "RELEVANT NOTES" in pruned_notes
        print("✅ TEST 11 PASSED: Smart Dynamic Context Pruning verified.")

        print("\n" + "=" * 60)
        print("🎉 ALL 11 MEMORY ENGINE TESTS PASSED SUCCESSFULLY!")
        print("=" * 60)

    finally:
        if test_dir.exists():
            shutil.rmtree(test_dir)


if __name__ == "__main__":
    run_tests()
