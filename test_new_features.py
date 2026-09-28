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

    def test_search_results_formatting(self):
        sample = {
            "query": "python tutorial",
            "source": "DuckDuckGo",
            "results": [
                {"title": "Python Basics", "url": "https://python.org", "snippet": "Learn python"}
            ]
        }
        text = format_search_results(sample)
        self.assertIn("Python Basics", text)
        self.assertIn("https://python.org", text)

    def test_webpage_formatting(self):
        sample = {
            "title": "Example Page",
            "source": "https://example.com",
            "text": "This is example body text.",
            "truncated": False
        }
        text = format_webpage_result(sample)
        self.assertIn("Example Page", text)
        self.assertIn("This is example body text.", text)


class TestEmailTools(unittest.TestCase):
    def test_email_config_unconfigured(self):
        is_configured, msg = check_email_configured()
        if not os.getenv("EMAIL_ADDRESS") or not os.getenv("EMAIL_APP_PASSWORD"):
            self.assertFalse(is_configured)

    def test_create_draft_unconfigured_fails_safely(self):
        res = create_draft("test@example.com", "Hello", "Body content")
        if not os.getenv("EMAIL_ADDRESS"):
            self.assertIn("error", res)

    def test_header_decoding(self):
        self.assertEqual(_decode_header("Simple Subject"), "Simple Subject")
        self.assertEqual(_decode_header(""), "")


class TestYouTubeTools(unittest.TestCase):
    def test_video_id_extraction(self):
        urls = [
            ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://www.youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://www.youtube.com/shorts/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ]
        for url, expected in urls:
            self.assertEqual(extract_video_id(url), expected, f"Failed on {url}")

    def test_playlist_id_extraction(self):
        urls = [
            ("https://www.youtube.com/playlist?list=PLrAXtmErZgOdP_8GztsuKi9f5QOfFQW4D", "PLrAXtmErZgOdP_8GztsuKi9f5QOfFQW4D"),
            ("https://www.youtube.com/watch?v=abc&list=PLrAXtmErZgOdP_8GztsuKi9f5QOfFQW4D", "PLrAXtmErZgOdP_8GztsuKi9f5QOfFQW4D"),
            ("PLrAXtmErZgOdP_8GztsuKi9f5QOfFQW4D", "PLrAXtmErZgOdP_8GztsuKi9f5QOfFQW4D"),
        ]
        for url, expected in urls:
            self.assertEqual(extract_playlist_id(url), expected, f"Failed on {url}")

    def test_duration_parsing(self):
        self.assertEqual(_iso_duration_to_seconds("PT1H2M3S"), 3723)
        self.assertEqual(_iso_duration_to_seconds("PT15M30S"), 930)
        self.assertEqual(_iso_duration_to_seconds("PT45S"), 45)
        self.assertEqual(_iso_duration_to_seconds("PT2H"), 7200)

    def test_seconds_to_human(self):
        self.assertEqual(_seconds_to_human(45), "0:45")
        self.assertEqual(_seconds_to_human(930), "15:30")
        self.assertEqual(_seconds_to_human(3723), "1:02:03")

    def test_progress_tracking_and_completion(self):
        # Track 30 minutes of a 60-minute video
        entry = track_video_progress(
            url_or_id="https://youtu.be/testvideo12",
            watched_seconds=1800,
            total_seconds=3600,
            title="Python Masterclass Test"
        )
        self.assertEqual(entry["percentage"], 50.0)
        self.assertFalse(entry["completed"])

        # Update to 58 minutes (97.2% -> completed)
        entry2 = track_video_progress(
            url_or_id="testvideo12",
            watched_seconds=3500,
            total_seconds=3600
        )
        self.assertGreaterEqual(entry2["percentage"], 95.0)
        self.assertTrue(entry2["completed"])

        # Fetch progress
        fetched = get_video_progress("testvideo12")
        self.assertTrue(fetched["tracked"])
        self.assertEqual(fetched["video_id"], "testvideo12")


class TestAgentToolsRegistration(unittest.TestCase):
    def test_agent_has_all_new_tools(self):
        from productivity_agent import ProductivityAgent
        class MockAgent:
            get_tools = ProductivityAgent.get_tools

        agent = MockAgent()
        tools = agent.get_tools()
        tool_names = {t["name"] for t in tools}

        expected_new_tools = [
            "web_search",
            "read_webpage",
            "confirm_sensitive_action",
            "read_emails",
            "read_email_by_id",
            "search_email",
            "create_email_draft",
            "send_email",
            "get_youtube_video_info",
            "track_youtube_video",
            "get_youtube_progress",
            "list_youtube_tracking",
            "get_youtube_playlist_progress",
        ]

        for expected in expected_new_tools:
            self.assertIn(expected, tool_names, f"Missing tool: {expected}")


if __name__ == "__main__":
    unittest.main(verbosity=2)

