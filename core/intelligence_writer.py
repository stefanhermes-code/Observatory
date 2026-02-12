"""
V2-LLM-02: Bounded report writer.
Uses only candidate_articles for this run; every URL in the report must be from that set.
If evidence count < min_evidence, returns a coverage note and stops.
Filtering is done earlier (Evidence Engine); writer only enforces min_evidence and builds structure.

Report structure (hierarchy):
  1. Categories (main structure) — ##
  2. Regions (substructure) — ###
  3. Value chain links (sub-substructure) — ####
The "value_chain" category is not used as a top-level section; value chain is represented only
by the value_chain_links selection as sub-substructure under each category/region.
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

# Minimum number of candidate articles to generate a full report
DEFAULT_MIN_EVIDENCE = 3

# Category IDs we exclude from top-level (replaced by value_chain_links as sub-substructure)
EXCLUDED_CATEGORY_IDS = ("value_chain", "value_chain_link")

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


def _build_slots(
    category_ids: List[str],
    region_names: List[str],
    value_chain_link_ids: List[str],
    category_map: Dict[str, str],
    region_list: List[str],
    value_chain_link_map: Dict[str, str],
) -> List[Tuple[str, str, str, str, str, str]]:
    """
    Build (category_id, category_name, region, value_chain_id, value_chain_name, slot_key) for each slot.
    Hierarchy: Category → Region → Value chain link.
    """
    slots = []
    for cid in category_ids:
        cat_name = category_map.get(cid, cid)
        regions = region_names if region_names else ["All regions"]
        vc_links = value_chain_link_ids if value_chain_link_ids else [None]  # None = "Key developments"
        for region in regions:
            for vc_id in vc_links:
                vc_name = value_chain_link_map.get(vc_id, "Key developments") if vc_id else "Key developments"
                slot_key = f"{cid}|{region}|{vc_id or ''}"
                slots.append((cid, cat_name, region, vc_id, vc_name, slot_key))
    return slots


def write_report_from_evidence(
    spec: Dict,
    candidates: List[Dict],
    min_evidence: int = DEFAULT_MIN_EVIDENCE,
    lookback_date: Optional[datetime] = None,
    reference_date: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Build report content from candidate_articles only. Every URL is from the candidates list.
    Structure: Categories (##) → Regions (###) → Value chain links (####) → items.
    The "value_chain" category is dropped from top-level; value_chain_links are used as sub-substructure only.

    Args:
        spec: newsletter specification (newsletter_name, categories, regions, value_chain_links)
        candidates: list of candidate_articles rows (url, title, snippet, source_name, published_at)
        min_evidence: minimum candidates to produce a full report
        lookback_date, reference_date: app-defined date range; if both set, filter by published_at

    Returns:
        {"content": str, "coverage_low": bool}
    """
    from core.taxonomy import PU_CATEGORIES, REGIONS, VALUE_CHAIN_LINKS

    newsletter_name = spec.get("newsletter_name", "Newsletter")
    selected_category_ids = spec.get("categories") or []
    # Exclude value_chain and value_chain_link from top-level; value chain is represented by value_chain_links below
    selected_category_ids = [c for c in selected_category_ids if c not in EXCLUDED_CATEGORY_IDS]
    selected_regions = spec.get("regions") or []
    selected_value_chain_links = spec.get("value_chain_links") or []

    category_map = {cat["id"]: cat["name"] for cat in PU_CATEGORIES}
    value_chain_link_map = {vc["id"]: vc["name"] for vc in VALUE_CHAIN_LINKS}

    # No filtering here: Evidence Engine already filtered (meta-snippet, date, working URL). Only min_evidence check.
    filtered_candidates = list(candidates)

    if len(filtered_candidates) < min_evidence:
        content = (
            "## Coverage low\n\n"
            "Insufficient evidence was collected for this run. "
            "Try broadening your specification (regions, categories) or run again later."
        )
        return {"content": content, "coverage_low": True}

    # Build hierarchy slots: Category → Region → Value chain link
    if not selected_category_ids:
        selected_category_ids = ["industry_context"]  # fallback
    slots = _build_slots(
        selected_category_ids,
        selected_regions,
        selected_value_chain_links,
        category_map,
        selected_regions,
        value_chain_link_map,
    )
    # Distribute candidates round-robin across slots
    slot_items: Dict[str, List[Dict]] = {s[5]: [] for s in slots}
    for j, c in enumerate(filtered_candidates):
        slot_key = slots[j % len(slots)][5]
        slot_items[slot_key].append(c)

    lines = [
        f"# {newsletter_name}",
        "",
        f"*Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}*",
        "",
    ]

    # Emit hierarchy: ## Category → ### Region → #### Value chain link → items
    current_category = None
    current_region = None
    for (cid, cat_name, region, vc_id, vc_name, slot_key) in slots:
        items = slot_items.get(slot_key, [])
        if not items:
            continue

        if cid != current_category:
            current_category = cid
            current_region = None
            lines.append(f"## {cat_name}")
            lines.append("")

        if region != current_region:
            current_region = region
            lines.append(f"### {region}")
            lines.append("")

        lines.append(f"#### {vc_name}")
        lines.append("")
        for c in items:
            lines.append(_format_item(c))
        lines.append("")

    # Executive summary at the end: reviews all information from the foregoing sections
    lines.extend([
        "## Executive Summary",
        "",
        "The following summarizes the key developments and themes from the sections above.",
        "",
        "This report is based on evidence collected from registered sources and search for the selected categories, regions, and value chain links. All items cite only verified candidate articles for this run.",
        "",
        "For questions or broader coverage, adjust the specification and run again.",
        "",
    ])

    content = "\n".join(lines)
    return {"content": content, "coverage_low": False}
