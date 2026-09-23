#!/usr/bin/env python3
"""
YouTube Tools
=============
Provides YouTube video/playlist metadata and manual progress tracking.

Two capabilities:
  1. METADATA — Fetch video title, duration, channel, and playlist contents
     via YouTube Data API v3 (requires YOUTUBE_API_KEY in .env)

  2. PROGRESS TRACKING — Manual watch position logging stored locally
     in agent_data/youtube_progress.json
     (YouTube does not expose real playback position via API — user updates manually)

Setup:
    1. Go to https://console.cloud.google.com/
    2. Create a project -> Enable "YouTube Data API v3"
    3. Create API Key -> Copy to .env as YOUTUBE_API_KEY=AIza...
"""

import os
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"
PROGRESS_FILE = Path(__file__).parent / "agent_data" / "youtube_progress.json"
REQUEST_TIMEOUT = 10


# ---------------------------------------------------------------------------
# Availability Checks
# ---------------------------------------------------------------------------

def check_youtube_api_available() -> tuple[bool, str]:
    """Check if YouTube API key is configured."""
    if not REQUESTS_AVAILABLE:
        return False, "requests library not installed. Run: pip install requests"
    if not YOUTUBE_API_KEY:
        return False, (
            "YOUTUBE_API_KEY not set in .env\n"
            "Get a free key at: https://console.cloud.google.com/"
        )
    return True, f"YouTube API configured (key ending ...{YOUTUBE_API_KEY[-6:]})"


# ---------------------------------------------------------------------------
# URL Parsing Helpers
# ---------------------------------------------------------------------------

def extract_video_id(url_or_id: str) -> Optional[str]:
    """
    Extract YouTube video ID from a URL or return as-is if it looks like an ID.
    Handles: youtu.be/ID, youtube.com/watch?v=ID, youtube.com/shorts/ID, etc.
    """
    url = url_or_id.strip()

    # Already looks like a plain video ID (11 chars, alphanumeric + dash/underscore)
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", url):
        return url

    patterns = [
        r"(?:v=|youtu\.be/|youtube\.com/embed/|youtube\.com/shorts/)([A-Za-z0-9_-]{11})",
        r"(?:vi=|v/)([A-Za-z0-9_-]{11})",
    ]
    for pat in patterns:
        match = re.search(pat, url)
        if match:
            return match.group(1)
    return None


def extract_playlist_id(url_or_id: str) -> Optional[str]:
    """Extract YouTube playlist ID from a URL or return as-is."""
    url = url_or_id.strip()

    if re.fullmatch(r"PL[A-Za-z0-9_-]+", url):
        return url

    match = re.search(r"[?&]list=([A-Za-z0-9_-]+)", url)
    if match:
        return match.group(1)
    return None


def _iso_duration_to_seconds(iso: str) -> int:
    """Convert ISO 8601 duration (PT1H2M3S) to total seconds."""
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso)
    if not match:
        return 0
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds


def _seconds_to_human(seconds: int) -> str:
    """Convert seconds to human-readable HH:MM:SS or MM:SS."""
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"

