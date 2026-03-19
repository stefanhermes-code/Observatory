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
        "signals_after_query_plan": 0,
        "signals_after_date_filter": 0,
        "drop_validation": 0,
        "drop_empty_url": 0,
        "drop_dedup": 0,
        "drop_other": 0,
        "signals_after_preinsert_validation": 0,
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
    signals_after_date_filter = _int(funnel.get("after_first_pass")) or _int(evidence_summary.get("inserted"))
    audit["signals_after_source_fetch"] = signals_after_source_fetch
    audit["signals_after_query_plan"] = signals_after_query_plan
    audit["signals_after_date_filter"] = signals_after_date_filter
    # Pre-insert filtering stage (CharlieC: expose where signals are removed before DB insert)
    audit["drop_validation"] = _int(funnel.get("drop_validation"))
    audit["drop_empty_url"] = _int(funnel.get("drop_empty_url"))
    audit["drop_dedup"] = _int(funnel.get("drop_dedup"))
    audit["drop_other"] = _int(funnel.get("drop_other"))
    audit["signals_after_preinsert_validation"] = _int(funnel.get("signals_after_preinsert_validation")) or _int(evidence_summary.get("inserted"))

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
    # Scope filter input = signals that survived pre-insert only. Total lost at scope = input - stage_3.
    scope_filter_input = _int(audit.get("signals_after_preinsert_validation")) or _int(audit["steps"].get("candidates_after_date_filter_count"))
    drop_customer_scope_total = scope_filter_input - _int(audit["steps"].get("candidates_after_customer_filter_count"))
    # Section mapping: stage_3 = stage_4 + drop_section_mapping_total
    stage_3_count = _int(audit["steps"].get("candidates_after_customer_filter_count"))
    stage_4_count = _int(audit["steps"].get("candidates_after_section_filter_count"))
    drop_section_mapping_total = max(0, stage_3_count - stage_4_count)
    drop_failed_section_filter = _int(report_metrics.get("drop_failed_section_filter"))
    drop_reason_counts: Dict[str, int] = {
        DROP_OUTSIDE_LOOKBACK: _int(drop_buckets.get("date")),
        "failed_category_mapping": no_mapped,
        DROP_NO_MAPPED_CATEGORY: no_mapped,
        DROP_FAILED_REGION_FILTER: _int(customer_filter_drop_counts.get("failed_region_filter")) or _int(report_metrics.get("drop_failed_region_filter")),
        DROP_FAILED_VALUE_CHAIN_FILTER: _int(customer_filter_drop_counts.get("failed_value_chain_filter")) or _int(report_metrics.get("drop_failed_value_chain_filter")),
        DROP_FAILED_SECTION_FILTER: drop_failed_section_filter,
        "drop_section_mapping_total": drop_section_mapping_total,
        DROP_NO_CLUSTER_FORMED: _int(report_metrics.get("drop_no_cluster_formed")),
        "below_strength_threshold": below_strength,
        DROP_BELOW_MINIMUM_STRENGTH: below_strength,
        DROP_MISSING_CLASSIFIER_CATEGORY: _int(report_metrics.get("drop_missing_classifier_category")),
        DROP_FAILED_CUSTOMER_FILTER: _int(customer_filter_drop_counts.get("dropped_total")) or drop_customer_scope_total,
        # Explicit derived metric so stage-3 losses are always visible.
        "drop_customer_scope_total": drop_customer_scope_total,
    }
    for key in ("url", "meta_snippet", "canonical", "pu_anchor_missing", "region_mismatch_proven_by_jsonld", "pu_not_relevant_proven_by_jsonld", "other"):
        if key in drop_buckets:
            drop_reason_counts[f"evidence_{key}"] = _int(drop_buckets[key])
    audit["drop_reason_counts"] = drop_reason_counts

    # ------------------------------------------------------------------
    # Specification validity vs run selection (two-layer model)
    # ------------------------------------------------------------------
    # Layer A – specification validity: signals that survive pre-insert validation.
    signals_valid_for_spec = _int(audit.get("signals_after_preinsert_validation"))
    signals_invalid_for_spec = max(0, signals_after_query_plan - signals_valid_for_spec)
    audit["signals_valid_for_spec"] = signals_valid_for_spec
    audit["signals_invalid_for_spec"] = signals_invalid_for_spec

    # Layer B – run selection: among spec-valid signals, which are included vs excluded by this run scope.
    signals_included_in_run = _int(audit["steps"].get("candidates_after_customer_filter_count"))
    signals_excluded_by_run_scope = max(0, signals_valid_for_spec - signals_included_in_run)
    audit["signals_included_in_run"] = signals_included_in_run
    audit["signals_excluded_by_run_scope"] = signals_excluded_by_run_scope

    # Validation-stage breakdown and pass-strength counters.
    validation_counters = evidence_summary.get("validation_counters") or {}

    # Hard rejected at validation (relaxed model)
    audit["validation_region_mismatch"] = _int(validation_counters.get("validation_region_mismatch"))
    audit["validation_other_hard_reject"] = _int(validation_counters.get("validation_other_hard_reject"))

    # Soft-kept at validation (relaxed model)
    audit["pu_anchor_missing_soft_kept"] = _int(validation_counters.get("pu_anchor_missing_soft_kept"))
    audit["weak_content_soft_kept"] = _int(validation_counters.get("weak_content_soft_kept"))
    audit["missing_category_soft_kept"] = _int(validation_counters.get("missing_category_soft_kept"))
    audit["missing_value_chain_soft_kept"] = _int(validation_counters.get("missing_value_chain_soft_kept"))

    # Pass strength (relaxed model)
    audit["strong_pass_count"] = _int(validation_counters.get("strong_pass_count")) or _int(
        validation_counters.get("validation_strong_pass_count")
    )
    audit["borderline_pass_count"] = _int(validation_counters.get("borderline_pass_count")) or _int(
        validation_counters.get("validation_borderline_pass_count")
    )

    # Backwards-compatible object for existing readers (now reflects hard rejects only).
    audit["validation_breakdown"] = {
        "validation_pu_anchor_missing": _int(validation_counters.get("validation_pu_anchor_missing")),
        "validation_region_mismatch": audit["validation_region_mismatch"],
        "validation_value_chain_mismatch": _int(validation_counters.get("validation_value_chain_mismatch")),
        "validation_missing_category": _int(validation_counters.get("validation_missing_category")),
        "validation_weak_content_signal": _int(validation_counters.get("validation_weak_content_signal")),
        "validation_other": _int(validation_counters.get("validation_other")) or audit["validation_other_hard_reject"],
    }
    audit["validation_strong_pass_count"] = _int(validation_counters.get("validation_strong_pass_count")) or audit["strong_pass_count"]
    audit["validation_borderline_pass_count"] = _int(validation_counters.get("validation_borderline_pass_count")) or audit["borderline_pass_count"]

    # Representative validation-rejected examples (per-run sample).
    validation_examples_in = evidence_summary.get("top_validation_rejected_examples") or []
    top_examples = []
    for ex in validation_examples_in:
        if len(top_examples) >= 10:
            break
        if not isinstance(ex, dict):
            continue
        top_examples.append(
            {
                "title": ex.get("title") or "",
                "canonical_url": ex.get("canonical_url") or ex.get("url") or "",
                "reason": ex.get("reason") or "",
            }
        )
    audit["top_validation_rejected_examples"] = top_examples

    # Section-mapping instrumentation (mapping attempts, outcomes, and near-misses).
    mapping_stats = report_metrics.get("mapping_stats") or {}
    audit["category_distribution"] = report_metrics.get("category_distribution") or {}
    audit["mapping_attempts_total"] = _int(mapping_stats.get("mapping_attempts_total")) or _int(
        audit["steps"].get("candidates_after_customer_filter_count")
    )
    audit["mapping_success_by_section"] = mapping_stats.get("mapping_success_by_section") or {}
    audit["mapping_fail_no_matching_section_rule"] = _int(mapping_stats.get("mapping_fail_no_matching_section_rule"))
    audit["mapping_fail_category_not_linked_to_section"] = _int(
        mapping_stats.get("mapping_fail_category_not_linked_to_section")
    )
    audit["mapping_fail_value_chain_not_linked"] = _int(mapping_stats.get("mapping_fail_value_chain_not_linked"))
    audit["mapping_fail_multi_match_conflict"] = _int(mapping_stats.get("mapping_fail_multi_match_conflict"))
    audit["mapping_fail_other"] = _int(mapping_stats.get("mapping_fail_other"))
    audit["signals_unmapped_but_categorized"] = _int(mapping_stats.get("signals_unmapped_but_categorized"))
    audit["top_unmapped_signals_sample"] = mapping_stats.get("top_unmapped_signals_sample") or []

    # Flow ratios for quick visibility on choke-point strength.
    stage_2_after_date = _int(audit["steps"].get("stage_2_after_date_filter"))
    stage_3_after_scope = _int(audit["steps"].get("stage_3_after_customer_scope_filter"))
    stage_4_after_mapping = _int(audit["steps"].get("stage_4_after_section_mapping"))
    stage_8_written = _int(audit["steps"].get("stage_8_developments_written_to_report"))

    audit["validation_pass_rate"] = (signals_valid_for_spec / stage_2_after_date) if stage_2_after_date > 0 else None
    audit["mapping_pass_rate"] = (stage_4_after_mapping / stage_3_after_scope) if stage_3_after_scope > 0 else None
    audit["overall_yield"] = (stage_8_written / signals_after_query_plan) if signals_after_query_plan > 0 else None

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
