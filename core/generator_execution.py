"""
Canonical Generator Execution Pattern.
Implements the 7-step execution flow as defined in the Generator Execution Pattern document.
"""

from typing import Dict, Optional, Tuple, List
from datetime import datetime
import json

from core.run_dates import get_lookback_from_cadence, get_lookback_from_days
from core.generator_db import (
    get_specification_detail,
    check_frequency_enforcement,
    create_newsletter_run,
    update_run_status,
    get_candidate_articles_for_run,
)
from core.content_pipeline import render_html_from_content

# Builder-only: can set lookback to 1/7/30 days and run without frequency limit
BUILDER_EMAIL = "stefan.hermes@htcglobal.asia"


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
    run = create_newsletter_run(spec_id, workspace_id, user_email, "running")
    run_id = run["id"]

    # V2: Run Evidence Engine — persist candidate_articles (date filter: builder can choose 1/7/30 days; else spec)
    ref_date = datetime.utcnow()
    is_builder = user_email and user_email.strip().lower() == BUILDER_EMAIL.lower()
    lookback_days_override = (lookback_override if is_builder and lookback_override in (1, 7, 30) else None)
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

    candidates = get_candidate_articles_for_run(run_id)
    if lookback_days_override is not None:
        lookback_date, reference_date = get_lookback_from_days(lookback_days_override, ref_date)
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
    except Exception as ext_err:
        extraction_result = {"signals_created": 0, "occurrences_created": 0}

    try:
        from core.intelligence_writer import write_report_from_evidence
        writer_output = write_report_from_evidence(
            spec=run_specification,
            candidates=candidates,
            lookback_date=lookback_date,
            reference_date=reference_date,
        )
    except Exception as e:
        update_run_status(run_id, "failed", error_message=str(e))
        return False, f"Report generation failed: {str(e)}", None, None

    # Use writer content as report body (evidence-only; no Assistant)
    report_content = writer_output["content"]
    coverage_low = writer_output.get("coverage_low", False)

    # Step 7: Persist Results — render writer output to HTML (same pipeline as before)
    display_cadence = cadence_override if cadence_override else None
    html_content, diagnostics = render_html_from_content(
        newsletter_name=spec.get("newsletter_name", "Newsletter"),
        assistant_content=report_content,
        spec=run_specification,
        metadata={
            "model": "v2_evidence_writer",
            "tokens_used": 0,
            "timestamp": datetime.utcnow().isoformat(),
            "extraction": extraction_result,
            "coverage_low": coverage_low,
        },
        user_email=user_email,
        cadence_override=display_cadence
    )

    artifact_path = f"workspace/{workspace_id}/spec/{spec_id}/{datetime.utcnow().strftime('%Y%m%d')}/{run_id}.html"
    metadata_with_html = {
        "html_content": html_content,
        "model": "v2_evidence_writer",
        "tokens_used": 0,
        "timestamp": datetime.utcnow().isoformat(),
        "content_diagnostics": diagnostics,
        "evidence_summary": evidence_summary,
        "extraction_result": extraction_result,
        "coverage_low": coverage_low,
    }

    update_run_status(run_id, "success", artifact_path, metadata=metadata_with_html)

    result_data = {
        "run_id": run_id,
        "html_content": html_content,
        "assistant_output": report_content,
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

    run = create_newsletter_run(spec_id, workspace_id, user_email, "running")
    run_id = run["id"]

    ref_date = datetime.utcnow()
    is_builder = user_email and user_email.strip().lower() == BUILDER_EMAIL.lower()
    lookback_days_override = (lookback_override if is_builder and lookback_override in (1, 7, 30) else None)
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
    if lookback_override in (1, 7, 30):
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

    from core.intelligence_writer import write_report_from_evidence
    writer_output = write_report_from_evidence(
        spec=run_specification,
        candidates=candidates,
        lookback_date=lookback_date,
        reference_date=reference_date,
    )
    return writer_output, extraction_result


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
    cadence_override: Optional[str] = None,
) -> Dict:
    """
    Phase 3: Render HTML, update run status, return result_data for UI.
    """
    report_content = writer_output["content"]
    coverage_low = writer_output.get("coverage_low", False)

    run_lookback = evidence_summary.get("lookback_date") if evidence_summary else None
    run_reference = evidence_summary.get("reference_date") if evidence_summary else None
    html_content, diagnostics = render_html_from_content(
        newsletter_name=spec.get("newsletter_name", "Newsletter"),
        assistant_content=report_content,
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
        "tokens_used": 0,
        "timestamp": datetime.utcnow().isoformat(),
        "content_diagnostics": diagnostics,
        "evidence_summary": evidence_summary,
        "extraction_result": extraction_result,
        "coverage_low": coverage_low,
    }
    update_run_status(run_id, "success", artifact_path, metadata=metadata_with_html)

    return {
        "run_id": run_id,
        "html_content": html_content,
        "assistant_output": report_content,
        "metadata": metadata_with_html,
        "artifact_path": artifact_path,
    }

