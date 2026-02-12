"""
Shared filtering for the report pipeline.
Used by Evidence Engine (filter before persist) so Writer and Pipeline do minimal filtering.
"""

import re

# Patterns that indicate title/snippet is search-result preamble, not actual news
META_SNIPPET_PATTERNS = [
    r"^Here are (several |the most )?(relevant and )?factual",
    r"^Here are the most relevant",
    r"search results (for the query |related to )",
    r"presented as titles?",
    r"including (article|titles?)",
    r"each with the title and a brief snippet",
    r"short snippets?,? and (their )?source URLs",
    r"in other words,.*?used in",
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
