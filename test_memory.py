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
