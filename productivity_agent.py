#!/usr/bin/env python3
"""
AI Life & Productivity Agent (v3.1 — Browser, Email & YouTube Edition)
A comprehensive personal productivity system powered by Claude AI via OmniRoute.
Features persistent sessions, episodic journaling, knowledge base, full CRUD memory,
browser access, email integration, and YouTube progress tracking.
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path
from anthropic import Anthropic
from dotenv import load_dotenv

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from memory_manager import MemoryManager

# Load environment variables from .env file
load_dotenv()

# New capability modules (imported with graceful fallback)
try:
    from web_tools import (
        web_search, read_webpage,
        format_search_results, format_webpage_result,
        check_web_tools_available, describe_sensitive_action,
        WEB_TOOLS_AVAILABLE,
    )
except ImportError:
    WEB_TOOLS_AVAILABLE = False
    def web_search(q, **kw): return {"error": "web_tools not installed", "results": []}
    def read_webpage(u, **kw): return {"error": "web_tools not installed", "text": ""}
    def format_search_results(r): return str(r)
    def format_webpage_result(r): return str(r)
    def check_web_tools_available(): return "❌ web_tools.py missing or dependencies not installed."
    def describe_sensitive_action(a, d=""): return f"⚠️ Sensitive action: {a} — {d}"

try:
    from email_tools import (
        list_emails, read_email, search_emails, create_draft, send_email,
        format_email_list, format_email_content,
        check_email_configured,
    )
    EMAIL_TOOLS_AVAILABLE = True
except ImportError:
    EMAIL_TOOLS_AVAILABLE = False
    def list_emails(**kw): return {"error": "email_tools not installed", "emails": []}
    def read_email(i, **kw): return {"error": "email_tools not installed"}
    def search_emails(q, **kw): return {"error": "email_tools not installed", "results": []}
    def create_draft(**kw): return {"error": "email_tools not installed"}
    def send_email(**kw): return {"success": False, "error": "email_tools not installed"}
    def format_email_list(r): return str(r)
    def format_email_content(r): return str(r)
    def check_email_configured(): return (False, "email_tools.py missing")

try:
    from youtube_tools import (
        get_video_info, get_playlist_info,
        track_video_progress, get_video_progress,
        list_all_tracked_videos, get_playlist_progress,
        format_video_progress, format_all_tracked, format_playlist_progress,
        extract_video_id, extract_playlist_id,
        check_youtube_api_available, _seconds_to_human,
    )
    YOUTUBE_TOOLS_AVAILABLE = True
except ImportError:
    YOUTUBE_TOOLS_AVAILABLE = False
    def get_video_info(u): return {"error": "youtube_tools not installed"}
    def get_playlist_info(u): return {"error": "youtube_tools not installed"}
    def track_video_progress(u, s, **kw): return {"error": "youtube_tools not installed"}
    def get_video_progress(u): return {"error": "youtube_tools not installed"}
    def list_all_tracked_videos(): return {"videos": [], "total_tracked": 0, "completed": 0, "in_progress": 0}
    def get_playlist_progress(u): return {"error": "youtube_tools not installed"}
    def format_video_progress(r): return str(r)
    def format_all_tracked(r): return str(r)
    def format_playlist_progress(r): return str(r)
    def extract_video_id(u): return None
    def extract_playlist_id(u): return None
    def check_youtube_api_available(): return (False, "youtube_tools.py missing")
    def _seconds_to_human(s): return str(s)

# System prompt for the agent
SYSTEM_PROMPT = """[Context: Current time is {current_time}]

AI LIFE & PRODUCTIVITY AGENT — MASTER SYSTEM PROMPT

You are an intelligent AI Life & Productivity Agent designed to help the user organize their life, achieve meaningful goals, manage projects, build productive habits, and make consistent progress.

Your role is not simply to answer questions. You act as the user's personal:
- Goal strategist
- Productivity coach
- Daily planner
- Project manager
- Learning assistant
- Habit and progress tracker
- Priority advisor

Your ultimate objective is to help the user turn ideas and goals into consistent real-world action.

---

1. ADVANCED MEMORY & PERSISTENCE OPERATING RULES

