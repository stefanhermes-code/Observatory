"""
Canonical Generator Execution Pattern.
Implements the 7-step execution flow and Run Bundle Architecture:
- execute_generator() is the single run controller: the only place that creates and finalizes runs.
- Every run produces a run bundle (run_id, status, spec_id, report_period_days, html_output_path, timing, run_audit, error_message).
- Audit is initialized at run start and updated during the pipeline; finalize_run() persists it in try/finally so audit is never skipped.
- A run is only marked success if run_audit and html_output_path exist; otherwise status is failed_finalization.
"""

from typing import Dict, Optional, Tuple, List
from datetime import datetime
import json
import os
from pathlib import Path

from core.run_dates import get_lookback_from_days, get_lookback_days
from core.generator_db import (
    get_specification_detail,
    check_frequency_enforcement,
    create_newsletter_run,
    update_run_status,
    get_candidate_articles_for_run,
    get_master_signals_for_run,
)
from core.token_tracking import compute_cost_for_usage

# Builder-only: can set lookback to 1/7/30 days and run without frequency limit
BUILDER_EMAIL = "stefan.hermes@htcglobal.asia"


class RunFailedError(Exception):
    """Raised when the pipeline fails after a run record exists; finally will call finalize_run."""
    pass


def _record_controller_milestone(run_id: str, user_email: str, milestone: str) -> None:
    """
    Minimal milestone trace for the run controller.

    Writes to audit_log via log_audit_action so we can see exactly where execution stopped,
    without depending on the full run audit.
    """
    try:
        from datetime import datetime, timezone
        from core.admin_db import log_audit_action

        payload = {
            "run_id": run_id,
            "milestone": milestone,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        }
        log_audit_action("run_controller_milestone", user_email or "generator", payload)
    except Exception:
        # Never block the run on observability.
        pass


def _flag_from_secrets_or_env(name: str) -> bool:
    """
    Read boolean feature flag from Streamlit secrets (Cloud) or environment (local).
    Returns True if the value (case-insensitive) equals 'true'.
    """
    val = None
    try:
        import streamlit as st  # type: ignore

        # st.secrets raises if not in a Streamlit context; guard with try/except.
        val = st.secrets.get(name)
    except Exception:
        pass
    if val is None:
        val = os.getenv(name)
    if val is None:
        return False
    return str(val).strip().lower() == "true"


def _build_run_usage_metadata(evidence_summary: Optional[Dict], writer_output: Optional[Dict]) -> Dict:
    """
    Aggregate token usage from Executive Summary (Chat Completions) and web search (Responses API).
    Returns dict with input_tokens, output_tokens, total_tokens, estimated_cost, model for run metadata.
    Empty dict if no usage (so we don't overwrite with zeros).
    """
    out = {}
    total_in, total_out = 0, 0
    cost = 0.0
    exec_usage = (writer_output or {}).get("exec_summary_usage")
    if exec_usage and isinstance(exec_usage, dict):
        inp = int(exec_usage.get("input_tokens") or 0)
        out_tok = int(exec_usage.get("output_tokens") or 0)
        total_in += inp
        total_out += out_tok
        cost += compute_cost_for_usage(inp, out_tok, exec_usage.get("model") or "gpt-4o-mini")
    web_usage = None
    if isinstance(evidence_summary, dict):
        web_usage = (evidence_summary.get("token_usage") or {}).get("web_search")
    if web_usage and isinstance(web_usage, dict):
        inp = int(web_usage.get("input_tokens") or 0)
        out_tok = int(web_usage.get("output_tokens") or 0)
        total_in += inp
        total_out += out_tok
        cost += compute_cost_for_usage(inp, out_tok, web_usage.get("model") or "gpt-4o")
    if total_in + total_out == 0:
        return out
    out["input_tokens"] = total_in
    out["output_tokens"] = total_out
    out["total_tokens"] = total_in + total_out
    out["estimated_cost"] = round(cost, 6)
    out["model"] = "gpt-4o" if web_usage else "gpt-4o-mini"
    return out


def _render_html_from_content(*args, **kwargs):
    """Lazy import to avoid KeyError on 'core.content_pipeline' under Streamlit Cloud."""
    from core.content_pipeline import render_html_from_content
    return render_html_from_content(*args, **kwargs)


def _persist_run_audit_on_failure(
    run_id: str,
    spec_id: str,
    workspace_id: str,
    user_email: str,
    run_specification: Dict,
    error_message: str,
    lookback_days_override: Optional[int] = None,
    use_phase5_report: bool = False,
    evidence_summary: Optional[Dict] = None,
    candidates_count: int = 0,
    candidates_after_customer_filter: int = 0,
    customer_filter_drop_counts: Optional[Dict] = None,
    run_audit_metrics: Optional[Dict] = None,
) -> None:
    """Build partial run audit and persist to audit_log + run metadata. Used only from phased runs / legacy paths."""
    try:
        from core.run_audit import build_run_audit, persist_run_audit
        use_phase5 = use_phase5_report or bool(_flag_from_secrets_or_env("USE_PHASE5_REPORT") or run_specification.get("use_phase5_report") is True)
        base_days = run_specification.get("report_period_days")
        if isinstance(base_days, int) and base_days > 0:
            default_days = base_days
        else:
            default_days = get_lookback_days(run_specification.get("frequency", "monthly"))
        report_period_days = lookback_days_override if lookback_days_override is not None else default_days
        audit = build_run_audit(
            run_id=run_id,
            spec_id=spec_id,
            spec=run_specification,
            report_period_days=report_period_days,
            use_phase5_report=use_phase5,
            evidence_summary=evidence_summary,
            candidates_count=candidates_count,
            candidates_after_customer_filter=candidates_after_customer_filter,
            report_metrics=run_audit_metrics or {},
            customer_filter_drop_counts=customer_filter_drop_counts or {},
            workspace_id=workspace_id,
        )
        audit["status"] = "failed"
        audit["error_message"] = error_message[:500] if error_message else None
        persist_run_audit(run_id, user_email or "generator", audit)
        update_run_status(
            run_id,
            "failed",
            error_message=error_message,
            metadata={"run_audit": audit},
            report_period_days=report_period_days,
        )
    except Exception:
        update_run_status(run_id, "failed", error_message=error_message)


