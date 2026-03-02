"""
JSON-LD enrichment for Evidence Engine (middle-road enrichment, no full article extraction).
Lightweight HTTP GET to candidate URL; parse <script type="application/ld+json">; build enriched_text.
Used for region and PU relevance gating only when enriched text length >= 200.
"""

import json
import re
import ssl
from typing import Dict, Any, List, Optional, Tuple
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

# Preferred @type values for article-like content (schema.org)
CONTENT_TYPES = {"NewsArticle", "Article", "Report", "BlogPosting"}

# Default timeout and user-agent for lightweight fetch
DEFAULT_TIMEOUT = 12
DEFAULT_USER_AGENT = "Mozilla/5.0 (compatible; PU-Observatory/1.0; +https://htcglobal.asia)"


def fetch_page(url: str, timeout: int = DEFAULT_TIMEOUT, user_agent: str = DEFAULT_USER_AGENT) -> Tuple[Optional[str], Optional[str]]:
    """
    Lightweight HTTP GET. No Playwright/Selenium. Respect redirects.
    Returns (html_string, None) on success or (None, error_message) on failure.
    """
    if not url or not url.strip().startswith(("http://", "https://")):
        return None, "invalid_url"
    url = url.strip()
    try:
        req = Request(url, headers={"User-Agent": user_agent})
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


def _extract_ld_json_blocks(html: str) -> List[str]:
    """Extract raw string content of every <script type="application/ld+json"> block."""
    if not html:
        return []
    # Match script tags with type application/ld+json (allow whitespace and single/double quotes)
    pattern = re.compile(
        r'<script[^>]*type\s*=\s*["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        re.DOTALL | re.IGNORECASE,
    )
    blocks = []
    for m in pattern.finditer(html):
        raw = (m.group(1) or "").strip()
        if raw:
            blocks.append(raw)
    return blocks


def _parse_json_blocks(blocks: List[str]) -> List[Dict[str, Any]]:
    """Parse each block as JSON; if it's an array, flatten to list of objects. Return flat list of dicts."""
    objects: List[Dict[str, Any]] = []
    for raw in blocks:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    objects.append(item)
        elif isinstance(data, dict):
            objects.append(data)
    return objects


def _get_types(obj: Dict[str, Any]) -> List[str]:
    """Return @type as list of strings (single value or @graph item types)."""
    t = obj.get("@type")
    if t is None:
        return []
    if isinstance(t, str):
        return [t]
    if isinstance(t, list):
        return [x for x in t if isinstance(x, str)]
    return []


def _text_richness(obj: Dict[str, Any]) -> int:
    """Heuristic: prefer articleBody, then description. Return total char count of main text fields."""
    total = 0
    for key in ("articleBody", "description", "headline", "name"):
        v = obj.get(key)
        if isinstance(v, str):
            total += len(v)
        elif isinstance(v, list):
            for item in v:
                if isinstance(item, str):
                    total += len(item)
    return total


