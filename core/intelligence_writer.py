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

# Only show "Coverage low" when zero items pass the scope filter; allow report with 1+ links
DEFAULT_MIN_EVIDENCE = 1

# Category IDs we exclude from top-level (replaced by value_chain_links as sub-substructure)
EXCLUDED_CATEGORY_IDS = ("value_chain", "value_chain_link")

def _sanitize_link_text(text: str) -> str:
    """Remove markdown artefacts (** etc.) from text used as link labels."""
    if not text or not isinstance(text, str):
        return text
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*+', '', text)
    text = text.strip()
    if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
        text = text[1:-1].strip()
    elif text.startswith('"'):
        text = text.lstrip('"').strip()
    return text


def _format_item(c: Dict) -> str:
    """Format one candidate as a bullet: title — Source (YYYY-MM-DD) url.

    IMPORTANT: The visible text must be the article TITLE, not the snippet,
    so the HTML report shows clean, headline-style links.
    """
    title = (c.get("title") or "").strip()
    snippet = (c.get("snippet") or "").strip()
    # Prefer title for link text; fall back to snippet only if there is no title.
    text = _sanitize_link_text(title or snippet or "No title")
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

    # Filter candidates to those matching the spec (category, region, value_chain_link).
    # All three are stored in the same format as the spec: category id, region name, value_chain_link id.
    filtered_candidates = []
    selected_vcl_set = set(selected_value_chain_links or [])
    for c in candidates:
        cat = (c.get("category") or "").strip()
        reg = (c.get("region") or "").strip()
        vcl = (c.get("value_chain_link") or "").strip()
        if cat not in selected_category_ids:
            continue
        if selected_regions and reg not in selected_regions:
            continue
        if selected_vcl_set and vcl not in selected_vcl_set:
            continue
        filtered_candidates.append(c)

    if len(filtered_candidates) < min_evidence:
        content = (
            "## Coverage low\n\n"
            "Insufficient evidence was collected for this run. "
            "Try broadening your specification (regions, categories) or run again later."
        )
        return {"content": content, "coverage_low": True}

    # Build hierarchy slots (Category → Region → Value chain link), but use them only
    # to *distribute* items. The VISIBLE structure in the report is:
    #   - Category (##) as the only section header level.
    # Regions and value chain links act as invisible sub-structure.
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
    # Assign each candidate to the slot matching its (category, region, value_chain_link)
    slot_items: Dict[str, List[Dict]] = {s[5]: [] for s in slots}
    for c in filtered_candidates:
        cat = (c.get("category") or "").strip()
        reg = (c.get("region") or "").strip()
        vcl = (c.get("value_chain_link") or "").strip() if selected_value_chain_links else ""
        slot_key = f"{cat}|{reg}|{vcl}"
        if slot_key not in slot_items:
            slot_key = f"{cat}|{reg}|"
        if slot_key in slot_items:
            slot_items[slot_key].append(c)

    # Flatten slots per category: for each category, gather all items across regions/value-chain links.
    category_items: Dict[str, List[Dict]] = {cid: [] for cid in selected_category_ids}
    for (cid, _cat_name, _region, _vc_id, _vc_name, slot_key) in slots:
        items = slot_items.get(slot_key, [])
        if items:
            category_items.setdefault(cid, []).extend(items)

    lines = [
        f"# {newsletter_name}",
        "",
        f"*Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}*",
        "",
    ]

    # Emit visible structure: ## Category only, with items listed underneath.
    for cid in selected_category_ids:
        items = category_items.get(cid) or []
        if not items:
            continue
        cat_name = category_map.get(cid, cid)
        lines.append(f"## {cat_name}")
        lines.append("")
        for c in items:
            lines.append(_format_item(c))
        lines.append("")

    # Dedicated LLM step: Executive Summary (core element of market intelligence; the other is signals).
    try:
        from core.openai_assistant import generate_executive_summary
    except ImportError:
        generate_executive_summary = None
    report_body = "\n".join(lines)
    scope_categories = [category_map.get(cid, cid) for cid in selected_category_ids]
    scope_regions = list(selected_regions) if selected_regions else []
    scope_vcl = [value_chain_link_map.get(vid, vid) for vid in selected_value_chain_links]
    exec_summary = None
    if generate_executive_summary:
        exec_summary = generate_executive_summary(
            report_body,
            newsletter_name,
            scope_categories=scope_categories,
            scope_regions=scope_regions,
            scope_value_chain_links=scope_vcl if selected_value_chain_links else None,
        )
    if exec_summary:
        lines.extend(["", "## Executive Summary", "", exec_summary, ""])
    content = "\n".join(lines)
    return {"content": content, "coverage_low": False}