def finalize_run(
    run_id: str,
    user_email: str,
    run_bundle: Dict,
    metadata: Optional[Dict] = None,
    report_period_days: Optional[int] = None,
    generation_duration_seconds: Optional[float] = None,
    categories_count: Optional[int] = None,
    regions_count: Optional[int] = None,
    links_count: Optional[int] = None,
) -> None:
    """
    Run Bundle Architecture: the only place that persists run completion.

    For debugging/diagnostics, we split responsibilities:
    - Core result finalization: persist status + html_output_path + metadata.
    - Audit/observability finalization: best-effort write of run_audit to audit_log + metadata.

    Rules:
    - If html_output_path exists but audit write fails, mark status as 'success_with_audit_failure'
      (or keep existing status if it is already non-success). Do NOT hide the run result.
    - Only use 'failed_finalization' for cases where even the core result cannot be finalized
      (e.g. missing html_output_path on an apparent success).
    """
    from core.run_audit import persist_run_audit

    status = run_bundle.get("status", "failed")
    run_audit = run_bundle.get("run_audit") if isinstance(run_bundle.get("run_audit"), dict) else None
    html_output_path = run_bundle.get("html_output_path")

    # Core result validity: a "success" with no HTML is a real finalization failure.
    if status == "success" and not html_output_path:
        status = "failed_finalization"

    if metadata is None:
        metadata = {}

    # Core result finalization (always runs, even if audit fails).
    rp_days = report_period_days if report_period_days is not None else run_bundle.get("report_period_days")
    update_run_status(
        run_id,
        status,
        artifact_path=html_output_path,
        error_message=run_bundle.get("error_message"),
        metadata=metadata if metadata else None,
        generation_duration_seconds=generation_duration_seconds,
        categories_count=categories_count,
        regions_count=regions_count,
        links_count=links_count,
        report_period_days=rp_days,
    )

    # Audit / observability finalization (best-effort; never hides a successful run).
    if run_audit is not None:
        try:
            run_audit["status"] = status
            if run_bundle.get("error_message"):
                run_audit["error_message"] = (run_bundle["error_message"] or "")[:500]
            persist_run_audit(run_id, user_email or "generator", run_audit)
            # Also attach into metadata for downstream readers (Admin History).
            metadata["run_audit"] = run_audit
            update_run_status(run_id, status, metadata=metadata)
        except Exception:
            # If HTML exists but audit write fails, mark as success_with_audit_failure
            if html_output_path and status == "success":
                status = "success_with_audit_failure"
                try:
                    update_run_status(run_id, status, artifact_path=html_output_path)
                except Exception:
                    # At this point, we have at least persisted the original success run.
                    pass


