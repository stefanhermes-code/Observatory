"""
V2 Build Spec Phase 2: Cluster extracted_signals by (company_name, signal_type, region, segment).
One row per cluster in signal_clusters; aggregate numeric_value when same unit.
"""

import hashlib
from collections import defaultdict
from typing import List, Dict, Any


def _cluster_key(company_name: str, signal_type: str, region: str, segment: str) -> str:
    """Stable key for grouping. Normalize empty to empty string."""
    c = (company_name or "").strip()
    t = (signal_type or "other").strip()
    r = (region or "").strip()
    s = (segment or "unknown").strip()
    raw = f"{c}|{t}|{r}|{s}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def _aggregate_numeric(signals: List[Dict]) -> tuple:
    """
    If all signals in group have same numeric_unit, sum numeric_value; else return (None, None).
    Returns (aggregated_value, unit or None).
    """
    units = set()
    total = 0
    count = 0
    for s in signals:
        val = s.get("numeric_value")
        unit = (s.get("numeric_unit") or "").strip() or None
        if val is not None:
            try:
                total += float(val)
                count += 1
                if unit:
                    units.add(unit)
            except (TypeError, ValueError):
                pass
    if count == 0:
        return None, None
    if len(units) <= 1:
        return total, (units.pop() if units else None)
    return None, None


def _structural_weight(signals: List[Dict]) -> float:
    """Proportion of signals with time_horizon = 'structural' (0.0 to 1.0)."""
    if not signals:
        return 0.0
    structural = sum(1 for s in signals if (s.get("time_horizon") or "").strip().lower() == "structural")
    return structural / len(signals)


def run_signal_clustering_v2(run_id: str) -> Dict[str, Any]:
    """
    Load extracted_signals for run_id, group by (company_name, signal_type, region, segment),
    aggregate numeric_value when same unit, write signal_clusters.

    Returns:
        {"clusters_created": N, "signals_grouped": M}
    """
    from core.generator_db import get_extracted_signals_for_run, insert_signal_clusters

    signals = get_extracted_signals_for_run(run_id)
    if not signals:
        return {"clusters_created": 0, "signals_grouped": 0}

    groups: Dict[str, List[Dict]] = defaultdict(list)
    for s in signals:
        key = _cluster_key(
            s.get("company_name"),
            s.get("signal_type"),
            s.get("region"),
            s.get("segment"),
        )
        groups[key].append(s)

    clusters = []
    for key, group in groups.items():
        if not group:
            continue
        first = group[0]
        agg_val, agg_unit = _aggregate_numeric(group)
        structural_weight = _structural_weight(group)
        clusters.append({
            "cluster_key": key,
            "signal_type": first.get("signal_type", "other"),
            "region": first.get("region"),
            "segment": first.get("segment", "unknown"),
            "aggregated_numeric_value": agg_val,
            "aggregated_numeric_unit": agg_unit,
            "cluster_size": len(group),
            "structural_weight": round(structural_weight, 4),
            "classification": None,
        })

    inserted = insert_signal_clusters(run_id, clusters)
    return {
        "clusters_created": inserted,
        "signals_grouped": len(signals),
    }
