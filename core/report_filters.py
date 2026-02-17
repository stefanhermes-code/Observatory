"""
Shared filtering for the report pipeline.
Used by Evidence Engine (filter before persist) so Writer and Pipeline do minimal filtering.
"""

import re

from core.taxonomy import REGION_KEYWORDS

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


def passes_region_relevance(title: str, snippet: str, region: str) -> bool:
    """
    True if title or snippet contains at least one keyword for the given region.
    Used to drop candidates that were returned by a region query but are about other regions
    (e.g. China article in a SEA-only report). When region has no mapping, we require the
    region label itself to appear (case-insensitive).
    """
    if not region:
        return True
    keywords = REGION_KEYWORDS.get(region, [region])
    text = ((title or "") + " " + (snippet or "")).strip()
    if not text:
        return False
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in keywords)
