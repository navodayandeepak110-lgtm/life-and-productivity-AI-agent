#!/usr/bin/env python3
"""
Telegram Bot Interface -- AI Life & Productivity Agent
======================================================
Connects your phone to the same agent brain running in VS Code.
- Fast CLI commands run locally (0ms, 0 tokens)
- Free-text messages are routed to OmniRoute AI
- Only responds to your personal Telegram user ID (secure)

Run: python telegram_bot.py
"""

import sys
import os
import logging
import asyncio
from datetime import datetime

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from dotenv import load_dotenv
load_dotenv()

from telegram import Update, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

from memory_manager import MemoryManager
from productivity_agent import ProductivityAgent

# New tool integrations
try:
    from web_tools import web_search, read_webpage, format_search_results, format_webpage_result, WEB_TOOLS_AVAILABLE
except ImportError:
    WEB_TOOLS_AVAILABLE = False
try:
    from email_tools import list_emails, search_emails, format_email_list, check_email_configured
except ImportError:
    pass
try:
    from youtube_tools import (
        track_video_progress, list_all_tracked_videos, get_playlist_progress,
        format_video_progress, format_all_tracked, format_playlist_progress
    )
except ImportError:
    pass

# --- Config -------------------------------------------------------------------

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
ALLOWED_USER_ID = int(os.getenv("TELEGRAM_ALLOWED_USER_ID", "0"))

if not BOT_TOKEN:
    print("ERROR: TELEGRAM_BOT_TOKEN not set in .env")
    sys.exit(1)
if not ALLOWED_USER_ID:
    print("ERROR: TELEGRAM_ALLOWED_USER_ID not set in .env")
    sys.exit(1)

# --- Logging ------------------------------------------------------------------

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("TelegramBot")

# --- Shared agent (same memory as VS Code terminal) --------------------------

_agent = None

def get_agent():
    global _agent
    if _agent is None:
        logger.info("Loading agent...")
        _agent = ProductivityAgent(resume_session=True)
        logger.info("Agent ready.")
    return _agent

# --- Helpers ------------------------------------------------------------------

def is_authorized(update: Update) -> bool:
    return update.effective_user.id == ALLOWED_USER_ID

def deny(update: Update):
    uid = update.effective_user.id
    name = update.effective_user.username or update.effective_user.first_name
    logger.warning(f"Unauthorized: {name} ({uid})")

async def send_long(update: Update, text: str):
    MAX = 4000
    text = text.strip() or "(empty)"
    if len(text) <= MAX:
        await update.message.reply_text(text)
        return
    parts = [text[i:i+MAX] for i in range(0, len(text), MAX)]
    for i, p in enumerate(parts):
        await update.message.reply_text(f"[{i+1}/{len(parts)}]\n{p}")

# --- Command Handlers ---------------------------------------------------------

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        deny(update)
        return
    a = get_agent()
    msg = "AI Life & Productivity Agent -- Phone Interface\n"
    msg += "================================================\n"
    msg += "Same brain as your VS Code terminal.\n"
    msg += "Type /help for commands, or just ask me anything!\n\n"
    msg += a.memory.get_morning_briefing()
    await send_long(update, msg)

