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


def _merge_usage(a: Dict, b: Dict) -> Dict:
    """Merge two usage dicts (input_tokens, output_tokens, total_tokens); model from second."""
    out = {}
    for key in ("input_tokens", "output_tokens", "total_tokens"):
        out[key] = int((a.get(key) or 0)) + int((b.get(key) or 0))
    out["model"] = b.get("model") or a.get("model") or "gpt-4o"
    return out


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
    run_id: Optional[str] = None,
    synthesis_scope: str = "GLOBAL",
    synthesis_region_macro: Optional[str] = None,
    synthesis_segment: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build report content from candidate_articles only. Every URL is from the candidates list.
    Structure: Categories (##) → Regions (###) → Value chain links (####) → items.
    The "value_chain" category is dropped from top-level; value_chain_links are used as sub-substructure only.
    Phase 5: Market Intelligence Report (5-section synthesis from structured signals + baseline) replaces Executive Summary.

    Args:
        spec: newsletter specification (newsletter_name, categories, regions, value_chain_links)
        candidates: list of candidate_articles rows (url, title, snippet, source_name, published_at)
        min_evidence: minimum candidates to produce a full report
        lookback_date, reference_date: app-defined date range; if both set, filter by published_at
        run_id: required for Phase 5 synthesis (clusters + baseline). If None, no synthesis is run.
        synthesis_scope: GLOBAL | REGION | REGION_SEGMENT
        synthesis_region_macro: for REGION / REGION_SEGMENT
        synthesis_segment: for REGION_SEGMENT

    Returns:
        {"content": str, "coverage_low": bool, "exec_summary_usage": dict?}
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

    # Phase 5: Market Intelligence Synthesis (structured signals + baseline). Replaces Executive Summary.
    # Phase 6: Adversarial critique after synthesis; optional one-time regeneration if requires_revision.
    exec_summary_usage = None
    synthesis_text = None
    final_quality_score = None
    critique_issues_stored = None
    regeneration_flag = False
    if run_id:
        try:
            from core.market_intelligence_synthesis import run_market_intelligence_synthesis, SCOPE_GLOBAL, SCOPE_REGION, SCOPE_REGION_SEGMENT
            from core.adversarial_critique import run_critique
            scope = synthesis_scope if synthesis_scope in (SCOPE_GLOBAL, SCOPE_REGION, SCOPE_REGION_SEGMENT) else SCOPE_GLOBAL
            synthesis_text, exec_summary_usage = run_market_intelligence_synthesis(
                run_id=run_id,
                scope=scope,
                region_macro=synthesis_region_macro,
                segment=synthesis_segment,
            )
            if synthesis_text:
                critique_result, critique_usage = run_critique(synthesis_text)
                if critique_usage and exec_summary_usage:
                    exec_summary_usage = _merge_usage(exec_summary_usage, critique_usage)
                if critique_result:
                    if critique_result.get("requires_revision"):
                        issues = critique_result.get("issues") or []
                        synthesis_text_2, usage_2 = run_market_intelligence_synthesis(
                            run_id=run_id,
                            scope=scope,
                            region_macro=synthesis_region_macro,
                            segment=synthesis_segment,
                            critique_issues=issues,
                        )
                        if usage_2 and exec_summary_usage:
                            exec_summary_usage = _merge_usage(exec_summary_usage, usage_2)
                        if synthesis_text_2:
                            synthesis_text = synthesis_text_2
                            regeneration_flag = True
                            critique_result_2, critique_usage_2 = run_critique(synthesis_text_2)
                            if critique_usage_2 and exec_summary_usage:
                                exec_summary_usage = _merge_usage(exec_summary_usage, critique_usage_2)
                            if critique_result_2:
                                final_quality_score = critique_result_2.get("quality_score")
                                critique_issues_stored = critique_result_2.get("issues")
                        else:
                            final_quality_score = critique_result.get("quality_score")
                            critique_issues_stored = critique_result.get("issues")
                    else:
                        final_quality_score = critique_result.get("quality_score")
                        critique_issues_stored = critique_result.get("issues")
        except Exception:
            pass
    if synthesis_text:
        lines.extend(["", "## Market Intelligence Report", "", synthesis_text, ""])
    content = "\n".join(lines)
    out = {"content": content, "coverage_low": False}
    if exec_summary_usage is not None:
        out["exec_summary_usage"] = exec_summary_usage
    if final_quality_score is not None:
        out["final_quality_score"] = final_quality_score
    if critique_issues_stored is not None:
        out["critique_issues"] = critique_issues_stored
    out["regeneration_flag"] = regeneration_flag
    return out
