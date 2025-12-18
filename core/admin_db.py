"""
Database operations for Admin app.
Handles specification requests, workspaces, users, and audit logs.
"""

import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False


def get_supabase_client() -> object:
    """Initialize and return Supabase client. Raises exception if not configured."""
    if not SUPABASE_AVAILABLE:
        raise Exception("supabase-py library is not installed. Install with: pip install supabase")
    
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_ANON_KEY")
    
    if not supabase_url or not supabase_key:
        raise Exception("Supabase is not configured. Set SUPABASE_URL and SUPABASE_ANON_KEY in your .env file.")
    
    try:
        client = create_client(supabase_url, supabase_key)
        # Test connection by trying to access a table
        client.table("specification_requests").select("id").limit(1).execute()
        return client
    except Exception as e:
        raise Exception(f"Failed to connect to Supabase: {str(e)}. Check your credentials and database connection.")


def get_pending_specification_requests() -> List[Dict]:
    """Get all pending specification requests."""
    supabase = get_supabase_client()
    result = supabase.table("specification_requests")\
        .select("*")\
        .eq("status", "pending_review")\
        .order("submission_timestamp", desc=True)\
        .execute()
    return result.data if result.data else []


def get_all_specification_requests() -> List[Dict]:
    """Get all specification requests regardless of status."""
    supabase = get_supabase_client()
    result = supabase.table("specification_requests")\
        .select("*")\
        .order("submission_timestamp", desc=True)\
        .execute()
    return result.data if result.data else []


def update_specification_request_status(request_id: str, status: str, notes: Optional[str] = None):
    """Update specification request status."""
    supabase = get_supabase_client()
    
    update_data = {
        "status": status,
        "updated_at": datetime.utcnow().isoformat()
    }
    
    if notes:
        update_data["admin_notes"] = notes
    
    result = supabase.table("specification_requests")\
        .update(update_data)\
        .eq("id", request_id)\
        .execute()
    
    if result.data:
        return result.data[0]
    return None


def get_all_workspaces() -> List[Dict]:
    """Get all workspaces."""
    supabase = get_supabase_client()
    result = supabase.table("workspaces").select("*").order("created_at", desc=True).execute()
    return result.data if result.data else []


def create_workspace(name: str, company_name: str, contact_email: str) -> Dict:
    """Create a new workspace."""
    supabase = get_supabase_client()
    workspace_data = {
        "name": name,
        "company_name": company_name,
        "contact_email": contact_email,
        "created_at": datetime.utcnow().isoformat()
    }
    result = supabase.table("workspaces").insert(workspace_data).execute()
    return result.data[0] if result.data else workspace_data


def update_workspace(workspace_id: str, name: Optional[str] = None, company_name: Optional[str] = None, contact_email: Optional[str] = None) -> Dict:
    """Update workspace details."""
    supabase = get_supabase_client()
    update_data = {
        "updated_at": datetime.utcnow().isoformat()
    }
    
    if name:
        update_data["name"] = name
    if company_name:
        update_data["company_name"] = company_name
    if contact_email:
        update_data["contact_email"] = contact_email
    
    result = supabase.table("workspaces")\
        .update(update_data)\
        .eq("id", workspace_id)\
        .execute()
    return result.data[0] if result.data else update_data


def assign_request_to_workspace(request_id: str, workspace_id: str) -> bool:
    """Assign a specification request to a workspace (creates the specification)."""
    supabase = get_supabase_client()
    
    # Get the request
    req_result = supabase.table("specification_requests")\
        .select("*")\
        .eq("id", request_id)\
        .execute()
    
    if not req_result.data:
        return False
    
    req = req_result.data[0]
    
    # Create the specification from the request
    spec_data = {
        "workspace_id": workspace_id,
        "newsletter_name": req.get("newsletter_name"),
        "industry_code": req.get("industry_code", "PU"),
        "categories": req.get("categories"),
        "regions": req.get("regions"),
        "frequency": req.get("frequency"),
        "status": "active",
        "created_at": datetime.utcnow().isoformat(),
        "created_by": "admin"
    }
    
    supabase.table("newsletter_specifications").insert(spec_data).execute()
    
    # Update request status
    supabase.table("specification_requests")\
        .update({"status": "paid_activated", "updated_at": datetime.utcnow().isoformat()})\
        .eq("id", request_id)\
        .execute()
    
    return True