async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    h = (
        "⚡ FAST NUMBERED COMMANDS (0ms, 0 Tokens):\n"
        "=========================================\n"
        "👉 You can type the [NUMBER] or /command:\n\n"
        "📊 DAILY & ROUTINE:\n"
        "  [1]  /today       - Morning briefing & routines\n"
        "  [2]  /radar       - Priorities & deadline radar\n"
        "  [3]  /schedule    - Study timetable & targets\n"
        "  [4]  /cal         - Weekly visual calendar\n"
        "  [5]  /deadlines   - All approaching deadlines\n"
        "  [6]  /streaks     - Habit coaching & streaks\n"
        "  [7]  /stats       - Memory dashboard overview\n\n"
        "📋 TASKS & ARCHIVE:\n"
        "  [8]  /tasks       - Pending tasks (priority sorted)\n"
        "  [9]  /tasks-all   - All tasks (pending + completed)\n"
        "  [10] /done <ids>  - Complete task(s) e.g. 10 2 or /done 1,2,3\n"
        "  [11] /add <title> - Add task        e.g. 11 Study Graphs due tomorrow\n"
        "  [12] /del <ids>   - Delete task(s)  e.g. 12 5 or /del 1,2 --archive\n"
        "  [13] /prio <id> <l>- Set priority   e.g. 13 6 urgent\n"
        "  [14] /due <id> <d>- Set deadline    e.g. 14 3 next Friday\n"
        "  [15] /cleardone   - Clean completed (add --archive to save)\n"
        "  [16] /archive <id>- Move task to archive.json\n"
        "  [17] /archived    - View archived tasks\n\n"
        "🔁 HABITS:\n"
        "  [18] /habits      - Habit tracker & streaks\n"
        "  [19] /log <ids>   - Log habit(s)    e.g. 19 1 or /log 1,2\n"
        "  [20] /unlog <ids> - Reset habit(s)  e.g. 20 1\n"
        "  [21] /addhabit <n>- Add habit       e.g. 21 DSA 2h daily\n"
        "  [22] /delhabit <i>- Delete habit    e.g. 22 3\n\n"
        "🎯 GOALS & PROJECTS:\n"
        "  [23] /goals       - Active goals\n"
        "  [24] /goal <name> - Add goal        e.g. 24 Master SQL\n"
        "  [27] /projects    - View projects\n"
        "  [28] /addproj <n> - Add project     e.g. 28 Backend API\n\n"
        "💡 KNOWLEDGE BASE & ATTACHMENTS:\n"
        "  [29] /notes       - Knowledge base\n"
        "  [30] /note t|c    - Save note       e.g. 30 DSA|tip here\n"
        "  [33] /attachments - List file attachments\n"
        "  [36] /review <txt>- Daily review    e.g. 36 Studied 2h DSA\n\n"
        "📈 ANALYTICS & SMART NOTIFICATIONS:\n"
        "  [44] /report      - Weekly / Monthly intelligence report\n"
        "  [45] /weekly      - Weekly completion trends & habit score\n"
        "  [46] /monthly     - Monthly analytics & consistency report\n"
        "  [47] /notify      - Check proactive alerts (2h due, streaks)\n"
        "  [48] /goals-progress - Visual goal progress bars & milestones\n\n"
        "🌐 BROWSER & WEB:\n"
        "  [49] /web <query> - Search the web       e.g. 49 Python tutorial\n"
        "  [50] /read <url>  - Read & summarize URL e.g. 50 https://python.org\n\n"
        "📧 EMAIL:\n"
        "  [51] /inbox [N]   - View inbox           e.g. 51 10 or 51 unread\n"
        "  [52] /emailsearch - Search emails        e.g. 52 invoice\n\n"
        "📺 YOUTUBE PROGRESS:\n"
        "  [54] /yttrack     - Track video progress e.g. 54 https://youtu.be/x 25 60\n"
        "  [55] /ytprogress  - View all tracked videos\n"
        "  [56] /ytplaylist  - Playlist progress    e.g. 56 <playlist_url>\n\n"
        "⚙️ BACKUP & CONTROL:\n"
        "  [37] /undo        - Revert last action\n"
        "  [38] /export      - Export JSON backup directly to chat\n"
        "  [39] /memory      - Full memory snapshot\n"
        "  [43] /help        - Show this menu\n\n"
        "📎 FILE ATTACHMENTS:\n"
        "Send any photo or document with an optional caption to store and analyze it!\n\n"
        "🤖 AI CHAT:\n"
        "Just send any message to chat with your AI agent."
    )
    await update.message.reply_text(h)

