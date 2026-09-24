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


def list_all_tracked_videos() -> dict:
    """
    List all tracked YouTube videos with progress summaries.

    Returns:
        dict with 'videos' list sorted by last_updated.
    """
    data = _load_progress()
    videos = list(data["videos"].values())
    videos.sort(key=lambda x: x.get("last_updated", ""), reverse=True)
    return {
        "videos": videos,
        "total_tracked": len(videos),
        "completed": sum(1 for v in videos if v.get("completed")),
        "in_progress": sum(1 for v in videos if not v.get("completed") and v.get("watched_seconds", 0) > 0),
    }


def get_playlist_progress(url_or_id: str) -> dict:
    """
    Get progress summary for all tracked videos in a playlist.

    Args:
        url_or_id: Playlist URL or ID.

    Returns:
        dict with per-video progress and overall completion percentage.
    """
    playlist_id = extract_playlist_id(url_or_id)
    if not playlist_id:
        return {"error": f"Could not extract playlist ID from: '{url_or_id}'"}

    # Fetch playlist structure from API
    pl_info = get_playlist_info(playlist_id)
    if "error" in pl_info:
        return pl_info

    # Match with local progress data
    data = _load_progress()
    tracked = data["videos"]

    report_videos = []
    completed_count = 0

    for video in pl_info["videos"]:
        vid_id = video["video_id"]
        progress = tracked.get(vid_id, {})
        is_completed = progress.get("completed", False)
        if is_completed:
            completed_count += 1

        report_videos.append({
            "position": video["position"],
            "video_id": vid_id,
            "title": video["title"],
            "url": video["url"],
            "watched_human": progress.get("watched_human", "0:00"),
            "total_human": progress.get("total_human", "?"),
            "percentage": progress.get("percentage"),
            "completed": is_completed,
            "last_updated": progress.get("last_updated", "Not started"),
        })

    total = pl_info["total_videos"]
    overall_pct = round(completed_count / total * 100, 1) if total else 0

    return {
        "playlist_id": playlist_id,
        "playlist_title": pl_info["playlist_title"],
        "playlist_url": pl_info["playlist_url"],
        "total_videos": total,
        "completed_videos": completed_count,
        "overall_percentage": overall_pct,
        "videos": report_videos,
    }


# ---------------------------------------------------------------------------
# Format Helpers
# ---------------------------------------------------------------------------

def format_video_progress(entry: dict) -> str:
    """Format a single video's progress for agent output."""
    if entry.get("error"):
        return f"📺 YouTube Error: {entry['error']}"

    if not entry.get("tracked"):
        return f"📺 Video not yet tracked.\n{entry.get('message', '')}"

    pct = entry.get("percentage")
    pct_bar = ""
    if pct is not None:
        filled = int(pct / 5)
        pct_bar = f"[{'█' * filled}{'░' * (20 - filled)}] {pct}%"

    status = "✅ Completed" if entry.get("completed") else "▶️ In Progress"

    lines = [
        f"📺 {entry.get('title', 'Video')}",
        f"🔗 {entry.get('url', '')}",
        f"Status:   {status}",
        f"Watched:  {entry.get('watched_human', '?')} / {entry.get('total_human', '?')}",
    ]
    if pct_bar:
        lines.append(f"Progress: {pct_bar}")
    lines.append(f"Updated:  {entry.get('last_updated', 'N/A')}")
    if entry.get("notes"):
        lines.append(f"Notes:    {entry['notes']}")

    return "\n".join(lines)


def format_all_tracked(result: dict) -> str:
    """Format list_all_tracked_videos() for agent output."""
    videos = result.get("videos", [])
    if not videos:
        return "📺 No YouTube videos are being tracked yet.\nUse /yt-track <url> <minutes> to start tracking."

    total = result.get("total_tracked", 0)
    completed = result.get("completed", 0)
    in_progress = result.get("in_progress", 0)

    lines = [
        f"📺 YouTube Progress — {total} tracked | ✅ {completed} completed | ▶️ {in_progress} in progress\n"
    ]

    for v in videos:
        pct = v.get("percentage")
        pct_str = f" ({pct}%)" if pct is not None else ""
        status = "✅" if v.get("completed") else "▶️"
        lines.append(f"  {status} [{v['video_id']}] {v.get('title', 'Unknown')[:60]}")
        lines.append(f"       {v.get('watched_human', '?')} / {v.get('total_human', '?')}{pct_str}  |  Last: {v.get('last_updated', 'N/A')}")
        lines.append("")

    return "\n".join(lines).strip()


def format_playlist_progress(result: dict) -> str:
    """Format get_playlist_progress() for agent output."""
    if result.get("error"):
        return f"📺 Playlist Error: {result['error']}"

    title = result.get("playlist_title", "Playlist")
    total = result.get("total_videos", 0)
    completed = result.get("completed_videos", 0)
    pct = result.get("overall_percentage", 0)

    filled = int(pct / 5)
    pct_bar = f"[{'█' * filled}{'░' * (20 - filled)}] {pct}%"

    lines = [
        f"📋 Playlist: {title}",
        f"🔗 {result.get('playlist_url', '')}",
        f"Overall: {pct_bar}  ({completed}/{total} videos completed)\n",
    ]

    for v in result.get("videos", []):
        pct_v = v.get("percentage")
        pct_str = f" {pct_v}%" if pct_v is not None else " —"
        status = "✅" if v.get("completed") else ("▶️" if v.get("watched_human", "0:00") != "0:00" else "⬜")
        lines.append(f"  {status} {v['position']:>2}. {v.get('title', '')[:55]}{pct_str}")

    return "\n".join(lines)
