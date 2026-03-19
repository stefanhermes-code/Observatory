from __future__ import annotations

from typing import Any, Dict, List, Tuple


def filter_candidates_by_spec(
    candidates: List[Dict[str, Any]],
    spec: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Apply customer specification filter to raw candidates BEFORE downstream processing.

    Strict behavior when constrained:
      - If spec.regions is empty: allow all regions.
      - If spec.regions is non-empty: require candidate.region in spec.regions.
      - Same pattern for spec.categories (against candidate.category) and
        spec.value_chain_links (against candidate.value_chain_link).

    Unset metadata does NOT count as a match when the customer has constrained a
    dimension. This matches the live alignment plan requirement that default
    behavior is strict when a dimension is constrained.
    """
    regions = spec.get("regions") or []
    categories = spec.get("categories") or []
    # Ultra-relaxed: value_chain_link is optional and must not influence filtering outcome.
    value_chain_links = spec.get("value_chain_links") or []

    if not regions and not categories and not value_chain_links:
        return list(candidates)

    filtered: List[Dict[str, Any]] = []
    for c in candidates:
        region = (c.get("region") or "").strip()
        category = (c.get("category") or "").strip()
        vcl = (c.get("value_chain_link") or "").strip()

        ok_region = (not regions) or (region in regions)
        ok_category = (not categories) or (category in categories)
        # Ignore vcl completely for Run 9 philosophy.
        ok_vcl = True

        # Ultra-relaxed: missing category should not be rejected.
        if ok_region and (ok_category or not category) and ok_vcl:
            filtered.append(c)
    return filtered


def filter_candidates_by_spec_with_stats(
    candidates: List[Dict[str, Any]],
    spec: Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """
    Same as filter_candidates_by_spec but also returns drop counts for audit.
    Returns (filtered_list, {"dropped_total", "failed_region_filter", "failed_value_chain_filter", "no_mapped_category"}).
    """
    regions = spec.get("regions") or []
    categories = spec.get("categories") or []
    # Ultra-relaxed: value_chain_link is optional and must not influence filtering outcome.
    value_chain_links = spec.get("value_chain_links") or []

    stats: Dict[str, int] = {"dropped_total": 0, "failed_region_filter": 0, "failed_value_chain_filter": 0, "no_mapped_category": 0}

    if not regions and not categories and not value_chain_links:
        return list(candidates), stats

    filtered: List[Dict[str, Any]] = []
    for c in candidates:
        region = (c.get("region") or "").strip()
        category = (c.get("category") or "").strip()
        vcl = (c.get("value_chain_link") or "").strip()

        ok_region = (not regions) or (region in regions)
        ok_category = (not categories) or (category in categories)
        # Ignore vcl completely for Run 9 philosophy.
        ok_vcl = True

        # Allow missing category through when categories are constrained.
        ok_category_relaxed = ok_category or (categories and not category)

        if ok_region and ok_category_relaxed and ok_vcl:
            filtered.append(c)
        else:
            stats["dropped_total"] += 1
            if not ok_region:
                stats["failed_region_filter"] += 1
            # Ultra-relaxed: missing category is not a drop reason.
            if not ok_category_relaxed:
                stats["no_mapped_category"] += 1
            # Ultra-relaxed: value_chain filtering disabled.
    return filtered, stats


def filter_signals_by_spec(
    signals: List[Dict[str, Any]],
    query_plan_map: Dict[str, Dict[str, str]],
    spec: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Apply strict customer specification filter to master signals using query intent map.
    Each signal has query_id; metadata (region, configurator_category, value_chain_link)
    is looked up from query_plan_map. Unset metadata does NOT pass when the spec
    constrains that dimension (same rule as filter_candidates_by_spec).
    """
    regions = spec.get("regions") or []
    categories = spec.get("categories") or []
    # Ultra-relaxed: value_chain_link is optional and must not influence filtering outcome.
    value_chain_links = spec.get("value_chain_links") or []

    if not regions and not categories and not value_chain_links:
        return list(signals)

    filtered: List[Dict[str, Any]] = []
    for s in signals:
        qid = (s.get("query_id") or "").strip()
        meta = query_plan_map.get(qid) or {}
        region = (meta.get("region") or "").strip()
        config_cat = (meta.get("configurator_category") or "").strip()
        vcl = (meta.get("value_chain_link") or "").strip()

        ok_region = (not regions) or (region in regions)
        ok_category = (not categories) or (config_cat in categories)
        # Ignore vcl completely for Run 9 philosophy.
        ok_vcl = True

        # Ultra-relaxed: missing category should not be rejected.
        if ok_region and (ok_category or not config_cat) and ok_vcl:
            filtered.append(s)
    return filtered


def filter_signals_by_spec_with_stats(
    signals: List[Dict[str, Any]],
    query_plan_map: Dict[str, Dict[str, str]],
    spec: Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """
    Same as filter_signals_by_spec but also returns drop counts for audit.
    Returns (filtered_list, {"dropped_total", "failed_region_filter", "failed_value_chain_filter", "no_mapped_category"}).
    When query_id is missing or not in query_plan_map, uses signal's own region, configurator_category, value_chain_link.
    """
    regions = spec.get("regions") or []
    categories = spec.get("categories") or []
    # Ultra-relaxed: value_chain_link is optional and must not influence filtering outcome.
    value_chain_links = spec.get("value_chain_links") or []

    stats: Dict[str, int] = {"dropped_total": 0, "failed_region_filter": 0, "failed_value_chain_filter": 0, "no_mapped_category": 0}

    if not regions and not categories and not value_chain_links:
        return list(signals), stats

    filtered: List[Dict[str, Any]] = []
    for s in signals:
        qid = (s.get("query_id") or "").strip()
        meta = query_plan_map.get(qid) if qid else None
        if meta:
            region = (meta.get("region") or "").strip()
            config_cat = (meta.get("configurator_category") or "").strip()
            vcl = (meta.get("value_chain_link") or "").strip()
        else:
            # Fallback: use signal's own metadata (e.g. candidate_articles have region, category, value_chain_link)
            region = (s.get("region") or "").strip()
            config_cat = (s.get("configurator_category") or s.get("category") or "").strip()
        vcl = (s.get("value_chain_link") or "").strip()

        ok_region = (not regions) or (region in regions)
        ok_category = (not categories) or (config_cat in categories)
        # Ignore vcl completely for Run 9 philosophy.
        ok_vcl = True

        # Allow missing category through when categories are constrained.
        ok_category_relaxed = ok_category or (categories and not config_cat)

        if ok_region and ok_category_relaxed and ok_vcl:
            filtered.append(s)
        else:
            stats["dropped_total"] += 1
            if not ok_region:
                stats["failed_region_filter"] += 1
            # Ultra-relaxed: missing category is not a drop reason.
            if not ok_category_relaxed:
                stats["no_mapped_category"] += 1
            # Ultra-relaxed: value_chain filtering disabled.
    return filtered, stats

