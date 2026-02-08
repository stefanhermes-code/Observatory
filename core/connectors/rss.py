"""
RSS/Atom feed connector for V2 Evidence Engine.
Returns list of {url, title, published_at, snippet, source_name}.
"""

from typing import List, Dict, Any, Optional
import re

try:
    import feedparser
    _HAS_FEEDPARSER = True
except ImportError:
    _HAS_FEEDPARSER = False


def _parse_date(entry: Any) -> Optional[str]:
    """Return date as YYYY-MM-DD string or None."""
    for key in ("published_parsed", "updated_parsed", "created_parsed"):
        val = getattr(entry, key, None)
        if val and hasattr(val, "tm_year"):
            try:
                return f"{val.tm_year:04d}-{val.tm_mon:02d}-{val.tm_mday:02d}"
            except (TypeError, IndexError):
                pass
    return None


def _get_link(entry: Any) -> Optional[str]:
    """Get best link from entry."""
    link = getattr(entry, "link", None)
    if link and isinstance(link, str):
        return link.strip()
    links = getattr(entry, "links", None)
    if links:
        for l in links:
            href = l.get("href") if isinstance(l, dict) else getattr(l, "href", None)
            if href:
                return href.strip() if isinstance(href, str) else None
    return None


def _snippet(entry: Any, max_len: int = 300) -> str:
    """Summary or description snippet."""
    s = (
        getattr(entry, "summary", None)
        or getattr(entry, "description", None)
        or getattr(entry, "title", None)
        or ""
    )
    if not s:
        return ""
    if hasattr(s, "get"):
        s = s.get("value", "") if isinstance(s, dict) else str(s)
    s = str(s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return (s[:max_len] + "...") if len(s) > max_len else s


def fetch_rss(rss_url: str, source_name: str, max_entries: int = 100) -> List[Dict[str, Any]]:
    """
    Fetch RSS/Atom feed and return candidate items.
    Each item: url, title, published_at (YYYY-MM-DD or None), snippet, source_name.
    """
    if not _HAS_FEEDPARSER:
        return []
    if not rss_url or not source_name:
        return []
    try:
        parsed = feedparser.parse(rss_url)
    except Exception:
        return []
    out: List[Dict[str, Any]] = []
    entries = getattr(parsed, "entries", [])[:max_entries]
    for entry in entries:
        link = _get_link(entry)
        if not link or not link.startswith(("http://", "https://")):
            continue
        title = getattr(entry, "title", None) or ""
        title = title.strip() if isinstance(title, str) else str(title).strip()
        published_at = _parse_date(entry)
        snippet = _snippet(entry)
        out.append({
            "url": link,
            "title": title or None,
            "published_at": published_at,
            "snippet": snippet or None,
            "source_name": source_name,
        })
    return out
