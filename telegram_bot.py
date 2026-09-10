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

