"""
Workspace member password management.
Handles password hashing, verification, and storage for workspace members.
"""

import json
import os
import bcrypt
from typing import Optional, Dict, List
from pathlib import Path

# File to store workspace user passwords (fallback if not in database)
WORKSPACE_USERS_FILE = Path("workspace_users.json")


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its hash."""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    except Exception:
        return False


def load_workspace_users() -> Dict[str, Dict]:
    """Load workspace users from JSON file (fallback)."""
    if WORKSPACE_USERS_FILE.exists():
        try:
            with open(WORKSPACE_USERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_workspace_users(users: Dict[str, Dict]):
    """Save workspace users to JSON file (fallback)."""
    try:
        with open(WORKSPACE_USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(users, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving workspace users: {e}")


def get_workspace_user_password_hash(email: str) -> Optional[str]:
    """
    Get password hash for a workspace user.
    First checks Supabase, then falls back to JSON file.
    """
    email_lower = email.lower().strip()
    
    # Try Supabase first
    try:
        from core.workspace_members import get_supabase_client
        supabase = get_supabase_client()
        
        result = supabase.table("workspace_members")\
            .select("password_hash")\
            .eq("user_email", email_lower)\
            .limit(1)\
            .execute()
        
        if result.data and result.data[0].get("password_hash"):
            return result.data[0]["password_hash"]
    except Exception:
        pass
    
    # Fallback to JSON file
    users = load_workspace_users()
    user = users.get(email_lower)
    if user and user.get("password_hash"):
        return user["password_hash"]
    
    return None


def set_workspace_user_password(email: str, password: str, workspace_id: Optional[str] = None) -> bool:
    """
    Set password for a workspace user.
    Updates both Supabase and JSON file (for fallback).
    """
    email_lower = email.lower().strip()
    password_hash = hash_password(password)
    
    # Update Supabase
    try:
        from core.workspace_members import get_supabase_client
        supabase = get_supabase_client()
        
        # Update password_hash for all memberships with this email
        # (user can belong to multiple workspaces)
        supabase.table("workspace_members")\
            .update({"password_hash": password_hash})\
            .eq("user_email", email_lower)\
            .execute()
    except Exception as e:
        print(f"Error updating password in Supabase: {e}")
        # Continue to update JSON file as fallback
    
    # Update JSON file (fallback)
    users = load_workspace_users()
    if email_lower not in users:
        users[email_lower] = {}
    users[email_lower]["password_hash"] = password_hash
    if workspace_id:
        users[email_lower]["workspace_id"] = workspace_id
    save_workspace_users(users)
    
    return True


def check_workspace_password(email: str, password: str) -> bool:
    """Check if email and password match for a workspace user."""
    email_lower = email.lower().strip()
    
    # First check if user is a workspace member
    try:
        from core.generator_db import get_user_workspaces
        workspaces = get_user_workspaces(email_lower)
        if not workspaces:
            return False
    except Exception:
        return False
    
    # Get password hash
    password_hash = get_workspace_user_password_hash(email_lower)
    
    if not password_hash:
        # No password set yet - return False (user needs to set password)
        return False
    
    # Verify password
    return verify_password(password, password_hash)


def has_password_set(email: str) -> bool:
    """Check if user has a password set."""
    password_hash = get_workspace_user_password_hash(email)
    return password_hash is not None


def get_all_workspace_users() -> List[Dict]:
    """Get all workspace users with their password status (for admin)."""
    try:
        from core.workspace_members import get_supabase_client
        supabase = get_supabase_client()
        
        result = supabase.table("workspace_members")\
            .select("user_email, password_hash")\
            .execute()
        
        users = []
        seen_emails = set()
        if result.data:
            for member in result.data:
                email = member.get("user_email")
                if email and email not in seen_emails:
                    seen_emails.add(email)
                    users.append({
                        "email": email,
                        "has_password": bool(member.get("password_hash"))
                    })
        return users
    except Exception:
        # Fallback to JSON file
        users_data = load_workspace_users()
        return [
            {"email": email, "has_password": bool(data.get("password_hash"))}
            for email, data in users_data.items()
        ]

