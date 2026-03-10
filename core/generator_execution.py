"""
Canonical Generator Execution Pattern.
Implements the 7-step execution flow as defined in the Generator Execution Pattern document.
"""

from typing import Dict, Optional, Tuple, List
from datetime import datetime
import json
import os
from pathlib import Path

from core.run_dates import get_lookback_from_cadence, get_lookback_from_days
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
    
    # Step 1: Retrieve Active Specification
    spec = get_specification_detail(spec_id)
    if not spec:
        return False, "Specification not found", None, None
    
    if spec.get("status") != "active":
        return False, f"Specification is not active (status: {spec.get('status')})", None, None
    
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
    
    # Step 4: Create run record (run_id must exist before evidence ingestion — V2-DB-02)
    run = create_newsletter_run(spec_id, workspace_id, user_email, "running", frequency=frequency)
    run_id = run["id"]

    try:
        from core.performance_logger import start_run, end_run, start_stage, end_stage, log_error
        start_run(run_id)
    except Exception:
        pass

    # V2: Run Evidence Engine — persist candidate_articles (date filter: builder can choose 1/7/30 or LOOKBACK_DAYS env; else spec)
    ref_date = datetime.utcnow()
    is_builder = user_email and user_email.strip().lower() == BUILDER_EMAIL.lower()
    lookback_days_override = (lookback_override if is_builder and isinstance(lookback_override, int) and lookback_override > 0 else None)
    try:
        from core.performance_logger import start_stage, end_stage, log_error
        start_stage("ingestion")
    except Exception:
        pass
    if os.environ.get("PHASE8_FORCE_FAIL") == "ingestion":
        try:
            from core.performance_logger import end_stage, log_error, end_run
            end_stage("ingestion", "fail", error_type="Phase8Validation", error_message="Phase 8 forced failure: ingestion")
            log_error("ingestion", "Phase 8 forced failure: ingestion")
            end_run("fail")
        except Exception:
            pass
        update_run_status(run_id, "failed", error_message="Phase 8 forced failure: ingestion")
        return False, "Phase 8 forced failure: ingestion", None, None
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
            lookback_days_override=lookback_days_override,
        )
        try:
            end_stage("ingestion", "success")
        except Exception:
            pass
    except Exception as ev_err:
        try:
            from core.performance_logger import end_stage, log_error
            end_stage("ingestion", "fail", error_type=type(ev_err).__name__, error_message=str(ev_err)[:500])
            log_error("ingestion", str(ev_err)[:500])
        except Exception:
            pass
        evidence_summary = {"error": str(ev_err), "inserted": 0, "query_plan": []}

    candidates = get_candidate_articles_for_run(run_id)
    if lookback_days_override is not None:
        lookback_date, reference_date = get_lookback_from_days(lookback_days_override, ref_date)
    else:
        lookback_date, reference_date = get_lookback_from_cadence(run_specification.get("frequency", "monthly"), ref_date)

    try:
        from core.performance_logger import start_stage, end_stage, log_error
        start_stage("extraction")
    except Exception:
        pass
    extraction_result = {"signals_created": 0, "occurrences_created": 0}
    signal_extraction_result = {"extracted_count": 0, "signals_inserted": 0, "articles_processed": 0}
    try:
        from core.customer_filter import filter_candidates_by_spec
        filtered_candidates = filter_candidates_by_spec(candidates, run_specification)

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
    try:
        from core.signal_clustering_v2 import run_signal_clustering_v2
        signal_clustering_result = run_signal_clustering_v2(run_id=run_id)
        try:
            from core.performance_logger import end_stage
            end_stage("clustering", "success")
        except Exception:
            pass
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
                write_html=False,
            )
            writer_output = {
                "content": report_result.get("report_text", ""),
                "coverage_low": False,
            }
        except Exception as e:
            try:
                from core.performance_logger import end_run, log_error
                log_error("synthesis", str(e)[:500])
                end_run("fail")
            except Exception:
                pass
            update_run_status(run_id, "failed", error_message=str(e))
            return False, f"Phase 5 report failed: {str(e)}", None, None
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
            update_run_status(run_id, "failed", error_message=str(e))
            return False, f"Structural pipeline failed: {str(e)}", None, None
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
            update_run_status(run_id, "failed", error_message=str(e))
            return False, f"Report generation failed: {str(e)}", None, None

    # Use writer content as report body (evidence-only; no Assistant)
    report_content = writer_output["content"]
    coverage_low = writer_output.get("coverage_low", False)

    # Step 7: Persist Results — render writer output to HTML (same pipeline as before)
    display_cadence = cadence_override if cadence_override else None
    run_lookback = evidence_summary.get("lookback_date") if isinstance(evidence_summary, dict) else None
    run_reference = evidence_summary.get("reference_date") if isinstance(evidence_summary, dict) else None
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
    update_run_status(
        run_id, "success", artifact_path, metadata=metadata_with_html,
        generation_duration_seconds=duration,
        categories_count=categories_count, regions_count=regions_count, links_count=links_count,
    )

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

    result_data = {
        "run_id": run_id,
        "html_content": html_content,
        "report_content": report_content,
        "metadata": metadata_with_html,
        "artifact_path": artifact_path
    }

    return True, None, result_data, artifact_path


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
    # Phase 1 protocol: allow 60 and 90 day lookback for builder (controlled live runs)
    lookback_days_override = (lookback_override if is_builder and lookback_override in (1, 7, 30, 60, 90) else None)
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
            lookback_days_override=lookback_days_override,
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
    """
    candidates = get_candidate_articles_for_run(run_id)
    ref_date = datetime.utcnow()
    if lookback_override in (1, 7, 30, 60, 90):
        lookback_date, reference_date = get_lookback_from_days(lookback_override, ref_date)
    else:
        lookback_date, reference_date = get_lookback_from_cadence(run_specification.get("frequency", "monthly"), ref_date)
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
        os.getenv("USE_PHASE5_REPORT", "").strip().lower() == "true"
        or run_specification.get("use_phase5_report") is True
    )
    use_structural_pipeline = bool(
        os.getenv("USE_STRUCTURAL_PIPELINE", "").strip().lower() == "true"
        or run_specification.get("use_structural_pipeline") is True
    )

    if use_phase5_report:
        from core.query_planner import build_query_plan_map
        from core.intelligence_report import generate_report_from_signals

        query_plan_map = build_query_plan_map(run_specification)
        signals = get_master_signals_for_run(run_id)
        report_result = generate_report_from_signals(
            signals,
            query_plan_map,
            run_specification,
            write_metrics=False,
            write_html=False,
        )
        writer_output = {
            "content": report_result.get("report_text", ""),
            "coverage_low": False,
        }
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
    update_run_status(
        run_id, "success", artifact_path, metadata=metadata_with_html,
        generation_duration_seconds=duration,
        categories_count=categories_count, regions_count=regions_count, links_count=links_count,
    )

    return {
        "run_id": run_id,
        "html_content": html_content,
        "report_content": report_content,
        "metadata": metadata_with_html,
        "artifact_path": artifact_path,
    }

