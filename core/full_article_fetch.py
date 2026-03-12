"""
Selective full-article fetch for structural classification rescue (Phase 2).

Used only when structural_category is None after first pass, behind USE_SELECTIVE_FULL_FETCH.
Fetches full HTML, extracts main body text (strip nav/ads/scripts), normalizes whitespace,
limits to 5_000 characters. Does not run during snapshot; no recursion.
"""

from __future__ import annotations

import re
import ssl
from typing import Optional, Tuple
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

DEFAULT_TIMEOUT = 15
MAX_BODY_CHARS = 5_000
USER_AGENT = "Mozilla/5.0 (compatible; PU-Observatory/1.0; +https://htcglobal.asia)"


def _normalize_whitespace(text: str) -> str:
    """Collapse runs of whitespace to single space, strip."""
    if not text or not isinstance(text, str):
        return ""
    return " ".join(text.split()).strip()


def _extract_main_body(html: str) -> str:
    """
    Extract main readable body text: strip script, style, nav-like blocks; prefer main/article/body.
    No external deps; heuristic only.
    """
    if not html:
        return ""
    # Remove script and style
    html = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<style[^>]*>.*?</style>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    # Prefer <main> or <article> or fallback to <body>
    for tag in ("main", "article", "body"):
        m = re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", html, re.DOTALL | re.IGNORECASE)
        if m:
            block = m.group(1)
            # Strip tags, get text
            text = re.sub(r"<[^>]+>", " ", block)
            text = _normalize_whitespace(text)
            if len(text) >= 100:
                return text
    # Fallback: strip all tags from full html
    text = re.sub(r"<[^>]+>", " ", html)
    return _normalize_whitespace(text)


def fetch_full_html(url: str, timeout: int = DEFAULT_TIMEOUT) -> Tuple[Optional[str], Optional[str]]:
    """
    Fetch full page HTML. Returns (html, None) on success or (None, error_message) on failure.
    Handles timeout, 403, and parse errors without raising.
    """
    if not url or not url.strip().startswith(("http://", "https://")):
        return None, "invalid_url"
    url = url.strip()
    try:
        req = Request(url, headers={"User-Agent": USER_AGENT})
        ctx = ssl.create_default_context()
        with urlopen(req, timeout=timeout, context=ctx) as resp:
            body = resp.read()
            charset = resp.headers.get_content_charset() or "utf-8"
            try:
                html = body.decode(charset, errors="replace")
            except Exception:
                html = body.decode("utf-8", errors="replace")
            return html, None
    except HTTPError as e:
        return None, f"http_{e.code}"
    except URLError as e:
        return None, f"url_error:{str(e.reason)[:50]}"
    except TimeoutError:
        return None, "timeout"
    except Exception as e:
        return None, f"error:{str(e)[:50]}"


def fetch_and_extract_body(url: str, timeout: int = DEFAULT_TIMEOUT) -> Tuple[str, Optional[str]]:
    """
    Fetch full HTML and extract main body text, normalized and limited to MAX_BODY_CHARS.
    Returns (extracted_text, None) on success or ("", error_message) on failure.
    """
    html, err = fetch_full_html(url, timeout=timeout)
    if err:
        return "", err
    body = _extract_main_body(html or "")
    body = body[:MAX_BODY_CHARS]
    return body, None
