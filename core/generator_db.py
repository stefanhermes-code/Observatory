"""
Database operations for Generator app.
Handles newsletter generation, frequency enforcement, and history.
"""

import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import json
from dotenv import load_dotenv

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
        # Test connection
        client.table("newsletter_specifications").select("id").limit(1).execute()
        return client
    except Exception as e:
        raise Exception(f"Failed to connect to Supabase: {str(e)}. Check your credentials and database connection.")


def get_user_workspaces(user_email: str) -> List[Dict]:
    """Get all workspaces the user belongs to."""
    supabase = get_supabase_client()
    
    # Get user's workspace memberships
    result = supabase.table("workspace_members")\
        .select("workspace_id, workspaces(*)")\
        .eq("user_email", user_email)\
        .execute()
    
    workspaces = []
    if result.data:
        for membership in result.data:
            if membership.get("workspaces"):
                workspaces.append(membership["workspaces"])
    return workspaces


def get_workspace_specifications(workspace_id: str) -> List[Dict]:
    """Get all active newsletter specifications for a workspace."""
    supabase = get_supabase_client()
    result = supabase.table("newsletter_specifications")\
        .select("*")\
        .eq("workspace_id", workspace_id)\
        .eq("status", "active")\
        .execute()
    return result.data if result.data else []


def get_specification_detail(spec_id: str) -> Optional[Dict]:
    """Get detailed specification information."""
    supabase = get_supabase_client()
    result = supabase.table("newsletter_specifications")\
        .select("*")\
        .eq("id", spec_id)\
        .single()\
        .execute()
    return result.data if result.data else None


def check_frequency_enforcement(spec_id: str, frequency: str, user_email: Optional[str] = None) -> tuple[bool, Optional[str], Optional[datetime]]:
    """
    Check if generation is allowed based on frequency limits.
    Returns: (is_allowed, reason_if_blocked, next_eligible_date)
    
    Special backdoor: If user_email is stefan.hermes@htcglobal.asia,
    always allow generation regardless of frequency (for testing and marketing).
    """
    # Backdoor for testing/marketing - always allow for stefan.hermes@htcglobal.asia
    if user_email and user_email.lower() == "stefan.hermes@htcglobal.asia":
        return True, None, None
    
    supabase = get_supabase_client()
    
    # Get successful runs for this specification
    result = supabase.table("newsletter_runs")\
        .select("created_at")\
        .eq("specification_id", spec_id)\
        .eq("status", "success")\
        .order("created_at", desc=True)\
        .limit(1)\
        .execute()
    
    last_success = result.data[0] if result.data else None
    
    now = datetime.utcnow()
    
    if frequency == "daily":
        if last_success:
            last_date = datetime.fromisoformat(last_success["created_at"].replace("Z", "+00:00"))
            if last_date.date() == now.date():
                next_date = now + timedelta(days=1)
                next_date = next_date.replace(hour=0, minute=0, second=0, microsecond=0)
                return False, "Daily limit reached. One newsletter per calendar day.", next_date
        
        return True, None, None
    
    elif frequency == "weekly":
        if last_success:
            last_date = datetime.fromisoformat(last_success["created_at"].replace("Z", "+00:00"))
            # ISO week calculation
            last_week = last_date.isocalendar()[1]
            last_year = last_date.isocalendar()[0]
            current_week = now.isocalendar()[1]
            current_year = now.isocalendar()[0]
            
            if (current_year, current_week) == (last_year, last_week):
                # Calculate next Monday
                days_until_monday = (7 - now.weekday()) % 7
                if days_until_monday == 0:
                    days_until_monday = 7
                next_date = now + timedelta(days=days_until_monday)
                next_date = next_date.replace(hour=0, minute=0, second=0, microsecond=0)
                return False, "Weekly limit reached. One newsletter per ISO week.", next_date
        
        return True, None, None
    
    elif frequency == "monthly":
        if last_success:
            last_date = datetime.fromisoformat(last_success["created_at"].replace("Z", "+00:00"))
            if last_date.year == now.year and last_date.month == now.month:
                # First day of next month
                if now.month == 12:
                    next_date = datetime(now.year + 1, 1, 1)
                else:
                    next_date = datetime(now.year, now.month + 1, 1)
                return False, "Monthly limit reached. One newsletter per calendar month.", next_date
        
        return True, None, None
    
    return True, None, None


def create_newsletter_run(spec_id: str, workspace_id: str, user_email: str, status: str = "running") -> Dict:
    """Create a new newsletter run record."""
    supabase = get_supabase_client()
    
    run_data = {
        "specification_id": spec_id,
        "workspace_id": workspace_id,
        "user_email": user_email,
        "status": status
    }
    
    result = supabase.table("newsletter_runs").insert(run_data).execute()
    return result.data[0] if result.data else run_data


def update_run_status(run_id: str, status: str, artifact_path: Optional[str] = None, error_message: Optional[str] = None, metadata: Optional[Dict] = None):
    """Update newsletter run status."""
    supabase = get_supabase_client()
    
    update_data = {
        "status": status,
        "completed_at": datetime.utcnow().isoformat() if status in ["success", "failed"] else None
    }
    
    if artifact_path:
        update_data["artifact_path"] = artifact_path
    
    if error_message:
        update_data["error_message"] = error_message
    
    if metadata:
        update_data["metadata"] = metadata
    
    supabase.table("newsletter_runs")\
        .update(update_data)\
        .eq("id", run_id)\
        .execute()


def get_specification_history(spec_id: str, limit: int = 50) -> List[Dict]:
    """Get history of runs for a specification."""
    supabase = get_supabase_client()
    try:
        result = supabase.table("newsletter_runs")\
            .select("*")\
            .eq("specification_id", spec_id)\
            .order("created_at", desc=True)\
            .limit(limit)\
            .execute()
        return result.data if result.data else []
    except Exception as e:
        # Fallback: Try selecting specific columns if * fails
        print(f"Warning: Full select failed for specification history: {e}. Trying fallback.")
        try:
            result = supabase.table("newsletter_runs")\
                .select("id, specification_id, status, created_at, artifact_path, error_message, metadata")\
                .eq("specification_id", spec_id)\
                .order("created_at", desc=True)\
                .limit(limit)\
                .execute()
            return result.data if result.data else []
        except Exception as e2:
            print(f"Error: Fallback query also failed: {e2}")
            # Return empty list to prevent app crash
            return []


def get_last_successful_run(spec_id: str) -> Optional[Dict]:
    """Get the last successful run for a specification."""
    supabase = get_supabase_client()
    result = supabase.table("newsletter_runs")\
        .select("*")\
        .eq("specification_id", spec_id)\
        .eq("status", "success")\
        .order("created_at", desc=True)\
        .limit(1)\
        .execute()
    return result.data[0] if result.data else None

