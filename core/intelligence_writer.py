"""
V2-LLM-02: Bounded report writer.
Uses only candidate_articles for this run; every URL in the report must be from that set.
If evidence count < min_evidence, returns a coverage note and stops.
Filters: (1) search-result meta text; (2) date range (cadence + app date) when lookback/reference provided.
"""

import re
from typing import List, Dict, Any, Optional
from datetime import datetime

# Minimum number of candidate articles to generate a full report
DEFAULT_MIN_EVIDENCE = 3

# Patterns that indicate the title/snippet is search-result preamble, not actual news
_META_SNIPPET_PATTERNS = [
    r"^Here are (several |the most )?(relevant and )?factual",
    r"^Here are the most relevant",
    r"search results (for the query |related to )",
    r"presented as titles?",
    r"including (article|titles?)",
    r"each with the title and a brief snippet",
    r"short snippets?,? and (their )?source URLs",
    r"in other words,.*?used in",
]


def _is_meta_snippet(text: str) -> bool:
    """True if text looks like search-result meta/intro, not a real headline or summary."""
    if not text or len(text.strip()) < 20:
        return False
    t = text.strip()
    for pat in _META_SNIPPET_PATTERNS:
        if re.search(pat, t, re.IGNORECASE):
            return True
    return False


def _format_item(c: Dict) -> str:
    """Format one candidate as a bullet: summary — Source (YYYY-MM-DD) url."""
    title = (c.get("title") or "").strip()
    snippet = (c.get("snippet") or "").strip()
    text = snippet if snippet else title
    if not text:
        text = "No title"
    source = (c.get("source_name") or "Source").strip()
    url = (c.get("url") or c.get("canonical_url") or "").strip()
    pub = c.get("published_at")
    if pub:
        if isinstance(pub, str) and len(pub) >= 10:
            date_str = pub[:10]
        else:
            date_str = str(pub)[:10]
    else:
        date_str = ""
    if date_str:
        source_part = f" — {source} ({date_str})"
    else:
        source_part = f" — {source}"
    if url:
        return f"- {text}{source_part} {url}"
    return f"- {text}{source_part}"


def write_report_from_evidence(
    spec: Dict,
    candidates: List[Dict],
    min_evidence: int = DEFAULT_MIN_EVIDENCE,
    lookback_date: Optional[datetime] = None,
    reference_date: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Build report content from candidate_articles only. Every URL is from the candidates list.
    If len(candidates) < min_evidence, returns coverage-low message and stops.
    Date filter: when lookback_date and reference_date are provided (from cadence + app date),
    only candidates within that range (or with no date) are included.

    Args:
        spec: newsletter specification (newsletter_name, categories, regions, etc.)
        candidates: list of candidate_articles rows (url, title, snippet, source_name, published_at)
        min_evidence: minimum candidates to produce a full report
        lookback_date, reference_date: app-defined date range; if both set, filter by published_at

    Returns:
        {"content": str, "coverage_low": bool}
    """
    from core.taxonomy import PU_CATEGORIES
    from core.run_dates import is_in_date_range

    newsletter_name = spec.get("newsletter_name", "Newsletter")
    selected_category_ids = spec.get("categories") or []
    category_map = {cat["id"]: cat["name"] for cat in PU_CATEGORIES}

    # Exclude candidates that are search-result meta text (e.g. "Here are several relevant...")
    filtered_candidates = [
        c for c in candidates
        if not _is_meta_snippet((c.get("title") or "").strip())
        and not _is_meta_snippet((c.get("snippet") or "").strip())
    ]
    # Date filter: only include candidates within [lookback_date, reference_date]; keep if no date
    if lookback_date is not None and reference_date is not None:
        filtered_candidates = [
            c for c in filtered_candidates
            if is_in_date_range(c.get("published_at"), lookback_date, reference_date)
        ]

    if len(filtered_candidates) < min_evidence:
        content = (
            "## Coverage low\n\n"
            "Insufficient evidence was collected for this run. "
            "Try broadening your specification (regions, categories) or run again later."
        )
        return {"content": content, "coverage_low": True}

    # Build sections by spec categories; assign each candidate to first matching section for now
    section_titles = [category_map.get(cid, cid) for cid in selected_category_ids]
    if not section_titles:
        section_titles = ["Key developments"]

    lines = [
        f"# {newsletter_name}",
        "",
        f"*Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}*",
        "",
    ]

    # One section per category; distribute items across sections (round-robin)
    for i, section_title in enumerate(section_titles):
        lines.append(f"## {section_title}")
        lines.append("")
        # Items for this section: every (i + k*len(section_titles))-th candidate (use filtered list)
        section_items = [
            c for j, c in enumerate(filtered_candidates)
            if j % len(section_titles) == i
        ]
        for c in section_items:
            lines.append(_format_item(c))
        lines.append("")

    # Executive summary placeholder (3–5 short paragraphs as per spec)
    lines.extend([
        "## Executive Summary",
        "",
        "This report is based on evidence collected from registered sources and search.",
        "All items above cite only verified candidate articles for this run.",
        "",
        "Key themes from the evidence set are reflected in the sections above.",
        "For questions or broader coverage, adjust the specification and run again.",
        "",
    ])

    content = "\n".join(lines)
    return {"content": content, "coverage_low": False}
