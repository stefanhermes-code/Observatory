"""
V2-LLM-02: Bounded report writer.
Uses only candidate_articles for this run; every URL in the report must be from that set.
If evidence count < min_evidence, returns a coverage note and stops.
"""

from typing import List, Dict, Any
from datetime import datetime

# Minimum number of candidate articles to generate a full report
DEFAULT_MIN_EVIDENCE = 3


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
) -> Dict[str, Any]:
    """
    Build report content from candidate_articles only. Every URL is from the candidates list.
    If len(candidates) < min_evidence, returns coverage-low message and stops.

    Args:
        spec: newsletter specification (newsletter_name, categories, regions, etc.)
        candidates: list of candidate_articles rows (url, title, snippet, source_name, published_at)
        min_evidence: minimum candidates to produce a full report

    Returns:
        {"content": str, "coverage_low": bool}
        - content: markdown report body, or "## Coverage low\\n\\nInsufficient evidence..."
        - coverage_low: True if report was truncated due to low evidence
    """
    from core.taxonomy import PU_CATEGORIES

    newsletter_name = spec.get("newsletter_name", "Newsletter")
    selected_category_ids = spec.get("categories") or []
    category_map = {cat["id"]: cat["name"] for cat in PU_CATEGORIES}

    if len(candidates) < min_evidence:
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
        # Items for this section: every (i + k*len(section_titles))-th candidate
        section_items = [
            c for j, c in enumerate(candidates)
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
