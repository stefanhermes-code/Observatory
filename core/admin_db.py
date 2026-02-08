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
    
    # Try Streamlit secrets first (for Streamlit Cloud), then environment variables (for local .env)
    try:
        import streamlit as st
        supabase_url = st.secrets.get("SUPABASE_URL") or os.getenv("SUPABASE_URL")
        supabase_key = st.secrets.get("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_ANON_KEY")
    except (AttributeError, FileNotFoundError, RuntimeError):
        # Not running in Streamlit or secrets not available, use environment variables
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_ANON_KEY")
    
    if not supabase_url or not supabase_key:
        raise Exception("Supabase is not configured. Set SUPABASE_URL and SUPABASE_ANON_KEY in Streamlit Cloud secrets or .env file.")
    
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
        "value_chain_links": req.get("value_chain_links", []),  # Include value chain links if present
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
                         regions: Optional[List] = None, frequency: Optional[str] = None, 
                         value_chain_links: Optional[List] = None) -> Dict:
    """Update a specification's details."""
    supabase = get_supabase_client()
    
    update_data = {}
    # Only include updated_at if the column exists (some schemas may not have it)
    # We'll try to include it, but if it fails, we'll retry without it
    
    if newsletter_name:
        update_data["newsletter_name"] = newsletter_name
    if categories is not None:
        update_data["categories"] = categories
    if regions is not None:
        update_data["regions"] = regions
    if frequency:
        update_data["frequency"] = frequency
    
    if newsletter_name:
        update_data["newsletter_name"] = newsletter_name
    if categories is not None:
        update_data["categories"] = categories
    if regions is not None:
        update_data["regions"] = regions
    if frequency:
        update_data["frequency"] = frequency
    if value_chain_links is not None:
        update_data["value_chain_links"] = value_chain_links
    
    # Try to update - handle missing columns gracefully
    try:
        # First attempt: include updated_at if possible
        update_data_with_timestamp = update_data.copy()
        update_data_with_timestamp["updated_at"] = datetime.utcnow().isoformat()
        result = supabase.table("newsletter_specifications")\
            .update(update_data_with_timestamp)\
            .eq("id", spec_id)\
            .execute()
        return result.data[0] if result.data else update_data_with_timestamp
    except Exception as e:
        error_msg = str(e).lower()
        # If updated_at column doesn't exist, retry without it
        if "updated_at" in error_msg or "pgrst204" in error_msg:
            try:
                # Retry without updated_at
                result = supabase.table("newsletter_specifications")\
                    .update(update_data)\
                    .eq("id", spec_id)\
                    .execute()
                return result.data[0] if result.data else update_data
            except Exception as e2:
                error_msg2 = str(e2).lower()
                # If value_chain_links column doesn't exist, retry without it
                if "value_chain_links" in error_msg2 or ("column" in error_msg2 and "value_chain_links" in error_msg2):
                    update_data_without_vcl = {k: v for k, v in update_data.items() if k != "value_chain_links"}
                    result = supabase.table("newsletter_specifications")\
                        .update(update_data_without_vcl)\
                        .eq("id", spec_id)\
                        .execute()
                    return result.data[0] if result.data else update_data_without_vcl
                else:
                    # Different error - re-raise it
                    raise
        # If value_chain_links column doesn't exist, retry without it
        elif "value_chain_links" in error_msg or ("column" in error_msg and "value_chain_links" in error_msg):
            update_data_without_vcl = {k: v for k, v in update_data.items() if k != "value_chain_links"}
            try:
                result = supabase.table("newsletter_specifications")\
                    .update(update_data_without_vcl)\
                    .eq("id", spec_id)\
                    .execute()
                return result.data[0] if result.data else update_data_without_vcl
            except Exception as e2:
                # Still failing - re-raise
                raise
        else:
            # Different error - re-raise it
            raise


def get_newsletter_specifications(workspace_id: Optional[str] = None) -> List[Dict]:
    """Get all newsletter specifications, optionally filtered by workspace."""
    supabase = get_supabase_client()
    query = supabase.table("newsletter_specifications").select("*")
    if workspace_id:
        query = query.eq("workspace_id", workspace_id)
    result = query.order("created_at", desc=True).execute()
    return result.data if result.data else []


def update_specification_status(spec_id: str, status: str, reason: Optional[str] = None):
    """Update newsletter specification status (activate/pause).
    Tries full update first (status, updated_at, status_change_reason); on any API error,
    retries with only status so it works even if optional columns are missing.
    """
    supabase = get_supabase_client()
    
    update_data = {
        "status": status,
        "updated_at": datetime.utcnow().isoformat()
    }
    if reason:
        update_data["status_change_reason"] = reason
    
    try:
        result = supabase.table("newsletter_specifications")\
            .update(update_data)\
            .eq("id", spec_id)\
            .execute()
        return result.data[0] if result.data else None
    except Exception:
        # On any failure (e.g. missing updated_at or status_change_reason), retry with only status
        try:
            result = supabase.table("newsletter_specifications")\
                .update({"status": status})\
                .eq("id", spec_id)\
                .execute()
            return result.data[0] if result.data else None
        except Exception:
            raise


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
    
    try:
        # Try nested select first (more efficient)
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
                del run["newsletter_specifications"]
        
        return runs
    except Exception as e:
        # Fallback: Get runs and specs separately, then join manually
        try:
            # Get runs
            runs_result = supabase.table("newsletter_runs")\
                .select("*")\
                .order("created_at", desc=True)\
                .limit(limit)\
                .execute()
            
            runs = runs_result.data if runs_result.data else []
            
            if not runs:
                return []
            
            # Get all specification IDs
            spec_ids = [run.get("specification_id") for run in runs if run.get("specification_id")]
            
            if spec_ids:
                # Get specifications
                specs_result = supabase.table("newsletter_specifications")\
                    .select("id, newsletter_name")\
                    .in_("id", spec_ids)\
                    .execute()
                
                specs_dict = {spec["id"]: spec.get("newsletter_name", "Unknown") for spec in (specs_result.data if specs_result.data else [])}
                
                # Add newsletter_name to each run
                for run in runs:
                    spec_id = run.get("specification_id")
                    run["newsletter_name"] = specs_dict.get(spec_id, "Unknown")
            
            return runs
        except Exception as fallback_error:
            # If even fallback fails, return empty list
            return []


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


