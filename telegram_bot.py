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

