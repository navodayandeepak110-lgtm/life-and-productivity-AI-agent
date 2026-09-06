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
            {
                "name": "get_recent_journal",
                "description": "Retrieve recent daily reviews and retrospective entries",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "days": {"type": "integer", "description": "Number of days of journal history to inspect (default: 7)"}
                    }
                }
            },

            # KNOWLEDGE BASE & NOTES (SEMANTIC MEMORY)
            {
                "name": "save_note",
                "description": "Save an important study note, cheat sheet, resource link, or user preference",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Title of the note"},
                        "content": {"type": "string", "description": "Detailed text content/notes/rules"},
                        "category": {"type": "string", "description": "Category (e.g. 'dsa', 'gate', 'java', 'preferences')"},
                        "tags": {"type": "array", "items": {"type": "string"}, "description": "Search tags"}
                    },
                    "required": ["title", "content"]
                }
            },
            {
                "name": "search_notes",
                "description": "Search saved notes and study resources by keyword or tag",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Keyword to search in title and content"},
                        "tag": {"type": "string", "description": "Tag to filter by (optional)"}
                    }
                }
            },
            {
                "name": "search_all_memory",
                "description": "Perform a universal search across tasks, goals, projects, notes, journal, and profile context",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Keyword to search across all memory stores"}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "archive_task",
                "description": "Move a completed or inactive task to archive.json storage",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "integer", "description": "ID of the task to archive"}
                    },
                    "required": ["task_id"]
                }
            },
            {
                "name": "export_memory",
                "description": "Export complete agent memory snapshot into a timestamped JSON backup file",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "export_dir": {"type": "string", "description": "Optional custom export directory"}
                    }
                }
            },
            {
                "name": "undo_last_action",
                "description": "Revert the most recent mutating operation (e.g. accidentally added, completed, or deleted task/goal/habit)",
                "input_schema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "list_attachments",
                "description": "List all uploaded/saved file attachments and documents in memory",
                "input_schema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "view_attachment",
                "description": "Inspect metadata and text preview of a file attachment by ID",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "attachment_id": {"type": "integer", "description": "ID of the attachment"}
                    },
                    "required": ["attachment_id"]
                }
            },
            # ANALYTICS & INSIGHTS
            {
                "name": "get_analytics_report",
                "description": "Generate a detailed productivity analytics report (weekly or monthly) including task completion rate trends, time-of-day productivity patterns, habit consistency scores, and coaching insights",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "period": {
                            "type": "string",
                            "enum": ["weekly", "monthly"],
                            "description": "Timeframe for the analytics report (default: 'weekly')"
                        }
                    }
                }
            },
            {
                "name": "get_smart_notifications",
                "description": "Retrieve current proactive notifications and alerts: tasks due soon (<= 2 hours), habit streaks at risk, or weekly review readiness",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "force": {
                            "type": "boolean",
                            "description": "Whether to check all triggers ignoring daily cooldowns (default: true)"
                        }
                    }
                }
            },
            {
                "name": "get_goal_progress",
                "description": "Get visual progress bars, milestone checklists, and execution status for all active goals",
                "input_schema": {
                    "type": "object",
                    "properties": {}
                }
            },

            # ── BROWSER / WEB ACCESS ────────────────────────────────────────
            {
                "name": "web_search",
                "description": "Search the web for information, news, tutorials, or any public content using DuckDuckGo. No API key required. Cite the source URL in your response.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query string"},
                        "max_results": {"type": "integer", "description": "Max results to return (default: 5, max: 10)"}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "read_webpage",
                "description": "Fetch and extract the readable text content from a public URL. Use this to read articles, documentation, Wikipedia pages, and other public websites. Always cite the source URL.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "Full URL of the page to read (must start with http:// or https://)"},
                        "max_chars": {"type": "integer", "description": "Maximum characters to return (default: 8000)"}
                    },
                    "required": ["url"]
                }
            },
            {
                "name": "confirm_sensitive_action",
                "description": "Use this tool BEFORE performing any sensitive browser action (login, form submit, purchase, download, posting, settings change). Shows the user a confirmation prompt and returns their response.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "action_type": {
                            "type": "string",
                            "enum": ["login", "submit_form", "purchase", "post_comment", "download_file", "change_settings"],
                            "description": "Type of sensitive action"
                        },
                        "details": {"type": "string", "description": "Description of what specifically will happen"}
                    },
                    "required": ["action_type", "details"]
                }
            },

            # ── EMAIL ACCESS ────────────────────────────────────────────────
            {
                "name": "read_emails",
                "description": "Read recent emails from the inbox. Can filter by unread only. Requires EMAIL_ADDRESS and EMAIL_APP_PASSWORD in .env.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "folder": {"type": "string", "description": "Mailbox folder (default: INBOX)"},
                        "count": {"type": "integer", "description": "Number of emails to fetch (default: 10, max: 50)"},
                        "unread_only": {"type": "boolean", "description": "If true, return only unread emails"}
                    }
                }
            },
            {
                "name": "read_email_by_id",
                "description": "Read the full content of a specific email by its ID (obtained from read_emails). Requires email credentials in .env.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "email_id": {"type": "string", "description": "Email ID string from read_emails result"},
                        "folder": {"type": "string", "description": "Folder containing the email (default: INBOX)"}
                    },
                    "required": ["email_id"]
                }
            },
            {
                "name": "search_email",
                "description": "Search the inbox for emails matching a keyword (searches subject and body). Requires email credentials in .env.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Keyword or phrase to search for"},
                        "folder": {"type": "string", "description": "Folder to search (default: INBOX)"},
                        "max_results": {"type": "integer", "description": "Maximum results (default: 10)"}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "create_email_draft",
                "description": "Create an email draft for the user to review. Returns a full preview with To, Subject, and Body. DOES NOT SEND — always show draft preview before sending.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "to": {"type": "string", "description": "Recipient email address"},
                        "subject": {"type": "string", "description": "Email subject line"},
                        "body": {"type": "string", "description": "Email body content (plain text)"}
                    },
                    "required": ["to", "subject", "body"]
                }
            },
            {
                "name": "send_email",
                "description": "Send an email. ONLY call this after showing the user the draft via create_email_draft and receiving explicit confirmation. Always confirm before sending.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "to": {"type": "string", "description": "Recipient email address"},
                        "subject": {"type": "string", "description": "Email subject line"},
                        "body": {"type": "string", "description": "Email body content"}
                    },
                    "required": ["to", "subject", "body"]
                }
            },

            # ── YOUTUBE PROGRESS TRACKING ───────────────────────────────────
            {
                "name": "get_youtube_video_info",
                "description": "Fetch YouTube video metadata (title, duration, channel) using the YouTube Data API. Requires YOUTUBE_API_KEY in .env.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "url_or_id": {"type": "string", "description": "YouTube video URL or 11-character video ID"}
                    },
                    "required": ["url_or_id"]
                }
            },
            {
                "name": "track_youtube_video",
                "description": "Record how much of a YouTube video you've watched (manual progress update). Calculates percentage and completion status. Stored locally in agent_data/youtube_progress.json.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "url_or_id": {"type": "string", "description": "YouTube video URL or video ID"},
                        "watched_minutes": {"type": "number", "description": "How many minutes of the video you have watched"},
                        "total_minutes": {"type": "number", "description": "Total video duration in minutes (optional — fetched from API if YOUTUBE_API_KEY is set)"},
                        "notes": {"type": "string", "description": "Optional notes about this viewing session (e.g. topics covered, timestamp to resume)"}
                    },
                    "required": ["url_or_id", "watched_minutes"]
                }
            },
            {
                "name": "get_youtube_progress",
                "description": "Get stored watch progress for a specific YouTube video. Shows watched time, total duration, percentage, and completion status.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "url_or_id": {"type": "string", "description": "YouTube video URL or video ID"}
                    },
                    "required": ["url_or_id"]
                }
            },
            {
                "name": "list_youtube_tracking",
                "description": "List all tracked YouTube videos with progress summaries — how much watched, percentage, completion status.",
                "input_schema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "get_youtube_playlist_progress",
                "description": "Get progress across a YouTube playlist — which videos are completed, current position, overall completion percentage. Requires YOUTUBE_API_KEY.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "url_or_id": {"type": "string", "description": "YouTube playlist URL or playlist ID"}
                    },
                    "required": ["url_or_id"]
                }
            }
        ]

    def execute_tool(self, tool_name: str, tool_input: dict) -> str:
        """Dispatch tool calls to MemoryManager and format clear responses."""
        try:
            # Goals
            if tool_name == "add_goal":
                goal = self.memory.add_goal(
                    title=tool_input["title"],
                    description=tool_input["description"],
                    category=tool_input.get("category", "general"),
                    deadline=tool_input.get("deadline"),
                    milestones=tool_input.get("milestones", [])
                )
                return f"✅ Goal #{goal['id']} '{goal['title']}' created successfully!"

            elif tool_name == "update_goal":
                goal = self.memory.update_goal(tool_input["goal_id"], **{k: v for k, v in tool_input.items() if k != "goal_id"})
                if goal:
                    return f"✅ Goal #{goal['id']} '{goal['title']}' updated."
                return f"❌ Goal #{tool_input['goal_id']} not found."

            elif tool_name == "delete_goal":
                success = self.memory.delete_goal(tool_input["goal_id"])
                return f"🗑️ Goal #{tool_input['goal_id']} deleted." if success else f"❌ Goal #{tool_input['goal_id']} not found."

            # Tasks
            elif tool_name == "add_task":
                task = self.memory.add_task(
                    title=tool_input["title"],
                    description=tool_input.get("description", ""),
                    priority=tool_input.get("priority", "medium"),
                    deadline=tool_input.get("deadline"),
                    project=tool_input.get("project"),
                    goal=tool_input.get("goal")
                )
                return f"✅ Task #{task['id']} '{task['title']}' added ({task['priority'].upper()} priority)."

            elif tool_name == "complete_task":
                task = self.memory.complete_task(tool_input["task_id"])
                if task:
                    return f"🎉 Task #{task['id']} '{task['title']}' marked as COMPLETED!"
                return f"❌ Task #{tool_input['task_id']} not found."

            elif tool_name == "update_task":
                task = self.memory.update_task(tool_input["task_id"], **{k: v for k, v in tool_input.items() if k != "task_id"})
                if task:
                    return f"✅ Task #{task['id']} '{task['title']}' updated."
                return f"❌ Task #{tool_input['task_id']} not found."

            elif tool_name == "delete_task":
                success = self.memory.delete_task(tool_input["task_id"])
                return f"🗑️ Task #{tool_input['task_id']} deleted." if success else f"❌ Task #{tool_input['task_id']} not found."

            elif tool_name == "search_tasks":
                results = self.memory.search_tasks(
                    query=tool_input.get("query", ""),
                    status=tool_input.get("status"),
                    priority=tool_input.get("priority")
                )
                if not results:
                    return "No matching tasks found."
                formatted = [f"- [ID #{t['id']}] [{t.get('priority').upper()}] {t.get('title')} ({t.get('status')})" for t in results]
                return f"Found {len(results)} task(s):\n" + "\n".join(formatted)

            # Projects
            elif tool_name == "add_project":
                project = self.memory.add_project(
                    name=tool_input["name"],
                    description=tool_input["description"],
                    goal=tool_input.get("goal"),
                    deliverables=tool_input.get("deliverables", [])
                )
                return f"📁 Project #{project['id']} '{project['name']}' created successfully!"

            elif tool_name == "update_project":
                project = self.memory.update_project(tool_input["project_id"], **{k: v for k, v in tool_input.items() if k != "project_id"})
                if project:
                    return f"📁 Project #{project['id']} '{project['name']}' updated."
                return f"❌ Project #{tool_input['project_id']} not found."

            # Habits
            elif tool_name == "add_habit":
                habit = self.memory.add_habit(
                    name=tool_input["name"],
                    frequency=tool_input.get("frequency", "daily"),
                    goal=tool_input.get("goal")
                )
                return f"🔁 Habit #{habit['id']} '{habit['name']}' added to tracker!"

            elif tool_name == "log_habit":
                habit = self.memory.log_habit(tool_input["habit_id"], tool_input["completed"])
                if habit:
                    status_txt = "completed" if tool_input["completed"] else "marked incomplete"
                    return f"🔁 Habit #{habit['id']} '{habit['name']}' {status_txt}. Current streak: 🔥 {habit.get('streak', 0)} days."
                return f"❌ Habit #{tool_input['habit_id']} not found."

            elif tool_name == "delete_habit":
                success = self.memory.delete_habit(tool_input["habit_id"])
                return f"🗑️ Habit #{tool_input['habit_id']} deleted." if success else f"❌ Habit #{tool_input['habit_id']} not found."

            # Context
            elif tool_name == "update_context":
                self.memory.update_context(tool_input["key"], tool_input["value"])
                return f"🧠 Memory updated: {tool_input['key']} = {tool_input['value']}"

            # Journal / Episodic
            elif tool_name == "log_daily_review":
                entry = self.memory.add_journal_entry(
                    summary=tool_input["summary"],
                    wins=tool_input.get("wins", []),
                    blockers=tool_input.get("blockers"),
                    hours_studied=tool_input.get("hours_studied"),
                    focus_tomorrow=tool_input.get("focus_tomorrow")
                )
                return f"📝 Daily review for {entry['date']} logged successfully!"

            elif tool_name == "get_recent_journal":
                days = tool_input.get("days", 7)
                entries = self.memory.get_recent_journal(days)
                if not entries:
                    return "No recent journal entries found."
                return json.dumps(entries, indent=2)

            # Notes / Knowledge
            elif tool_name == "save_note":
                note = self.memory.save_note(
                    title=tool_input["title"],
                    content=tool_input["content"],
                    category=tool_input.get("category", "general"),
                    tags=tool_input.get("tags", [])
                )
                return f"💡 Note #{note['id']} '{note['title']}' saved to Knowledge Base!"

            elif tool_name == "search_notes":
                notes = self.memory.search_notes(
                    query=tool_input.get("query", ""),
                    tag=tool_input.get("tag")
                )
                if not notes:
                    return "No notes found matching the query."
                return json.dumps(notes, indent=2)

            elif tool_name == "search_all_memory":
                results = self.memory.search_all_memory(tool_input["query"])
                if not results:
                    return f"No memory items matching '{tool_input['query']}' found."
                return json.dumps(results, indent=2)

            # Archive
            elif tool_name == "archive_task":
                archived = self.memory.archive_task(tool_input["task_id"])
                if archived:
                    return f"📁 Task #{tool_input['task_id']} '{archived.get('title')}' moved to archive.json."
                return f"❌ Task #{tool_input['task_id']} not found."

            # Export
            elif tool_name == "export_memory":
                path = self.memory.export_backup(tool_input.get("export_dir"))
                return f"💾 Memory snapshot backup exported successfully to: {path}"

            # Undo
            elif tool_name == "undo_last_action":
                return self.memory.undo()

            # Attachments
            elif tool_name == "list_attachments":
                return self.memory.get_attachments_formatted()

            elif tool_name == "view_attachment":
                att = self.memory.get_attachment(tool_input["attachment_id"])
                if not att:
                    return f"❌ Attachment #{tool_input['attachment_id']} not found."
                return json.dumps(att, indent=2)

            # Analytics & Insights
            elif tool_name == "get_analytics_report":
                period = tool_input.get("period", "weekly")
                return self.memory.get_analytics_report_formatted(period)

            elif tool_name == "get_smart_notifications":
                force = tool_input.get("force", True)
                return self.memory.get_proactive_notifications_formatted(force=force)

            elif tool_name == "get_goal_progress":
                return self.memory.get_goal_progress_visualizations()

            # ── BROWSER / WEB TOOLS ──────────────────────────────────────────

            elif tool_name == "web_search":
                result = web_search(
                    query=tool_input["query"],
                    max_results=min(tool_input.get("max_results", 5), 10)
                )
                return format_search_results(result)

            elif tool_name == "read_webpage":
                result = read_webpage(
                    url=tool_input["url"],
                    max_chars=tool_input.get("max_chars", 8000)
                )
                return format_webpage_result(result)