def execute_generator(
    spec_id: str,
    workspace_id: str,
    user_email: str,
    cadence_override: Optional[str] = None,
    lookback_override: Optional[int] = None,
    categories_override: Optional[List[str]] = None,
    regions_override: Optional[List[str]] = None,
    value_chain_links_override: Optional[List[str]] = None
) -> Tuple[bool, Optional[str], Optional[Dict], Optional[str]]:
    """
    Execute the canonical 7-step Generator execution pattern.
    
    Returns:
        (success, error_message, result_data, artifact_path)
        - success: Boolean indicating if generation succeeded
        - error_message: Error message if failed, None if succeeded
        - result_data: Dictionary with run_id, html_content, metadata if succeeded
        - artifact_path: Path to stored artifact if succeeded
    """
    
    _record_controller_milestone("pending", user_email, "controller_entered")

    # Step 1: Retrieve Active Specification
    spec = get_specification_detail(spec_id)
    if not spec:
        return False, "Specification not found", None, None
    
    if spec.get("status") != "active":
        return False, f"Specification is not active (status: {spec.get('status')})", None, None
    _record_controller_milestone("pending", user_email, "spec_loaded")
    
    # Step 2: Enforce Cadence Rules
    frequency = spec.get("frequency", "monthly")
    # Allow cadence override for testing/marketing (e.g., stefan.hermes@htcglobal.asia)
    # When override is provided, bypass frequency enforcement (infinite mode)
    if cadence_override:
        frequency = cadence_override
        # For cadence override, always allow (infinite mode)
        is_allowed, reason, next_date = True, None, None
    else:
        # Note: Infinite frequency override is handled in generator_app.py before calling this function
        is_allowed, reason, next_date = check_frequency_enforcement(spec_id, frequency, user_email)
    
    if not is_allowed:
        return False, reason, None, None

    # Create a modified specification with overridden categories/regions if provided
    run_specification = spec.copy()
    if categories_override:
        run_specification["categories"] = categories_override
    if regions_override:
        run_specification["regions"] = regions_override
    if value_chain_links_override is not None:
        run_specification["value_chain_links"] = value_chain_links_override

    # Canonical report period. Builder (stefan.hermes@htcglobal.asia): use chosen lookback only, no fallback. Others: spec or frequency default only.
    is_builder = user_email and user_email.strip().lower() == BUILDER_EMAIL.lower()
    lookback_days_override = (lookback_override if is_builder and isinstance(lookback_override, int) and lookback_override > 0 else None)
    base_days = run_specification.get("report_period_days")
    default_days = base_days if (isinstance(base_days, int) and base_days > 0) else get_lookback_days(run_specification.get("frequency", "monthly"))
    report_period_days = lookback_days_override if lookback_days_override is not None else default_days
    run_specification["report_period_days"] = report_period_days

    # Step 4: Create run record (run_id must exist before evidence ingestion — V2-DB-02)
    # Run Bundle Architecture: only place that creates and finalizes runs.
    run = create_newsletter_run(spec_id, workspace_id, user_email, "running", frequency=frequency)
    run_id = run["id"]
    _record_controller_milestone(run_id, user_email, "run_created")

    # Diagnostic: record effective lookback inputs for this run in audit_log so we can confirm source of 2-day window.
    try:
        from core.admin_db import log_audit_action

        log_audit_action(
            "run_lookback_debug",
            user_email or "generator",
            {
                "run_id": run_id,
                "user_email": user_email or "generator",
                "spec_id": spec_id,
                "workspace_id": workspace_id,
                "lookback_override_param": lookback_override,
                "spec_report_period_days": base_days,
                "spec_frequency": run_specification.get("frequency", "monthly"),
                "effective_report_period_days": report_period_days,
            },
        )
    except Exception:
        # Debug logging must never block the run.
        pass

    from core.run_audit import create_empty_run_audit
    run_audit_init = create_empty_run_audit(report_period_days)
    run_audit_init["run_id"] = run_id
    run_audit_init["spec_id"] = spec_id
    run_bundle = {
        "run_id": run_id,
        "status": "running",
        "spec_id": spec_id,
        "report_period_days": report_period_days,
        "html_output_path": None,
        "timing": None,
        "run_audit": run_audit_init,
        "error_message": None,
    }
    metadata_with_html = None
    result_data = None
    artifact_path_out = None
    duration = None
    categories_count = None
    regions_count = None
    links_count = None

    try:
        from core.performance_logger import start_run, end_run, start_stage, end_stage, log_error
        start_run(run_id)
    except Exception:
        pass

    # V2: Run Evidence Engine — persist candidate_articles (date window already set above: builder = chosen lookback, others = spec/frequency).
    ref_date = datetime.utcnow()
    try:
        from core.performance_logger import start_stage, end_stage, log_error
        start_stage("ingestion")
    except Exception:
        pass
    _record_controller_milestone(run_id, user_email, "ingestion_started")
    if os.environ.get("PHASE8_FORCE_FAIL") == "ingestion":
        try:
            from core.performance_logger import end_stage, log_error, end_run
            end_stage("ingestion", "fail", error_type="Phase8Validation", error_message="Phase 8 forced failure: ingestion")
            log_error("ingestion", "Phase 8 forced failure: ingestion")
            end_run("fail")
        except Exception:
            pass
        run_bundle["status"] = "failed"
        run_bundle["error_message"] = "Phase 8 forced failure: ingestion"
        if isinstance(run_bundle.get("run_audit"), dict):
            run_bundle["run_audit"]["status"] = "failed"
            run_bundle["run_audit"]["error_message"] = "Phase 8 forced failure: ingestion"
        raise RunFailedError("Phase 8 forced failure: ingestion")
    try:
        from core.evidence_engine import run_evidence_engine
        evidence_summary = run_evidence_engine(
            run_id=run_id,
            workspace_id=workspace_id,
            specification_id=spec_id,
            spec=run_specification,
            validate_urls=True,
            cadence_override=cadence_override,
            reference_date=ref_date,
            report_period_days=run_specification["report_period_days"],
        )
        try:
            end_stage("ingestion", "success")
        except Exception:
            pass
        _record_controller_milestone(run_id, user_email, "ingestion_finished")
    except Exception as ev_err:
        try:
            from core.performance_logger import end_stage, log_error
            end_stage("ingestion", "fail", error_type=type(ev_err).__name__, error_message=str(ev_err)[:500])
            log_error("ingestion", str(ev_err)[:500])
        except Exception:
            pass
        evidence_summary = {"error": str(ev_err), "inserted": 0, "query_plan": []}

    candidates = get_candidate_articles_for_run(run_id)
    lookback_date, reference_date = get_lookback_from_days(run_specification["report_period_days"], ref_date)

    try:
        from core.performance_logger import start_stage, end_stage, log_error
        start_stage("extraction")
    except Exception:
        pass
    _record_controller_milestone(run_id, user_email, "filtering_started")
    extraction_result = {"signals_created": 0, "occurrences_created": 0}
    signal_extraction_result = {"extracted_count": 0, "signals_inserted": 0, "articles_processed": 0}
    customer_filter_drop_counts: Dict = {}
    try:
        from core.customer_filter import filter_candidates_by_spec_with_stats
        filtered_candidates, customer_filter_drop_counts = filter_candidates_by_spec_with_stats(candidates, run_specification)
    except Exception:
        from core.customer_filter import filter_candidates_by_spec
        filtered_candidates = filter_candidates_by_spec(candidates, run_specification)
    try:
        from core.intelligence_extraction import run_intelligence_extraction
        extraction_result = run_intelligence_extraction(
            run_id=run_id,
            workspace_id=workspace_id,
            specification_id=spec_id,
            candidates=filtered_candidates,
        )
        from core.signal_extraction_v2 import run_signal_extraction_v2
        signal_extraction_result = run_signal_extraction_v2(run_id=run_id, candidates=filtered_candidates)
        try:
            from core.performance_logger import end_stage
            end_stage("extraction", "success")
        except Exception:
            pass
        _record_controller_milestone(run_id, user_email, "filtering_finished")
    except Exception as ext_err:
        try:
            from core.performance_logger import end_stage, log_error
            end_stage("extraction", "fail", error_type=type(ext_err).__name__, error_message=str(ext_err)[:500])
            log_error("extraction", str(ext_err)[:500])
        except Exception:
            pass
        extraction_result = {"signals_created": 0, "occurrences_created": 0}
        signal_extraction_result = {"extracted_count": 0, "signals_inserted": 0, "articles_processed": 0}

    try:
        from core.performance_logger import start_stage, end_stage, log_error
        start_stage("clustering")
    except Exception:
        pass
    _record_controller_milestone(run_id, user_email, "clustering_started")
    try:
        from core.signal_clustering_v2 import run_signal_clustering_v2
        signal_clustering_result = run_signal_clustering_v2(run_id=run_id)
        try:
            from core.performance_logger import end_stage
            end_stage("clustering", "success")
        except Exception:
            pass
        _record_controller_milestone(run_id, user_email, "clustering_finished")
    except Exception as cl_err:
        try:
            from core.performance_logger import end_stage, log_error
            end_stage("clustering", "fail", error_type=type(cl_err).__name__, error_message=str(cl_err)[:500])
            log_error("clustering", str(cl_err)[:500])
        except Exception:
            pass
        signal_clustering_result = {"clusters_created": 0, "signals_grouped": 0}

    try:
        from core.performance_logger import start_stage, end_stage, log_error
        start_stage("llm_classification")
    except Exception:
        pass
    try:
        from core.signal_classification_v2 import run_signal_classification_v2
        signal_classification_result = run_signal_classification_v2(run_id=run_id)
        try:
            from core.performance_logger import end_stage
            end_stage("llm_classification", "success")
        except Exception:
            pass
    except Exception:
        try:
            from core.performance_logger import end_stage
            end_stage("llm_classification", "fail")
        except Exception:
            pass
        signal_classification_result = {"classified": 0, "clusters_processed": 0, "failed": 0}

    try:
        from core.performance_logger import start_stage, end_stage, log_error
        start_stage("doctrine_resolution")
    except Exception:
        pass
    try:
        from core.doctrine_resolver import run_doctrine_resolver_v2
        doctrine_result = run_doctrine_resolver_v2(run_id=run_id)
        try:
            from core.performance_logger import end_stage
            end_stage("doctrine_resolution", "success")
        except Exception:
            pass
    except Exception:
        try:
            from core.performance_logger import end_stage
            end_stage("doctrine_resolution", "fail")
        except Exception:
            pass
        doctrine_result = {"resolved": 0, "clusters_processed": 0, "failed": 0}

    try:
        from core.performance_logger import start_stage, end_stage
        start_stage("baseline_update")
        end_stage("baseline_update", "skipped")
        start_stage("momentum_update")
        end_stage("momentum_update", "skipped")
    except Exception:
        pass

    use_phase5_report = bool(
        _flag_from_secrets_or_env("USE_PHASE5_REPORT")
        or run_specification.get("use_phase5_report") is True
    )
    use_structural_pipeline = bool(
        _flag_from_secrets_or_env("USE_STRUCTURAL_PIPELINE")
        or run_specification.get("use_structural_pipeline") is True
    )
    run_audit_metrics: Optional[Dict] = None

    if use_phase5_report:
        try:
            from core.query_planner import build_query_plan_map
            from core.intelligence_report import generate_report_from_signals

            query_plan_map = build_query_plan_map(run_specification)
            signals = get_master_signals_for_run(run_id)
            report_result = generate_report_from_signals(
                signals,
                query_plan_map,
                run_specification,
                write_metrics=False,
                write_html=True,
                report_period_days=run_specification.get("report_period_days"),
            )
            run_audit_metrics = report_result.get("run_audit_metrics")
            writer_output = {
                "content": report_result.get("report_text", ""),
                "coverage_low": False,
            }
            if report_result.get("html"):
                writer_output["html"] = report_result["html"]
        except Exception as e:
            try:
                from core.performance_logger import end_run, log_error
                log_error("synthesis", str(e)[:500])
                end_run("fail")
            except Exception:
                pass
            run_bundle["status"] = "failed"
            run_bundle["error_message"] = f"Phase 5 report failed: {str(e)}"
            if isinstance(run_bundle.get("run_audit"), dict):
                run_bundle["run_audit"]["status"] = "failed"
                run_bundle["run_audit"]["error_message"] = (str(e))[:500]
            raise RunFailedError(f"Phase 5 report failed: {str(e)}")
    elif use_structural_pipeline:
        try:
            from core.structural_pipeline import run_structural_pipeline

            structural_output = run_structural_pipeline(
                run_id=run_id,
                spec=run_specification,
                candidates=candidates,
                lookback_date=lookback_date,
                reference_date=reference_date,
            )
            writer_output = {
                "content": structural_output.get("report_content", ""),
                "coverage_low": False,
                "structural_diagnostics": structural_output.get("diagnostics") or {},
            }
        except Exception as e:
            try:
                from core.performance_logger import end_run, log_error
                log_error("synthesis", str(e)[:500])
                end_run("fail")
            except Exception:
                pass
            # E: Write diagnostics for every run, including failed (so zero-output runs are visible).
            try:
                diag_dir = Path("development/outputs")
                diag_dir.mkdir(parents=True, exist_ok=True)
                diag_path = diag_dir / f"run_{run_id}_diagnostics.json"
                funnel = evidence_summary.get("funnel") if isinstance(evidence_summary, dict) else None
                diag_payload = {
                    "run_id": run_id,
                    "timestamp_utc": datetime.utcnow().isoformat() + "Z",
                    "success": False,
                    "error": str(e)[:500],
                    "evidence_summary": evidence_summary if isinstance(evidence_summary, dict) else None,
                    "funnel": funnel,
                    "candidates_total": funnel.get("combined") if isinstance(funnel, dict) else (len(candidates) if candidates else None),
                }
                diag_path.write_text(json.dumps(diag_payload, indent=2, default=str), encoding="utf-8")
            except Exception:
                pass
            run_bundle["status"] = "failed"
            run_bundle["error_message"] = f"Structural pipeline failed: {str(e)}"
            if isinstance(run_bundle.get("run_audit"), dict):
                run_bundle["run_audit"]["status"] = "failed"
                run_bundle["run_audit"]["error_message"] = (str(e))[:500]
            raise RunFailedError(f"Structural pipeline failed: {str(e)}")
    else:
        try:
            from core.intelligence_writer import write_report_from_evidence
            writer_output = write_report_from_evidence(
                spec=run_specification,
                candidates=candidates,
                lookback_date=lookback_date,
                reference_date=reference_date,
                run_id=run_id,
            )
        except Exception as e:
            try:
                from core.performance_logger import end_run, log_error
                log_error("synthesis", str(e)[:500])
                end_run("fail")
            except Exception:
                pass
            run_bundle["status"] = "failed"
            run_bundle["error_message"] = f"Report generation failed: {str(e)}"
            if isinstance(run_bundle.get("run_audit"), dict):
                run_bundle["run_audit"]["status"] = "failed"
                run_bundle["run_audit"]["error_message"] = (str(e))[:500]
            raise RunFailedError(f"Report generation failed: {str(e)}")

    # Use writer content as report body (evidence-only; no Assistant)
    report_content = writer_output["content"]
    coverage_low = writer_output.get("coverage_low", False)

    # Step 7: Persist Results — use Phase 5 HTML when available, else render from content
    display_cadence = cadence_override if cadence_override else None
    run_lookback = evidence_summary.get("lookback_date") if isinstance(evidence_summary, dict) else None
    run_reference = evidence_summary.get("reference_date") if isinstance(evidence_summary, dict) else None
    if writer_output.get("html"):
        html_content = writer_output["html"]
        diagnostics = {}
    else:
        html_content, diagnostics = _render_html_from_content(
            newsletter_name=spec.get("newsletter_name", "Newsletter"),
            report_content=report_content,
            spec=run_specification,
            metadata={
                "model": "v2_evidence_writer",
                "timestamp": datetime.utcnow().isoformat(),
                "extraction": extraction_result,
                "coverage_low": coverage_low,
            },
            user_email=user_email,
            cadence_override=display_cadence,
            lookback_date=run_lookback,
            reference_date=run_reference,
        )

    artifact_path = f"workspace/{workspace_id}/spec/{spec_id}/{datetime.utcnow().strftime('%Y%m%d')}/{run_id}.html"
    from core.app_version import get_deploy_version

    metadata_with_html = {
        "html_content": html_content,
        "model": "v2_evidence_writer",
        "timestamp": datetime.utcnow().isoformat(),
        "content_diagnostics": diagnostics,
        "evidence_summary": evidence_summary,
        "extraction_result": extraction_result,
        "signal_extraction_v2": signal_extraction_result,
        "signal_clustering_v2": signal_clustering_result,
        "signal_classification_v2": signal_classification_result,
        "doctrine_v2": doctrine_result,
        "coverage_low": coverage_low,
        "deploy_version": get_deploy_version(),
    }
    usage_meta = _build_run_usage_metadata(evidence_summary, writer_output)
    if usage_meta:
        metadata_with_html.update(usage_meta)
    else:
        metadata_with_html["tokens_used"] = 0
    if writer_output.get("final_quality_score") is not None:
        metadata_with_html["final_quality_score"] = writer_output["final_quality_score"]
    if writer_output.get("critique_issues") is not None:
        metadata_with_html["critique_issues"] = writer_output["critique_issues"]
    if writer_output.get("structural_diagnostics") is not None:
        metadata_with_html["structural_diagnostics"] = writer_output["structural_diagnostics"]
        # One diagnostic file per run (observability for testing; B1: include funnel and post-score fields)
        try:
            diag_dir = Path("development/outputs")
            diag_dir.mkdir(parents=True, exist_ok=True)
            diag_path = diag_dir / f"run_{run_id}_diagnostics.json"
            funnel = evidence_summary.get("funnel") if isinstance(evidence_summary, dict) else None
            structural_diag = writer_output.get("structural_diagnostics") or {}
            diag_payload = {
                "run_id": run_id,
                "timestamp_utc": datetime.utcnow().isoformat() + "Z",
                "evidence_summary": evidence_summary if isinstance(evidence_summary, dict) else None,
                "funnel": funnel,
                "candidates_total": funnel.get("combined") if isinstance(funnel, dict) else len(candidates),
                "structural_diagnostics": structural_diag,
                "kept_after_scoring": structural_diag.get("kept_after_scoring"),
                "kept_final": structural_diag.get("kept_final"),
            }
            diag_path.write_text(json.dumps(diag_payload, indent=2, default=str), encoding="utf-8")
        except Exception:
            pass
    metadata_with_html["regeneration_flag"] = writer_output.get("regeneration_flag", False)
    if report_content:
        metadata_with_html["report_content"] = report_content
    # Per-run audit: spec context, step counts, drop_reason_counts (counts only)
    base_days = run_specification.get("report_period_days")
    if isinstance(base_days, int) and base_days > 0:
        default_days = base_days
    else:
        default_days = get_lookback_days(run_specification.get("frequency", "monthly"))
    report_period_days = lookback_days_override if lookback_days_override is not None else default_days
    from core.run_audit import build_run_audit, persist_run_audit
    try:
        run_audit = build_run_audit(
            run_id=run_id,
            spec_id=spec_id,
            spec=run_specification,
            report_period_days=report_period_days,
            use_phase5_report=use_phase5_report,
            evidence_summary=evidence_summary,
            candidates_count=len(candidates),
            candidates_after_customer_filter=len(filtered_candidates),
            report_metrics=run_audit_metrics or {},
            customer_filter_drop_counts=customer_filter_drop_counts,
            workspace_id=workspace_id,
        )
        run_audit["status"] = "success"
    except Exception as e:
        # Minimal fallback audit so every successful run still has an audit record
        run_audit = {
            "run_id": run_id,
            "spec_id": spec_id,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "success",
            "error_message": f"audit_build_failed: {str(e)[:300]}",
        }
    metadata_with_html["run_audit"] = run_audit
    duration = None
    if isinstance(evidence_summary, dict):
        timing = evidence_summary.get("timing_seconds") or {}
        if isinstance(timing, dict) and timing.get("total") is not None:
            try:
                duration = float(timing["total"])
            except (TypeError, ValueError):
                pass
    categories_count = len(run_specification.get("categories") or [])
    regions_count = len(run_specification.get("regions") or [])
    links_count = (diagnostics or {}).get("items_included") if isinstance(diagnostics, dict) else None
    if links_count is None and isinstance(evidence_summary, dict):
        links_count = evidence_summary.get("inserted")

    # Run bundle: success path — finalize_run (in finally) will persist
    run_bundle["status"] = "success"
    run_bundle["html_output_path"] = artifact_path
    run_bundle["timing"] = evidence_summary.get("timing_seconds") if isinstance(evidence_summary, dict) else None
    run_bundle["run_audit"] = run_audit
    result_data = {
        "run_id": run_id,
        "html_content": html_content,
        "report_content": report_content,
        "metadata": metadata_with_html,
        "artifact_path": artifact_path
    }
    artifact_path_out = artifact_path

    try:
        from core.performance_logger import end_run
        ext_count = signal_extraction_result.get("signals_inserted")
        if ext_count is None and isinstance(extraction_result, dict):
            ext_count = extraction_result.get("signals_created")
        end_run(
            "success",
            candidate_articles_count=len(candidates),
            extracted_signals_count=ext_count if ext_count is not None else None,
            clusters_count_total=signal_clustering_result.get("clusters_created") if isinstance(signal_clustering_result, dict) else None,
            clusters_count_structural=None,
            doctrine_overrides_count=doctrine_result.get("resolved") if isinstance(doctrine_result, dict) else None,
            baseline_rows_updated_count=None,
            momentum_rows_updated_count=None,
            synthesis_reports_generated_count=1 if writer_output.get("content") else 0,
            critique_items_generated_count=len(writer_output.get("critique_issues") or []),
            regeneration_count=1 if writer_output.get("regeneration_flag") else 0,
        )
    except Exception:
        pass

    except RunFailedError:
        pass
    except Exception as e:
        run_bundle["status"] = "failed"
        run_bundle["error_message"] = str(e)
        if isinstance(run_bundle.get("run_audit"), dict):
            run_bundle["run_audit"]["status"] = "failed"
            run_bundle["run_audit"]["error_message"] = (str(e))[:500]
    finally:
        finalize_run(
            run_id,
            user_email,
            run_bundle,
            metadata=metadata_with_html,
            report_period_days=report_period_days,
            generation_duration_seconds=duration,
            categories_count=categories_count,
            regions_count=regions_count,
            links_count=links_count,
        )

    if run_bundle.get("status") == "success":
        return True, None, result_data, artifact_path_out
    return False, run_bundle.get("error_message") or "Run failed", None, None


