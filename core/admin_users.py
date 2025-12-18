"""
Admin/Owner user management.
Stores admin users with passwords for the admin app.
"""

import os
import json
from typing import List, Dict, Optional
from pathlib import Path
import hashlib
from datetime import datetime

# File to store admin users (simple JSON file for now)
ADMIN_USERS_FILE = Path(__file__).parent.parent / "admin_users.json"


def get_admin_users_file() -> Path:
    """Get the path to admin users file."""
    return ADMIN_USERS_FILE


def load_admin_users() -> List[Dict]:
    """Load admin users from file."""
    if ADMIN_USERS_FILE.exists():
        try:
            with open(ADMIN_USERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading admin users: {e}")
            return []
    return []


def save_admin_users(users: List[Dict]):
    """Save admin users to file."""
    try:
        with open(ADMIN_USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(users, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving admin users: {e}")


def hash_password(password: str) -> str:
    """Simple password hashing (for development). In production, use proper hashing."""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash."""
    return hash_password(password) == hashed


def get_all_admin_users() -> List[Dict]:
    """Get all admin users."""
    users = load_admin_users()
    # Don't return passwords
    return [{k: v for k, v in user.items() if k != 'password_hash'} for user in users]


def add_admin_user(email: str, password: str) -> bool:
    """Add a new admin user."""
    users = load_admin_users()
    
    # Check if user already exists
    if any(u['email'].lower() == email.lower() for u in users):
        return False
    
    users.append({
        "email": email.lower(),
        "password_hash": hash_password(password),
        "created_at": datetime.utcnow().isoformat(),
        "created_by": "system"  # Could track who created it
    })
    
    save_admin_users(users)
    return True


def remove_admin_user(email: str) -> bool:
    """Remove an admin user."""
    users = load_admin_users()
    original_count = len(users)
    users = [u for u in users if u['email'].lower() != email.lower()]
    
    if len(users) < original_count:
        save_admin_users(users)
        return True
    return False


def update_admin_password(email: str, new_password: str) -> bool:
    """Update admin user password."""
    users = load_admin_users()
    
    for user in users:
        if user['email'].lower() == email.lower():
            user['password_hash'] = hash_password(new_password)
            user['password_updated_at'] = datetime.utcnow().isoformat()
            save_admin_users(users)
            return True
    
    return False


def check_admin_password(email: str, password: str) -> bool:
    """Check if email/password combination is valid for admin access."""
    users = load_admin_users()
    
    for user in users:
        if user['email'].lower() == email.lower():
            return verify_password(password, user['password_hash'])
    
    return False


def initialize_default_admin():
    """Initialize with default admin user if no users exist."""
    users = load_admin_users()
    if not users:
        # Add default admin
        add_admin_user("stefan.hermes@htcglobal.asia", "Stefan2025")
        print("Initialized default admin user: stefan.hermes@htcglobal.asia")


# Initialize on import
initialize_default_admin()

