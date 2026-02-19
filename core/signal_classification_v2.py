"""
V2 Build Spec Phase 3: Classify each signal_cluster by structural impact.
One gpt-4o-mini call per cluster; store result in signal_clusters.classification.
"""

import re
from collections import defaultdict
from typing import List, Dict, Any, Optional

from core.signal_clustering_v2 import _cluster_key

VALID_CLASSIFICATIONS = {"noise", "tactical", "cyclical", "structural", "transformational"}

CLASSIFICATION_SYSTEM = "You classify polyurethane industry signals by structural impact."

CLASSIFICATION_USER_TEMPLATE = """Given this cluster:

Signal Type: {signal_type} Segment: {segment} Region: {region} Cluster Size: {cluster_size} Aggregated Value: {aggregated_numeric_value} Time Horizons in Signals: {time_horizons}

Classify impact as one of:

- noise
- tactical
- cyclical
- structural
- transformational

Return only the classification label, nothing else."""


def _time_horizons_by_cluster_key(signals: List[Dict]) -> Dict[str, List[str]]:
    """Group extracted_signals by cluster_key, return list of time_horizon values per key."""
    groups: Dict[str, List[str]] = defaultdict(list)
    for s in signals:
        key = _cluster_key(
            s.get("company_name"),
            s.get("signal_type"),
            s.get("region"),
            s.get("segment"),
        )
        th = (s.get("time_horizon") or "unknown").strip().lower()
        groups[key].append(th)
    return dict(groups)


def _call_classification(
    signal_type: str,
    segment: str,
    region: str,
    cluster_size: int,
    aggregated_numeric_value: Optional[float],
    time_horizons: List[str],
) -> Optional[str]:
    """Single cluster classification call. Returns one of VALID_CLASSIFICATIONS or None."""
    try:
        import os
        from openai import OpenAI
        try:
            import streamlit as st
            api_key = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
        except Exception:
            api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return None
        client = OpenAI(api_key=api_key)
        time_horizons_str = ", ".join(time_horizons) if time_horizons else "unknown"
        agg_val = aggregated_numeric_value if aggregated_numeric_value is not None else "—"
        user_content = CLASSIFICATION_USER_TEMPLATE.format(
            signal_type=signal_type or "other",
            segment=segment or "unknown",
            region=region or "—",
            cluster_size=cluster_size,
            aggregated_numeric_value=agg_val,
            time_horizons=time_horizons_str,
        )
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": CLASSIFICATION_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            temperature=0.1,
            max_tokens=32,
        )
        if not resp.choices or not resp.choices[0].message or not resp.choices[0].message.content:
            return None
        label = resp.choices[0].message.content.strip().lower()
        label = re.sub(r"[^a-z_]", "", label)
        if label in VALID_CLASSIFICATIONS:
            return label
        if "tactical" in label or label == "tactical":
            return "tactical"
        if "cyclical" in label:
            return "cyclical"
        if "structural" in label:
            return "structural"
        if "transformational" in label:
            return "transformational"
        if "noise" in label:
            return "noise"
        return "noise"
    except Exception:
        return None


def run_signal_classification_v2(run_id: str) -> Dict[str, Any]:
    """
    Load signal_clusters and extracted_signals for run_id; for each cluster call classifier,
    then update signal_clusters.classification.

    Returns:
        {"classified": N, "clusters_processed": M, "failed": K}
    """
    from core.generator_db import (
        get_signal_clusters_for_run,
        get_extracted_signals_for_run,
        update_signal_cluster_classification,
    )

    clusters = get_signal_clusters_for_run(run_id)
    if not clusters:
        return {"classified": 0, "clusters_processed": 0, "failed": 0}

    signals = get_extracted_signals_for_run(run_id)
    time_horizons_by_key = _time_horizons_by_cluster_key(signals)

    classified = 0
    failed = 0
    for c in clusters:
        cluster_id = c.get("id")
        cluster_key = c.get("cluster_key")
        if not cluster_id:
            continue
        time_horizons = time_horizons_by_key.get(cluster_key, [])
        signal_type = c.get("signal_type") or "other"
        # Hard rule: operational + short_term -> tactical (no LLM upgrade to structural)
        time_horizons_normalized = [t.strip().lower() for t in time_horizons if t]
        all_short_term = time_horizons_normalized and all(th == "short_term" for th in time_horizons_normalized)
        if signal_type == "operational" and all_short_term:
            label = "tactical"
        else:
            label = _call_classification(
                signal_type=signal_type,
                segment=c.get("segment"),
                region=c.get("region"),
                cluster_size=int(c.get("cluster_size") or 0),
                aggregated_numeric_value=c.get("aggregated_numeric_value"),
                time_horizons=time_horizons,
            )
        if label and update_signal_cluster_classification(cluster_id, label):
            classified += 1
        else:
            failed += 1

    return {
        "classified": classified,
        "clusters_processed": len(clusters),
        "failed": failed,
    }