# --- Phased execution for UI progress feedback (each phase can be run, then UI updates, then next phase) ---


def run_phase_evidence(
    spec_id: str,
    workspace_id: str,
    user_email: str,
    run_specification: Dict,
    cadence_override: Optional[str] = None,
    lookback_override: Optional[int] = None,
) -> Tuple[Optional[str], Optional[Dict], Optional[Dict], Optional[Dict], Optional[str]]:
    """
    Phase 1: Create run record and run evidence engine. Call from UI; then show "Found X items" and run next phase.
    Returns (run_id, evidence_summary, run_specification, spec, error_message).
    If error_message is set, other return values are None.
    """
    spec = get_specification_detail(spec_id)
    if not spec:
        return None, None, None, None, "Specification not found"
    if spec.get("status") != "active":
        return None, None, None, None, f"Specification is not active (status: {spec.get('status')})"

    frequency = spec.get("frequency", "monthly")
    if cadence_override:
        is_allowed, reason, next_date = True, None, None
    else:
        is_allowed, reason, next_date = check_frequency_enforcement(spec_id, frequency, user_email)
    if not is_allowed:
        return None, None, None, None, reason or "Cadence limit reached"

    run = create_newsletter_run(spec_id, workspace_id, user_email, "running", frequency=frequency)
    run_id = run["id"]

    ref_date = datetime.utcnow()
    is_builder = user_email and user_email.strip().lower() == BUILDER_EMAIL.lower()
    # Builder only: use chosen lookback with no fallback (any positive int). Others: spec or frequency only.
    lookback_days_override = (lookback_override if is_builder and isinstance(lookback_override, int) and lookback_override > 0 else None)
    base_days = run_specification.get("report_period_days")
    default_days = base_days if (isinstance(base_days, int) and base_days > 0) else get_lookback_days(frequency)
    report_period_days = lookback_days_override if lookback_days_override is not None else default_days
    run_specification["report_period_days"] = report_period_days
    try:
        from core.evidence_engine import run_evidence_engine
        evidence_summary = run_evidence_engine(
            run_id=run_id,
            workspace_id=workspace_id,
            specification_id=spec_id,
            spec=run_specification,
            validate_urls=True,
            cadence_override=cadence_override,
            reference_date=ref_date,
            report_period_days=run_specification["report_period_days"],
        )
    except Exception as ev_err:
        evidence_summary = {"error": str(ev_err), "inserted": 0, "query_plan": []}

    return run_id, evidence_summary, run_specification, spec, None