# ---------- V2 Source Registry (global, admin-only) ----------

def get_all_sources() -> List[Dict]:
    """Get all sources (global registry). workspace_id must be NULL."""
    supabase = get_supabase_client()
    try:
        result = supabase.table("sources").select("*").order("source_name").execute()
        return result.data if result.data else []
    except Exception as e:
        # Table may not exist yet if migration not applied
        if "does not exist" in str(e).lower() or "sources" in str(e).lower():
            return []
        raise


def get_source_by_id(source_id: str) -> Optional[Dict]:
    """Get a single source by id."""
    supabase = get_supabase_client()
    result = supabase.table("sources").select("*").eq("id", source_id).single().execute()
    return result.data if result.data else None


def create_source(
    source_name: str,
    source_type: str,
    base_url: str,
    rss_url: Optional[str] = None,
    sitemap_url: Optional[str] = None,
    list_url: Optional[str] = None,
    selectors: Optional[Dict] = None,
    trust_tier: int = 2,
    enabled: bool = True,
    notes: Optional[str] = None,
) -> Dict:
    """Create a new source. workspace_id is forced to NULL (global)."""
    supabase = get_supabase_client()
    row = {
        "workspace_id": None,
        "source_name": source_name,
        "source_type": source_type,
        "base_url": base_url,
        "rss_url": rss_url,
        "sitemap_url": sitemap_url,
        "list_url": list_url,
        "selectors": selectors,
        "trust_tier": max(1, min(4, trust_tier)),
        "enabled": enabled,
        "notes": notes,
        "updated_at": datetime.utcnow().isoformat(),
    }
    result = supabase.table("sources").insert(row).execute()
    return result.data[0] if result.data else row


def update_source(
    source_id: str,
    source_name: Optional[str] = None,
    source_type: Optional[str] = None,
    base_url: Optional[str] = None,
    rss_url: Optional[str] = None,
    sitemap_url: Optional[str] = None,
    list_url: Optional[str] = None,
    selectors: Optional[Dict] = None,
    trust_tier: Optional[int] = None,
    enabled: Optional[bool] = None,
    notes: Optional[str] = None,
) -> Optional[Dict]:
    """Update a source."""
    supabase = get_supabase_client()
    update_data = {"updated_at": datetime.utcnow().isoformat()}
    if source_name is not None:
        update_data["source_name"] = source_name
    if source_type is not None:
        update_data["source_type"] = source_type
    if base_url is not None:
        update_data["base_url"] = base_url
    if rss_url is not None:
        update_data["rss_url"] = rss_url
    if sitemap_url is not None:
        update_data["sitemap_url"] = sitemap_url
    if list_url is not None:
        update_data["list_url"] = list_url
    if selectors is not None:
        update_data["selectors"] = selectors
    if trust_tier is not None:
        update_data["trust_tier"] = max(1, min(4, trust_tier))
    if enabled is not None:
        update_data["enabled"] = enabled
    if notes is not None:
        update_data["notes"] = notes
    result = supabase.table("sources").update(update_data).eq("id", source_id).execute()
    return result.data[0] if result.data else None


def delete_source(source_id: str) -> bool:
    """Delete a source."""
    supabase = get_supabase_client()
    try:
        supabase.table("sources").delete().eq("id", source_id).execute()
        return True
    except Exception:
        return False


# ---------- Tracked companies (PU industry list for evidence / query planning) ----------

def get_tracked_companies(active_only: bool = True) -> List[Dict]:
    """Get tracked companies from DB. If active_only, only status='active'."""
    supabase = get_supabase_client()
    try:
        query = supabase.table("tracked_companies").select("*").order("name")
        if active_only:
            query = query.eq("status", "active")
        result = query.execute()
        return result.data if result.data else []
    except Exception as e:
        if "does not exist" in str(e).lower() or "tracked_companies" in str(e).lower():
            return []
        raise


def seed_tracked_companies_from_list(companies: List[Dict]) -> int:
    """
    Upsert companies into tracked_companies from a list of dicts (e.g. from company_list.json).
    Each dict: name, aliases (list), value_chain_position (list), regions (list), status, notes.
    Returns number of rows upserted.
    """
    if not companies:
        return 0
    supabase = get_supabase_client()
    now = datetime.utcnow().isoformat()
    rows = []
    for c in companies:
        name = (c.get("name") or "").strip()
        if not name:
            continue
        status = (c.get("status") or "active").lower()
        if status not in ("active", "inactive"):
            status = "active"
        rows.append({
            "name": name,
            "aliases": c.get("aliases") if isinstance(c.get("aliases"), list) else [],
            "value_chain_position": c.get("value_chain_position") if isinstance(c.get("value_chain_position"), list) else [],
            "regions": c.get("regions") if isinstance(c.get("regions"), list) else [],
            "status": status,
            "notes": (c.get("notes") or "") or None,
            "updated_at": now,
        })
    if not rows:
        return 0
    try:
        supabase.table("tracked_companies").upsert(rows, on_conflict="name").execute()
        return len(rows)
    except Exception:
        return 0