You possess a comprehensive, multi-tiered memory system:
- **User Profile & Personal Context**: Deep understanding of the user's background, available hours, schedule, and current skills.
- **Active Goals & Milestones**: Long-term and short-term objectives.
- **Projects & Deliverables**: Multi-step initiatives.
- **Task Management**: Prioritized, actionable items.
- **Habits Tracker**: Consistency, streaks, and daily tracking.
- **Episodic Journal & Reviews**: Daily reflections, study hours, wins, and blockers.
- **Knowledge Base & Notes**: Saved concepts, tips, learning notes, and custom rules.

**Memory Guidelines:**
1. **Never forget established facts**: Reference the user's background, schedule, and goals naturally.
2. **Proactive Memory Updates**: When the user mentions new preferences, constraints, schedule changes, or insights, use `update_context`, `save_note`, or `add_journal_entry` to record them.
3. **Keep data accurate**: Use `update_task`, `complete_task`, or `delete_task` to keep the user's task board clean and up-to-date.
4. **Use exact IDs**: When completing or modifying tasks, goals, habits, or notes, always use their exact `ID` shown in the memory summary.
5. **Search memory when needed**: Use `search_all_memory` or `search_notes` to recall specific information when answering user queries.

---

2. DAILY PLANNING & PRIORITIZATION SYSTEM

When creating a daily plan or recommending tasks:
1. Review active goals and the user's personal schedule.
2. Prioritize URGENT and HIGH priority tasks.
3. Focus on high-impact items that unblock major milestones.
4. Avoid overloading the user with unrealistic workloads.

Structure daily recommendations clearly:
- **Today's Main Focus**: The #1 priority objective.
- **Top Priorities**: Maximum 3 high-impact tasks.
- **Quick Wins**: Small, fast actions.
- **Next Action**: The single concrete step to take immediately.

---

3. COMMUNICATION STYLE

- **Direct, practical, and action-focused**.
- Avoid long filler or generic motivational speeches.
- Always end actionable planning discussions with a clear **NEXT ACTION**.

---

7. BROWSER ACCESS RULES

You can browse the web using the `web_search` and `read_webpage` tools.

**Capabilities:**
- Search the web for information, news, tutorials, or any public content.
- Read and summarize public webpages (Wikipedia, documentation, articles, etc.).
- Always cite the URL source when presenting web-fetched information.

**Safety guardrails — ALWAYS ask for confirmation before:**
- Logging into any account
- Submitting forms
- Making purchases
- Posting comments or messages
- Downloading files
- Changing account settings

**Never** attempt to access passwords, banking data, or authentication codes.
**Never** claim to have read a page without actually calling `read_webpage`.
When presenting web content, clearly state: "🌐 Source: [URL]"

---

8. EMAIL ACCESS RULES

You can access the user's email using `read_emails`, `search_email`, `create_email_draft`, and `send_email` tools.

**Capabilities:**
- Read and summarize inbox emails
- Search for specific emails by keyword or sender
- Create draft replies for user review
- Send emails — ONLY after explicitly showing the recipient, subject, and message body and receiving user confirmation

**Mandatory safety rules:**
- NEVER send an email without first showing a full preview and getting explicit "yes" from the user.
- NEVER delete, archive, or permanently modify emails without user confirmation.
- NEVER expose private email content to anyone other than the authenticated user.
- Always state clearly when email features require account authorization.
- If EMAIL_ADDRESS or EMAIL_APP_PASSWORD are not configured, clearly inform the user.

---

9. YOUTUBE PROGRESS TRACKING RULES

You can track YouTube learning progress using `track_youtube_video`, `get_youtube_progress`, `list_youtube_tracking`, and `get_youtube_playlist_progress` tools.

**Important transparency rule:**
YouTube's API does NOT provide real playback position or watch history data. Progress is manually logged by the user. NEVER claim a video is "completed" unless the stored data confirms it.

**Capabilities:**
- Fetch video metadata (title, duration, channel) via YouTube Data API
- Track watch position (user provides minutes/seconds watched)
- Calculate percentage completed and remaining time
- Track progress through playlists (which videos are done, overall % complete)

**Progress tracking:**
- For playlists: show videos completed, current video, total videos, overall %
- For videos: show watched vs total duration, progress bar, completion status
- If YOUTUBE_API_KEY is not configured, metadata fetching will fail — inform the user.

---

CURRENT USER MEMORY SNAPSHOT:

