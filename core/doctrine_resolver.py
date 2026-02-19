"""
V2 Build Spec Phase 4: Deterministic Doctrine Resolver.
Input: cluster (with signal_type, numeric value/unit, time_horizon info) + llm_classification.
Output: final_classification, override_source, materiality_flag, override_reason.
Does not modify capacity sign (decreases remain negative).
"""

from typing import Dict, Any, Optional, List

VALID_FINAL = {"noise", "tactical", "cyclical", "structural", "transformational"}

# Rule 1 thresholds
CAPACITY_TPA_ABS_THRESHOLD = 20000
CAPACITY_PERCENT_ABS_THRESHOLD = 5


def resolve(
    cluster: Dict[str, Any],
    llm_classification: Optional[str],
    time_horizons: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Deterministic doctrine resolution. cluster must have signal_type, aggregated_numeric_value,
    aggregated_numeric_unit, structural_weight. classification column = llm_classification.
    Returns dict: final_classification, override_source, materiality_flag, override_reason.
    """
    llm = (llm_classification or "").strip().lower()
    if llm not in VALID_FINAL:
        llm = "noise"
    signal_type = (cluster.get("signal_type") or "other").strip().lower()
    num_val = cluster.get("aggregated_numeric_value")
    try:
        num_val = float(num_val) if num_val is not None else None
    except (TypeError, ValueError):
        num_val = None
    unit = (cluster.get("aggregated_numeric_unit") or "").strip().lower() or None
    structural_weight = cluster.get("structural_weight")
    try:
        structural_weight = float(structural_weight) if structural_weight is not None else 0.0
    except (TypeError, ValueError):
        structural_weight = 0.0
    trend_multi_year = cluster.get("trend_multi_year") in (True, "true", 1)
    time_horizons = time_horizons or []
    th_normalized = [t.strip().lower() for t in time_horizons if t]
    all_short_term = th_normalized and all(t == "short_term" for t in th_normalized)

    # Rule 1 – Capacity hard structural trigger
    if signal_type == "capacity":
        if unit == "tpa" and num_val is not None:
            if num_val >= CAPACITY_TPA_ABS_THRESHOLD or num_val <= -CAPACITY_TPA_ABS_THRESHOLD:
                return {
                    "final_classification": "structural",
                    "override_source": "doctrine",
                    "materiality_flag": True,
                    "override_reason": "capacity TPA threshold",
                }
        if unit == "percent" and num_val is not None:
            if num_val >= CAPACITY_PERCENT_ABS_THRESHOLD or num_val <= -CAPACITY_PERCENT_ABS_THRESHOLD:
                return {
                    "final_classification": "structural",
                    "override_source": "doctrine",
                    "materiality_flag": True,
                    "override_reason": "capacity percent threshold",
                }
        # Rule 2 – Capacity below threshold
        return {
            "final_classification": llm,
            "override_source": "llm",
            "materiality_flag": False,
            "override_reason": None,
        }

    # Rule 3 – Demand
    if signal_type == "demand":
        if trend_multi_year and num_val is not None and abs(num_val) >= 5:
            return {
                "final_classification": "structural",
                "override_source": "doctrine",
                "materiality_flag": True,
                "override_reason": "demand multi-year material",
            }
        return {
            "final_classification": "cyclical",
            "override_source": "doctrine",
            "materiality_flag": False,
            "override_reason": "demand YoY/MoM",
        }

    # Rule 4 – Regulation
    if signal_type == "regulation":
        return {
            "final_classification": "structural",
            "override_source": "doctrine",
            "materiality_flag": True,
            "override_reason": "regulation default",
        }

    # Rule 5 – Operational / tactical
    if signal_type == "operational" and (all_short_term or structural_weight == 0):
        return {
            "final_classification": "tactical",
            "override_source": "doctrine",
            "materiality_flag": False,
            "override_reason": "operational short_term",
        }

    # Rule 6 – Investment (no threshold)
    if signal_type == "investment":
        return {
            "final_classification": llm,
            "override_source": "llm",
            "materiality_flag": False,
            "override_reason": None,
        }

    # Default: keep LLM
    return {
        "final_classification": llm,
        "override_source": "llm",
        "materiality_flag": False,
        "override_reason": None,
    }


def run_doctrine_resolver_v2(run_id: str) -> Dict[str, Any]:
    """
    Load clusters (with classification = llm), resolve doctrine for each, persist final_classification etc.
    Returns: {"resolved": N, "clusters_processed": M, "failed": K}
    """
    from core.generator_db import (
        get_signal_clusters_for_run,
        get_extracted_signals_for_run,
        update_signal_cluster_doctrine,
    )
    from core.signal_clustering_v2 import _cluster_key

    clusters = get_signal_clusters_for_run(run_id)
    if not clusters:
        return {"resolved": 0, "clusters_processed": 0, "failed": 0}

    signals = get_extracted_signals_for_run(run_id)
    time_horizons_by_key: Dict[str, List[str]] = {}
    for s in signals:
        key = _cluster_key(
            s.get("company_name"),
            s.get("signal_type"),
            s.get("region"),
            s.get("segment"),
        )
        th = (s.get("time_horizon") or "unknown").strip().lower()
        time_horizons_by_key.setdefault(key, []).append(th)

    resolved = 0
    failed = 0
    for c in clusters:
        cluster_id = c.get("id")
        if not cluster_id:
            failed += 1
            continue
        llm = c.get("classification")
        time_horizons = time_horizons_by_key.get(c.get("cluster_key"), [])
        out = resolve(c, llm, time_horizons)
        if update_signal_cluster_doctrine(
            cluster_id,
            final_classification=out["final_classification"],
            override_source=out["override_source"],
            materiality_flag=out["materiality_flag"],
            override_reason=out.get("override_reason"),
        ):
            resolved += 1
        else:
            failed += 1
    return {
        "resolved": resolved,
        "clusters_processed": len(clusters),
        "failed": failed,
    }
