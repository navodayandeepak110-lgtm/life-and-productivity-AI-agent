#!/usr/bin/env python3
"""
Test Suite for AI Agent v3.1 Capabilities
- Browser Tools (web search, webpage reader, sensitive action guards)
- Email Tools (configuration checks, draft preview, safety rules)
- YouTube Tools (URL/ID extraction, ISO duration parsing, progress tracking, playlist math)
- Agent Tool Registration (all new tools present in agent)
"""

import os
import sys
import unittest
from pathlib import Path

# Ensure UTF-8 output
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from web_tools import (
    describe_sensitive_action,
    format_search_results,
    format_webpage_result,
    WEB_TOOLS_AVAILABLE
)
from email_tools import (
    check_email_configured,
    create_draft,
    format_email_list,
    format_email_content,
    _decode_header
)
from youtube_tools import (
    extract_video_id,
    extract_playlist_id,
    _iso_duration_to_seconds,
    _seconds_to_human,
    track_video_progress,
    get_video_progress,
    list_all_tracked_videos,
    format_video_progress,
    format_all_tracked
)


class TestWebTools(unittest.TestCase):
    def test_sensitive_action_guard(self):
        msg = describe_sensitive_action("login", "Logging into GitHub")
        self.assertIn("CONFIRMATION REQUIRED", msg)
        self.assertIn("Logging into an account", msg)
        self.assertIn("Logging into GitHub", msg)
