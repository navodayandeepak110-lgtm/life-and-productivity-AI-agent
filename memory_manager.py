#!/usr/bin/env python3
"""
Memory Manager for AI Life & Productivity Agent
Provides persistent working memory, structured memory, episodic journaling,
and semantic/knowledge base search capabilities.
"""

import json
import os
import shutil
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

try:
    import dateparser
except ImportError:
    dateparser = None


class MemoryManager:
    """Central manager for agent long-term memory, session state, and knowledge search."""

    def __init__(self, data_dir: str = "agent_data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

        # File paths
        self.goals_file = self.data_dir / "goals.json"
        self.tasks_file = self.data_dir / "tasks.json"
        self.archive_file = self.data_dir / "archive.json"
        self.projects_file = self.data_dir / "projects.json"
        self.habits_file = self.data_dir / "habits.json"
        self.context_file = self.data_dir / "context.json"
        self.journal_file = self.data_dir / "journal.json"
        self.notes_file = self.data_dir / "notes.json"
        self.sessions_file = self.data_dir / "conversations.json"
        self.attachments_file = self.data_dir / "attachments.json"
        self.notifications_file = self.data_dir / "notifications_state.json"

        # Directories
        self.attachments_dir = self.data_dir / "attachments"
        self.attachments_dir.mkdir(exist_ok=True)
        self.exports_dir = self.data_dir / "exports"
        self.exports_dir.mkdir(exist_ok=True)

        # Memory store in memory
        self.goals: List[Dict[str, Any]] = []
        self.tasks: List[Dict[str, Any]] = []
        self.archive: List[Dict[str, Any]] = []
        self.projects: List[Dict[str, Any]] = []
        self.habits: List[Dict[str, Any]] = []
        self.context: Dict[str, Any] = {}
        self.journal: List[Dict[str, Any]] = []
        self.notes: List[Dict[str, Any]] = []
        self.conversations: List[Dict[str, Any]] = []
        self.attachments: List[Dict[str, Any]] = []
        self.notifications_state: Dict[str, Any] = {}

        # Undo stack: max 5 reversible operations
        self.undo_stack: List[Dict[str, Any]] = []

        self.current_session_id = datetime.now().strftime("session_%Y%m%d_%H%M%S")
        self.load_all()

    # =========================================================================
    # PERSISTENCE HELPERS
    # =========================================================================

    def load_all(self):
        """Load all memory stores from disk."""
        self.goals = self._load_json(self.goals_file, [])
        self.tasks = self._load_json(self.tasks_file, [])
        self.archive = self._load_json(self.archive_file, [])
        self.projects = self._load_json(self.projects_file, [])
        self.habits = self._load_json(self.habits_file, [])
        self.context = self._load_json(self.context_file, {})
        self.journal = self._load_json(self.journal_file, [])
        self.notes = self._load_json(self.notes_file, [])
        self.conversations = self._load_json(self.sessions_file, [])
        self.attachments = self._load_json(self.attachments_file, [])
        self.notifications_state = self._load_json(self.notifications_file, {})

    def save_all(self):
        """Save all memory stores to disk."""
        self._save_json(self.goals_file, self.goals)
        self._save_json(self.tasks_file, self.tasks)
        self._save_json(self.archive_file, self.archive)
        self._save_json(self.projects_file, self.projects)
        self._save_json(self.habits_file, self.habits)
        self._save_json(self.context_file, self.context)
        self._save_json(self.journal_file, self.journal)
        self._save_json(self.notes_file, self.notes)
        self._save_json(self.sessions_file, self.conversations)
        self._save_json(self.attachments_file, self.attachments)
        self._save_json(self.notifications_file, self.notifications_state)

    def _load_json(self, filepath: Path, default: Any) -> Any:
        if filepath.exists():
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️ Warning: Could not load {filepath.name}: {e}")
                return default
        return default

    def _save_json(self, filepath: Path, data: Any):
        def _default_encoder(obj):
            if hasattr(obj, "model_dump"):
                return obj.model_dump()
            if hasattr(obj, "dict"):
                return obj.dict()
            if hasattr(obj, "type") and obj.type == "text":
                return {"type": "text", "text": getattr(obj, "text", "")}
            if hasattr(obj, "type") and obj.type == "tool_use":
                return {
                    "type": "tool_use",
                    "id": getattr(obj, "id", ""),
                    "name": getattr(obj, "name", ""),
                    "input": getattr(obj, "input", {})
                }
            if hasattr(obj, "__dict__"):
                return obj.__dict__
            return str(obj)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=_default_encoder)

    def _get_next_id(self, collection: List[Dict[str, Any]]) -> int:
        """Safely compute next sequential ID."""
        if not collection:
            return 1
        ids = [item.get("id", 0) for item in collection if isinstance(item.get("id"), int)]
        return max(ids, default=0) + 1

    def parse_natural_date(self, date_str: Optional[str]) -> Optional[str]:
        """
        Parse natural language date (e.g. 'tomorrow', 'next Friday', 'in 3 days', 'Sep 5', '5pm next monday')
        and return a clean formatted date string (YYYY-MM-DD or YYYY-MM-DD HH:MM).
        """
        if not date_str:
            return None
        s = str(date_str).strip()
        if not s:
            return None
        if dateparser:
            try:
                dt = dateparser.parse(
                    s,
                    settings={
                        "PREFER_DATES_FROM": "future",
                        "RELATIVE_BASE": datetime.now()
                    }
                )
                if dt:
                    if dt.hour != 0 or dt.minute != 0:
                        return dt.strftime("%Y-%m-%d %I:%M %p")
                    return dt.strftime("%Y-%m-%d")
            except Exception:
                pass
        return s

    def _parse_id_list(self, raw_input: Any) -> List[int]:
        """Parse comma-separated or space-separated ID strings like '1,2,3', '1, 2, 3', '1 2 3'."""
        if isinstance(raw_input, list):
            return [int(x) for x in raw_input if str(x).isdigit()]
        if isinstance(raw_input, int):
            return [raw_input]
        if not isinstance(raw_input, str):
            return []
        
        cleaned = raw_input.replace(",", " ").replace(";", " ")
        ids = []
        for token in cleaned.split():
            if token.isdigit():
                ids.append(int(token))
        return ids

    def _push_undo(self, description: str, action_type: str, data: Dict[str, Any]):
        """Push an operation onto the undo stack (keeps last 5 operations)."""
        self.undo_stack.append({
            "description": description,
            "action_type": action_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        })
        if len(self.undo_stack) > 5:
            self.undo_stack.pop(0)

    def undo(self) -> str:
        """Revert the most recent operation on the undo stack (up to 5 reversible operations)."""
        if not self.undo_stack:
            return "⚠️ Nothing to undo. Undo stack is empty."
        
        entry = self.undo_stack.pop()
        action_type = entry.get("action_type")
        data = entry.get("data", {})
        desc = entry.get("description", "Last operation")

        try:
            if action_type == "add_task":
                task_id = data.get("task_id")
                self.tasks = [t for t in self.tasks if t.get("id") != task_id]
                self._save_json(self.tasks_file, self.tasks)
                return f"↩️ Undone: {desc} (Task #{task_id} removed)."

            elif action_type == "complete_task":
                task_id = data.get("task_id")
                prev_status = data.get("prev_status", "pending")
                prev_completed_at = data.get("prev_completed_at")
                task = next((t for t in self.tasks if t.get("id") == task_id), None)
                if task:
                    task["status"] = prev_status
                    if prev_completed_at:
                        task["completed_at"] = prev_completed_at
                    elif "completed_at" in task:
                        del task["completed_at"]
                    self._save_json(self.tasks_file, self.tasks)
                    return f"↩️ Undone: {desc} (Task #{task_id} reverted to {prev_status})."
                return f"⚠️ Task #{task_id} no longer exists."

            elif action_type == "delete_task":
                restored_tasks = data.get("tasks", [])
                for t in restored_tasks:
                    if not any(curr.get("id") == t.get("id") for curr in self.tasks):
                        self.tasks.append(t)
                self._save_json(self.tasks_file, self.tasks)
                ids_str = ", ".join(str(t.get("id")) for t in restored_tasks)
                return f"↩️ Undone: {desc} (Restored task(s) #{ids_str})."

            elif action_type == "bulk_complete":
                prev_states = data.get("prev_states", {})
                for task_id_str, prev in prev_states.items():
                    tid = int(task_id_str)
                    task = next((t for t in self.tasks if t.get("id") == tid), None)
                    if task:
                        task["status"] = prev.get("status", "pending")
                        if prev.get("completed_at"):
                            task["completed_at"] = prev["completed_at"]
                        elif "completed_at" in task:
                            del task["completed_at"]
                self._save_json(self.tasks_file, self.tasks)
                return f"↩️ Undone: {desc}."

            elif action_type in ["clear_completed", "archive_completed"]:
                cleared_tasks = data.get("tasks", [])
                for t in cleared_tasks:
                    if not any(curr.get("id") == t.get("id") for curr in self.tasks):
                        self.tasks.append(t)
                if action_type == "archive_completed":
                    archived_ids = {t.get("id") for t in cleared_tasks}
                    self.archive = [a for a in self.archive if a.get("id") not in archived_ids]
                    self._save_json(self.archive_file, self.archive)
                self._save_json(self.tasks_file, self.tasks)
                return f"↩️ Undone: {desc} (Restored {len(cleared_tasks)} task(s))."

            elif action_type == "archive_task":
                task_data = data.get("task")
                if task_data:
                    if not any(curr.get("id") == task_data.get("id") for curr in self.tasks):
                        self.tasks.append(task_data)
                    self.archive = [a for a in self.archive if a.get("id") != task_data.get("id")]
                    self._save_json(self.tasks_file, self.tasks)
                    self._save_json(self.archive_file, self.archive)
                    return f"↩️ Undone: {desc} (Task #{task_data.get('id')} unarchived)."

            elif action_type == "update_task":
                task_id = data.get("task_id")
                prev_task = data.get("prev_task")
                task = next((t for t in self.tasks if t.get("id") == task_id), None)
                if task and prev_task:
                    task.clear()
                    task.update(prev_task)
                    self._save_json(self.tasks_file, self.tasks)
                    return f"↩️ Undone: {desc} (Task #{task_id} state restored)."

            elif action_type == "add_habit":
                habit_id = data.get("habit_id")
                self.habits = [h for h in self.habits if h.get("id") != habit_id]
                self._save_json(self.habits_file, self.habits)
                return f"↩️ Undone: {desc} (Habit #{habit_id} removed)."

            elif action_type == "delete_habit":
                restored_habit = data.get("habit")
                if restored_habit:
                    self.habits.append(restored_habit)
                    self._save_json(self.habits_file, self.habits)
                    return f"↩️ Undone: {desc} (Habit #{restored_habit.get('id')} restored)."

            elif action_type == "log_habit":
                habit_id = data.get("habit_id")
                prev_log = data.get("prev_log", [])
                prev_streak = data.get("prev_streak", 0)
                habit = next((h for h in self.habits if h.get("id") == habit_id), None)
                if habit:
                    habit["log"] = prev_log
                    habit["streak"] = prev_streak
                    self._save_json(self.habits_file, self.habits)
                    return f"↩️ Undone: {desc} (Habit #{habit_id} log reset)."

            elif action_type == "add_goal":
                goal_id = data.get("goal_id")
                self.goals = [g for g in self.goals if g.get("id") != goal_id]
                self._save_json(self.goals_file, self.goals)
                return f"↩️ Undone: {desc} (Goal #{goal_id} removed)."

            elif action_type == "delete_goal":
                restored_goal = data.get("goal")
                if restored_goal:
                    self.goals.append(restored_goal)
                    self._save_json(self.goals_file, self.goals)
                    return f"↩️ Undone: {desc} (Goal #{restored_goal.get('id')} restored)."

            elif action_type == "add_note":
                note_id = data.get("note_id")
                self.notes = [n for n in self.notes if n.get("id") != note_id]
                self._save_json(self.notes_file, self.notes)
                return f"↩️ Undone: {desc} (Note #{note_id} removed)."

            elif action_type == "delete_note":
                restored_note = data.get("note")
                if restored_note:
                    self.notes.append(restored_note)
                    self._save_json(self.notes_file, self.notes)
                    return f"↩️ Undone: {desc} (Note #{restored_note.get('id')} restored)."

            return f"↩️ Undone: {desc}."
        except Exception as e:
            return f"❌ Error during undo: {str(e)}"

    # =========================================================================
    # CONVERSATION & SESSION MEMORY
    # =========================================================================

    def save_session_history(self, history: List[Dict[str, Any]]):
        """Persist or update the current conversation session."""
        session_entry = next((s for s in self.conversations if s.get("id") == self.current_session_id), None)
        timestamp = datetime.now().isoformat()

        if session_entry:
            session_entry["messages"] = history
            session_entry["updated_at"] = timestamp
        else:
            self.conversations.append({
                "id": self.current_session_id,
                "created_at": timestamp,
                "updated_at": timestamp,
                "messages": history
            })

        # Keep last 10 sessions on disk to prevent unlimited file bloat
        if len(self.conversations) > 10:
            self.conversations = self.conversations[-10:]

        self._save_json(self.sessions_file, self.conversations)

    def load_latest_session(self) -> List[Dict[str, Any]]:
        """Load messages from the most recent session if available."""
        if self.conversations:
            latest = self.conversations[-1]
            self.current_session_id = latest.get("id", self.current_session_id)
            return latest.get("messages", [])
        return []

    def start_new_session(self) -> str:
        """Start a new distinct session ID."""
        self.current_session_id = datetime.now().strftime("session_%Y%m%d_%H%M%S")
        return self.current_session_id

    def compact_history(self, history: List[Dict[str, Any]], max_messages: int = 14) -> List[Dict[str, Any]]:
        """Keep the recent messages intact while ensuring message history doesn't explode."""
        if len(history) <= max_messages:
            return history
        
        cutoff = len(history) - max_messages
        while cutoff < len(history) and history[cutoff].get("role") != "user":
            cutoff += 1
        return history[cutoff:]

    # =========================================================================
    # COMPREHENSIVE PROMPT SUMMARY BUILDER
    # =========================================================================

    def get_user_data_summary(self) -> str:
        """
        Generate a complete, structured summary of user memory for the system prompt.
        Fixes context injection, priority groupings, deliverables, and streaks.
        """
        sections = []

        # 1. USER PROFILE & CONTEXT (Crucial Fix!)
        if self.context:
            context_lines = ["## USER PROFILE & PERSONAL CONTEXT"]
            for key, val in self.context.items():
                label = key.replace("_", " ").title()
                context_lines.append(f"- **{label}**: {val}")
            sections.append("\n".join(context_lines))

        # 2. GOALS
        if self.goals:
            goal_lines = ["## ACTIVE GOALS"]
            for g in self.goals:
                status_icon = "🟢" if g.get("status") == "active" else "⚪"
                deadline_str = f" (Deadline: {g.get('deadline')})" if g.get("deadline") else ""
                goal_lines.append(f"{status_icon} [ID #{g['id']}] **{g.get('title')}** [{g.get('category', 'general')}]{deadline_str} - Status: {g.get('status')}")
                if g.get("milestones"):
                    for m in g.get("milestones", []):
                        goal_lines.append(f"    • Milestone: {m}")
            sections.append("\n".join(goal_lines))

        # 3. PROJECTS
        if self.projects:
            proj_lines = ["## ACTIVE PROJECTS"]
            for p in self.projects:
                goal_ref = f" (Linked to: {p.get('goal')})" if p.get("goal") else ""
                proj_lines.append(f"📁 [ID #{p['id']}] **{p.get('name')}** - Status: {p.get('status', 'active')}{goal_ref}")
                if p.get("deliverables"):
                    for d in p.get("deliverables", [])[:4]:
                        proj_lines.append(f"    - {d}")
            sections.append("\n".join(proj_lines))

        # 4. TASKS (Grouped by Priority & Status)
        pending_tasks = [t for t in self.tasks if t.get("status") != "completed"]
        completed_tasks = [t for t in self.tasks if t.get("status") == "completed"]

        if self.tasks:
            task_lines = [f"## TASKS ({len(pending_tasks)} Pending, {len(completed_tasks)} Completed)"]

            # Sort pending by priority order
            priority_weights = {"urgent": 4, "high": 3, "medium": 2, "low": 1}
            sorted_pending = sorted(
                pending_tasks,
                key=lambda x: priority_weights.get(x.get("priority", "medium").lower(), 2),
                reverse=True
            )

            for t in sorted_pending:
                prio = t.get("priority", "medium").upper()
                deadline = f" | Due: {t.get('deadline')}" if t.get("deadline") else ""
                proj = f" | Project: {t.get('project')}" if t.get("project") else ""
                task_lines.append(f"• [ID #{t['id']}] [{prio}] **{t.get('title')}**{deadline}{proj}")

            if completed_tasks:
                task_lines.append("\n*Recent Completed:*")
                for t in completed_tasks[-3:]:
                    task_lines.append(f"  ✓ [ID #{t['id']}] {t.get('title')} (Done: {t.get('completed_at', 'N/A')[:10]})")

            sections.append("\n".join(task_lines))

        # 5. HABITS
        if self.habits:
            today_str = date.today().isoformat()
            habit_lines = ["## HABITS TRACKER"]
            for h in self.habits:
                logs = h.get("log", [])
                done_today = any(l.get("date") == today_str and l.get("completed") for l in logs)
                status_str = "✅ Done today" if done_today else "⏳ Pending today"
                habit_lines.append(f"🔁 [ID #{h['id']}] **{h.get('name')}** ({h.get('frequency', 'daily')}) | Streak: 🔥 {h.get('streak', 0)} days | {status_str}")
            sections.append("\n".join(habit_lines))

        # 6. RECENT JOURNAL / DAILY REVIEWS
        if self.journal:
            journal_lines = ["## RECENT DAILY REVIEWS & LOGS"]
            for entry in self.journal[-2:]:
                journal_lines.append(f"📝 **{entry.get('date')}**: {entry.get('summary', '')}")
                if entry.get("wins"):
                    journal_lines.append(f"   - Wins: {', '.join(entry.get('wins', []))}")
                if entry.get("blockers"):
                    journal_lines.append(f"   - Blockers: {entry.get('blockers')}")
            sections.append("\n".join(journal_lines))

        # 7. KNOWLEDGE BASE / NOTES
        if self.notes:
            note_lines = ["## KNOWLEDGE BASE & SAVED NOTES"]
            for n in self.notes[-5:]:
                tags = f" [{', '.join(n.get('tags', []))}]" if n.get("tags") else ""
                note_lines.append(f"💡 [ID #{n['id']}] **{n.get('title')}**{tags}: {n.get('content')[:120]}...")
            sections.append("\n".join(note_lines))

        if not sections:
            return "No data recorded yet."

        return "\n\n".join(sections)

    # =========================================================================
    # GOALS CRUD
    # =========================================================================

    def add_goal(self, title: str, description: str, category: str = "general",
                 deadline: Optional[str] = None, milestones: Optional[List[str]] = None) -> Dict[str, Any]:
        parsed_deadline = self.parse_natural_date(deadline) if deadline else deadline
        goal = {
            "id": self._get_next_id(self.goals),
            "title": title,
            "description": description,
            "category": category,
            "deadline": parsed_deadline,
            "milestones": milestones or [],
            "status": "active",
            "created_at": datetime.now().isoformat()
        }