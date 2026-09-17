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

        soup = BeautifulSoup(resp.text, "html.parser")
        results = []

        for result in soup.select(".result"):
            title_tag = result.select_one(".result__title")
            snippet_tag = result.select_one(".result__snippet")
            url_tag = result.select_one(".result__url")

            title = title_tag.get_text(strip=True) if title_tag else ""
            snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""
            link = url_tag.get_text(strip=True) if url_tag else ""

            # Try to get real href
            a_tag = result.select_one(".result__title a")
            if a_tag and a_tag.get("href"):
                href = a_tag["href"]
                # DuckDuckGo sometimes wraps URLs
                if href.startswith("//duckduckgo.com/l/?"):
                    parsed = urllib.parse.urlparse(href)
                    qs = urllib.parse.parse_qs(parsed.query)
                    link = qs.get("uddg", [link])[0]
                elif href.startswith("http"):
                    link = href

            if title and (snippet or link):
                results.append({
                    "title": title,
                    "url": link,
                    "snippet": snippet
                })

            if len(results) >= max_results:
                break

        if not results:
            # Fallback: use DuckDuckGo Instant Answer JSON API
            api_url = f"https://api.duckduckgo.com/?q={encoded_query}&format=json&no_html=1&skip_disambig=1"
            api_resp = requests.get(api_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            data = api_resp.json()

            abstract = data.get("AbstractText", "")
            abstract_url = data.get("AbstractURL", "")
            abstract_source = data.get("AbstractSource", "")

            if abstract:
                results.append({
                    "title": data.get("Heading", query),
                    "url": abstract_url,
                    "snippet": abstract,
                    "source": abstract_source
                })

            for topic in data.get("RelatedTopics", [])[:max_results - len(results)]:
                if isinstance(topic, dict) and "Text" in topic:
                    results.append({
                        "title": topic.get("Text", "")[:80],
                        "url": topic.get("FirstURL", ""),
                        "snippet": topic.get("Text", "")
                    })

        return {
            "query": query,
            "results": results,
            "source": "DuckDuckGo",
            "total_found": len(results)
        }

    except requests.RequestException as e:
        return {
            "query": query,
            "results": [],
            "error": f"Network error during search: {str(e)}",
            "source": "DuckDuckGo"
        }
    except Exception as e:
        return {
            "query": query,
            "results": [],
            "error": f"Search failed: {str(e)}",
            "source": "DuckDuckGo"
        }


# ---------------------------------------------------------------------------
# Webpage Reader — Clean Text Extraction
# ---------------------------------------------------------------------------

def read_webpage(url: str, max_chars: int = 8000) -> dict:
    """
    Fetch a public webpage and extract its clean readable text.

    Args:
        url: The URL to read.
        max_chars: Maximum characters of text to return (default 8000).

    Returns:
        dict with keys: 'url', 'title', 'text', 'source', 'char_count', 'error'.
    """
    if not WEB_TOOLS_AVAILABLE:
        return {
            "error": "Web tools not installed. Run: pip install requests beautifulsoup4",
            "url": url,
            "text": ""
        }

    # Validate URL
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT, allow_redirects=True)
        resp.raise_for_status()

        # Detect encoding
        if resp.encoding and resp.encoding.lower() not in ("utf-8", "utf8"):
            try:
                content = resp.content.decode("utf-8", errors="replace")
            except Exception:
                content = resp.text
        else:
            content = resp.text

        soup = BeautifulSoup(content, "html.parser")

        # Remove noise tags
        for tag in soup(_NOISE_TAGS):
            tag.decompose()

        # Get page title
        title = ""
        title_tag = soup.find("title")
        if title_tag:
            title = title_tag.get_text(strip=True)

        # Try to find main content first
        main_content = (
            soup.find("main") or
            soup.find("article") or
            soup.find(id=re.compile(r"content|main|article|post", re.I)) or
            soup.find(class_=re.compile(r"content|main|article|post|body", re.I)) or
            soup.body or
            soup
        )

        # Extract text with paragraph breaks
        lines = []
        for element in main_content.find_all(["p", "h1", "h2", "h3", "h4", "h5", "li", "td", "th"]):
            text = element.get_text(separator=" ", strip=True)
            if text and len(text) > 20:  # Skip tiny fragments
                lines.append(text)

        raw_text = "\n\n".join(lines)

        # Fallback to full text if no structured content found
        if len(raw_text) < 200:
            raw_text = main_content.get_text(separator="\n", strip=True)

        # Normalize whitespace
        raw_text = re.sub(r"\n{3,}", "\n\n", raw_text)
        raw_text = re.sub(r"[ \t]+", " ", raw_text)

        text = raw_text[:max_chars]
        truncated = len(raw_text) > max_chars

        return {
            "url": resp.url,  # Final URL after redirects
            "title": title,
            "text": text,
            "char_count": len(text),
            "truncated": truncated,
            "source": resp.url
        }

    except requests.exceptions.Timeout:
        return {"url": url, "text": "", "error": f"Request timed out after {REQUEST_TIMEOUT}s"}
    except requests.exceptions.ConnectionError as e:
        return {"url": url, "text": "", "error": f"Connection error: {str(e)}"}
    except requests.exceptions.HTTPError as e:
        return {"url": url, "text": "", "error": f"HTTP error {resp.status_code}: {str(e)}"}
    except Exception as e:
        return {"url": url, "text": "", "error": f"Failed to read page: {str(e)}"}


# ---------------------------------------------------------------------------
# Format Helpers (for agent output)
# ---------------------------------------------------------------------------

def format_search_results(result: dict) -> str:
    """Format web_search() result dict into a readable string for the agent."""
    if result.get("error"):
        return f"🌐 Web Search Error: {result['error']}"

    query = result.get("query", "")
    results = result.get("results", [])
    source = result.get("source", "Web")

    if not results:
        return f"🌐 No results found for: '{query}'\n📡 Source: {source}"

    lines = [f"🌐 Web Search Results for: '{query}' (via {source})\n"]
    for i, r in enumerate(results, 1):
        lines.append(f"**{i}. {r.get('title', 'No title')}**")
        if r.get("url"):
            lines.append(f"   🔗 {r['url']}")
        if r.get("snippet"):
            lines.append(f"   {r['snippet']}")
        lines.append("")

    return "\n".join(lines).strip()


def format_webpage_result(result: dict) -> str:
    """Format read_webpage() result dict into a readable string for the agent."""
    if result.get("error"):
        return f"🌐 Page Read Error: {result['error']}\n🔗 URL: {result.get('url', '')}"

    title = result.get("title", "")
    url = result.get("source") or result.get("url", "")
    text = result.get("text", "")
    truncated = result.get("truncated", False)

    header = f"🌐 **{title}**\n🔗 Source: {url}\n"
    footer = "\n\n📄 _(Content truncated — page has more text)_" if truncated else ""
    return header + "\n" + text + footer