{user_data}
"""


def _serialize_content_blocks(blocks):
    """Ensure all Anthropic SDK content blocks (TextBlock, ToolUseBlock, etc.) are converted to JSON-serializable dicts."""
    if isinstance(blocks, str):
        return blocks
    if isinstance(blocks, list):
        serialized = []
        for b in blocks:
            if hasattr(b, "model_dump"):
                serialized.append(b.model_dump())
            elif hasattr(b, "dict"):
                serialized.append(b.dict())
            elif hasattr(b, "type") and b.type == "text":
                serialized.append({"type": "text", "text": getattr(b, "text", "")})
            elif hasattr(b, "type") and b.type == "tool_use":
                serialized.append({
                    "type": "tool_use",
                    "id": getattr(b, "id", ""),
                    "name": getattr(b, "name", ""),
                    "input": getattr(b, "input", {})
                })
            elif hasattr(b, "type") and b.type == "tool_result":
                serialized.append({
                    "type": "tool_result",
                    "tool_use_id": getattr(b, "tool_use_id", ""),
                    "content": getattr(b, "content", "")
                })
            elif isinstance(b, dict):
                serialized.append(b)
            else:
                serialized.append(str(b))
        return serialized
    return str(blocks)


class ProductivityAgent:
    def __init__(self, resume_session: bool = True):
        """Initialize the productivity agent with OmniRoute and MemoryManager."""
        self.base_url = os.getenv("ANTHROPIC_BASE_URL")
        self.auth_token = os.getenv("ANTHROPIC_AUTH_TOKEN")
        self.model = os.getenv("ANTHROPIC_MODEL", "deepak-ai")

        if not self.base_url:
            raise ValueError(
                "ANTHROPIC_BASE_URL not found in environment variables.\n"
                "Please set it in your .env file or environment."
            )

        if not self.auth_token:
            raise ValueError(
                "ANTHROPIC_AUTH_TOKEN not found in environment variables.\n"
                "Please set it in your .env file or environment."
            )

        # Initialize Anthropic client with OmniRoute configuration
        self.client = Anthropic(
            base_url=self.base_url,
            api_key=self.auth_token
        )

        # Initialize Advanced Memory Subsystem
        self.memory = MemoryManager()

        # Load session history if resuming
        if resume_session:
            self.conversation_history = self.memory.load_latest_session()
        else:
            self.memory.start_new_session()
            self.conversation_history = []

        print(f"✓ Connected to OmniRoute at {self.base_url}")
        print(f"✓ Using model: {self.model}")
        print(f"✓ Memory System active (Session: {self.memory.current_session_id})")

    def get_tools(self):
        """Define the complete suite of memory and productivity tools."""
        return [
            # GOALS
            {
                "name": "add_goal",
                "description": "Add a new long-term or short-term goal",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "The goal title"},
                        "description": {"type": "string", "description": "Detailed description"},
                        "category": {"type": "string", "description": "Category (career, learning, personal, health)"},
                        "deadline": {"type": "string", "description": "Target deadline date/month"},
                        "milestones": {"type": "array", "items": {"type": "string"}, "description": "Key milestone checkpoints"}
                    },
                    "required": ["title", "description"]
                }
            },
            {
                "name": "update_goal",
                "description": "Update an existing goal's details or status",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "goal_id": {"type": "integer", "description": "ID of the goal to update"},
                        "title": {"type": "string", "description": "New title (optional)"},
                        "status": {"type": "string", "enum": ["active", "completed", "paused", "archived"], "description": "New status"},
                        "deadline": {"type": "string", "description": "New deadline (optional)"}
                    },
                    "required": ["goal_id"]
                }
            },
            {
                "name": "delete_goal",
                "description": "Delete a goal by its ID",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "goal_id": {"type": "integer", "description": "ID of the goal to delete"}
                    },
                    "required": ["goal_id"]
                }
            },

            # TASKS
            {
                "name": "add_task",
                "description": "Add a new actionable task",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Task title"},
                        "description": {"type": "string", "description": "Task description/steps"},
                        "priority": {"type": "string", "enum": ["low", "medium", "high", "urgent"], "description": "Priority level"},
                        "deadline": {"type": "string", "description": "Deadline (optional)"},
                        "project": {"type": "string", "description": "Associated project name (optional)"},
                        "goal": {"type": "string", "description": "Associated goal name (optional)"}
                    },
                    "required": ["title"]
                }
            },
            {
                "name": "complete_task",
                "description": "Mark a task as completed using its exact ID",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "integer", "description": "Exact ID of the task (e.g. 1, 2, 3...)"}
                    },
                    "required": ["task_id"]
                }
            },
            {
                "name": "update_task",
                "description": "Edit or reschedule an existing task",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "integer", "description": "Exact ID of the task to update"},
                        "title": {"type": "string", "description": "New title (optional)"},
                        "description": {"type": "string", "description": "New description (optional)"},
                        "priority": {"type": "string", "enum": ["low", "medium", "high", "urgent"], "description": "New priority"},
                        "deadline": {"type": "string", "description": "New deadline (optional)"},
                        "status": {"type": "string", "enum": ["pending", "in_progress", "completed", "cancelled"]}
                    },
                    "required": ["task_id"]
                }
            },
            {
                "name": "delete_task",
                "description": "Delete a task by its ID",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "integer", "description": "Exact ID of the task to delete"}
                    },
                    "required": ["task_id"]
                }
            },
            {
                "name": "search_tasks",
                "description": "Search and filter tasks by keyword, status, or priority",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Keyword to search in task titles or descriptions"},
                        "status": {"type": "string", "enum": ["pending", "completed", "in_progress"], "description": "Status filter (optional)"},
                        "priority": {"type": "string", "enum": ["low", "medium", "high", "urgent"], "description": "Priority filter (optional)"}
                    }
                }
            },

            # PROJECTS
            {
                "name": "add_project",
                "description": "Create a new project roadmap",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Project name"},
                        "description": {"type": "string", "description": "Project description and scope"},
                        "goal": {"type": "string", "description": "Associated goal"},
                        "deliverables": {"type": "array", "items": {"type": "string"}, "description": "Key deliverables"}
                    },
                    "required": ["name", "description"]
                }
            },
            {
                "name": "update_project",
                "description": "Update project details or status",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "integer", "description": "ID of the project"},
                        "status": {"type": "string", "enum": ["active", "completed", "paused", "archived"]},
                        "description": {"type": "string", "description": "Updated description"}
                    },
                    "required": ["project_id"]
                }
            },

            # HABITS
            {
                "name": "add_habit",
                "description": "Add a new recurring habit to track",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Habit name"},
                        "frequency": {"type": "string", "description": "Frequency (daily, weekly, weekdays)"},
                        "goal": {"type": "string", "description": "Associated goal (optional)"}
                    },
                    "required": ["name", "frequency"]
                }
            },
            {
                "name": "log_habit",
                "description": "Log completion of a habit for today using its exact ID",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "habit_id": {"type": "integer", "description": "Exact ID of the habit"},
                        "completed": {"type": "boolean", "description": "Whether the habit was completed today"}
                    },
                    "required": ["habit_id", "completed"]
                }
            },
            {
                "name": "delete_habit",
                "description": "Delete a habit by its ID",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "habit_id": {"type": "integer", "description": "Exact ID of the habit to delete"}
                    },
                    "required": ["habit_id"]
                }
            },

            # USER CONTEXT & PROFILE
            {
                "name": "update_context",
                "description": "Store or update long-term user profile facts, constraints, and schedules",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "key": {"type": "string", "description": "Context key (e.g. 'study_schedule', 'target_exam', 'preferred_stack')"},
                        "value": {"type": "string", "description": "Context details/value"}
                    },
                    "required": ["key", "value"]
                }
            },

            # EPISODIC MEMORY / JOURNAL
            {
                "name": "log_daily_review",
                "description": "Record a daily reflection, review, study hours, wins, and blockers",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "summary": {"type": "string", "description": "Overview of today's progress and focus"},
                        "wins": {"type": "array", "items": {"type": "string"}, "description": "Key achievements and victories today"},
                        "blockers": {"type": "string", "description": "Any challenges, fatigue, or delays experienced"},
                        "hours_studied": {"type": "number", "description": "Total effective hours studied/worked today"},
                        "focus_tomorrow": {"type": "string", "description": "Planned top priority for tomorrow"}
                    },
                    "required": ["summary"]
                }
            },