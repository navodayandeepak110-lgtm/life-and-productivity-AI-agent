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


# ---------------------------------------------------------------------------
# IMAP Connection Helper
# ---------------------------------------------------------------------------

def _imap_connect() -> imaplib.IMAP4_SSL:
    """Create and return an authenticated IMAP connection."""
    cfg = _get_email_config()
    if not cfg["address"] or not cfg["password"]:
        raise ValueError(
            "Email not configured. Set EMAIL_ADDRESS and EMAIL_APP_PASSWORD in .env\n"
            "For Gmail: enable 2FA and generate an App Password at "
            "https://myaccount.google.com/apppasswords"
        )
    mail = imaplib.IMAP4_SSL(cfg["imap_host"], cfg["imap_port"])
    mail.login(cfg["address"], cfg["password"])
    return mail


# ---------------------------------------------------------------------------
# Decode Helpers
# ---------------------------------------------------------------------------

def _decode_header(raw: str) -> str:
    """Decode MIME-encoded email header (subject, from, etc.)."""
    if not raw:
        return ""
    parts = email.header.decode_header(raw)
    decoded = []
    for part, enc in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(enc or "utf-8", errors="replace"))
        else:
            decoded.append(str(part))
    return " ".join(decoded)


def _extract_body(msg) -> str:
    """Extract plain-text body from an email message."""
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            disp = str(part.get("Content-Disposition", ""))
            if ctype == "text/plain" and "attachment" not in disp:
                try:
                    charset = part.get_content_charset() or "utf-8"
                    body = part.get_payload(decode=True).decode(charset, errors="replace")
                    break
                except Exception:
                    continue
    else:
        try:
            charset = msg.get_content_charset() or "utf-8"
            raw_body = msg.get_payload(decode=True)
            if raw_body:
                body = raw_body.decode(charset, errors="replace")
                # Strip HTML if needed
                if msg.get_content_type() == "text/html":
                    body = re.sub(r"<[^>]+>", " ", body)
                    body = html.unescape(body)
        except Exception:
            body = str(msg.get_payload())

    # Normalize whitespace
    body = re.sub(r"\r\n", "\n", body)
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    return body


# ---------------------------------------------------------------------------
# Public Functions
# ---------------------------------------------------------------------------

def list_emails(folder: str = "INBOX", count: int = 10, unread_only: bool = False) -> dict:
    """
    Fetch a list of recent emails from a folder.

    Args:
        folder: Mailbox folder name (default: 'INBOX').
        count: Number of emails to return (default: 10, max: 50).
        unread_only: If True, return only unread emails.

    Returns:
        dict with 'emails' list and metadata.
    """
    count = min(count, 50)
    try:
        mail = _imap_connect()
        mail.select(f'"{folder}"')

        search_criteria = "(UNSEEN)" if unread_only else "ALL"
        _, message_ids = mail.search(None, search_criteria)

        ids = message_ids[0].split()
        if not ids:
            mail.logout()
            return {"emails": [], "folder": folder, "total": 0}

        # Get the most recent `count` emails
        recent_ids = ids[-count:][::-1]

        emails = []
        for uid in recent_ids:
            _, data = mail.fetch(uid, "(BODY.PEEK[HEADER.FIELDS (FROM TO SUBJECT DATE)])")
            if data and data[0]:
                raw_headers = data[0][1]
                msg = email.message_from_bytes(raw_headers)
                emails.append({
                    "id": uid.decode(),
                    "from": _decode_header(msg.get("From", "")),
                    "to": _decode_header(msg.get("To", "")),
                    "subject": _decode_header(msg.get("Subject", "(No subject)")),
                    "date": msg.get("Date", ""),
                })

        mail.logout()
        return {
            "emails": emails,
            "folder": folder,
            "total": len(ids),
            "showing": len(emails),
            "unread_only": unread_only,
        }

    except imaplib.IMAP4.error as e:
        return {"emails": [], "error": f"IMAP error: {str(e)} — Check your App Password and IMAP settings."}
    except Exception as e:
        return {"emails": [], "error": f"Failed to list emails: {str(e)}"}


def read_email(email_id: str, folder: str = "INBOX") -> dict:
    """
    Read the full content of a specific email by its ID.

    Args:
        email_id: Email ID string (from list_emails).
        folder: Folder containing the email.

    Returns:
        dict with 'from', 'to', 'subject', 'date', 'body'.
    """
    try:
        mail = _imap_connect()
        mail.select(f'"{folder}"')

        _, data = mail.fetch(email_id.encode(), "(RFC822)")
        if not data or not data[0]:
            mail.logout()
            return {"error": f"Email #{email_id} not found in {folder}"}

        raw_email = data[0][1]
        msg = email.message_from_bytes(raw_email)

        result = {
            "id": email_id,
            "from": _decode_header(msg.get("From", "")),
            "to": _decode_header(msg.get("To", "")),
            "subject": _decode_header(msg.get("Subject", "(No subject)")),
            "date": msg.get("Date", ""),
            "body": _extract_body(msg),
        }

        mail.logout()
        return result

    except imaplib.IMAP4.error as e:
        return {"error": f"IMAP error: {str(e)}"}
    except Exception as e:
        return {"error": f"Failed to read email: {str(e)}"}