def run_phase_extract_and_write(
    run_id: str,
    workspace_id: str,
    spec_id: str,
    run_specification: Dict,
    cadence_override: Optional[str] = None,
    lookback_override: Optional[int] = None,
) -> Tuple[Dict, Dict]:
    """
    Phase 2: Get candidates, run extraction, run writer. Returns (writer_output, extraction_result).
    When lookback_override is set (builder only, 1/7/30 days), use it; else use spec frequency.
    Applies customer filter to candidates before extraction (plan §7–8: filter before clustering).
    """
    candidates = get_candidate_articles_for_run(run_id)
    try:
        from core.customer_filter import filter_candidates_by_spec
        candidates = filter_candidates_by_spec(candidates, run_specification)
    except Exception:
        pass
    ref_date = datetime.utcnow()
    # Use run_spec from Phase 1: builder already has chosen lookback there; others have spec/frequency.
    report_period_days = run_specification.get("report_period_days")
    if not (report_period_days and isinstance(report_period_days, int) and report_period_days > 0):
        report_period_days = get_lookback_days(run_specification.get("frequency", "monthly"))
    lookback_date, reference_date = get_lookback_from_days(report_period_days, ref_date)
    try:
        from core.intelligence_extraction import run_intelligence_extraction
        extraction_result = run_intelligence_extraction(
            run_id=run_id,
            workspace_id=workspace_id,
            specification_id=spec_id,
            candidates=candidates,
        )
    except Exception:
        extraction_result = {"signals_created": 0, "occurrences_created": 0}

    try:
        from core.signal_extraction_v2 import run_signal_extraction_v2
        signal_extraction_result = run_signal_extraction_v2(run_id=run_id, candidates=candidates)
    except Exception:
        signal_extraction_result = {"extracted_count": 0, "signals_inserted": 0, "articles_processed": 0}

    try:
        from core.signal_clustering_v2 import run_signal_clustering_v2
        signal_clustering_result = run_signal_clustering_v2(run_id=run_id)
    except Exception:
        signal_clustering_result = {"clusters_created": 0, "signals_grouped": 0}

    try:
        from core.signal_classification_v2 import run_signal_classification_v2
        signal_classification_result = run_signal_classification_v2(run_id=run_id)
    except Exception:
        signal_classification_result = {"classified": 0, "clusters_processed": 0, "failed": 0}

    try:
        from core.doctrine_resolver import run_doctrine_resolver_v2
        doctrine_result = run_doctrine_resolver_v2(run_id=run_id)
    except Exception:
        doctrine_result = {"resolved": 0, "clusters_processed": 0, "failed": 0}

    use_phase5_report = bool(
        _flag_from_secrets_or_env("USE_PHASE5_REPORT")
        or run_specification.get("use_phase5_report") is True
    )
    use_structural_pipeline = bool(
        os.getenv("USE_STRUCTURAL_PIPELINE", "").strip().lower() == "true"
        or run_specification.get("use_structural_pipeline") is True
    )

    if use_phase5_report:
        from core.query_planner import build_query_plan_map
        from core.intelligence_report import generate_report_from_signals
        from core.run_dates import get_lookback_days

        query_plan_map = build_query_plan_map(run_specification)
        signals = get_master_signals_for_run(run_id)

        # Determine effective report period in days for this run (used for reporting period label).
        base_days = (run_specification or {}).get("report_period_days")
        if isinstance(base_days, int) and base_days > 0:
            default_days = base_days
        else:
            default_days = get_lookback_days((run_specification or {}).get("frequency", "monthly"))
        if lookback_override in (1, 7, 30, 60, 90, 120, 150, 180):
            report_period_days = lookback_override
        else:
            report_period_days = default_days

        report_result = generate_report_from_signals(
            signals,
            query_plan_map,
            run_specification,
            write_metrics=False,
            write_html=True,
            report_period_days=report_period_days,
        )
        writer_output = {
            "content": report_result.get("report_text", ""),
            "coverage_low": False,
        }
        if report_result.get("html"):
            writer_output["html"] = report_result["html"]
    elif use_structural_pipeline:
        from core.structural_pipeline import run_structural_pipeline

        structural_output = run_structural_pipeline(
            run_id=run_id,
            spec=run_specification,
            candidates=candidates,
            lookback_date=lookback_date,
            reference_date=reference_date,
        )
        writer_output = {
            "content": structural_output.get("report_content", ""),
            "coverage_low": False,
            "structural_diagnostics": structural_output.get("diagnostics") or {},
        }
    else:
        from core.intelligence_writer import write_report_from_evidence

        writer_output = write_report_from_evidence(
            spec=run_specification,
            candidates=candidates,
            lookback_date=lookback_date,
            reference_date=reference_date,
            run_id=run_id,
        )

    return writer_output, extraction_result, signal_extraction_result, signal_clustering_result, signal_classification_result, doctrine_result


