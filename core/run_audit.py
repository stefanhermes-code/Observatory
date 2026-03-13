"""
Per-run audit log: spec context, step counts, and drop-reason counts.
Stored in newsletter_runs.metadata.run_audit and optionally written to audit_log
for Admin visibility. All values are counts (integers) or fixed fields; no narrative.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

# Drop reason keys (counts only)
DROP_OUTSIDE_LOOKBACK = "outside_lookback_window"
DROP_NO_MAPPED_CATEGORY = "no_mapped_category"
DROP_FAILED_REGION_FILTER = "failed_region_filter"
DROP_FAILED_VALUE_CHAIN_FILTER = "failed_value_chain_filter"
DROP_FAILED_SECTION_FILTER = "failed_section_filter"
DROP_NO_CLUSTER_FORMED = "no_cluster_formed"
DROP_BELOW_MINIMUM_STRENGTH = "below_minimum_strength"
DROP_MISSING_CLASSIFIER_CATEGORY = "missing_classifier_category"
DROP_FAILED_CUSTOMER_FILTER = "failed_customer_filter"  # aggregate when not split

# Step keys (counts)
STEP_MASTER_SIGNALS_LOADED = "master_signals_loaded_count"
STEP_QUERY_PLAN_CANDIDATES = "query_plan_candidates_count"
STEP_AFTER_DATE_FILTER = "candidates_after_date_filter_count"
STEP_AFTER_CUSTOMER_FILTER = "candidates_after_customer_filter_count"
STEP_AFTER_SECTION_FILTER = "candidates_after_section_filter_count"
STEP_GROUPED_CLUSTERS = "grouped_clusters_count"
STEP_EXTRACTED_DEVELOPMENTS = "extracted_developments_count"
STEP_AFTER_STRENGTH_THRESHOLD = "developments_after_strength_threshold_count"
STEP_WRITTEN_TO_REPORT = "developments_written_to_report_count"


def _int(v: Any) -> int:
    if v is None:
        return 0
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def create_empty_run_audit(report_period_days: Optional[int] = None) -> Dict[str, Any]:
    """
    Initialize run_audit at run start (Run Bundle Architecture).
    Every run has this object; the pipeline updates steps and drop_reason_counts during execution.
    """
    return {
        "steps": {
            "stage_1_master_signals_loaded": 0,
            "stage_2_after_date_filter": 0,
            "stage_3_after_customer_scope_filter": 0,
            "stage_4_after_section_mapping": 0,
            "stage_5_clusters_formed": 0,
            "stage_6_developments_extracted": 0,
            "stage_7_after_strength_threshold": 0,
            "stage_8_developments_written_to_report": 0,
            "master_signals_loaded_count": 0,
            "query_plan_candidates_count": 0,
            "candidates_after_date_filter_count": 0,
            "candidates_after_customer_filter_count": 0,
            "candidates_after_section_filter_count": 0,
            "grouped_clusters_count": 0,
            "extracted_developments_count": 0,
            "developments_after_strength_threshold_count": 0,
            "developments_written_to_report_count": 0,
        },
        "drop_reason_counts": {},
        "report_period_days": report_period_days,
    }


def build_run_audit(
    run_id: str,
    spec_id: str,
    spec: Dict[str, Any],
    report_period_days: Optional[int],
    use_phase5_report: bool,
    evidence_summary: Optional[Dict[str, Any]] = None,
    candidates_count: int = 0,
    candidates_after_customer_filter: int = 0,
    report_metrics: Optional[Dict[str, Any]] = None,
    customer_filter_drop_counts: Optional[Dict[str, int]] = None,
    workspace_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build the per-run audit payload: spec context, step counts, drop_reason_counts.
    All values are counts (integers) or fixed fields. No narrative.
    """
    spec = spec or {}
    evidence_summary = evidence_summary or {}
    report_metrics = report_metrics or {}
    customer_filter_drop_counts = customer_filter_drop_counts or {}

    funnel = evidence_summary.get("funnel") or {}
    drop_buckets = funnel.get("drop_buckets") or {}

    # Spec context (RUN_ID, TIMESTAMP, SPEC_ID, CUSTOMER_ID, LOOKBACK_DAYS, USE_PHASE5_REPORT, MIN_SIGNAL_STRENGTH, INCLUDED_SECTIONS)
    audit: Dict[str, Any] = {
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "spec_id": spec_id,
        "customer_id": workspace_id,
        "lookback_days": report_period_days,
        "report_period_days": report_period_days,
        "use_phase5_report": use_phase5_report,
        "minimum_signal_strength": spec.get("minimum_signal_strength_in_report"),
        "min_signal_strength": spec.get("minimum_signal_strength_in_report"),
        "included_sections": list(spec.get("included_sections") or []),
    }

    # CharlieC: signals after source fetch and after query plan (evidence engine funnel)
    signals_after_source_fetch = _int(funnel.get("from_sources")) or _int(evidence_summary.get("candidates_from_sources", 0))
    signals_after_query_plan = _int(funnel.get("combined")) or (_int(evidence_summary.get("candidates_from_sources", 0)) + _int(evidence_summary.get("candidates_from_search", 0)))
    audit["signals_after_source_fetch"] = signals_after_source_fetch
    audit["signals_after_query_plan"] = signals_after_query_plan

    # Pipeline stage counters (STAGE_1..STAGE_8 + query_plan_candidates for diagnostics)
    audit["steps"] = {
        "master_signals_loaded_count": _int(report_metrics.get("master_signals_loaded_count")),
        "signals_after_source_fetch": signals_after_source_fetch,
        "signals_after_query_plan": signals_after_query_plan,
        "query_plan_candidates_count": _int(funnel.get("combined")) or _int(evidence_summary.get("candidates_from_sources", 0)) + _int(evidence_summary.get("candidates_from_search", 0)),
        "candidates_after_date_filter_count": _int(funnel.get("after_first_pass")) or _int(evidence_summary.get("inserted")),
        "candidates_after_customer_filter_count": candidates_after_customer_filter,
        "candidates_after_section_filter_count": _int(report_metrics.get("candidates_after_section_filter_count")),
        "grouped_clusters_count": _int(report_metrics.get("grouped_clusters_count")),
        "extracted_developments_count": _int(report_metrics.get("extracted_developments_count")),
        "developments_after_strength_threshold_count": _int(report_metrics.get("developments_after_strength_threshold_count")),
        "developments_written_to_report_count": _int(report_metrics.get("developments_written_to_report_count")),
    }
    # Aliases for CharlieC checklist (STAGE_N naming)
    audit["steps"]["stage_1_master_signals_loaded"] = audit["steps"]["master_signals_loaded_count"]
    audit["steps"]["stage_2_after_date_filter"] = audit["steps"]["candidates_after_date_filter_count"]
    audit["steps"]["stage_3_after_customer_scope_filter"] = audit["steps"]["candidates_after_customer_filter_count"]
    audit["steps"]["stage_4_after_section_mapping"] = audit["steps"]["candidates_after_section_filter_count"]
    audit["steps"]["stage_5_clusters_formed"] = audit["steps"]["grouped_clusters_count"]
    audit["steps"]["stage_6_developments_extracted"] = audit["steps"]["extracted_developments_count"]
    audit["steps"]["stage_7_after_strength_threshold"] = audit["steps"]["developments_after_strength_threshold_count"]
    audit["steps"]["stage_8_developments_written_to_report"] = audit["steps"]["developments_written_to_report_count"]
    if audit["steps"]["query_plan_candidates_count"] == 0 and evidence_summary:
        audit["steps"]["query_plan_candidates_count"] = _int(funnel.get("combined"))
        audit["steps"]["candidates_after_date_filter_count"] = _int(evidence_summary.get("inserted"))

    # Drop reason counts (always include standard keys; values are counts)
    no_mapped = _int(customer_filter_drop_counts.get("no_mapped_category")) or _int(report_metrics.get("drop_no_mapped_category"))
    below_strength = _int(report_metrics.get("drop_below_minimum_strength"))
    drop_reason_counts: Dict[str, int] = {
        DROP_OUTSIDE_LOOKBACK: _int(drop_buckets.get("date")),
        "failed_category_mapping": no_mapped,
        DROP_NO_MAPPED_CATEGORY: no_mapped,
        DROP_FAILED_REGION_FILTER: _int(customer_filter_drop_counts.get("failed_region_filter")) or _int(report_metrics.get("drop_failed_region_filter")),
        DROP_FAILED_VALUE_CHAIN_FILTER: _int(customer_filter_drop_counts.get("failed_value_chain_filter")) or _int(report_metrics.get("drop_failed_value_chain_filter")),
        DROP_FAILED_SECTION_FILTER: _int(report_metrics.get("drop_failed_section_filter")),
        DROP_NO_CLUSTER_FORMED: _int(report_metrics.get("drop_no_cluster_formed")),
        "below_strength_threshold": below_strength,
        DROP_BELOW_MINIMUM_STRENGTH: below_strength,
        DROP_MISSING_CLASSIFIER_CATEGORY: _int(report_metrics.get("drop_missing_classifier_category")),
        DROP_FAILED_CUSTOMER_FILTER: _int(customer_filter_drop_counts.get("dropped_total")),
    }
    for key in ("url", "meta_snippet", "canonical", "pu_anchor_missing", "region_mismatch_proven_by_jsonld", "pu_not_relevant_proven_by_jsonld", "other"):
        if key in drop_buckets:
            drop_reason_counts[f"evidence_{key}"] = _int(drop_buckets[key])
    audit["drop_reason_counts"] = drop_reason_counts

    return audit


def persist_run_audit(run_id: str, user_email: str, audit_payload: Dict[str, Any]) -> None:
    """
    Write run audit to audit_log so Admin can see per-run counts and drop reasons.
    Uses action_type 'run_audit' and target_type 'newsletter_run'. Does not raise on failure.
    """
    try:
        from core.admin_db import log_audit_action
        log_audit_action("run_audit", user_email or "generator", {"run_id": run_id, **audit_payload})
    except Exception:
        pass