def update_specification(spec_id: str, newsletter_name: Optional[str] = None, categories: Optional[List] = None, 
                         regions: Optional[List] = None, frequency: Optional[str] = None) -> Dict:
    """Update a specification's details."""
    supabase = get_supabase_client()
    
    update_data = {
        "updated_at": datetime.utcnow().isoformat()
    }
    
    if newsletter_name:
        update_data["newsletter_name"] = newsletter_name
    if categories is not None:
        update_data["categories"] = categories
    if regions is not None:
        update_data["regions"] = regions
    if frequency:
        update_data["frequency"] = frequency
    
    result = supabase.table("newsletter_specifications")\
        .update(update_data)\
        .eq("id", spec_id)\
        .execute()
    return result.data[0] if result.data else update_data


def get_newsletter_specifications(workspace_id: Optional[str] = None) -> List[Dict]:
    """Get all newsletter specifications, optionally filtered by workspace."""
    supabase = get_supabase_client()
    query = supabase.table("newsletter_specifications").select("*")
    if workspace_id:
        query = query.eq("workspace_id", workspace_id)
    result = query.order("created_at", desc=True).execute()
    return result.data if result.data else []


def update_specification_status(spec_id: str, status: str, reason: Optional[str] = None):
    """Update newsletter specification status (activate/pause)."""
    supabase = get_supabase_client()
    
    update_data = {
        "status": status,
        "updated_at": datetime.utcnow().isoformat()
    }
    
    if reason:
        update_data["status_change_reason"] = reason
    
    result = supabase.table("newsletter_specifications")\
        .update(update_data)\
        .eq("id", spec_id)\
        .execute()
    return result.data[0] if result.data else None


def override_frequency_limit(spec_id: str, reason: str) -> Dict:
    """Override frequency limit for a specification."""
    supabase = get_supabase_client()
    
    override_data = {
        "frequency_override": True,
        "override_reason": reason,
        "override_timestamp": datetime.utcnow().isoformat()
    }
    
    result = supabase.table("newsletter_specifications")\
        .update(override_data)\
        .eq("id", spec_id)\
        .execute()
    return result.data[0] if result.data else override_data


def get_recent_runs(limit: int = 10) -> List[Dict]:
    """Get recent newsletter generation runs with specification names."""
    supabase = get_supabase_client()
    result = supabase.table("newsletter_runs")\
        .select("*, newsletter_specifications(newsletter_name)")\
        .order("created_at", desc=True)\
        .limit(limit)\
        .execute()
    
    runs = result.data if result.data else []
    # Flatten the nested specification name
    for run in runs:
        if run.get("newsletter_specifications"):
            spec = run["newsletter_specifications"]
            if isinstance(spec, list) and len(spec) > 0:
                run["newsletter_name"] = spec[0].get("newsletter_name", "Unknown")
            elif isinstance(spec, dict):
                run["newsletter_name"] = spec.get("newsletter_name", "Unknown")
    
    return runs


def get_audit_logs(limit: int = 50) -> List[Dict]:
    """Get audit log entries."""
    supabase = get_supabase_client()
    result = supabase.table("audit_log")\
        .select("*")\
        .order("created_at", desc=True)\
        .limit(limit)\
        .execute()
    return result.data if result.data else []


def log_audit_action(action: str, user_email: str, details: Dict, reason: Optional[str] = None):
    """Log an audit action."""
    supabase = get_supabase_client()
    
    # Determine target_type and target_id from details if available
    target_type = None
    target_id = None
    if details:
        if "request_id" in details:
            target_type = "specification_request"
            target_id = details.get("request_id")
        elif "workspace_id" in details:
            target_type = "workspace"
            target_id = details.get("workspace_id")
        elif "spec_id" in details:
            target_type = "specification"
            target_id = details.get("spec_id")
    
    # Include reason in details if provided
    details_with_reason = details.copy() if details else {}
    if reason:
        details_with_reason["reason"] = reason
    
    log_entry = {
        "action_type": action,
        "actor_email": user_email,
        "target_type": target_type,
        "target_id": target_id,
        "details": details_with_reason  # JSONB field - pass as dict, Supabase will convert
    }
    
    supabase.table("audit_log").insert(log_entry).execute()