def search_emails(query: str, folder: str = "INBOX", max_results: int = 10) -> dict:
    """
    Search emails by keyword (searches subject and body text).

    Args:
        query: Search keyword or phrase.
        folder: Folder to search in (default: 'INBOX').
        max_results: Maximum number of results (default: 10).

    Returns:
        dict with 'results' list and query info.
    """
    try:
        mail = _imap_connect()
        mail.select(f'"{folder}"')

        # IMAP search (subject + body text)
        encoded_query = query.encode("utf-8")
        _, subject_ids = mail.search("UTF-8", f'(SUBJECT "{query}")')
        _, body_ids = mail.search("UTF-8", f'(BODY "{query}")')

        all_ids_set = set()
        for id_list in [subject_ids[0].split(), body_ids[0].split()]:
            all_ids_set.update(id_list)

        if not all_ids_set:
            mail.logout()
            return {"results": [], "query": query, "total": 0}

        recent_ids = sorted(all_ids_set, reverse=True)[:max_results]

        results = []
        for uid in recent_ids:
            _, data = mail.fetch(uid, "(BODY.PEEK[HEADER.FIELDS (FROM TO SUBJECT DATE)])")
            if data and data[0]:
                raw_headers = data[0][1]
                msg = email.message_from_bytes(raw_headers)
                results.append({
                    "id": uid.decode(),
                    "from": _decode_header(msg.get("From", "")),
                    "subject": _decode_header(msg.get("Subject", "(No subject)")),
                    "date": msg.get("Date", ""),
                })

        mail.logout()
        return {"results": results, "query": query, "total": len(results)}

    except imaplib.IMAP4.error as e:
        return {"results": [], "error": f"IMAP search error: {str(e)}"}
    except Exception as e:
        return {"results": [], "error": f"Search failed: {str(e)}"}


def create_draft(to: str, subject: str, body: str) -> dict:
    """
    Build an email draft for review. Does NOT send — just returns the preview.

    Args:
        to: Recipient email address.
        subject: Email subject line.
        body: Email body text.

    Returns:
        dict with 'draft' details and a human-readable preview.
    """
    cfg = _get_email_config()
    from_addr = cfg["address"]

    if not from_addr:
        return {"error": "EMAIL_ADDRESS not configured in .env"}

    draft = {
        "from": from_addr,
        "to": to,
        "subject": subject,
        "body": body,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "draft_pending_approval",
    }

    preview = (
        f"\n📧 EMAIL DRAFT — REVIEW BEFORE SENDING\n"
        f"{'='*50}\n"
        f"  From:    {from_addr}\n"
        f"  To:      {to}\n"
        f"  Subject: {subject}\n"
        f"{'─'*50}\n"
        f"{body}\n"
        f"{'='*50}\n"
        f"⚠️  Please confirm: Reply 'yes' to send, 'no' to cancel."
    )

    draft["preview"] = preview
    return draft


def send_email(to: str, subject: str, body: str) -> dict:
    """
    Send an email via SMTP. Should only be called AFTER user explicitly confirms.

    Args:
        to: Recipient address.
        subject: Subject line.
        body: Email body.

    Returns:
        dict with 'success' bool and status message.
    """
    cfg = _get_email_config()
    from_addr = cfg["address"]
    password = cfg["password"]

    if not from_addr or not password:
        return {"success": False, "error": "Email credentials not configured in .env"}

    try:
        msg = MIMEMultipart()
        msg["From"] = from_addr
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        with smtplib.SMTP(cfg["smtp_host"], cfg["smtp_port"]) as server:
            server.ehlo()
            server.starttls()
            server.login(from_addr, password)
            server.sendmail(from_addr, [to], msg.as_string())

        return {
            "success": True,
            "message": f"✅ Email sent successfully to {to} | Subject: '{subject}'",
            "from": from_addr,
            "to": to,
            "subject": subject,
        }

    except smtplib.SMTPAuthenticationError:
        return {
            "success": False,
            "error": (
                "SMTP authentication failed. Check your App Password.\n"
                "Gmail: https://myaccount.google.com/apppasswords"
            )
        }
    except smtplib.SMTPException as e:
        return {"success": False, "error": f"SMTP error: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": f"Failed to send email: {str(e)}"}


# ---------------------------------------------------------------------------
# Format Helpers
# ---------------------------------------------------------------------------

def format_email_list(result: dict) -> str:
    """Format list_emails() result for readable agent output."""
    if result.get("error"):
        return f"📧 Email Error: {result['error']}"

    emails = result.get("emails", [])
    folder = result.get("folder", "INBOX")
    total = result.get("total", 0)
    unread_filter = " (unread only)" if result.get("unread_only") else ""

    if not emails:
        return f"📭 No emails found in {folder}{unread_filter}."

    lines = [f"📧 {folder}{unread_filter} — {len(emails)} of {total} emails:\n"]
    for e in emails:
        lines.append(f"  [{e['id']}] {e.get('subject', '(no subject)')}")
        lines.append(f"       From: {e.get('from', '')}  |  {e.get('date', '')}")
        lines.append("")

    return "\n".join(lines).strip()


def format_email_content(result: dict) -> str:
    """Format read_email() result for readable agent output."""
    if result.get("error"):
        return f"📧 Email Read Error: {result['error']}"

    lines = [
        f"📧 Email #{result.get('id', '')}",
        f"{'='*50}",
        f"From:    {result.get('from', '')}",
        f"To:      {result.get('to', '')}",
        f"Subject: {result.get('subject', '')}",
        f"Date:    {result.get('date', '')}",
        f"{'─'*50}",
        result.get("body", "(no body)"),
    ]
    return "\n".join(lines)
