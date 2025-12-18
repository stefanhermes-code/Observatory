"""
Workspace member management functions.
"""

import os
from datetime import datetime
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
        client.table("workspace_members").select("id").limit(1).execute()
        return client
    except Exception as e:
        raise Exception(f"Failed to connect to Supabase: {str(e)}. Check your credentials and database connection.")


def get_workspace_members(workspace_id: str) -> List[Dict]:
    """Get all members of a workspace."""
    supabase = get_supabase_client()
    result = supabase.table("workspace_members")\
        .select("*")\
        .eq("workspace_id", workspace_id)\
        .order("added_at", desc=True)\
        .execute()
    return result.data if result.data else []


def add_workspace_member(workspace_id: str, user_email: str, role: str = "member", added_by: Optional[str] = None) -> Dict:
    """Add a member to a workspace."""
    supabase = get_supabase_client()
    
    member_data = {
        "workspace_id": workspace_id,
        "user_email": user_email.lower(),
        "role": role,
        "added_by": added_by
    }
    
    result = supabase.table("workspace_members").insert(member_data).execute()
    return result.data[0] if result.data else member_data


def remove_workspace_member(workspace_id: str, user_email: str) -> bool:
    """Remove a member from a workspace."""
    supabase = get_supabase_client()
    supabase.table("workspace_members")\
        .delete()\
        .eq("workspace_id", workspace_id)\
        .eq("user_email", user_email.lower())\
        .execute()
    return True


def update_member_role(workspace_id: str, user_email: str, new_role: str) -> bool:
    """Update a member's role in a workspace."""
    supabase = get_supabase_client()
    supabase.table("workspace_members")\
        .update({"role": new_role})\
        .eq("workspace_id", workspace_id)\
        .eq("user_email", user_email.lower())\
        .execute()
    return True

