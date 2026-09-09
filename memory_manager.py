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
        self.goals.append(goal)
        self._save_json(self.goals_file, self.goals)
        self._push_undo(
            description=f"Added goal #{goal['id']} '{goal['title']}'",
            action_type="add_goal",
            data={"goal_id": goal["id"]}
        )
        return goal

    def update_goal(self, goal_id: int, **updates) -> Optional[Dict[str, Any]]:
        goal = next((g for g in self.goals if g.get("id") == goal_id), None)
        if goal:
            if "deadline" in updates and updates["deadline"]:
                updates["deadline"] = self.parse_natural_date(updates["deadline"])
            for k, v in updates.items():
                if v is not None:
                    goal[k] = v
            goal["updated_at"] = datetime.now().isoformat()
            self._save_json(self.goals_file, self.goals)
            return goal
        return None

    def delete_goal(self, goal_id: int) -> bool:
        goal = next((g for g in self.goals if g.get("id") == goal_id), None)
        if goal:
            self.goals = [g for g in self.goals if g.get("id") != goal_id]
            self._save_json(self.goals_file, self.goals)
            self._push_undo(
                description=f"Deleted goal #{goal_id} '{goal.get('title')}'",
                action_type="delete_goal",
                data={"goal": goal}
            )
            return True
        return False

    # =========================================================================
    # TASKS CRUD & SEARCH
    # =========================================================================

    def add_task(self, title: str, description: str = "", priority: str = "medium",
                 deadline: Optional[str] = None, project: Optional[str] = None,
                 goal: Optional[str] = None) -> Dict[str, Any]:
        parsed_deadline = self.parse_natural_date(deadline) if deadline else deadline
        task = {
            "id": self._get_next_id(self.tasks),
            "title": title,
            "description": description,
            "priority": priority.lower(),
            "deadline": parsed_deadline,
            "project": project,
            "goal": goal,
            "status": "pending",
            "created_at": datetime.now().isoformat()
        }
        self.tasks.append(task)
        self._save_json(self.tasks_file, self.tasks)
        self._push_undo(
            description=f"Added task #{task['id']} '{task['title']}'",
            action_type="add_task",
            data={"task_id": task["id"]}
        )
        return task

    def complete_task(self, task_id: int) -> Optional[Dict[str, Any]]:
        """Fixes bug: uses exact ID match rather than list index offset!"""
        task = next((t for t in self.tasks if t.get("id") == task_id), None)
        if task:
            prev_status = task.get("status", "pending")
            prev_completed_at = task.get("completed_at")
            task["status"] = "completed"
            task["completed_at"] = datetime.now().isoformat()
            self._save_json(self.tasks_file, self.tasks)
            self._push_undo(
                description=f"Marked task #{task_id} '{task['title']}' as completed",
                action_type="complete_task",
                data={"task_id": task_id, "prev_status": prev_status, "prev_completed_at": prev_completed_at}
            )
            return task
        return None

    def update_task(self, task_id: int, **updates) -> Optional[Dict[str, Any]]:
        task = next((t for t in self.tasks if t.get("id") == task_id), None)
        if task:
            prev_task = dict(task)
            if "deadline" in updates and updates["deadline"]:
                updates["deadline"] = self.parse_natural_date(updates["deadline"])
            for k, v in updates.items():
                if v is not None:
                    task[k] = v
            task["updated_at"] = datetime.now().isoformat()
            self._save_json(self.tasks_file, self.tasks)
            self._push_undo(
                description=f"Updated task #{task_id} '{task.get('title')}'",
                action_type="update_task",
                data={"task_id": task_id, "prev_task": prev_task}
            )
            return task
        return None

    def delete_task(self, task_id: int) -> bool:
        task = next((t for t in self.tasks if t.get("id") == task_id), None)
        if task:
            self.tasks = [t for t in self.tasks if t.get("id") != task_id]
            self._save_json(self.tasks_file, self.tasks)
            self._push_undo(
                description=f"Deleted task #{task_id} '{task.get('title')}'",
                action_type="delete_task",
                data={"tasks": [task]}
            )
            return True
        return False

    def search_tasks(self, query: str = "", status: Optional[str] = None, priority: Optional[str] = None) -> List[Dict[str, Any]]:
        results = []
        q = query.lower()
        for t in self.tasks:
            if status and t.get("status") != status:
                continue
            if priority and t.get("priority") != priority.lower():
                continue
            if not query or q in t.get("title", "").lower() or q in t.get("description", "").lower():
                results.append(t)
        return results

    # =========================================================================
    # PROJECTS CRUD
    # =========================================================================

    def add_project(self, name: str, description: str, goal: Optional[str] = None,
                    deliverables: Optional[List[str]] = None) -> Dict[str, Any]:
        project = {
            "id": self._get_next_id(self.projects),
            "name": name,
            "description": description,
            "goal": goal,
            "deliverables": deliverables or [],
            "status": "active",
            "created_at": datetime.now().isoformat()
        }
        self.projects.append(project)
        self._save_json(self.projects_file, self.projects)
        return project

    def update_project(self, project_id: int, **updates) -> Optional[Dict[str, Any]]:
        project = next((p for p in self.projects if p.get("id") == project_id), None)
        if project:
            for k, v in updates.items():
                if v is not None:
                    project[k] = v
            project["updated_at"] = datetime.now().isoformat()
            self._save_json(self.projects_file, self.projects)
            return project
        return None

    # =========================================================================
    # HABITS CRUD
    # =========================================================================

    def add_habit(self, name: str, frequency: str = "daily", goal: Optional[str] = None) -> Dict[str, Any]:
        habit = {
            "id": self._get_next_id(self.habits),
            "name": name,
            "frequency": frequency,
            "goal": goal,
            "streak": 0,
            "log": [],
            "created_at": datetime.now().isoformat()
        }
        self.habits.append(habit)
        self._save_json(self.habits_file, self.habits)
        self._push_undo(
            description=f"Added habit #{habit['id']} '{habit['name']}'",
            action_type="add_habit",
            data={"habit_id": habit["id"]}
        )
        return habit

    def log_habit(self, habit_id: int, completed: bool) -> Optional[Dict[str, Any]]:
        """Fixes bug: uses exact ID match rather than list index offset!"""
        habit = next((h for h in self.habits if h.get("id") == habit_id), None)
        if habit:
            today = date.today().isoformat()
            if "log" not in habit:
                habit["log"] = []
            
            prev_log = [dict(l) for l in habit.get("log", [])]
            prev_streak = habit.get("streak", 0)

            existing_today = next((l for l in habit["log"] if l.get("date") == today), None)
            if existing_today:
                existing_today["completed"] = completed
            else:
                habit["log"].append({
                    "date": today,
                    "completed": completed
                })

            if completed:
                habit["streak"] = habit.get("streak", 0) + 1
            else:
                habit["streak"] = 0

            self._save_json(self.habits_file, self.habits)
            self._push_undo(
                description=f"Logged habit #{habit_id} '{habit['name']}' (completed={completed})",
                action_type="log_habit",
                data={"habit_id": habit_id, "prev_log": prev_log, "prev_streak": prev_streak}
            )
            return habit
        return None

    def delete_habit(self, habit_id: int) -> bool:
        habit = next((h for h in self.habits if h.get("id") == habit_id), None)
        if habit:
            self.habits = [h for h in self.habits if h.get("id") != habit_id]
            self._save_json(self.habits_file, self.habits)
            self._push_undo(
                description=f"Deleted habit #{habit_id} '{habit.get('name')}'",
                action_type="delete_habit",
                data={"habit": habit}
            )
            return True
        return False

    # =========================================================================
    # USER CONTEXT / PROFILE
    # =========================================================================

    def update_context(self, key: str, value: Any) -> Dict[str, Any]:
        self.context[key] = value
        self._save_json(self.context_file, self.context)
        return self.context

    def delete_context(self, key: str) -> bool:
        if key in self.context:
            del self.context[key]
            self._save_json(self.context_file, self.context)
            return True
        return False

    # =========================================================================
    # EPISODIC MEMORY: JOURNAL & DAILY REVIEWS
    # =========================================================================

    def add_journal_entry(self, summary: str, wins: Optional[List[str]] = None,
                          blockers: Optional[str] = None, hours_studied: Optional[float] = None,
                          focus_tomorrow: Optional[str] = None) -> Dict[str, Any]:
        entry = {
            "id": self._get_next_id(self.journal),
            "date": date.today().isoformat(),
            "summary": summary,
            "wins": wins or [],
            "blockers": blockers or "",
            "hours_studied": hours_studied,
            "focus_tomorrow": focus_tomorrow,
            "created_at": datetime.now().isoformat()
        }
        self.journal.append(entry)
        self._save_json(self.journal_file, self.journal)
        return entry

    def get_recent_journal(self, days: int = 7) -> List[Dict[str, Any]]:
        return self.journal[-days:] if self.journal else []

    # =========================================================================
    # KNOWLEDGE BASE & NOTES (SEMANTIC MEMORY)
    # =========================================================================

    def save_note(self, title: str, content: str, category: str = "general",
                  tags: Optional[List[str]] = None) -> Dict[str, Any]:
        note = {
            "id": self._get_next_id(self.notes),
            "title": title,
            "content": content,
            "category": category,
            "tags": tags or [],
            "created_at": datetime.now().isoformat()
        }
        self.notes.append(note)
        self._save_json(self.notes_file, self.notes)
        self._push_undo(
            description=f"Saved note #{note['id']} '{note['title']}'",
            action_type="add_note",
            data={"note_id": note["id"]}
        )
        return note

    def search_notes(self, query: str = "", tag: Optional[str] = None) -> List[Dict[str, Any]]:
        q = query.lower()
        results = []
        for n in self.notes:
            if tag and tag.lower() not in [t.lower() for t in n.get("tags", [])]:
                continue
            if not query or q in n.get("title", "").lower() or q in n.get("content", "").lower():
                results.append(n)
        return results

    def delete_note(self, note_id: int) -> bool:
        note = next((n for n in self.notes if n.get("id") == note_id), None)
        if note:
            self.notes = [n for n in self.notes if n.get("id") != note_id]
            self._save_json(self.notes_file, self.notes)
            self._push_undo(
                description=f"Deleted note #{note_id} '{note.get('title')}'",
                action_type="delete_note",
                data={"note": note}
            )
            return True
        return False

    # =========================================================================
    # GLOBAL MULTI-STORE MEMORY SEARCH
    # =========================================================================

    def search_all_memory(self, query: str) -> Dict[str, List[Any]]:
        """Searches across tasks, goals, projects, notes, context, and journal entries."""
        q = query.lower()
        matches = {
            "tasks": [],
            "goals": [],
            "projects": [],
            "notes": [],
            "journal": [],
            "context": []
        }

        # Tasks
        for t in self.tasks:
            if q in t.get("title", "").lower() or q in t.get("description", "").lower():
                matches["tasks"].append(t)

        # Goals
        for g in self.goals:
            if q in g.get("title", "").lower() or q in g.get("description", "").lower():
                matches["goals"].append(g)

        # Projects
        for p in self.projects:
            if q in p.get("name", "").lower() or q in p.get("description", "").lower():
                matches["projects"].append(p)

        # Notes
        for n in self.notes:
            if q in n.get("title", "").lower() or q in n.get("content", "").lower():
                matches["notes"].append(n)

        # Journal
        for j in self.journal:
            if q in j.get("summary", "").lower() or q in j.get("blockers", "").lower():
                matches["journal"].append(j)

        # Context
        for k, v in self.context.items():
            if q in k.lower() or q in str(v).lower():
                matches["context"].append({k: v})

        # Remove empty categories
        return {k: v for k, v in matches.items() if v}

    # =========================================================================
    # PROACTIVE MORNING BRIEFING & SMART CONTEXT PRUNING
    # =========================================================================

    # =========================================================================
    # TEMPORAL INTELLIGENCE ENGINE
    # =========================================================================

    def _days_until(self, deadline_str: Optional[str]) -> Optional[int]:
        """Return days until deadline (negative = overdue).
        Handles ISO dates AND natural language: 'September 1, 2026', 'February 2028'.
        """
        if not deadline_str:
            return None
        s = str(deadline_str).strip()
        # ISO format: 2026-09-01
        try:
            dl = date.fromisoformat(s[:10])
            return (dl - date.today()).days
        except (ValueError, TypeError):
            pass
        # Full date: "September 1, 2026"
        try:
            dl = datetime.strptime(s, "%B %d, %Y").date()
            return (dl - date.today()).days
        except (ValueError, TypeError):
            pass
        # Month-year only: "February 2028"
        try:
            dl = datetime.strptime(s, "%B %Y").date()
            return (dl - date.today()).days
        except (ValueError, TypeError):
            pass
        # dateparser fallback
        if dateparser:
            try:
                dt = dateparser.parse(
                    s,
                    settings={"PREFER_DATES_FROM": "future", "RELATIVE_BASE": datetime.now()}
                )
                if dt:
                    return (dt.date() - date.today()).days
            except Exception:
                pass
        return None

    def _get_effective_priority(self, item: Dict[str, Any]) -> int:
        """
        Deadline-adjusted effective priority weight.
        Boosts priority score when deadline is approaching, regardless of set label.
        Returns int weight: urgent(4+) -> high(3) -> medium(2) -> low(1)
        """
        base_weights = {"urgent": 4, "high": 3, "medium": 2, "low": 1}
        base = base_weights.get(item.get("priority", "medium").lower(), 2)
        days = self._days_until(item.get("deadline"))

        if days is None:
            return base
        if days < 0:           # OVERDUE: always treat as max
            return 10
        if days == 0:          # DUE TODAY: +4 boost
            return base + 4
        if days <= 2:          # CRITICAL (<=2 days): +3 boost
            return base + 3
        if days <= 5:          # WARNING (<=5 days): +2 boost
            return base + 2
        if days <= 7:          # WATCH (<=7 days): +1 boost
            return base + 1
        return base

    def get_deadline_alerts(self) -> str:
        """
        Scan all tasks and goals for approaching or missed deadlines.
        Returns a formatted alert block to show in briefing / reminders.
        """
        overdue, today_due, critical, warning = [], [], [], []

        # Scan tasks
        for t in self.tasks:
            if t.get("status") == "completed":
                continue
            days = self._days_until(t.get("deadline"))
            if days is None:
                continue
            entry = f"[Task #{t['id']}] {t.get('title')}"
            if days < 0:
                overdue.append(f"{entry}  ({abs(days)}d OVERDUE!)")
            elif days == 0:
                today_due.append(f"{entry}  (Due TODAY)")
            elif days <= 2:
                critical.append(f"{entry}  (Due in {days}d)")
            elif days <= 7:
                warning.append(f"{entry}  (Due in {days}d)")

        # Scan goals
        for g in self.goals:
            if g.get("status") == "completed":
                continue
            days = self._days_until(g.get("deadline"))
            if days is None:
                continue
            entry = f"[Goal #{g['id']}] {g.get('title')}"
            if days < 0:
                overdue.append(f"{entry}  ({abs(days)}d OVERDUE!)")
            elif days == 0:
                today_due.append(f"{entry}  (Due TODAY)")
            elif days <= 2:
                critical.append(f"{entry}  (Due in {days}d)")
            elif days <= 7:
                warning.append(f"{entry}  (Due in {days}d)")

        if not any([overdue, today_due, critical, warning]):
            return "No approaching deadlines this week."

        lines = ["DEADLINE ALERTS:"]
        for a in overdue:
            lines.append(f"  OVERDUE  -> {a}")
        for a in today_due:
            lines.append(f"  TODAY    -> {a}")
        for a in critical:
            lines.append(f"  CRITICAL -> {a}")
        for a in warning:
            lines.append(f"  WARNING  -> {a}")
        return "\n".join(lines)

    def get_habit_adaptive_recommendations(self) -> str:
        """
        Analyze habit streaks and today's completion status to generate
        adaptive coaching messages tailored to Deepak's consistency patterns.
        """
        if not self.habits:
            return "ADAPTIVE HABIT COACHING:\n  No habits tracked yet."

        today_str = date.today().isoformat()
        recs = []
        fire_habits, at_risk, broken, building = [], [], [], []

        for h in self.habits:
            streak = h.get("streak", 0)
            done_today = any(
                l.get("date") == today_str and l.get("completed")
                for l in h.get("log", [])
            )
            completed_logs = [l for l in h.get("log", []) if l.get("completed")]
            if completed_logs:
                last_date_str = sorted(completed_logs, key=lambda x: x["date"])[-1]["date"]
                try:
                    days_since = (date.today() - date.fromisoformat(last_date_str)).days
                except Exception:
                    days_since = 999
            else:
                days_since = 999

            entry = (h["name"], streak, done_today, days_since)
            if streak >= 5 and done_today:
                fire_habits.append(entry)
            elif streak >= 3 and not done_today:
                at_risk.append(entry)
            elif days_since >= 3 and streak == 0:
                broken.append(entry)
            elif streak < 4 and not done_today:
                building.append(entry)

        if fire_habits:
            for name, streak, _, _ in fire_habits:
                recs.append(f"  GREAT STREAK: '{name}' -- {streak}d streak! Keep the fire burning!")
        if at_risk:
            for name, streak, _, _ in at_risk:
                recs.append(f"  AT RISK: '{name}' -- {streak}-day streak at risk! Don't break it today.")
        if broken:
            for name, _, _, days_since in broken:
                recs.append(f"  RESTART: '{name}' -- Not done in {days_since} days. Time to rebuild!")
        if building:
            for name, streak, _, _ in building:
                next_milestone = 7 if streak < 7 else (14 if streak < 14 else 30)
                recs.append(f"  BUILDING: '{name}' -- {streak}-day streak. Push to {next_milestone}!")
        if not recs:
            recs.append("  All habits on track today -- solid consistency!")

        return "ADAPTIVE HABIT COACHING:\n" + "\n".join(recs)

    # =========================================================================
    # BUILT-IN STUDY CALENDAR
    # =========================================================================

    def get_calendar_view(self) -> str:
        """
        Weekly calendar view with tasks plotted by day + milestone countdowns.
        Shows Mon-Sun of the current week, highlights today, plots task deadlines.
        """
        import datetime as _dt

        today = date.today()
        now = datetime.now()

        # Week boundaries: Monday = weekday 0
        week_start = today - _dt.timedelta(days=today.weekday())  # This Monday
        week_end   = week_start + _dt.timedelta(days=6)           # This Sunday

        month_str  = today.strftime("%B %Y")
        week_num   = today.isocalendar()[1]

        day_abbrs  = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
        day_emojis = ["📗", "📘", "📙", "📕", "📒", "📓", "🛋️"]
        study_slots = {
            0: "College (8-5) | DSA (5:30-8) + Java Core (8-10:30) + SQL (10:30-11)",
            1: "College (8-5) | DSA (5:30-8) + GATE DSA (8-10:30) + SQL (10:30-11)",
            2: "College (8-5) | DSA (5:30-8) + Java Core (8-10:30) + SQL (10:30-11)",
            3: "College (8-5) | DSA (5:30-8) + GATE DSA (8-10:30) + SQL (10:30-11)",
            4: "College (8-5) | DSA (5:30-8) + Java Core (8-10:30) + SQL (10:30-11)",
            5: "College (8-5) | DSA (5:30-8) + GATE DSA (8-10:30) + SQL (10:30-11)",
            6: "Rest Day — recharge completely 😴",
        }

        # Build a dict: date_str -> list of (priority, title) for pending tasks
        task_map: dict = {}
        pending = [t for t in self.tasks if t.get("status") != "completed"]
        for t in pending:
            days = self._days_until(t.get("deadline"))
            if days is None:
                continue
            dl_date = today + _dt.timedelta(days=days)
            dl_str  = dl_date.isoformat()
            if dl_str not in task_map:
                task_map[dl_str] = []
            task_map[dl_str].append(t)

        L = []

        # ── HEADER ────────────────────────────────────────────────────
        L.append("")
        L.append(f"📆  {month_str.upper()}  —  WEEK {week_num}")
        L.append("─" * 56)

        # ── DAY ROWS ──────────────────────────────────────────────────
        for i in range(7):
            day_date  = week_start + _dt.timedelta(days=i)
            day_str   = day_date.isoformat()
            abbr      = day_abbrs[i]
            emoji     = day_emojis[i]
            date_disp = day_date.strftime("%d %b")
            is_today  = (day_date == today)
            is_past   = (day_date < today)

            marker = " << TODAY" if is_today else ("" if not is_past else "  ✓ past")

            L.append("")
            header_line = f"  {emoji}  {abbr}  {date_disp}{marker}"
            L.append(header_line)

            # Study block
            slot = study_slots.get(i, "")
            if i < 6:
                L.append(f"        📚  {slot}")
            else:
                L.append(f"        {slot}")

            # Tasks due this day
            day_tasks = task_map.get(day_str, [])
            prio_weights = {"urgent": 4, "high": 3, "medium": 2, "low": 1}
            day_tasks_sorted = sorted(
                day_tasks,
                key=lambda x: prio_weights.get(x.get("priority", "medium"), 2),
                reverse=True
            )
            for t in day_tasks_sorted:
                prio = t.get("priority", "medium")
                dot = {"urgent": "🔴", "high": "🟠", "medium": "🟡"}.get(prio, "🟢")
                title = t.get("title", "")
                if len(title) > 42:
                    title = title[:39] + "..."
                L.append(f"        {dot}  {title}")

            if not day_tasks and i < 6:
                L.append(f"        ✅  Free — great for revision or extra practice")

        # ── WEEK SUMMARY BAR ──────────────────────────────────────────
        total_week_tasks = sum(
            len(task_map.get((week_start + _dt.timedelta(days=i)).isoformat(), []))
            for i in range(7)
        )
        L.append("")
        L.append("─" * 56)
        L.append(f"📊  This week: {total_week_tasks} task deadlines across 6 study days")
        L.append("")

        # ── MILESTONE COUNTDOWNS ──────────────────────────────────────
        L.append("⏳  MILESTONE COUNTDOWNS")
        L.append("─" * 56)

        milestones = []

        # Java deadline from context
        java_dl = self.context.get("september_goal", "")
        if "Sep" in java_dl or "September" in java_dl:
            java_date = _dt.date(today.year, 9, 30)
            java_days = (java_date - today).days
            bar = self._progress_bar(java_days, 30)
            milestones.append((java_days, f"🟠  Java Complete (Sep 30)   {bar}  {java_days}d left"))

        # GATE 2028 — February 1 2028 (approximate)
        gate_date = _dt.date(2028, 2, 1)
        gate_days = (gate_date - today).days
        gate_bar  = self._progress_bar(gate_days, 365 * 2)
        milestones.append((gate_days, f"🎯  GATE CSE 2028            {gate_bar}  {gate_days}d left"))

        # Days since study journey started (agent created Aug 30)
        start_date = _dt.date(2026, 8, 30)
        days_in = (today - start_date).days
        milestones.append((0, f"🌱  Study Journey            Day {days_in} in progress!"))

        # Check goals for custom deadlines
        for g in self.goals:
            dl = g.get("deadline")
            if not dl:
                continue
            gdays = self._days_until(dl)
            if gdays is None or gdays < 0 or gdays > 365 * 2:
                continue
            title = g.get("title", "Goal")[:28]
            bar   = self._progress_bar(gdays, 365)
            # Avoid duplicates with known milestones
            if "GATE" in title or "Java" in title or "Backend" in title:
                continue
            milestones.append((gdays, f"🏆  {title:<28} {bar}  {gdays}d left"))

        for _, line in milestones:
            L.append(f"  {line}")

        L.append("")
        L.append("─" * 56)
        L.append("💡  Commands:")
        L.append("    /cal       — refresh this calendar")
        L.append("    /tasks     — full task list with priorities")
        L.append("    /deadlines — detailed deadline alerts")
        L.append("")

        return "\n".join(L)

    def _progress_bar(self, days_left: int, total_days: int, width: int = 12) -> str:
        """Generate a compact ASCII progress bar showing time elapsed vs total."""
        if total_days <= 0:
            return "[" + "░" * width + "]"
        elapsed = max(0, total_days - days_left)
        filled  = int((elapsed / total_days) * width)
        filled  = min(filled, width)
        empty   = width - filled
        return "[" + "█" * filled + "░" * empty + "]"

    def get_morning_briefing(self) -> str:
        """Beautiful dashboard: Dashboard -> This Week -> Tomorrow -> Today -> What do you need?"""
        import datetime as _dt
        now = datetime.now()
        day_name = now.strftime("%A")
        date_str = now.strftime("%B %d, %Y")
        today = date.today()
        today_str = today.isoformat()
        tomorrow = today + _dt.timedelta(days=1)

        # Time-based greeting
        hour = now.hour
        if hour < 12:
            greeting, greet_emoji = "Good Morning", "🌅"
        elif hour < 17:
            greeting, greet_emoji = "Good Afternoon", "☀️"
        else:
            greeting, greet_emoji = "Good Evening", "🌙"

        name = self.context.get("name", "Deepak")
        pending = [t for t in self.tasks if t.get("status") != "completed"]
        completed_count = len([t for t in self.tasks if t.get("status") == "completed"])
        urgent_count = len([t for t in pending if t.get("priority") == "urgent"])
        high_count   = len([t for t in pending if t.get("priority") == "high"])

        L = []  # lines accumulator

        # ── HEADER ────────────────────────────────────────
        L.append(f"{greet_emoji}  {greeting}, {name}!")
        L.append(f"📅  {day_name}, {date_str}")
        L.append("─" * 52)

        # ── 1. THIS WEEK'S PLAN ───────────────────────────
        L.append("")
        L.append("📅  THIS WEEK'S PLAN")
        L.append("─" * 52)

        L.append("📚  Study Timetable  (Mon – Sat):")
        L.append("    🎓  College        ->  8:00 AM – 5:00 PM")
        L.append("    🌆  Evening 5:30   ->  Block 1: DSA Java (Pepcoding — 2.5h)")
        L.append("    🌙  Night 8:00     ->  Block 2: Java Core / GATE DSA Alternating (2.5h)")
        L.append("                           • Odd Days (Mon/Wed/Fri): Java Core (Coder Army)")
        L.append("                           • Even Days (Tue/Thu/Sat): DSA for GATE (Viswadeep Sir)")
        L.append("    ✨  Night 10:30    ->  Block 3: SQL One-shot Progress (30m)")
        L.append("    🛋  Sunday         ->  Complete Rest (No Study)")
        L.append("")
        L.append("🎯  Daily Targets This Week:")
        L.append("    💻  10 DSA Java videos    (Pepcoding — from basics)")
        L.append("    📹  1 Java video          (Coder Army — Mon/Wed/Fri)")
        L.append("    📖  1 GATE DSA video      (Viswadeep Sir — Tue/Thu/Sat)")
        L.append("    🗄  SQL one-shot progress (30m daily)")

        # ── 2. TOMORROW'S PLAN ────────────────────────────
        L.append("")
        L.append("─" * 52)
        L.append("🌙  TOMORROW'S PLAN")
        L.append("─" * 52)

        tomorrow_tasks = [t for t in pending if self._days_until(t.get("deadline")) == 1]
        if tomorrow_tasks:
            L.append("📌  Due tomorrow:")
            for t in tomorrow_tasks:
                prio = t.get("priority", "medium")
                icon = {"urgent": "🔴", "high": "🟠", "medium": "🟡"}.get(prio, "🟢")
                L.append(f"    {icon}  [Task #{t['id']}] {t.get('title')}")
        else:
            L.append("    ✨  No deadlines due tomorrow — great position!")

        L.append("")
        L.append("💡  Prep tonight:")
        L.append("    📝  Review today's notes before sleeping")
        L.append("    🎒  Plan which videos to watch tomorrow")
        L.append("    😴  Sleep by 11 PM for a fresh morning")

        # ── 3. TODAY'S PLAN ───────────────────────────────
        L.append("")
        L.append("─" * 52)
        L.append("☀️  TODAY'S PLAN")
        L.append("─" * 52)

        today_weekday = today.weekday()
        if today_weekday == 6:
            L.append("🛋️  Today's Routine: Sunday Complete Rest Day — relax and recharge!")
        elif today_weekday in [0, 2, 4]:
            day_label = "Monday" if today_weekday == 0 else ("Wednesday" if today_weekday == 2 else "Friday")
            L.append(f"📚  Today's Routine ({day_label} — Odd Day):")
            L.append("    🎓  8:00 AM – 5:00 PM  : College")
            L.append("    🌆  5:30 – 8:00 PM     : Block 1 — DSA Java (Pepcoding — 10 videos from basics)")
            L.append("    🟢  8:00 – 10:30 PM    : Block 2 — Java Core (Coder Army — 1 video)")
            L.append("    ✨  10:30 – 11:00 PM   : Block 3 — SQL One-shot progress (30 min)")
        else:
            day_label = "Tuesday" if today_weekday == 1 else ("Thursday" if today_weekday == 3 else "Saturday")
            L.append(f"📚  Today's Routine ({day_label} — Even Day):")
            L.append("    🎓  8:00 AM – 5:00 PM  : College")
            L.append("    🌆  5:30 – 8:00 PM     : Block 1 — DSA Java (Pepcoding — 10 videos from basics)")
            L.append("    🟢  8:00 – 10:30 PM    : Block 2 — DSA for GATE (Viswadeep Sir — 1 video)")
            L.append("    ✨  10:30 – 11:00 PM   : Block 3 — SQL One-shot progress (30 min)")

        # Habits with ID numbers
        if self.habits:
            L.append("")
            L.append("🔁  Habits Today:")
            for h in self.habits:
                done = any(
                    lg.get("date") == today_str and lg.get("completed")
                    for lg in h.get("log", [])
                )
                status = "✅  Done" if done else "⏳  Pending"
                streak_str = f" (🔥 {h.get('streak', 0)}d)" if h.get("streak", 0) > 0 else ""
                L.append(f"    [#{h['id']}] {status}  —  {h.get('name')}{streak_str}")

        # ── 4. PRIORITIES & DEADLINE RADAR ────────────────
        L.append("")
        L.append("─" * 52)
        L.append("⚡  PRIORITIES & DEADLINE RADAR")
        L.append("─" * 52)

        # 4a. Deadline Alerts
        alert_text = self.get_deadline_alerts()
        if "No approaching" not in alert_text:
            L.append("⏰  Deadline Alerts:")
            for al in alert_text.split("\n")[1:]:
                al = al.strip()
                if not al:
                    continue
                if "OVERDUE" in al:
                    L.append(f"    🔴  {al.replace('OVERDUE  ->', '').strip()}")
                elif "TODAY" in al:
                    L.append(f"    🟠  {al.replace('TODAY    ->', '').strip()}")
                elif "CRITICAL" in al:
                    L.append(f"    🟡  {al.replace('CRITICAL ->', '').strip()}")
                elif "WARNING" in al:
                    L.append(f"    🔵  {al.replace('WARNING  ->', '').strip()}")
            L.append("")
        else:
            L.append("⏰  Deadline Alerts:\n    ✨  No overdue or urgent deadlines!\n")

        # 4b. Top Priorities
        sorted_pending = sorted(pending, key=lambda x: self._get_effective_priority(x), reverse=True)
        if sorted_pending:
            L.append("🥇  Top Priorities:")
            medals = ["🥇", "🥈", "🥉"]
            for i, t in enumerate(sorted_pending[:3]):
                days = self._days_until(t.get("deadline"))
                if days is not None and days < 0:
                    urgency = f"  ⚠️ {abs(days)}d OVERDUE"
                elif days == 0:
                    urgency = "  ⚠️ Due TODAY"
                elif days is not None and days <= 2:
                    urgency = f"  ⚡ {days}d left"
                else:
                    urgency = f"  (Due: {t.get('deadline')})" if t.get("deadline") else ""
                medal = medals[i] if i < 3 else "   •"
                L.append(f"    {medal}  [Task #{t['id']}] {t.get('title')}{urgency}")
            L.append("")
        else:
            L.append("🥇  Top Priorities:\n    🎉  All caught up — add a task with /add-task!\n")

        # 4c. Tasks Due This Week
        week_tasks = []
        for t in pending:
            days = self._days_until(t.get("deadline"))
            if days is not None and 0 <= days <= 7:
                week_tasks.append((days, t))
        week_tasks.sort(key=lambda x: x[0])

        if week_tasks:
            L.append("📅  Tasks Due This Week:")
            for days_left, t in week_tasks[:6]:
                prio = t.get("priority", "medium")
                dot = {"urgent": "🔴", "high": "🟠", "medium": "🟡"}.get(prio, "🟢")
                due_label = "today" if days_left == 0 else ("tomorrow" if days_left == 1 else f"in {days_left} days")
                L.append(f"    {dot}  [Task #{t['id']}] {t.get('title')}  —  due {due_label}")
        else:
            L.append("📅  Tasks Due This Week:\n    ✨  No specific tasks due this week.")

        # ── 5. QUICK ACTIONS & SHORTCUTS ──────────────────
        L.append("")
        L.append("─" * 52)
        L.append("💬  QUICK ACTIONS & SHORTCUTS (Type Number or /cmd)")
        L.append("─" * 52)
        L.append("    [1]   🌅  Morning Briefing & Routine")
        L.append("    [2]   ⚡  Priorities & Deadline Radar")
        L.append("    [4]   📆  Weekly Study Calendar & Milestones")
        L.append("    [8]   📋  Pending Tasks List")
        L.append("    [10]  ✅  Check off completed tasks (e.g. 10 1,2)")
        L.append("    [18]  🔁  Habits Tracker (or 19 to log)")
        L.append("    [43]  📖  View ALL 43 Fast Commands (/help)")
        L.append("    [0]   🚪  Exit Agent")
        L.append("")
        L.append("    👉  Type any command number (0-43), /command, or chat with AI!")
        L.append("")

        return "\n".join(L)

    def get_pruned_context_summary(self, query: str = "") -> str:
        """
        Dynamically extracts ONLY relevant context sections based on query intent.
        Reduces prompt token payload by 50-70% for faster responses and lower cost.
        """
        q = query.lower()
        sections = []

        # 1. Compact User Profile (Essential facts only)
        if self.context:
            context_summary = f"👤 User: {self.context.get('name', 'User')} ({self.context.get('year', 'Student')})"
            if self.context.get("study_schedule"):
                context_summary += f"\n📅 Schedule: {self.context.get('study_schedule')}"
            sections.append(context_summary)

        # Classify query intent
        is_task_query = any(k in q for k in ["task", "todo", "plan", "today", "focus", "priority", "schedule", "do next", "work on", "week", "september"])
        is_goal_query = any(k in q for k in ["goal", "gate", "career", "milestone", "backend", "target", "roadmap"])
        is_habit_query = any(k in q for k in ["habit", "streak", "consistency", "routine", "daily"])
        is_note_query = any(k in q for k in ["note", "playlist", "link", "resource", "youtube", "video", "formula", "cheat sheet"])
        is_review_query = any(k in q for k in ["review", "yesterday", "progress", "week", "reflect", "journal"])

        # Default: provide high-level snapshot if ambiguous
        if not (is_task_query or is_goal_query or is_habit_query or is_note_query or is_review_query):
            is_task_query = True
            is_goal_query = True
            is_habit_query = True

        # Goals (Include active goals)
        if (is_goal_query or is_task_query) and self.goals:
            goal_lines = ["## GOALS"]
            for g in self.goals:
                if g.get("status") == "active":
                    deadline_str = f" (Due: {g.get('deadline')})" if g.get("deadline") else ""
                    goal_lines.append(f"- [ID #{g['id']}] {g.get('title')}{deadline_str}")
            sections.append("\n".join(goal_lines))

        # Tasks (Deadline-adjusted effective priority sort)
        if is_task_query and self.tasks:
            pending_tasks = [t for t in self.tasks if t.get("status") != "completed"]
            sorted_pending = sorted(
                pending_tasks,
                key=lambda x: self._get_effective_priority(x),
                reverse=True
            )
            task_lines = [f"## PENDING TASKS ({len(pending_tasks)} active)"]
            for t in sorted_pending[:8]:
                prio = t.get("priority", "medium").upper()
                days = self._days_until(t.get("deadline"))
                if days is not None and days < 0:
                    due = f" [!! {abs(days)}d OVERDUE]"
                elif days == 0:
                    due = " [!! DUE TODAY]"
                elif days is not None and days <= 2:
                    due = f" [>> {days}d left]"
                else:
                    due = f" (Due: {t.get('deadline')})" if t.get("deadline") else ""
                task_lines.append(f"- [ID #{t['id']}] [{prio}] {t.get('title')}{due}")
            sections.append("\n".join(task_lines))

            # Inject deadline alerts if any
            alert_text = self.get_deadline_alerts()
            if "No approaching" not in alert_text:
                sections.append(alert_text)

        # Habits
        if is_habit_query and self.habits:
            today_str = date.today().isoformat()
            habit_lines = ["## HABITS"]
            for h in self.habits:
                done = any(l.get("date") == today_str and l.get("completed") for l in h.get("log", []))
                status = "✅ Done" if done else "⏳ Pending"
                habit_lines.append(f"- [ID #{h['id']}] {h.get('name')} (🔥 {h.get('streak', 0)}d) | {status}")
            sections.append("\n".join(habit_lines))

        # Notes
        if is_note_query and self.notes:
            note_lines = ["## RELEVANT NOTES"]
            for n in self.notes[-3:]:
                note_lines.append(f"- [ID #{n['id']}] **{n.get('title')}**: {n.get('content')[:140]}...")
            sections.append("\n".join(note_lines))

        # Journal / Retrospectives
        if is_review_query and self.journal:
            journal_lines = ["## RECENT JOURNAL"]
            for j in self.journal[-2:]:
                journal_lines.append(f"- {j.get('date')}: {j.get('summary')}")
            sections.append("\n".join(journal_lines))

        return "\n\n".join(sections) if sections else "No user data recorded."

    # =========================================================================
    # FAST LOCAL CLI FORMATTERS & ACTION HELPERS
    # =========================================================================

    def get_tasks_formatted(self, status: str = "pending") -> str:
        """Return clean, instant formatted task list without LLM latency."""
        pending = [t for t in self.tasks if t.get("status") != "completed"]
        completed = [t for t in self.tasks if t.get("status") == "completed"]

        if status == "pending":
            if not pending:
                return "No pending tasks! You are all caught up."
            # Deadline-adjusted effective priority sort
            sorted_tasks = sorted(pending, key=lambda x: self._get_effective_priority(x), reverse=True)
            output = [f"PENDING TASKS ({len(pending)}):"]
            for t in sorted_tasks:
                prio = t.get("priority", "medium").upper()
                days = self._days_until(t.get("deadline"))
                if days is not None and days < 0:
                    due = f" | !! {abs(days)}d OVERDUE"
                elif days == 0:
                    due = " | !! DUE TODAY"
                elif days is not None and days <= 2:
                    due = f" | >> {days}d left"
                else:
                    due = f" | Due: {t.get('deadline')}" if t.get("deadline") else ""
                proj = f" | Project: {t.get('project')}" if t.get("project") else ""
                output.append(f"  [ID #{t['id']}] [{prio}] {t.get('title')}{due}{proj}")
            output.append("\nTip: Type '10 <id>' or '/done <id>' (e.g. 10 1 or /done 1) to mark complete instantly.")
            return "\n".join(output)

        elif status == "completed":
            if not completed:
                return "No completed tasks yet."
            output = [f"COMPLETED TASKS ({len(completed)}):"]
            for t in completed[-10:]:
                output.append(f"  [ID #{t['id']}] {t.get('title')} (Done: {t.get('completed_at', 'N/A')[:10]})")
            return "\n".join(output)

        return ""

    def get_goals_formatted(self) -> str:
        if not self.goals:
            return "No active goals found."
        output = ["🎯 ACTIVE GOALS:"]
        for g in self.goals:
            deadline = f" (Deadline: {g.get('deadline')})" if g.get("deadline") else ""
            output.append(f"\n  [ID #{g['id']}] **{g.get('title')}** [{g.get('category', 'general')}]{deadline}")
            if g.get("milestones"):
                for m in g.get("milestones", []):
                    output.append(f"     • Milestone: {m}")
        return "\n".join(output)

    def get_habits_formatted(self) -> str:
        if not self.habits:
            return "No habits tracked yet."
        today_str = date.today().isoformat()
        output = ["🔁 HABIT TRACKER:"]
        for h in self.habits:
            done = any(l.get("date") == today_str and l.get("completed") for l in h.get("log", []))
            status = "✅ Completed Today" if done else "⏳ Due Today"
            output.append(f"  • [ID #{h['id']}] {h.get('name')} ({h.get('frequency', 'daily')}) | Streak: 🔥 {h.get('streak', 0)} days | {status}")
        output.append("\n💡 Tip: Type '19 <id>' or '/log <id>' to toggle habit completion for today.")
        return "\n".join(output)

    def get_notes_formatted(self) -> str:
        if not self.notes:
            return "No saved notes found."
        output = ["💡 KNOWLEDGE BASE & SAVED NOTES:"]
        for n in self.notes:
            tags = f" [{', '.join(n.get('tags', []))}]" if n.get("tags") else ""
            output.append(f"\n  [ID #{n['id']}] **{n.get('title')}**{tags}:")
            output.append(f"  {n.get('content')}")
        return "\n".join(output)

    def quick_complete_task(self, task_id: int) -> str:
        task = self.complete_task(task_id)
        if task:
            return f"✅ Task #{task_id} '{task['title']}' marked as COMPLETED! 🎉"
        return f"❌ Task with ID {task_id} not found."

    def quick_complete_tasks(self, task_ids: List[int]) -> str:
        """Complete multiple tasks in a single bulk operation."""
        if not task_ids:
            return "⚠️ No valid task IDs provided."
        if len(task_ids) == 1:
            return self.quick_complete_task(task_ids[0])
        
        completed_names = []
        not_found = []
        prev_states = {}
        
        for tid in task_ids:
            t = next((task for task in self.tasks if task.get("id") == tid), None)
            if t:
                prev_states[str(tid)] = {"status": t.get("status"), "completed_at": t.get("completed_at")}
                t["status"] = "completed"
                t["completed_at"] = datetime.now().isoformat()
                completed_names.append(f"#{tid} '{t.get('title')}'")
            else:
                not_found.append(str(tid))
        
        if completed_names:
            self._save_json(self.tasks_file, self.tasks)
            self._push_undo(
                description=f"Bulk completed {len(completed_names)} task(s)",
                action_type="bulk_complete",
                data={"prev_states": prev_states}
            )
        
        msg = f"🎉 Completed {len(completed_names)} task(s): {', '.join(completed_names)}"
        if not_found:
            msg += f"\n⚠️ Tasks not found: {', '.join(not_found)}"
        return msg

    def quick_add_task(self, title: str, priority: str = "medium", deadline: Optional[str] = None) -> str:
        task = self.add_task(title=title, priority=priority, deadline=deadline)
        deadline_msg = f" (Due: {task['deadline']})" if task.get('deadline') else ""
        return f"✅ Task #{task['id']} '{task['title']}' added ([{task['priority'].upper()} priority]{deadline_msg})."

    def quick_delete_task(self, task_id: int, archive: bool = False) -> str:
        if archive:
            archived = self.archive_task(task_id)
            if archived:
                return f"📁 Task #{task_id} '{archived.get('title')}' moved to archive.json."
            return f"❌ Task #{task_id} not found."
        ok = self.delete_task(task_id)
        if ok:
            return f"🗑️ Task #{task_id} deleted."
        return f"❌ Task #{task_id} not found."

    def quick_delete_tasks(self, task_ids: List[int], archive: bool = False) -> str:
        """Delete or archive multiple tasks in a single bulk operation."""
        if not task_ids:
            return "⚠️ No valid task IDs provided."
        if len(task_ids) == 1:
            return self.quick_delete_task(task_ids[0], archive=archive)

        if archive:
            archived_items = []
            not_found = []
            for tid in task_ids:
                res = self.archive_task(tid)
                if res:
                    archived_items.append(f"#{tid} '{res.get('title')}'")
                else:
                    not_found.append(str(tid))
            msg = f"📁 Archived {len(archived_items)} task(s) to archive.json: {', '.join(archived_items)}"
            if not_found:
                msg += f"\n⚠️ Tasks not found: {', '.join(not_found)}"
            return msg

        deleted_tasks = []
        not_found = []
        for tid in task_ids:
            t = next((task for task in self.tasks if task.get("id") == tid), None)
            if t:
                deleted_tasks.append(t)
                self.tasks = [task for task in self.tasks if task.get("id") != tid]
            else:
                not_found.append(str(tid))
        
        if deleted_tasks:
            self._save_json(self.tasks_file, self.tasks)
            self._push_undo(
                description=f"Deleted {len(deleted_tasks)} task(s)",
                action_type="delete_task",
                data={"tasks": deleted_tasks}
            )
        
        ids_str = ", ".join(f"#{t.get('id')}" for t in deleted_tasks)
        msg = f"🗑️ Deleted {len(deleted_tasks)} task(s): {ids_str}"
        if not_found:
            msg += f"\n⚠️ Tasks not found: {', '.join(not_found)}"
        return msg

    def quick_set_task_priority(self, task_id: int, priority: str) -> str:
        prio = priority.lower()
        if prio not in ["urgent", "high", "medium", "low"]:
            return "⚠️ Priority must be: urgent, high, medium, or low."
        task = self.update_task(task_id, priority=prio)
        if task:
            return f"⚡ Task #{task_id} priority updated to [{prio.upper()}]."
        return f"❌ Task #{task_id} not found."

    def quick_set_task_deadline(self, task_id: int, deadline: str) -> str:
        parsed_dl = self.parse_natural_date(deadline)
        task = self.update_task(task_id, deadline=parsed_dl)
        if task:
            return f"📅 Task #{task_id} deadline set to '{task.get('deadline')}'."
        return f"❌ Task #{task_id} not found."

    def quick_clear_completed_tasks(self, archive: bool = False) -> str:
        """Clear completed tasks, optionally moving them to archive.json."""
        completed = [t for t in self.tasks if t.get("status") == "completed"]
        if not completed:
            return "✨ No completed tasks to clear."
        
        if archive:
            archived = self.archive_completed_tasks()
            return f"📁 Archived {len(archived)} completed task(s) to archive.json."
        
        self.tasks = [t for t in self.tasks if t.get("status") != "completed"]
        self._save_json(self.tasks_file, self.tasks)
        self._push_undo(
            description=f"Cleared {len(completed)} completed task(s)",
            action_type="clear_completed",
            data={"tasks": completed}
        )
        return f"🧹 Cleared {len(completed)} completed task(s)."

    def quick_log_habit(self, habit_id: int, completed: bool = True) -> str:
        habit = self.log_habit(habit_id, completed)
        if habit:
            status = "logged" if completed else "reset"
            return f"🔁 Habit #{habit_id} '{habit['name']}' {status}! Current streak: 🔥 {habit.get('streak', 0)} days."
        return f"❌ Habit with ID {habit_id} not found."

    def quick_unlog_habit(self, habit_id: int) -> str:
        return self.quick_log_habit(habit_id, completed=False)

    def quick_add_habit(self, name: str, frequency: str = "daily", goal: Optional[str] = None) -> str:
        habit = self.add_habit(name=name, frequency=frequency, goal=goal)
        return f"🔁 Habit #{habit['id']} '{habit['name']}' added to tracker!"

    def quick_delete_habit(self, habit_id: int) -> str:
        ok = self.delete_habit(habit_id)
        if ok:
            return f"🗑️ Habit #{habit_id} deleted."
        return f"❌ Habit #{habit_id} not found."

    def quick_complete_goal(self, goal_id: int) -> str:
        goal = self.update_goal(goal_id, status="completed")
        if goal:
            return f"🏆 Goal #{goal_id} '{goal['title']}' marked as COMPLETED! 🎉"
        return f"❌ Goal #{goal_id} not found."

    def quick_delete_goal(self, goal_id: int) -> str:
        ok = self.delete_goal(goal_id)
        if ok:
            return f"🗑️ Goal #{goal_id} deleted."
        return f"❌ Goal #{goal_id} not found."

    def quick_add_note(self, title: str, content: str, tags: Optional[List[str]] = None) -> str:
        note = self.save_note(title=title, content=content, tags=tags)
        return f"💡 Note #{note['id']} '{note['title']}' saved to Knowledge Base!"

    def quick_delete_note(self, note_id: int) -> str:
        ok = self.delete_note(note_id)
        if ok:
            return f"🗑️ Note #{note_id} deleted."
        return f"❌ Note #{note_id} not found."

    def get_projects_formatted(self) -> str:
        if not self.projects:
            return "📁 No active projects found. Add one with /add-project <name>"
        output = ["📁 ACTIVE PROJECTS:"]
        for p in self.projects:
            goal_str = f" (Goal: {p.get('goal')})" if p.get("goal") else ""
            output.append(f"\n  [ID #{p['id']}] **{p.get('name')}** - Status: {p.get('status', 'active')}{goal_str}")
            if p.get("description"):
                output.append(f"     Description: {p.get('description')}")
            if p.get("deliverables"):
                output.append("     Deliverables:")
                for d in p.get("deliverables", []):
                    output.append(f"       • {d}")
        return "\n".join(output)

    def quick_add_project(self, name: str, description: str = "", goal: Optional[str] = None) -> str:
        proj = self.add_project(name=name, description=description, goal=goal)
        return f"📁 Project #{proj['id']} '{proj['name']}' created!"

    def get_schedule_formatted(self) -> str:
        lines = [
            "📅 STUDY TIMETABLE & TARGETS",
            "─" * 52,
            "📚 Study Timetable (Mon – Sat):",
            "    🎓 College        -> 8:00 AM – 5:00 PM",
            "    🌆 Evening 5:30   -> Block 1: DSA Java (Pepcoding — 2.5h)",
            "    🌙 Night 8:00     -> Block 2: Java Core / GATE DSA Alternating (2.5h)",
            "                           • Odd Days (Mon/Wed/Fri): Java Core (Coder Army)",
            "                           • Even Days (Tue/Thu/Sat): DSA for GATE (Viswadeep Sir)",
            "    ✨ Night 10:30    -> Block 3: SQL One-shot Progress (30m)",
            "    🛋 Sunday         -> Complete Rest (No Study)",
            "",
            "🎯 Daily Targets This Week:",
            "    💻 10 DSA Java videos    (Pepcoding — from basics)",
            "    📹 1 Java video          (Coder Army — Mon/Wed/Fri)",
            "    📖 1 GATE DSA video      (Viswadeep Sir — Tue/Thu/Sat)",
            "    🗄 SQL one-shot progress (30m daily)"
        ]
        return "\n".join(lines)

    def get_priorities_radar_formatted(self) -> str:
        pending = [t for t in self.tasks if t.get("status") != "completed"]
        L = [
            "⚡ PRIORITIES & DEADLINE RADAR",
            "─" * 52
        ]
        # Alerts
        alert_text = self.get_deadline_alerts()
        if "No approaching" not in alert_text:
            L.append("⏰ Deadline Alerts:")
            for al in alert_text.split("\n")[1:]:
                al = al.strip()
                if not al: continue
                if "OVERDUE" in al: L.append(f"    🔴 {al.replace('OVERDUE  ->', '').strip()}")
                elif "TODAY" in al: L.append(f"    🟠 {al.replace('TODAY    ->', '').strip()}")
                elif "CRITICAL" in al: L.append(f"    🟡 {al.replace('CRITICAL ->', '').strip()}")
                elif "WARNING" in al: L.append(f"    🔵 {al.replace('WARNING  ->', '').strip()}")
            L.append("")
        else:
            L.append("⏰ Deadline Alerts:\n    ✨ No overdue or urgent deadlines!\n")

        # Top priorities
        sorted_pending = sorted(pending, key=lambda x: self._get_effective_priority(x), reverse=True)
        if sorted_pending:
            L.append("🥇 Top Priorities:")
            medals = ["🥇", "🥈", "🥉"]
            for i, t in enumerate(sorted_pending[:3]):
                days = self._days_until(t.get("deadline"))
                if days is not None and days < 0: urgency = f"  ⚠️ {abs(days)}d OVERDUE"
                elif days == 0: urgency = "  ⚠️ Due TODAY"
                elif days is not None and days <= 2: urgency = f"  ⚡ {days}d left"
                else: urgency = f"  (Due: {t.get('deadline')})" if t.get("deadline") else ""
                medal = medals[i] if i < 3 else "   •"
                L.append(f"    {medal} [Task #{t['id']}] {t.get('title')}{urgency}")
            L.append("")
        else:
            L.append("🥇 Top Priorities:\n    🎉 All caught up!\n")

        # Tasks due this week
        week_tasks = []
        for t in pending:
            days = self._days_until(t.get("deadline"))
            if days is not None and 0 <= days <= 7:
                week_tasks.append((days, t))
        week_tasks.sort(key=lambda x: x[0])
        if week_tasks:
            L.append("📅 Tasks Due This Week:")
            for days_left, t in week_tasks[:6]:
                prio = t.get("priority", "medium")
                dot = {"urgent": "🔴", "high": "🟠", "medium": "🟡"}.get(prio, "🟢")
                due_label = "today" if days_left == 0 else ("tomorrow" if days_left == 1 else f"in {days_left} days")
                L.append(f"    {dot} [Task #{t['id']}] {t.get('title')}  —  due {due_label}")
        else:
            L.append("📅 Tasks Due This Week:\n    ✨ No specific tasks due this week.")
        return "\n".join(L)

    # =========================================================================
    # ARCHIVE MANAGEMENT
    # =========================================================================

    def archive_task(self, task_id: int) -> Optional[Dict[str, Any]]:
        """Move a task to archive.json and remove from active tasks."""
        task = next((t for t in self.tasks if t.get("id") == task_id), None)
        if task:
            self.tasks = [t for t in self.tasks if t.get("id") != task_id]
            archived_item = dict(task)
            archived_item["archived_at"] = datetime.now().isoformat()
            self.archive.append(archived_item)
            self._save_json(self.tasks_file, self.tasks)
            self._save_json(self.archive_file, self.archive)
            self._push_undo(
                description=f"Archived task #{task_id} '{task.get('title')}'",
                action_type="archive_task",
                data={"task": task}
            )
            return archived_item
        return None

    def archive_completed_tasks(self) -> List[Dict[str, Any]]:
        """Move all completed tasks to archive.json."""
        completed = [t for t in self.tasks if t.get("status") == "completed"]
        if not completed:
            return []
        
        self.tasks = [t for t in self.tasks if t.get("status") != "completed"]
        for t in completed:
            item = dict(t)
            item["archived_at"] = datetime.now().isoformat()
            self.archive.append(item)
        
        self._save_json(self.tasks_file, self.tasks)
        self._save_json(self.archive_file, self.archive)
        self._push_undo(
            description=f"Archived {len(completed)} completed task(s)",
            action_type="archive_completed",
            data={"tasks": completed}
        )
        return completed

    def get_archived_tasks_formatted(self) -> str:
        """Formatted overview of archived tasks."""
        if not self.archive:
            return "📁 Archive is empty. No tasks archived yet."
        output = [f"📁 ARCHIVED TASKS ({len(self.archive)}):"]
        for a in self.archive[-25:]:
            arch_date = a.get("archived_at", "N/A")[:10]
            output.append(f"  [ID #{a.get('id')}] {a.get('title')} (Archived: {arch_date} | Status: {a.get('status')})")
        return "\n".join(output)

    # =========================================================================
    # BULK HABIT LOGGING
    # =========================================================================

    def quick_bulk_log_habits(self, habit_ids: List[int], completed: bool = True) -> str:
        """Log or reset completion for multiple habits at once."""
        if not habit_ids:
            return "⚠️ No habit IDs provided."
        
        logged = []
        not_found = []
        for hid in habit_ids:
            h = self.log_habit(hid, completed)
            if h:
                logged.append(f"#{hid} '{h.get('name')}' (🔥 {h.get('streak', 0)}d)")
            else:
                not_found.append(str(hid))
        
        status_txt = "logged" if completed else "reset"
        msg = f"🔁 Habits {status_txt}: {', '.join(logged)}"
        if not_found:
            msg += f"\n⚠️ Habits not found: {', '.join(not_found)}"
        return msg

    # =========================================================================
    # FULL MEMORY EXPORT (JSON BACKUP)
    # =========================================================================

    def export_backup(self, export_dir: Optional[str] = None) -> Path:
        """Export complete agent memory snapshot into a timestamped JSON backup file."""
        out_dir = Path(export_dir) if export_dir else self.exports_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_path = out_dir / f"agent_backup_{timestamp}.json"
        
        payload = {
            "exported_at": datetime.now().isoformat(),
            "version": "3.0",
            "stats": {
                "tasks_pending": len([t for t in self.tasks if t.get("status") != "completed"]),
                "tasks_completed": len([t for t in self.tasks if t.get("status") == "completed"]),
                "tasks_archived": len(self.archive),
                "goals": len(self.goals),
                "projects": len(self.projects),
                "habits": len(self.habits),
                "journal_entries": len(self.journal),
                "notes": len(self.notes),
                "attachments": len(self.attachments)
            },
            "user_profile": self.context,
            "goals": self.goals,
            "projects": self.projects,
            "tasks": self.tasks,
            "archive": self.archive,
            "habits": self.habits,
            "journal": self.journal,
            "notes": self.notes,
            "attachments": self.attachments,
            "active_session": self.current_session_id
        }
        
        self._save_json(export_path, payload)
        return export_path

    # =========================================================================
    # FILE ATTACHMENT SYSTEM
    # =========================================================================

    def add_attachment(self, source_path_or_bytes: Any, filename: str, description: str = "", content_type: Optional[str] = None) -> Dict[str, Any]:
        """Save an attached file or bytes into agent_data/attachments and track in attachments.json."""
        att_id = self._get_next_id(self.attachments)
        
        clean_name = Path(filename).name
        stored_name = f"att_{att_id}_{clean_name}"
        target_path = self.attachments_dir / stored_name
        
        text_preview = ""
        file_size = 0
        
        if isinstance(source_path_or_bytes, (str, Path)):
            src = Path(source_path_or_bytes)
            if src.exists():
                file_size = src.stat().st_size
                shutil.copy2(src, target_path)
                if src.suffix.lower() in [".txt", ".md", ".py", ".json", ".csv", ".log", ".yaml", ".yml", ".html", ".js", ".java", ".sql"]:
                    try:
                        with open(src, "r", encoding="utf-8", errors="ignore") as f:
                            text_preview = f.read(2000)
                    except Exception:
                        pass
            else:
                raise FileNotFoundError(f"Source file {source_path_or_bytes} not found.")
        elif isinstance(source_path_or_bytes, bytes):
            file_size = len(source_path_or_bytes)
            with open(target_path, "wb") as f:
                f.write(source_path_or_bytes)
            suffix = Path(filename).suffix.lower()
            if suffix in [".txt", ".md", ".py", ".json", ".csv", ".log", ".yaml", ".yml", ".html", ".js", ".java", ".sql"]:
                try:
                    text_preview = source_path_or_bytes[:2000].decode("utf-8", errors="ignore")
                except Exception:
                    pass

        record = {
            "id": att_id,
            "filename": stored_name,
            "original_name": clean_name,
            "file_type": content_type or Path(filename).suffix.lower() or "file",
            "file_size": file_size,
            "file_path": str(target_path),
            "description": description,
            "text_preview": text_preview,
            "created_at": datetime.now().isoformat()
        }
        self.attachments.append(record)
        self._save_json(self.attachments_file, self.attachments)
        return record

    def get_attachments_formatted(self) -> str:
        """Formatted list of all saved attachments."""
        if not self.attachments:
            return "📎 No file attachments found. Use '/attach <filepath>' in CLI or send files/photos in Telegram."
        output = [f"📎 FILE ATTACHMENTS ({len(self.attachments)}):"]
        for a in self.attachments:
            size_kb = a.get("file_size", 0) / 1024
            desc = f" — {a.get('description')}" if a.get("description") else ""
            date_str = a.get("created_at", "")[:10]
            output.append(f"  • [ID #{a.get('id')}] **{a.get('original_name')}** ({size_kb:.1f} KB, {a.get('file_type')}) [{date_str}]{desc}")
        return "\n".join(output)

    def get_attachment(self, attachment_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve attachment record by ID."""
        return next((a for a in self.attachments if a.get("id") == attachment_id), None)

    def delete_attachment(self, attachment_id: int) -> bool:
        """Delete an attachment record and remove the stored file from disk."""
        att = self.get_attachment(attachment_id)
        if att:
            try:
                p = Path(att.get("file_path", ""))
                if p.exists():
                    p.unlink()
            except Exception:
                pass
            self.attachments = [a for a in self.attachments if a.get("id") != attachment_id]
            self._save_json(self.attachments_file, self.attachments)
            return True
        return False

    # =========================================================================
    # ANALYTICS & INSIGHTS ENGINE
    # =========================================================================

    def _make_progress_bar(self, percent: float, length: int = 10) -> str:
        """Render a visual Unicode progress bar e.g. [████████░░] 80%."""
        clamped = max(0.0, min(100.0, float(percent)))
        filled = int(round((clamped / 100.0) * length))
        empty = length - filled
        return f"[{'█' * filled}{'░' * empty}] {clamped:.0f}%"

    def generate_analytics_data(self, period: str = "weekly") -> Dict[str, Any]:
        """
        Compute deep productivity analytics over 'weekly' (7 days) or 'monthly' (30 days).
        Includes:
        - Task completion rate trends & comparison to prior period
        - Time-of-day productivity patterns & peak focus window
        - Habit consistency scores & grading
        - Goal progress visualizations & health
        """
        now = datetime.now()
        days = 7 if period.lower() == "weekly" else 30
        period_start = now - timedelta(days=days)
        prior_start = period_start - timedelta(days=days)

        period_start_str = period_start.strftime("%Y-%m-%d")
        prior_start_str = prior_start.strftime("%Y-%m-%d")

        # 1. TASK COMPLETION TRENDS
        all_tasks = self.tasks + self.archive
        completed_in_period = []
        completed_in_prior = []
        created_in_period = []

        daily_completions: Dict[str, int] = {}
        for d_offset in range(days):
            d_key = (period_start + timedelta(days=d_offset + 1)).strftime("%Y-%m-%d")
            daily_completions[d_key] = 0

        time_of_day_counts = {
            "Early Morning (05-09)": 0,
            "Late Morning (09-13)": 0,
            "Afternoon (13-17)": 0,
            "Evening (17-21)": 0,
            "Night (21-05)": 0,
        }
        hourly_counts: Dict[int, int] = {h: 0 for h in range(24)}

        for t in all_tasks:
            cat = t.get("completed_at")
            c_at = t.get("created_at")

            # Creation tracking
            if c_at:
                try:
                    c_dt = datetime.fromisoformat(c_at)
                    if c_dt >= period_start:
                        created_in_period.append(t)
                except Exception:
                    pass

            # Completion tracking
            if cat:
                try:
                    dt = datetime.fromisoformat(cat)
                    if dt >= period_start:
                        completed_in_period.append(t)
                        day_key = dt.strftime("%Y-%m-%d")
                        if day_key in daily_completions:
                            daily_completions[day_key] += 1
                        else:
                            daily_completions[day_key] = 1

                        # Time-of-day distribution
                        hour = dt.hour
                        hourly_counts[hour] = hourly_counts.get(hour, 0) + 1
                        if 5 <= hour < 9:
                            time_of_day_counts["Early Morning (05-09)"] += 1
                        elif 9 <= hour < 13:
                            time_of_day_counts["Late Morning (09-13)"] += 1
                        elif 13 <= hour < 17:
                            time_of_day_counts["Afternoon (13-17)"] += 1
                        elif 17 <= hour < 21:
                            time_of_day_counts["Evening (17-21)"] += 1
                        else:
                            time_of_day_counts["Night (21-05)"] += 1

                    elif dt >= prior_start:
                        completed_in_prior.append(t)
                except Exception:
                    pass

        # If sparse completions in current window, fall back to all-time completions for time-of-day pattern
        if sum(time_of_day_counts.values()) == 0:
            for t in all_tasks:
                cat = t.get("completed_at")
                if cat:
                    try:
                        dt = datetime.fromisoformat(cat)
                        hour = dt.hour
                        hourly_counts[hour] = hourly_counts.get(hour, 0) + 1
                        if 5 <= hour < 9:
                            time_of_day_counts["Early Morning (05-09)"] += 1
                        elif 9 <= hour < 13:
                            time_of_day_counts["Late Morning (09-13)"] += 1
                        elif 13 <= hour < 17:
                            time_of_day_counts["Afternoon (13-17)"] += 1
                        elif 17 <= hour < 21:
                            time_of_day_counts["Evening (17-21)"] += 1
                        else:
                            time_of_day_counts["Night (21-05)"] += 1
                    except Exception:
                        pass

        pending_tasks = [t for t in self.tasks if t.get("status") != "completed"]
        total_active_pool = len(completed_in_period) + len(pending_tasks)
        completion_rate = (len(completed_in_period) / total_active_pool * 100.0) if total_active_pool > 0 else 0.0

        prior_count = len(completed_in_prior)
        curr_count = len(completed_in_period)
        if prior_count > 0:
            trend_pct = ((curr_count - prior_count) / prior_count) * 100.0
            trend_str = f"{'+' if trend_pct >= 0 else ''}{trend_pct:.1f}% vs prior {period}"
        else:
            trend_str = f"+{curr_count} tasks completed" if curr_count > 0 else "Baseline period"

        # Peak focus determination
        peak_time_slot = max(time_of_day_counts.items(), key=lambda x: x[1]) if sum(time_of_day_counts.values()) > 0 else ("Night (21-05)", 0)

        # 2. HABIT CONSISTENCY SCORE
        habit_scores = []
        for h in self.habits:
            logs = h.get("log", [])
            completed_days = 0
            for d_offset in range(days):
                d_str = (period_start + timedelta(days=d_offset + 1)).strftime("%Y-%m-%d")
                if any(l.get("date") == d_str and l.get("completed") for l in logs):
                    completed_days += 1
            
            # For newly created habits, scale by days existing
            c_at = h.get("created_at")
            possible_days = days
            if c_at:
                try:
                    c_date = datetime.fromisoformat(c_at).date()
                    days_alive = (now.date() - c_date).days + 1
                    possible_days = max(1, min(days, days_alive))
                except Exception:
                    pass
