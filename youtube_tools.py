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


# ---------------------------------------------------------------------------
# YouTube API Calls
# ---------------------------------------------------------------------------

def get_video_info(url_or_id: str) -> dict:
    """
    Fetch video metadata: title, duration, channel, description snippet.

    Args:
        url_or_id: YouTube video URL or video ID.

    Returns:
        dict with video info or 'error'.
    """
    available, msg = check_youtube_api_available()
    if not available:
        return {"error": msg}

    video_id = extract_video_id(url_or_id)
    if not video_id:
        return {"error": f"Could not extract video ID from: '{url_or_id}'"}

    try:
        resp = requests.get(
            f"{YOUTUBE_API_BASE}/videos",
            params={
                "part": "snippet,contentDetails,statistics",
                "id": video_id,
                "key": YOUTUBE_API_KEY,
            },
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()

        items = data.get("items", [])
        if not items:
            return {"error": f"Video not found: {video_id}"}

        item = items[0]
        snippet = item.get("snippet", {})
        details = item.get("contentDetails", {})
        stats = item.get("statistics", {})

        duration_iso = details.get("duration", "PT0S")
        duration_sec = _iso_duration_to_seconds(duration_iso)

        return {
            "video_id": video_id,
            "title": snippet.get("title", ""),
            "channel": snippet.get("channelTitle", ""),
            "published_at": snippet.get("publishedAt", ""),
            "description": snippet.get("description", "")[:300],
            "duration_seconds": duration_sec,
            "duration_human": _seconds_to_human(duration_sec),
            "view_count": stats.get("viewCount", "N/A"),
            "url": f"https://www.youtube.com/watch?v={video_id}",
        }

    except requests.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}
    except Exception as e:
        return {"error": f"Failed to get video info: {str(e)}"}


def get_playlist_info(url_or_id: str) -> dict:
    """
    Fetch all videos in a YouTube playlist.

    Args:
        url_or_id: Playlist URL or playlist ID.

    Returns:
        dict with playlist metadata and list of videos.
    """
    available, msg = check_youtube_api_available()
    if not available:
        return {"error": msg}

    playlist_id = extract_playlist_id(url_or_id)
    if not playlist_id:
        return {"error": f"Could not extract playlist ID from: '{url_or_id}'"}

    try:
        # Get playlist metadata
        pl_resp = requests.get(
            f"{YOUTUBE_API_BASE}/playlists",
            params={
                "part": "snippet,contentDetails",
                "id": playlist_id,
                "key": YOUTUBE_API_KEY,
            },
            timeout=REQUEST_TIMEOUT,
        )
        pl_resp.raise_for_status()
        pl_data = pl_resp.json()
        pl_items = pl_data.get("items", [])

        pl_title = pl_items[0]["snippet"]["title"] if pl_items else "Unknown Playlist"
        pl_channel = pl_items[0]["snippet"].get("channelTitle", "") if pl_items else ""

        # Get all video IDs in playlist (paginated)
        videos = []
        next_page = None

        while True:
            params = {
                "part": "snippet,contentDetails",
                "playlistId": playlist_id,
                "maxResults": 50,
                "key": YOUTUBE_API_KEY,
            }
            if next_page:
                params["pageToken"] = next_page

            items_resp = requests.get(
                f"{YOUTUBE_API_BASE}/playlistItems",
                params=params,
                timeout=REQUEST_TIMEOUT,
            )
            items_resp.raise_for_status()
            items_data = items_resp.json()

            for item in items_data.get("items", []):
                snippet = item.get("snippet", {})
                resource = snippet.get("resourceId", {})
                vid_id = resource.get("videoId", "")
                if vid_id:
                    videos.append({
                        "position": snippet.get("position", len(videos)) + 1,
                        "video_id": vid_id,
                        "title": snippet.get("title", ""),
                        "url": f"https://www.youtube.com/watch?v={vid_id}",
                    })

            next_page = items_data.get("nextPageToken")
            if not next_page:
                break

        return {
            "playlist_id": playlist_id,
            "playlist_title": pl_title,
            "channel": pl_channel,
            "total_videos": len(videos),
            "videos": videos,
            "playlist_url": f"https://www.youtube.com/playlist?list={playlist_id}",
        }

    except requests.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}
    except Exception as e:
        return {"error": f"Failed to get playlist: {str(e)}"}


# ---------------------------------------------------------------------------
# Local Progress Tracking (stored in agent_data/youtube_progress.json)
# ---------------------------------------------------------------------------

def _load_progress() -> dict:
    """Load progress data from local JSON file."""
    PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if PROGRESS_FILE.exists():
        try:
            with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"videos": {}, "playlists": {}}


def _save_progress(data: dict):
    """Save progress data to local JSON file."""
    PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def track_video_progress(
    url_or_id: str,
    watched_seconds: int,
    total_seconds: Optional[int] = None,
    title: Optional[str] = None,
    playlist_id: Optional[str] = None,
    notes: Optional[str] = None,
) -> dict:
    """
    Record manually entered watch progress for a video.

    Args:
        url_or_id: YouTube video URL or ID.
        watched_seconds: How many seconds of the video you've watched.
        total_seconds: Total video duration in seconds (fetched from API if not provided).
        title: Video title (optional, fetched from API if not provided).
        playlist_id: Associated playlist ID (optional).
        notes: Any notes about this session.

    Returns:
        dict with updated progress info.
    """
    video_id = extract_video_id(url_or_id)
    if not video_id:
        return {"error": f"Could not extract video ID from: '{url_or_id}'"}

    # Try to fetch metadata if title/duration not provided
    if not title or not total_seconds:
        info = get_video_info(video_id)
        if "error" not in info:
            title = title or info.get("title", "")
            total_seconds = total_seconds or info.get("duration_seconds", 0)

    progress_data = _load_progress()

    existing = progress_data["videos"].get(video_id, {})
    watched_seconds = max(0, watched_seconds)
    if total_seconds:
        watched_seconds = min(watched_seconds, total_seconds)

    percentage = round((watched_seconds / total_seconds * 100), 1) if total_seconds else None
    completed = percentage is not None and percentage >= 95.0

    entry = {
        "video_id": video_id,
        "title": title or "Unknown",
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "watched_seconds": watched_seconds,
        "watched_human": _seconds_to_human(watched_seconds),
        "total_seconds": total_seconds or existing.get("total_seconds"),
        "total_human": _seconds_to_human(total_seconds) if total_seconds else existing.get("total_human", "?"),
        "percentage": percentage,
        "completed": completed,
        "playlist_id": playlist_id or existing.get("playlist_id"),
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "notes": notes or "",
        "sessions": existing.get("sessions", 0) + 1,
    }

    progress_data["videos"][video_id] = entry
    _save_progress(progress_data)

    return entry


def get_video_progress(url_or_id: str) -> dict:
    """
    Get stored progress for a specific video.

    Args:
        url_or_id: YouTube video URL or ID.

    Returns:
        dict with progress details or 'error' if not tracked.
    """
    video_id = extract_video_id(url_or_id)
    if not video_id:
        return {"error": f"Could not extract video ID from: '{url_or_id}'"}

    data = _load_progress()
    entry = data["videos"].get(video_id)

    if not entry:
        return {
            "video_id": video_id,
            "tracked": False,
            "message": f"No progress recorded for video {video_id}. Use track_youtube_video to log progress."
        }

    return {**entry, "tracked": True}

