"""
Sitemap connector for V2 Evidence Engine.
Parses sitemap XML and returns list of {url, title, published_at, snippet, source_name}.
Sitemaps often only have URLs; title/snippet may be empty.
"""

from typing import List, Dict, Any, Optional
from xml.etree import ElementTree as ET
import re

try:
    import urllib.request
    _HAS_URLLIB = True
except ImportError:
    _HAS_URLLIB = False


def _parse_sitemap_date(elem: Any) -> Optional[str]:
    """Extract lastmod or similar as YYYY-MM-DD."""
    for tag in ("lastmod", "news:publication_date", "publication_date"):
        child = elem.find(tag)
        if child is not None and child.text:
            s = child.text.strip()[:10]
            if re.match(r"\d{4}-\d{2}-\d{2}", s):
                return s
    return None


def fetch_sitemap(sitemap_url: str, source_name: str, max_urls: int = 200) -> List[Dict[str, Any]]:
    """
    Fetch sitemap XML and return candidate items.
    Each item: url, title (often None), published_at (from lastmod if present), snippet (None), source_name.
    """
    if not _HAS_URLLIB or not sitemap_url or not source_name:
        return []
    try:
        req = urllib.request.Request(sitemap_url)
        req.add_header("User-Agent", "Mozilla/5.0 (compatible; PU-Observatory/2.0)")
        with urllib.request.urlopen(req, timeout=15) as r:
            body = r.read()
    except Exception:
        return []
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        return []
    SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
    out: List[Dict[str, Any]] = []
    for url_elem in root.findall(f".//{{{SITEMAP_NS}}}url") or root.findall(".//url"):
        loc = url_elem.find(f"{{{SITEMAP_NS}}}loc") or url_elem.find("loc")
        if loc is None or not loc.text:
            continue
        url = loc.text.strip()
        if not url.startswith(("http://", "https://")):
            continue
        published_at = _parse_sitemap_date(url_elem)
        out.append({
            "url": url,
            "title": None,
            "published_at": published_at,
            "snippet": None,
            "source_name": source_name,
        })
        if len(out) >= max_urls:
            break
    # Fallback: no namespace
    if not out and not root.findall(".//sm:url", ns):
        for url_elem in root.iter():
            if url_elem.tag.endswith("}url") or url_elem.tag == "url":
                loc = None
                for c in url_elem:
                    if c.tag.endswith("}loc") or c.tag == "loc":
                        loc = c
                        break
                if loc is not None and loc.text:
                    url = loc.text.strip()
                    if url.startswith(("http://", "https://")):
                        out.append({
                            "url": url,
                            "title": None,
                            "published_at": None,
                            "snippet": None,
                            "source_name": source_name,
                        })
                    if len(out) >= max_urls:
                        break
    return out
