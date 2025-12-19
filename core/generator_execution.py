"""
Canonical Generator Execution Pattern.
Implements the 7-step execution flow as defined in the Generator Execution Pattern document.
"""

from typing import Dict, Optional, Tuple, List
from datetime import datetime
import json

from core.generator_db import (
    get_specification_detail,
    check_frequency_enforcement,
    create_newsletter_run,
    update_run_status,
    get_last_successful_run,
    get_specification_history
)
from core.openai_assistant import (
    build_run_package,
    execute_assistant,
    validate_output
)
from core.content_pipeline import render_html_from_content


def execute_generator(
    spec_id: str,
    workspace_id: str,
    user_email: str,
    cadence_override: Optional[str] = None,
    categories_override: Optional[List[str]] = None,
    regions_override: Optional[List[str]] = None
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
    
    # Step 3: Assemble Run Package
    # Get historical reference (last successful run for context)
    last_run = get_last_successful_run(spec_id)
    historical_reference = None
    if last_run:
        historical_reference = [f"Last run: {last_run.get('created_at', '')[:10]}"]
    
    # Use override cadence if provided, otherwise use specification frequency
    cadence_for_package = cadence_override if cadence_override else frequency
    
    # Create a modified specification with overridden categories/regions if provided
    run_specification = spec.copy()
    if categories_override:
        run_specification["categories"] = categories_override
    if regions_override:
        run_specification["regions"] = regions_override
    
    run_package = build_run_package(
        specification=run_specification,
        cadence=cadence_for_package,
        historical_reference=historical_reference
    )
    
    # Step 4: Execute Assistant
    # Create run record with "running" status
    run = create_newsletter_run(spec_id, workspace_id, user_email, "running")
    run_id = run["id"]
    
    try:
        assistant_output = execute_assistant(run_package)
    except Exception as e:
        # Update run status to failed
        update_run_status(run_id, "failed", error_message=str(e))
        return False, f"Assistant execution failed: {str(e)}", None, None
    
    # Step 5: Validate Output
    is_valid, validation_errors = validate_output(assistant_output, spec)
    
    if not is_valid:
        error_msg = f"Output validation failed: {', '.join(validation_errors)}"
        update_run_status(run_id, "failed", error_message=error_msg)
        # Failed runs do not consume cadence quota
        return False, error_msg, None, None
    
    # Step 6: Persist Results
    # Convert Assistant output to HTML
    # Use override cadence if provided for display purposes
    display_cadence = cadence_override if cadence_override else None
    # Use run_specification (with overrides) for HTML rendering
    html_content = render_html_from_content(
        newsletter_name=spec.get("newsletter_name", "Newsletter"),
        assistant_content=assistant_output["content"],
        spec=run_specification,  # Use the modified specification with overrides
        metadata=assistant_output.get("metadata", {}),
        user_email=user_email,
        cadence_override=display_cadence
    )
    
    # Store artifact path (in production, upload to Supabase Storage)
    artifact_path = f"workspace/{workspace_id}/spec/{spec_id}/{datetime.utcnow().strftime('%Y%m%d')}/{run_id}.html"
    
    # Store HTML content in metadata for later retrieval (History page)
    # Include all metadata from assistant_output, including tool_usage tracking
    assistant_metadata = assistant_output.get("metadata", {})
    metadata_with_html = {
        "html_content": html_content,
        "model": assistant_metadata.get("model"),
        "tokens_used": assistant_metadata.get("tokens_used"),
        "thread_id": assistant_metadata.get("thread_id"),
        "run_id": assistant_metadata.get("run_id"),
        "timestamp": assistant_metadata.get("timestamp"),
        "tool_usage": assistant_metadata.get("tool_usage", {})  # Include vector store usage tracking
    }
    
    # Update run status to success with HTML stored in metadata
    update_run_status(run_id, "success", artifact_path, metadata=metadata_with_html)
    
    # Step 7: Return Result to User
    result_data = {
        "run_id": run_id,
        "html_content": html_content,
        "assistant_output": assistant_output["content"],
        "metadata": assistant_output.get("metadata", {}),
        "artifact_path": artifact_path
    }
    
    return True, None, result_data, artifact_path