def run_phase_render_and_save(
    run_id: str,
    workspace_id: str,
    spec_id: str,
    user_email: str,
    spec: Dict,
    run_specification: Dict,
    writer_output: Dict,
    extraction_result: Dict,
    evidence_summary: Dict,
    signal_extraction_result: Optional[Dict] = None,
    signal_clustering_result: Optional[Dict] = None,
    signal_classification_result: Optional[Dict] = None,
    doctrine_result: Optional[Dict] = None,
    cadence_override: Optional[str] = None,
) -> Dict:
    """
    Phase 3: Render HTML, update run status, return result_data for UI.
    """
    report_content = writer_output["content"]
    coverage_low = writer_output.get("coverage_low", False)

    run_lookback = evidence_summary.get("lookback_date") if evidence_summary else None
    run_reference = evidence_summary.get("reference_date") if evidence_summary else None
    if writer_output.get("html"):
        html_content = writer_output["html"]
        diagnostics = {}
    else:
        html_content, diagnostics = _render_html_from_content(
            newsletter_name=spec.get("newsletter_name", "Newsletter"),
            report_content=report_content,
            spec=run_specification,
            metadata={
                "model": "v2_evidence_writer",
                "tokens_used": 0,
                "timestamp": datetime.utcnow().isoformat(),
                "extraction": extraction_result,
                "coverage_low": coverage_low,
            },
            user_email=user_email,
            cadence_override=cadence_override,
            lookback_date=run_lookback,
            reference_date=run_reference,
        )

    artifact_path = f"workspace/{workspace_id}/spec/{spec_id}/{datetime.utcnow().strftime('%Y%m%d')}/{run_id}.html"
    metadata_with_html = {
        "html_content": html_content,
        "model": "v2_evidence_writer",
        "timestamp": datetime.utcnow().isoformat(),
        "content_diagnostics": diagnostics,
        "evidence_summary": evidence_summary,
        "extraction_result": extraction_result,
        "coverage_low": coverage_low,
    }
    if signal_extraction_result is not None:
        metadata_with_html["signal_extraction_v2"] = signal_extraction_result
    if signal_clustering_result is not None:
        metadata_with_html["signal_clustering_v2"] = signal_clustering_result
    if signal_classification_result is not None:
        metadata_with_html["signal_classification_v2"] = signal_classification_result
    if doctrine_result is not None:
        metadata_with_html["doctrine_v2"] = doctrine_result
    usage_meta = _build_run_usage_metadata(evidence_summary, writer_output)
    if usage_meta:
        metadata_with_html.update(usage_meta)
    else:
        metadata_with_html["tokens_used"] = 0
    if writer_output.get("final_quality_score") is not None:
        metadata_with_html["final_quality_score"] = writer_output["final_quality_score"]
    if writer_output.get("critique_issues") is not None:
        metadata_with_html["critique_issues"] = writer_output["critique_issues"]
    metadata_with_html["regeneration_flag"] = writer_output.get("regeneration_flag", False)
    if report_content:
        metadata_with_html["report_content"] = report_content
    duration = None
    if isinstance(evidence_summary, dict):
        timing = evidence_summary.get("timing_seconds") or {}
        if isinstance(timing, dict) and timing.get("total") is not None:
            try:
                duration = float(timing["total"])
            except (TypeError, ValueError):
                pass
    categories_count = len(run_specification.get("categories") or [])
    regions_count = len(run_specification.get("regions") or [])
    links_count = (diagnostics or {}).get("items_included") if isinstance(diagnostics, dict) else None
    if links_count is None and isinstance(evidence_summary, dict):
        links_count = evidence_summary.get("inserted")

    # Build and persist run audit for phased runs as well (so Admin never sees "audit missing").
    from core.run_audit import build_run_audit, persist_run_audit
    # Reuse the same Phase5 flag logic as the main controller.
    use_phase5_report = bool(
        _flag_from_secrets_or_env("USE_PHASE5_REPORT")
        or run_specification.get("use_phase5_report") is True
    )
    base_days = run_specification.get("report_period_days")
    if isinstance(base_days, int) and base_days > 0:
        report_period_days = base_days
    else:
        report_period_days = get_lookback_days(run_specification.get("frequency", "monthly"))
    try:
        run_audit = build_run_audit(
            run_id=run_id,
            spec_id=spec_id,
            spec=run_specification,
            report_period_days=report_period_days,
            use_phase5_report=use_phase5_report,
            evidence_summary=evidence_summary if isinstance(evidence_summary, dict) else {},
            candidates_count=0,
            candidates_after_customer_filter=0,
            report_metrics={},
            customer_filter_drop_counts={},
            workspace_id=workspace_id,
        )
        run_audit["status"] = "success"
    except Exception as e:
        # Minimal fallback so even phased-success runs always have an audit record.
        run_audit = {
            "run_id": run_id,
            "spec_id": spec_id,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "success",
            "error_message": f"audit_build_failed: {str(e)[:300]}",
        }
    metadata_with_html["run_audit"] = run_audit
    try:
        persist_run_audit(run_id, user_email or "generator", run_audit)
    except Exception:
        # Do not block a successful run if audit_log insert fails; metadata still carries run_audit.
        pass

    update_run_status(
        run_id,
        "success",
        artifact_path,
        metadata=metadata_with_html,
        generation_duration_seconds=duration,
        categories_count=categories_count,
        regions_count=regions_count,
        links_count=links_count,
        report_period_days=report_period_days,
    )

    return {
        "run_id": run_id,
        "html_content": html_content,
        "report_content": report_content,
        "metadata": metadata_with_html,
        "artifact_path": artifact_path,
    }

