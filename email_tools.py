#!/usr/bin/env python3
"""
Email Tools (IMAP + SMTP)
=========================
Provides email access using standard IMAP (read) and SMTP (send) with an App Password.
Works with Gmail, Outlook, Yahoo, and any IMAP/SMTP provider.

Setup in .env:
    EMAIL_PROVIDER=gmail          # gmail | outlook | custom
    EMAIL_ADDRESS=you@gmail.com
    EMAIL_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx
    EMAIL_IMAP_HOST=imap.gmail.com     # auto-set for gmail/outlook
    EMAIL_SMTP_HOST=smtp.gmail.com     # auto-set for gmail/outlook
    EMAIL_IMAP_PORT=993
    EMAIL_SMTP_PORT=587

Gmail App Password setup:
    1. Go to https://myaccount.google.com/security
    2. Enable 2-Step Verification
    3. Search "App passwords" -> Create one for "Mail"
    4. Paste the 16-character password as EMAIL_APP_PASSWORD

SAFETY RULES (enforced in code):
    - Never send without explicit user confirmation (show to/subject/body first)
    - Never delete or permanently modify emails without confirmation
    - Never expose email content to unauthorized users
"""

import os
import imaplib
import smtplib
import email
import email.header
import html
import re
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

# ---------------------------------------------------------------------------
# Provider Presets
# ---------------------------------------------------------------------------

PROVIDER_PRESETS = {
    "gmail": {
        "imap_host": "imap.gmail.com",
        "imap_port": 993,
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
    },
    "outlook": {
        "imap_host": "outlook.office365.com",
        "imap_port": 993,
        "smtp_host": "smtp.office365.com",
        "smtp_port": 587,
    },
    "yahoo": {
        "imap_host": "imap.mail.yahoo.com",
        "imap_port": 993,
        "smtp_host": "smtp.mail.yahoo.com",
        "smtp_port": 587,
    },
}


# ---------------------------------------------------------------------------
# Config Helper
# ---------------------------------------------------------------------------

def _get_email_config() -> dict:
    """Load email configuration from environment variables."""
    provider = os.getenv("EMAIL_PROVIDER", "gmail").lower()
    preset = PROVIDER_PRESETS.get(provider, PROVIDER_PRESETS["gmail"])

    return {
        "address": os.getenv("EMAIL_ADDRESS", ""),
        "password": os.getenv("EMAIL_APP_PASSWORD", ""),
        "imap_host": os.getenv("EMAIL_IMAP_HOST", preset["imap_host"]),
        "imap_port": int(os.getenv("EMAIL_IMAP_PORT", preset["imap_port"])),
        "smtp_host": os.getenv("EMAIL_SMTP_HOST", preset["smtp_host"]),
        "smtp_port": int(os.getenv("EMAIL_SMTP_PORT", preset["smtp_port"])),
        "provider": provider,
    }


def check_email_configured() -> tuple[bool, str]:
    """Check if email credentials are configured. Returns (is_configured, message)."""
    cfg = _get_email_config()
    if not cfg["address"]:
        return False, "EMAIL_ADDRESS not set in .env"
    if not cfg["password"]:
        return False, "EMAIL_APP_PASSWORD not set in .env"
    return True, f"Email configured: {cfg['address']} ({cfg['provider']})"

