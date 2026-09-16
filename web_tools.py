#!/usr/bin/env python3
"""
Web / Browser Tools
===================
Provides lightweight browser-like capabilities using requests + BeautifulSoup.
No headless browser installation required.

Capabilities:
  - Web search (DuckDuckGo Instant Answers API — no key needed)
  - Read & extract clean text from any public webpage
  - Source attribution for all fetched content
"""

import re
import urllib.parse
from typing import Optional

try:
    import requests
    from bs4 import BeautifulSoup
    WEB_TOOLS_AVAILABLE = True
except ImportError:
    WEB_TOOLS_AVAILABLE = False


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

REQUEST_TIMEOUT = 15  # seconds

# Tags whose content is noise (scripts, styles, navigation, ads)
_NOISE_TAGS = [
    "script", "style", "noscript", "header", "footer", "nav",
    "aside", "form", "button", "iframe", "svg", "img", "meta", "link"
]


# ---------------------------------------------------------------------------
# Availability Check
# ---------------------------------------------------------------------------

def check_web_tools_available() -> str:
    """Return a status message about web tool availability."""
    if not WEB_TOOLS_AVAILABLE:
        return (
            "❌ Web tools unavailable. Install dependencies with:\n"
            "   pip install requests beautifulsoup4"
        )
    return "✅ Web tools available (requests + BeautifulSoup)."


# ---------------------------------------------------------------------------
# Web Search — DuckDuckGo Instant Answers (no API key required)
# ---------------------------------------------------------------------------

def web_search(query: str, max_results: int = 5) -> dict:
    """
    Search the web using DuckDuckGo's public API.

    Args:
        query: Search query string.
        max_results: Maximum number of results to return (default 5).

    Returns:
        dict with keys: 'query', 'results' (list), 'source', 'error' (if any).
    """
    if not WEB_TOOLS_AVAILABLE:
        return {
            "error": "Web tools not installed. Run: pip install requests beautifulsoup4",
            "query": query,
            "results": []
        }

    try:
        # DuckDuckGo HTML search (scraping the results page)
        encoded_query = urllib.parse.quote_plus(query)
        url = f"https://html.duckduckgo.com/html/?q={encoded_query}"

        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
