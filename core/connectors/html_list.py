"""
HTML list page connector for V2 Evidence Engine.
Uses admin-curated selectors to extract links from a list page.
Returns list of {url, title, published_at, snippet, source_name}.
"""

from typing import List, Dict, Any, Optional
import re

try:
    import urllib.request
    from html.parser import HTMLParser
    _HAS_URLLIB = True
except ImportError:
    _HAS_URLLIB = False

try:
    from bs4 import BeautifulSoup
    _HAS_BS4 = True
except ImportError:
    _HAS_BS4 = False


def _resolve_url(base: str, href: str) -> str:
    """Resolve relative href against base URL."""
    if not href or not base:
        return href or ""
    href = href.strip()
    if href.startswith(("http://", "https://")):
        return href
    base = base.rstrip("/")
    if href.startswith("/"):
        try:
            from urllib.parse import urlparse
            p = urlparse(base)
            return f"{p.scheme}://{p.netloc}{href}"
        except Exception:
            return href
    if not base.endswith("/"):
        base = base + "/"
    return base + href.lstrip("./")


def fetch_html_list(
    list_url: str,
    source_name: str,
    selectors: Optional[Dict[str, Any]] = None,
    base_url: Optional[str] = None,
    max_items: int = 50,
) -> List[Dict[str, Any]]:
    """
    Fetch HTML list page and extract items using selectors.
    selectors: item_selector, link_selector, title_selector, date_selector, date_attr, max_items.
    Each item: url, title, published_at (YYYY-MM-DD or None), snippet, source_name.
    """
    if not _HAS_URLLIB or not list_url or not source_name:
        return []
    base = base_url or list_url
    try:
        req = urllib.request.Request(list_url)
        req.add_header("User-Agent", "Mozilla/5.0 (compatible; PU-Observatory/2.0)")
        with urllib.request.urlopen(req, timeout=15) as r:
            html = r.read().decode("utf-8", errors="replace")
    except Exception:
        return []

    sel = selectors or {}
    item_sel = sel.get("item_selector") or "article, .news-item, li"
    link_sel = sel.get("link_selector") or "a"
    title_sel = sel.get("title_selector") or "a"
    date_sel = sel.get("date_selector") or "time"
    date_attr = sel.get("date_attr") or "datetime"
    max_items = min(int(sel.get("max_items", max_items)), 100)

    out: List[Dict[str, Any]] = []

    if _HAS_BS4:
        soup = BeautifulSoup(html, "html.parser")
        items = soup.select(item_sel) if item_sel else []
        for item in items[:max_items]:
            link_el = item.select_one(link_sel) if link_sel else item.find("a")
            if not link_el or not link_el.get("href"):
                continue
            href = link_el.get("href", "").strip()
            url = _resolve_url(base, href)
            if not url.startswith(("http://", "https://")):
                continue
            title_el = item.select_one(title_sel) if title_sel else link_el
            title = (title_el.get_text(strip=True) if title_el else "") or None
            published_at = None
            date_el = item.select_one(date_sel) if date_sel else None
            if date_el and date_attr:
                published_at = date_el.get(date_attr) or (date_el.get_text(strip=True) if date_el else None)
            if published_at and len(published_at) >= 10:
                published_at = published_at[:10]
            else:
                published_at = None
            out.append({
                "url": url,
                "title": title,
                "published_at": published_at,
                "snippet": None,
                "source_name": source_name,
            })
        return out

    # Fallback: simple regex for <a href="..."> when no BeautifulSoup
    link_re = re.compile(r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>([^<]*)</a>', re.I)
    for m in link_re.finditer(html)[:max_items]:
        href, title = m.group(1).strip(), (m.group(2).strip() or None)
        url = _resolve_url(base, href)
        if url.startswith(("http://", "https://")):
            out.append({
                "url": url,
                "title": title,
                "published_at": None,
                "snippet": None,
                "source_name": source_name,
            })
    return out