def _select_content_object(objects: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Prefer objects whose @type contains one of NewsArticle, Article, Report, BlogPosting.
    If multiple matches, select the one with richest text (articleBody first, then description).
    """
    candidates: List[tuple[int, Dict[str, Any]]] = []
    for obj in objects:
        types = _get_types(obj)
        if not any(t in CONTENT_TYPES for t in types):
            continue
        richness = _text_richness(obj)
        candidates.append((richness, obj))
    if not candidates:
        return None
    candidates.sort(key=lambda x: -x[0])
    return candidates[0][1]


def _str_or_join(value: Any) -> str:
    """If value is list of strings, join with space; else str(value) if string."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        parts = [x.strip() for x in value if isinstance(x, str) and x.strip()]
        return " ".join(parts)
    return str(value).strip() if value else ""


def build_enriched_text(obj: Dict[str, Any]) -> str:
    """
    Concatenate headline, description, articleBody, about, keywords (skip nulls/empty).
    Order per protocol: headline + description + articleBody + about + keywords.
    """
    parts = []
    for key in ("headline", "description", "articleBody", "about", "keywords"):
        v = obj.get(key)
        s = _str_or_join(v)
        if s:
            parts.append(s)
    return " ".join(parts)


def get_all_jsonld_types(objects: List[Dict[str, Any]]) -> List[str]:
    """Collect all @type values from parsed objects for metadata."""
    types: List[str] = []
    seen = set()
    for obj in objects:
        for t in _get_types(obj):
            if t and t not in seen:
                seen.add(t)
                types.append(t)
    return types


def _extract_og_meta(html: str) -> str:
    """
    Extract OpenGraph/meta description fallback:
    - og:title
    - og:description
    - meta[name=description]
    Concatenate in that order (skip empties).
    """
    if not html:
        return ""

    parts: List[str] = []

    # Helper to extract meta content by attribute match
    def _meta_content(pattern: str) -> List[str]:
        out: List[str] = []
        for m in re.finditer(pattern, html, re.IGNORECASE | re.DOTALL):
            content = (m.group(1) or "").strip()
            if content:
                out.append(content)
        return out

    # og:title and og:description
    og_title_pat = r'<meta[^>]+property=["\']og:title["\'][^>]*content=["\'](.*?)["\']'
    og_desc_pat = r'<meta[^>]+property=["\']og:description["\'][^>]*content=["\'](.*?)["\']'
    meta_desc_pat = r'<meta[^>]+name=["\']description["\'][^>]*content=["\'](.*?)["\']'

    for txt in _meta_content(og_title_pat):
        parts.append(txt)
    for txt in _meta_content(og_desc_pat):
        parts.append(txt)
    for txt in _meta_content(meta_desc_pat):
        parts.append(txt)

    return " ".join(parts)


def enrich_candidate(url: str, timeout: int = DEFAULT_TIMEOUT) -> Dict[str, Any]:
    """
    For a candidate URL: fetch page, parse all JSON-LD blocks, select best content object,
    build enriched_text. Return enrichment result dict for evidence engine.

    Returns:
        enrichment_source: 'jsonld+meta'
        jsonld_found: bool
        jsonld_types_found: list of @type strings (or empty)
        jsonld_found_but_empty: bool
        enriched_text: str (may be empty)
        enriched_text_length: int
        enrichment_success: bool (True if we got enough to use for gating)
        enrichment_error: str or None
    """
    result: Dict[str, Any] = {
        "enrichment_source": "jsonld+meta",
        "jsonld_found": False,
        "jsonld_types_found": [],
        "jsonld_found_but_empty": False,
        "enriched_text": "",
        "enriched_text_length": 0,
        "enrichment_success": False,
        "enrichment_error": None,
    }
    html, err = fetch_page(url, timeout=timeout)
    if err:
        result["enrichment_error"] = err
        return result

    # JSON-LD part
    blocks = _extract_ld_json_blocks(html)
    jsonld_text = ""
    if blocks:
        objects = _parse_json_blocks(blocks)
        result["jsonld_found"] = len(objects) > 0
        result["jsonld_types_found"] = get_all_jsonld_types(objects)
        content_obj = _select_content_object(objects)
        if content_obj:
            jsonld_text = build_enriched_text(content_obj) or ""
        if result["jsonld_found"] and not jsonld_text.strip():
            result["jsonld_found_but_empty"] = True

    # OpenGraph/meta fallback (always, even if JSON-LD exists)
    og_meta_text = _extract_og_meta(html)

    # Final enriched_text: JSON-LD first, then meta/OG
    parts: List[str] = []
    if jsonld_text:
        parts.append(jsonld_text.strip())
    if og_meta_text:
        parts.append(og_meta_text.strip())

    enriched_text = " ".join(parts).strip()
    result["enriched_text"] = enriched_text
    result["enriched_text_length"] = len(enriched_text)
    result["enrichment_success"] = result["enriched_text_length"] >= 200
    return result
