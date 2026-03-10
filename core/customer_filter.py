from __future__ import annotations

from typing import Any, Dict, List


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
        ok_vcl = (not value_chain_links) or (vcl in value_chain_links)

        if ok_region and ok_category and ok_vcl:
            filtered.append(c)
    return filtered


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
        ok_vcl = (not value_chain_links) or (vcl in value_chain_links)

        if ok_region and ok_category and ok_vcl:
            filtered.append(s)
    return filtered