async def cmd_radar(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    await send_long(update, get_agent().memory.get_priorities_radar_formatted())

async def cmd_schedule(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    await send_long(update, get_agent().memory.get_schedule_formatted())

async def cmd_today(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    await send_long(update, get_agent().memory.get_morning_briefing())

async def cmd_calendar(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    await send_long(update, get_agent().memory.get_calendar_view())

async def cmd_tasks(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    await send_long(update, get_agent().memory.get_tasks_formatted("pending"))

async def cmd_tasks_all(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    msg = get_agent().memory.get_tasks_formatted("pending") + "\n\n" + get_agent().memory.get_tasks_formatted("completed")
    await send_long(update, msg)

async def cmd_archived(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    await send_long(update, get_agent().memory.get_archived_tasks_formatted())

async def cmd_archive(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    raw = " ".join(ctx.args).strip()
    ids = get_agent().memory._parse_id_list(raw)
    if not ids:
        await update.message.reply_text("Usage: /archive <id(s)>  e.g. /archive 3 or /archive 1,2,3")
        return
    await update.message.reply_text(get_agent().memory.quick_delete_tasks(ids, archive=True))

async def cmd_done(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    raw = " ".join(ctx.args).strip()
    ids = get_agent().memory._parse_id_list(raw)
    if not ids:
        await update.message.reply_text("Usage: /done <id(s)>  e.g. /done 3 or /done 1,2,3")
        return
    await update.message.reply_text(get_agent().memory.quick_complete_tasks(ids))

async def cmd_add(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    title = " ".join(ctx.args).strip()
    if not title:
        await update.message.reply_text("Usage: /add <task title>  e.g. /add Solve 3 LeetCode due tomorrow")
        return
    prio = "medium"
    tl = title.lower()
    if "urgent" in tl:      prio = "urgent"
    elif "important" in tl or "high" in tl: prio = "high"
    elif "low" in tl:       prio = "low"
    await update.message.reply_text(get_agent().memory.quick_add_task(title=title, priority=prio))

async def cmd_del(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    raw = " ".join(ctx.args).strip()
    do_archive = "--archive" in raw.lower()
    clean_raw = raw.replace("--archive", "").replace("-a", "")
    ids = get_agent().memory._parse_id_list(clean_raw)
    if not ids:
        await update.message.reply_text("Usage: /del <id(s)> [--archive]  e.g. /del 5 or /del 1,2,3 --archive")
        return
    await update.message.reply_text(get_agent().memory.quick_delete_tasks(ids, archive=do_archive))

async def cmd_prio(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    args = ctx.args
    if len(args) < 2:
        await update.message.reply_text("Usage: /prio <id(s)> <urgent|high|medium|low>  e.g. /prio 6 urgent")
        return
    prio = args[-1].lower()
    ids = get_agent().memory._parse_id_list(" ".join(args[:-1]))
    if not ids or prio not in ["urgent", "high", "medium", "low"]:
        await update.message.reply_text("Usage: /prio <id(s)> <urgent|high|medium|low>  e.g. /prio 6 urgent")
        return
    results = [get_agent().memory.quick_set_task_priority(tid, prio) for tid in ids]
    await update.message.reply_text("\n".join(results))

async def cmd_due(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    args = ctx.args
    if len(args) < 2 or not args[0].isdigit():
        await update.message.reply_text("Usage: /due <id> <deadline>  e.g. /due 6 next Friday")
        return
    dl = " ".join(args[1:])
    await update.message.reply_text(get_agent().memory.quick_set_task_deadline(int(args[0]), dl))

async def cmd_clear_done(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    raw = " ".join(ctx.args).lower()
    do_archive = "--archive" in raw or "-a" in raw
    await update.message.reply_text(get_agent().memory.quick_clear_completed_tasks(archive=do_archive))

async def cmd_undo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    await update.message.reply_text(get_agent().memory.undo())

async def cmd_export(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    try:
        export_path = get_agent().memory.export_backup()
        with open(export_path, "rb") as doc:
            await update.message.reply_document(
                document=doc,
                filename=export_path.name,
                caption=f"💾 Memory Backup ({export_path.name})\nComplete JSON snapshot created successfully."
            )
    except Exception as e:
        await update.message.reply_text(f"❌ Export failed: {e}")

async def cmd_attachments(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    await send_long(update, get_agent().memory.get_attachments_formatted())

async def cmd_habits(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    await send_long(update, get_agent().memory.get_habits_formatted())

async def cmd_log(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    raw = " ".join(ctx.args).strip()
    ids = get_agent().memory._parse_id_list(raw)
    if not ids:
        await update.message.reply_text("Usage: /log <habit_id(s)>  e.g. /log 1 or /log 1,2")
        return
    await update.message.reply_text(get_agent().memory.quick_bulk_log_habits(ids, completed=True))

async def cmd_unlog(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    raw = " ".join(ctx.args).strip()
    ids = get_agent().memory._parse_id_list(raw)
    if not ids:
        await update.message.reply_text("Usage: /unlog <habit_id(s)>  e.g. /unlog 1 or /unlog 1,2")
        return
    await update.message.reply_text(get_agent().memory.quick_bulk_log_habits(ids, completed=False))

async def cmd_habit_add(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    name = " ".join(ctx.args).strip()
    if not name:
        await update.message.reply_text("Usage: /addhabit <name>  e.g. /addhabit DSA 2h daily")
        return
    await update.message.reply_text(get_agent().memory.quick_add_habit(name))

async def cmd_habit_del(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    args = ctx.args
    if not args or not args[0].isdigit():
        await update.message.reply_text("Usage: /delhabit <id>  e.g. /delhabit 3")
        return
    await update.message.reply_text(get_agent().memory.quick_delete_habit(int(args[0])))

async def cmd_goals(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    await send_long(update, get_agent().memory.get_goals_formatted())

async def cmd_goal_add(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    title = " ".join(ctx.args).strip()
    if not title:
        await update.message.reply_text("Usage: /goal <title>  e.g. /goal Master SQL")
        return
    g = get_agent().memory.add_goal(title=title, description=title)
    await update.message.reply_text(f"Goal #{g['id']} '{g['title']}' added!")

async def cmd_goal_complete(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    args = ctx.args
    if not args or not args[0].isdigit():
        await update.message.reply_text("Usage: /donegoal <id>  e.g. /donegoal 1")
        return
    await update.message.reply_text(get_agent().memory.quick_complete_goal(int(args[0])))

async def cmd_goal_del(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    args = ctx.args
    if not args or not args[0].isdigit():
        await update.message.reply_text("Usage: /delgoal <id>  e.g. /delgoal 2")
        return
    await update.message.reply_text(get_agent().memory.quick_delete_goal(int(args[0])))

async def cmd_projects(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    await send_long(update, get_agent().memory.get_projects_formatted())

async def cmd_project_add(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    name = " ".join(ctx.args).strip()
    if not name:
        await update.message.reply_text("Usage: /addproj <name>  e.g. /addproj Backend API")
        return
    await update.message.reply_text(get_agent().memory.quick_add_project(name))

async def cmd_deadlines(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    await send_long(update, get_agent().memory.get_deadline_alerts())

async def cmd_streaks(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    await send_long(update, get_agent().memory.get_habit_adaptive_recommendations())

async def cmd_notes(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    await send_long(update, get_agent().memory.get_notes_formatted())

async def cmd_note_add(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    raw = " ".join(ctx.args).strip()
    if not raw:
        await update.message.reply_text("Usage: /note <title>|<content>  e.g. /note DSA|Sliding window tip")
        return
    if "|" in raw:
        t, c = raw.split("|", 1)
        res = get_agent().memory.quick_add_note(t.strip(), c.strip())
    else:
        res = get_agent().memory.quick_add_note(raw[:40], raw)
    await update.message.reply_text(res)

async def cmd_note_del(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    args = ctx.args
    if not args or not args[0].isdigit():
        await update.message.reply_text("Usage: /delnote <id>  e.g. /delnote 2")
        return
    await update.message.reply_text(get_agent().memory.quick_delete_note(int(args[0])))

async def cmd_review(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    summary = " ".join(ctx.args).strip()
    if not summary:
        await update.message.reply_text("Usage: /review <summary>  e.g. /review Studied Trees 2h, solved 2 LeetCode")
        return
    get_agent().memory.add_journal_entry(summary=summary)
    today = datetime.now().strftime("%B %d")
    await update.message.reply_text(f"Daily review logged for {today}:\n'{summary}'")

async def cmd_memory(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    await send_long(update, get_agent().memory.get_user_data_summary())

async def cmd_report(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    raw = " ".join(ctx.args).lower()
    period = "monthly" if "month" in raw else "weekly"
    await send_long(update, get_agent().memory.get_analytics_report_formatted(period=period))

async def cmd_weekly(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    await send_long(update, get_agent().memory.get_analytics_report_formatted(period="weekly"))

async def cmd_monthly(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    await send_long(update, get_agent().memory.get_analytics_report_formatted(period="monthly"))

async def cmd_notify(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    await send_long(update, get_agent().memory.get_proactive_notifications_formatted(force=True))

async def cmd_goals_progress(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    await send_long(update, get_agent().memory.get_goal_progress_visualizations())

# --- Browser, Email, YouTube Command Handlers --------------------------------

async def cmd_web(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    query = " ".join(ctx.args).strip()
    if not query:
        await update.message.reply_text("Usage: /web <search query>  e.g. /web Python async tutorial")
        return
    await update.message.chat.send_action(action="typing")
    res = web_search(query, max_results=5)
    await send_long(update, format_search_results(res))

async def cmd_read(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    url = " ".join(ctx.args).strip()
    if not url:
        await update.message.reply_text("Usage: /read <url>  e.g. /read https://example.com")
        return
    await update.message.chat.send_action(action="typing")
    res = read_webpage(url)
    await send_long(update, format_webpage_result(res))

async def cmd_inbox(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    configured, msg = check_email_configured()
    if not configured:
        await update.message.reply_text(f"📧 Email not configured: {msg}\nAdd EMAIL_ADDRESS and EMAIL_APP_PASSWORD to your .env file.")
        return
    args = " ".join(ctx.args).lower()
    unread_only = "unread" in args
    count = 10
    for tok in ctx.args:
        if tok.isdigit():
            count = int(tok)
            break
    await update.message.chat.send_action(action="typing")
    res = list_emails(count=count, unread_only=unread_only)
    await send_long(update, format_email_list(res))

async def cmd_email_search(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    query = " ".join(ctx.args).strip()
    if not query:
        await update.message.reply_text("Usage: /emailsearch <keyword>  e.g. /emailsearch invoice")
        return
    configured, msg = check_email_configured()
    if not configured:
        await update.message.reply_text(f"📧 Email not configured: {msg}")
        return
    await update.message.chat.send_action(action="typing")
    res = search_emails(query)
    if res.get("error"):
        await update.message.reply_text(f"❌ {res['error']}")
        return
    emails = res.get("results", [])
    if not emails:
        await update.message.reply_text(f"📭 No emails found matching '{query}'.")
        return
    lines = [f"📧 Found {len(emails)} email(s) for '{query}':\n"]
    for e in emails:
        lines.append(f"  [{e['id']}] {e.get('subject', '(no subject)')}\n       From: {e.get('from', '')} | {e.get('date', '')}")
    await send_long(update, "\n".join(lines))

async def cmd_yt_track(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    if len(ctx.args) < 2:
        await update.message.reply_text("Usage: /yttrack <url> <minutes_watched> [total_minutes]\nExample: /yttrack https://youtu.be/abc 25 60")
        return
    url = ctx.args[0]
    try:
        watched_min = float(ctx.args[1])
        total_min = float(ctx.args[2]) if len(ctx.args) >= 3 else None
    except ValueError:
        await update.message.reply_text("⚠️ Minutes must be numbers.")
        return
    res = track_video_progress(
        url_or_id=url,
        watched_seconds=int(watched_min * 60),
        total_seconds=int(total_min * 60) if total_min else None
    )
    if res.get("error"):
        await update.message.reply_text(f"❌ {res['error']}")
    else:
        await send_long(update, format_video_progress(res))

async def cmd_yt_progress(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    res = list_all_tracked_videos()
    await send_long(update, format_all_tracked(res))

async def cmd_yt_playlist(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    url = " ".join(ctx.args).strip()
    if not url:
        await update.message.reply_text("Usage: /ytplaylist <playlist_url_or_id>")
        return
    await update.message.chat.send_action(action="typing")
    res = get_playlist_progress(url)
    await send_long(update, format_playlist_progress(res))

# --- Background Proactive Smart Notifications Worker --------------------------

async def smart_notification_worker(app: Application):
    """
    Background worker running every 60 seconds.
    Proactively checks for:
    - Tasks due in <= 2 hours
    - Habits at risk of streak loss
    - Weekly review readiness
    Sends push alerts directly to the authorized user.
    """
    logger.info("Smart notifications worker started (running every 60s).")
    await asyncio.sleep(5)  # initial warmup delay
    while True:
        try:
            agent = get_agent()
            notifs = agent.memory.check_smart_notifications(force=False)
            for n in notifs:
                alert_text = f"🔔 *{n['title']}*\n{n['message']}"
                logger.info(f"Dispatching proactive alert: {n['title']}")
                await app.bot.send_message(
                    chat_id=ALLOWED_USER_ID,
                    text=alert_text,
                    parse_mode="Markdown"
                )
        except Exception as e:
            logger.error(f"Error in smart_notification_worker: {e}")
        
        await asyncio.sleep(60)

# --- Free-text & Attachments -> AI ---------------------------------------------

async def handle_attachment(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        deny(update)
        return
    
    msg = update.message
    caption = (msg.caption or "").strip()
    file_obj = None
    filename = "attachment"
    content_type = "file"

    if msg.photo:
        photo = msg.photo[-1]
        file_obj = await photo.get_file()
        filename = f"photo_{photo.file_unique_id}.jpg"
        content_type = "image/jpeg"
    elif msg.document:
        doc = msg.document
        file_obj = await doc.get_file()
        filename = doc.file_name or f"doc_{doc.file_unique_id}"
        content_type = doc.mime_type or "document"
    elif msg.voice:
        voice = msg.voice
        file_obj = await voice.get_file()
        filename = f"voice_{voice.file_unique_id}.ogg"
        content_type = "audio/ogg"

    if not file_obj:
        return

    await update.message.chat.send_action(action="typing")
    try:
        file_bytes = await file_obj.download_as_bytearray()
        rec = get_agent().memory.add_attachment(
            source_path_or_bytes=bytes(file_bytes),
            filename=filename,
            description=caption,
            content_type=content_type
        )
        
        reply = f"📎 Saved attachment #{rec['id']}: '{rec['original_name']}' ({rec['file_size']/1024:.1f} KB)"
        
        if caption:
            prompt = f"[User attached file: {rec['original_name']} (Type: {rec['file_type']})]\n"
            if rec.get("text_preview"):
                prompt += f"[File Content Preview: {rec['text_preview'][:800]}...]\n"
            prompt += f"User message: {caption}"
            ai_response = get_agent().chat(prompt)
            await send_long(update, f"{reply}\n\n🤖 Agent:\n{ai_response}")
        else:
            await update.message.reply_text(f"{reply}\n💡 Tip: Use /attachments to list your stored files.")
    except Exception as e:
        logger.error(f"Attachment error: {e}")
        await update.message.reply_text(f"❌ Failed to process attachment: {e}")

async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        deny(update)
        return
    text = update.message.text.strip()
    if not text:
        return

    # Check fast number shortcuts
    t_lower = text.lower()
    parts = t_lower.split(maxsplit=1)
    tok = parts[0]
    arg = parts[1].strip() if len(parts) > 1 else ""

    a = get_agent()

    if tok in ["43", "help"]:
        await cmd_help(update, ctx)
        return
    elif tok == "1":
        await send_long(update, a.memory.get_morning_briefing())
        return
    elif tok == "2":
        await send_long(update, a.memory.get_priorities_radar_formatted())
        return
    elif tok == "3":
        await send_long(update, a.memory.get_schedule_formatted())
        return
    elif tok == "4":
        await send_long(update, a.memory.get_calendar_view())
        return
    elif tok == "5":
        await send_long(update, a.memory.get_deadline_alerts())
        return
    elif tok == "6":
        await send_long(update, a.memory.get_habit_adaptive_recommendations())
        return
    elif tok == "7":
        await send_long(update, a.memory.get_user_data_summary())
        return
    elif tok == "8":
        await send_long(update, a.memory.get_tasks_formatted("pending"))
        return
    elif tok == "9":
        await send_long(update, a.memory.get_tasks_formatted("pending") + "\n\n" + a.memory.get_tasks_formatted("completed"))
        return
    elif tok == "10" and arg:
        ids = a.memory._parse_id_list(arg)
        if ids:
            await update.message.reply_text(a.memory.quick_complete_tasks(ids))
            return
    elif tok == "11" and arg:
        prio = "urgent" if "urgent" in arg else ("high" if "high" in arg else "medium")
        await update.message.reply_text(a.memory.quick_add_task(title=arg, priority=prio))
        return
    elif tok == "12" and arg:
        do_archive = "--archive" in arg or "-a" in arg
        ids = a.memory._parse_id_list(arg.replace("--archive", "").replace("-a", ""))
        if ids:
            await update.message.reply_text(a.memory.quick_delete_tasks(ids, archive=do_archive))
            return
    elif tok == "15":
        await update.message.reply_text(a.memory.quick_clear_completed_tasks(archive="--archive" in arg))
        return
    elif tok == "17":
        await send_long(update, a.memory.get_archived_tasks_formatted())
        return
    elif tok == "18":
        await send_long(update, a.memory.get_habits_formatted())
        return
    elif tok == "19" and arg:
        ids = a.memory._parse_id_list(arg)
        if ids:
            await update.message.reply_text(a.memory.quick_bulk_log_habits(ids, completed=True))
            return
    elif tok == "20" and arg:
        ids = a.memory._parse_id_list(arg)
        if ids:
            await update.message.reply_text(a.memory.quick_bulk_log_habits(ids, completed=False))
            return
    elif tok == "23":
        await send_long(update, a.memory.get_goals_formatted())
        return
    elif tok == "27":
        await send_long(update, a.memory.get_projects_formatted())
        return
    elif tok == "29":
        await send_long(update, a.memory.get_notes_formatted())
        return
    elif tok == "33":
        await send_long(update, a.memory.get_attachments_formatted())
        return
    elif tok == "37":
        await update.message.reply_text(a.memory.undo())
        return
    elif tok == "39":
        await send_long(update, a.memory.get_user_data_summary())
        return
    elif tok == "44":
        p = "monthly" if "month" in arg else "weekly"
        await send_long(update, a.memory.get_analytics_report_formatted(period=p))
        return
    elif tok == "45":
        await send_long(update, a.memory.get_analytics_report_formatted(period="weekly"))
        return
    elif tok == "46":
        await send_long(update, a.memory.get_analytics_report_formatted(period="monthly"))
        return
    elif tok == "47":
        await send_long(update, a.memory.get_proactive_notifications_formatted(force=True))
        return
    elif tok == "48":
        await send_long(update, a.memory.get_goal_progress_visualizations())
        return
    elif tok == "49":
        if not arg:
            await update.message.reply_text("Usage: 49 <search query> (e.g. 49 Python tutorial)")
            return
        await update.message.chat.send_action(action="typing")
        await send_long(update, format_search_results(web_search(arg, max_results=5)))
        return
    elif tok == "50":
        if not arg:
            await update.message.reply_text("Usage: 50 <url> (e.g. 50 https://example.com)")
            return
        await update.message.chat.send_action(action="typing")
        await send_long(update, format_webpage_result(read_webpage(arg)))
        return
    elif tok == "51":
        configured, msg = check_email_configured()
        if not configured:
            await update.message.reply_text(f"📧 Email not configured: {msg}")
            return
        unread_only = "unread" in arg.lower()
        count = 10
        for p in arg.split():
            if p.isdigit():
                count = int(p)
                break
        await update.message.chat.send_action(action="typing")
        await send_long(update, format_email_list(list_emails(count=count, unread_only=unread_only)))
        return
    elif tok == "52":
        if not arg:
            await update.message.reply_text("Usage: 52 <keyword> (e.g. 52 invoice)")
            return
        configured, msg = check_email_configured()
        if not configured:
            await update.message.reply_text(f"📧 Email not configured: {msg}")
            return
        await update.message.chat.send_action(action="typing")
        res = search_emails(arg)
        if res.get("error"):
            await update.message.reply_text(f"❌ {res['error']}")
        else:
            emails = res.get("results", [])
            if not emails:
                await update.message.reply_text(f"📭 No emails found for '{arg}'.")
            else:
                lines = [f"📧 Found {len(emails)} email(s) for '{arg}':\n"]
                for e in emails:
                    lines.append(f"  [{e['id']}] {e.get('subject', '(no subject)')}\n       From: {e.get('from', '')} | {e.get('date', '')}")
                await send_long(update, "\n".join(lines))
        return
    elif tok == "54":
        parts_yt = arg.split()
        if len(parts_yt) < 2:
            await update.message.reply_text("Usage: 54 <url> <minutes_watched> [total_minutes]")
            return
        try:
            w_min = float(parts_yt[1])
            t_min = float(parts_yt[2]) if len(parts_yt) >= 3 else None
        except ValueError:
            await update.message.reply_text("⚠️ Minutes must be numbers.")
            return
        res = track_video_progress(
            url_or_id=parts_yt[0],
            watched_seconds=int(w_min * 60),
            total_seconds=int(t_min * 60) if t_min else None
        )
        if res.get("error"):
            await update.message.reply_text(f"❌ {res['error']}")
        else:
            await send_long(update, format_video_progress(res))
        return
    elif tok == "55":
        await send_long(update, format_all_tracked(list_all_tracked_videos()))
        return
    elif tok == "56":
        if not arg:
            await update.message.reply_text("Usage: 56 <playlist_url_or_id>")
            return
        await update.message.chat.send_action(action="typing")
        await send_long(update, format_playlist_progress(get_playlist_progress(arg)))
        return

    await update.message.chat.send_action(action="typing")
    try:
        response = get_agent().chat(text)
        await send_long(update, response)
    except Exception as e:
        logger.error(f"AI error: {e}")
        await update.message.reply_text(
            f"AI error: {e}\n\nMake sure OmniRoute is running at http://localhost:20128"
        )

# --- Error handler ------------------------------------------------------------

async def error_handler(update: object, ctx: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Telegram error: {ctx.error}", exc_info=ctx.error)

# --- Bot command menu ---------------------------------------------------------

async def post_init(app: Application):
    commands = [
        BotCommand("start",       "Start & see morning briefing"),
        BotCommand("help",        "Show all commands"),
        BotCommand("today",       "Morning briefing + routine"),
        BotCommand("radar",       "Priorities & Deadline Radar"),
        BotCommand("schedule",    "College & study timetable"),
        BotCommand("cal",         "Weekly visual calendar"),
        BotCommand("tasks",       "Pending tasks"),
        BotCommand("done",        "Complete tasks: /done 1,2,3"),
        BotCommand("add",         "Add task: /add Study due tomorrow"),
        BotCommand("del",         "Delete task: /del 5 --archive"),
        BotCommand("prio",        "Set priority: /prio 6 urgent"),
        BotCommand("due",         "Set deadline: /due 6 next Friday"),
        BotCommand("cleardone",   "Clean tasks: /cleardone --archive"),
        BotCommand("archive",     "Move task to archive.json"),
        BotCommand("archived",    "View archived tasks"),
        BotCommand("habits",      "Habit tracker & streaks"),
        BotCommand("log",         "Log habit(s): /log 1,2"),
        BotCommand("unlog",       "Reset habit: /unlog 1"),
        BotCommand("goals",       "Active goals"),
        BotCommand("goal",        "Add goal: /goal Master SQL"),
        BotCommand("projects",    "Active projects"),
        BotCommand("deadlines",   "Approaching deadlines"),
        BotCommand("streaks",     "Habit coaching"),
        BotCommand("notes",       "Knowledge base"),
        BotCommand("note",        "Save note: /note DSA|tip"),
        BotCommand("attachments", "List file attachments"),
        BotCommand("undo",        "Undo last operation"),
        BotCommand("export",      "Export JSON backup file"),
        BotCommand("review",      "Log study review"),
        BotCommand("memory",      "Full memory snapshot"),
        BotCommand("report",      "Weekly/Monthly intelligence report"),
        BotCommand("weekly",      "Weekly analytics & habit score"),
        BotCommand("monthly",     "Monthly productivity review"),
        BotCommand("notify",      "Check proactive smart alerts"),
        BotCommand("goals_progress", "Goal roadmap progress bars"),
        BotCommand("web",         "Web search: /web query"),
        BotCommand("read",        "Read webpage: /read url"),
        BotCommand("inbox",       "View email inbox: /inbox"),
        BotCommand("emailsearch", "Search emails: /emailsearch query"),
        BotCommand("yttrack",     "Track YouTube: /yttrack url min"),
        BotCommand("ytprogress",  "View all YouTube progress"),
        BotCommand("ytplaylist",  "Playlist progress: /ytplaylist url"),
    ]
    await app.bot.set_my_commands(commands)
    logger.info("Command menu set.")

    # Start background proactive notifications scheduler
    asyncio.create_task(smart_notification_worker(app))

# --- Main ---------------------------------------------------------------------

def main():
    print("=" * 60)
    print("AI Productivity Agent -- Telegram Bot (v3.1)")
    print("=" * 60)
    print(f"Allowed user ID : {ALLOWED_USER_ID}")
    print(f"Bot token       : {BOT_TOKEN[:24]}...")
    print()

    try:
        get_agent()
    except Exception as e:
        print(f"WARNING: Could not pre-load agent: {e}")
        print("Make sure OmniRoute is running. Fast commands will still work.\n")

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )    

    app.add_handler(CommandHandler("start",         cmd_start))
    app.add_handler(CommandHandler("help",          cmd_help))
    app.add_handler(CommandHandler("today",         cmd_today))
    app.add_handler(CommandHandler("briefing",      cmd_today))
    app.add_handler(CommandHandler("radar",         cmd_radar))
    app.add_handler(CommandHandler("focus",         cmd_radar))
    app.add_handler(CommandHandler("priorities",    cmd_radar))
    app.add_handler(CommandHandler("schedule",      cmd_schedule))
    app.add_handler(CommandHandler("timetable",     cmd_schedule))
    app.add_handler(CommandHandler("routine",       cmd_schedule))
    app.add_handler(CommandHandler("cal",           cmd_calendar))
    app.add_handler(CommandHandler("calendar",      cmd_calendar))
    app.add_handler(CommandHandler("tasks",         cmd_tasks))
    app.add_handler(CommandHandler("todo",          cmd_tasks))
    app.add_handler(CommandHandler("tasksall",      cmd_tasks_all))
    app.add_handler(CommandHandler("done",          cmd_done))
    app.add_handler(CommandHandler("complete",      cmd_done))
    app.add_handler(CommandHandler("add",           cmd_add))
    app.add_handler(CommandHandler("del",           cmd_del))
    app.add_handler(CommandHandler("prio",          cmd_prio))
    app.add_handler(CommandHandler("due",           cmd_due))
    app.add_handler(CommandHandler("cleardone",     cmd_clear_done))
    app.add_handler(CommandHandler("archive",       cmd_archive))
    app.add_handler(CommandHandler("archived",      cmd_archived))
    app.add_handler(CommandHandler("habits",        cmd_habits))
    app.add_handler(CommandHandler("log",           cmd_log))
    app.add_handler(CommandHandler("unlog",         cmd_unlog))
    app.add_handler(CommandHandler("addhabit",      cmd_habit_add))
    app.add_handler(CommandHandler("delhabit",      cmd_habit_del))
    app.add_handler(CommandHandler("goals",         cmd_goals))
    app.add_handler(CommandHandler("goal",          cmd_goal_add))
    app.add_handler(CommandHandler("donegoal",      cmd_goal_complete))
    app.add_handler(CommandHandler("delgoal",       cmd_goal_del))
    app.add_handler(CommandHandler("projects",      cmd_projects))
    app.add_handler(CommandHandler("proj",          cmd_projects))
    app.add_handler(CommandHandler("addproj",       cmd_project_add))
    app.add_handler(CommandHandler("deadlines",     cmd_deadlines))
    app.add_handler(CommandHandler("alerts",        cmd_deadlines))
    app.add_handler(CommandHandler("streaks",       cmd_streaks))
    app.add_handler(CommandHandler("coaching",      cmd_streaks))
    app.add_handler(CommandHandler("notes",         cmd_notes))
    app.add_handler(CommandHandler("note",          cmd_note_add))
    app.add_handler(CommandHandler("delnote",       cmd_note_del))
    app.add_handler(CommandHandler("attachments",   cmd_attachments))
    app.add_handler(CommandHandler("undo",          cmd_undo))
    app.add_handler(CommandHandler("export",        cmd_export))
    app.add_handler(CommandHandler("review",        cmd_review))
    app.add_handler(CommandHandler("memory",        cmd_memory))
    app.add_handler(CommandHandler("profile",       cmd_memory))
    app.add_handler(CommandHandler("report",        cmd_report))
    app.add_handler(CommandHandler("analytics",     cmd_report))
    app.add_handler(CommandHandler("weekly",        cmd_weekly))
    app.add_handler(CommandHandler("monthly",       cmd_monthly))
    app.add_handler(CommandHandler("notify",        cmd_notify))
    app.add_handler(CommandHandler("goals_progress", cmd_goals_progress))
    app.add_handler(CommandHandler("goalprogress",   cmd_goals_progress))
    app.add_handler(CommandHandler("web",           cmd_web))
    app.add_handler(CommandHandler("read",          cmd_read))
    app.add_handler(CommandHandler("inbox",         cmd_inbox))
    app.add_handler(CommandHandler("emailsearch",   cmd_email_search))
    app.add_handler(CommandHandler("yttrack",       cmd_yt_track))
    app.add_handler(CommandHandler("ytprogress",    cmd_yt_progress))
    app.add_handler(CommandHandler("ytplaylist",    cmd_yt_playlist))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL | filters.VOICE, handle_attachment))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)

    print("Bot is running! Open Telegram and send /start to your bot.")
    print("Press Ctrl+C to stop.\n")
    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )

if __name__ == "__main__":
    main()
