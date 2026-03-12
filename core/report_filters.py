"""
Shared filtering for the report pipeline.
Used by Evidence Engine (filter before persist) so Writer and Pipeline do minimal filtering.
"""

import re
from typing import Optional

from core.taxonomy import REGION_KEYWORDS, PU_RELEVANCE_KEYWORDS

# Patterns that indicate title/snippet is search-result preamble, not actual news
# (Often the first "result" from search is meta-wording; we filter these in evidence engine.)
META_SNIPPET_PATTERNS = [
    r"^Here are (several |the most )?(relevant and )?factual",
    r"^Here are the most relevant",
    r"^Here are (some |a few )?(relevant )?(search )?results",
    r"^Based on (your |the )?query",
    r"^The following (articles?|links?|results?)",
    r"^Search results (for |related to )",
    r"^Below are (the )?(relevant )?",
    r"^These are (the )?relevant",
    r"^Summary of (the )?search",
    r"^Results from (your )?search",
    r"search results (for the query |related to )",
    r"presented as titles?",
    r"including (article|titles?)",
    r"each with the title and a brief snippet",
    r"short snippets?,? and (their )?source URLs",
    r"in other words,.*?used in",
    r"^I (found|retrieved) (the following|these)",
    r"^Below (is|are) (the )?(search )?result",
]


def is_meta_snippet(text: str) -> bool:
    """True if text looks like search-result meta/intro, not a real headline or summary."""
    if not text or len(text.strip()) < 20:
        return False
    t = text.strip()
    for pat in META_SNIPPET_PATTERNS:
        if re.search(pat, t, re.IGNORECASE):
            return True
    return False


def passes_region_relevance(title: str, snippet: str, region: str, body: Optional[str] = None) -> bool:
    """
    True if the content contains at least one keyword for the given region.
    Region is meant to qualify the item and should be present somewhere in the full item text.
    title, snippet: from RSS/search (always available). body: full article text when fetched (optional).
    When region has no mapping, we require the region label itself (case-insensitive).
    """
    if not region:
        return True
    keywords = REGION_KEYWORDS.get(region, [region])
    text = ((title or "") + " " + (snippet or "") + " " + (body or "")).strip()
    if not text:
        return False
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in keywords)


def passes_pu_relevance(title: str, snippet: str, body: Optional[str] = None) -> bool:
    """
    True if the content contains at least one PU-specific keyword (polyurethane, MDI, TDI,
    polyol, foam, TPU, etc.). title, snippet: from RSS/search; body: full article text when fetched (optional).
    """
    text = ((title or "") + " " + (snippet or "") + " " + (body or "")).strip()
    if not text:
        return False
    text_lower = text.lower()
    text_padded = " " + text_lower + " "
    for kw in PU_RELEVANCE_KEYWORDS:
        k = kw.strip().lower()
        if not k:
            continue
        if kw.startswith(" ") or kw.endswith(" "):
            if (" " + k + " ") in text_padded:
                return True
        else:
            if k in text_lower:
                return True
    return False
