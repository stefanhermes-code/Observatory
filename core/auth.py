"""
Authentication utilities for the PU Observatory platform.
Handles user authentication and role-based access control.
"""

import streamlit as st
from typing import Optional
import os
from core.admin_users import check_admin_password, get_all_admin_users

# For now, we'll use a simple session-based auth
# In production, this will integrate with Supabase Auth

def check_owner_role(user_email: str) -> bool:
    """
    Check if a user has Owner role.
    Checks against admin users database.
    """
    # Check admin users file
    admin_users = get_all_admin_users()
    admin_emails = [u['email'].lower() for u in admin_users]
    
    # Also check environment variable/Streamlit secrets for backward compatibility
    try:
        import streamlit as st
        owner_email = st.secrets.get("OWNER_EMAIL") or os.getenv("OWNER_EMAIL")
        owner_emails_env = os.getenv("OWNER_EMAILS", "")
        if owner_email:
            admin_emails.append(owner_email.lower())
        if owner_emails_env:
            owner_emails = owner_emails_env.split(",")
            owner_emails = [e.strip().lower() for e in owner_emails if e.strip()]
            admin_emails.extend(owner_emails)
    except (AttributeError, FileNotFoundError, RuntimeError):
        # Not running in Streamlit, use environment variables
        owner_email = os.getenv("OWNER_EMAIL")
        owner_emails_env = os.getenv("OWNER_EMAILS", "")
        if owner_email:
            admin_emails.append(owner_email.lower())
        if owner_emails_env:
            owner_emails = owner_emails_env.split(",")
            owner_emails = [e.strip().lower() for e in owner_emails if e.strip()]
            admin_emails.extend(owner_emails)
    
    return user_email.lower() in admin_emails


def require_owner_auth():
    """
    Require owner authentication for Admin app.
    Redirects to login if not authenticated.
    """
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.user_email = None
        st.session_state.user_role = None
    
    if not st.session_state.authenticated:
        return False
    
    # Check if user has Owner role
    if st.session_state.user_role != "owner":
        return False
    
    return True


def login_page():
    """Render login page and handle authentication."""
    st.title("🔐 Admin Login")
    st.markdown("**Polyurethane Observatory - Owner Control Tower**")
    
    with st.form("login_form"):
        email = st.text_input("Email", placeholder="your.email@company.com")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login", type="primary")
        
        if submit:
            # Authenticate using admin users database
            if email and password:
                # Check password against admin users
                if not check_admin_password(email, password):
                    st.error("❌ Invalid email or password.")
                    return
                
                # Check if user is owner/admin
                if check_owner_role(email):
                    st.session_state.authenticated = True
                    st.session_state.user_email = email
                    st.session_state.user_role = "owner"
                    st.success("✅ Login successful!")
                    st.rerun()
                else:
                    st.error("❌ Access denied. Owner role required.")
            else:
                st.error("Please enter both email and password.")
    
    st.info("💡 This is the owner-only control tower. Only users with Owner role can access.")


def logout():
    """Logout current user."""
    st.session_state.authenticated = False
    st.session_state.user_email = None
    st.session_state.user_role = None
    st.rerun()


def login_page_workspace():
    """Render login page for workspace users (Generator app)."""
    # Header with logo (same as Configurator)
    logo_path = "Background Documentation/PU Observatory logo V3.png"
    try:
        from pathlib import Path
        if Path(logo_path).exists():
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown('<h1 class="main-header" style="font-size: 5rem !important; font-weight: bold !important; color: #1f77b4 !important; margin: 0 !important; padding: 0 !important; line-height: 1.1 !important;">Polyurethane Observatory</h1>', unsafe_allow_html=True)
            with col2:
                st.image(logo_path, use_container_width=False, width=120)
        else:
            st.markdown('<h1 class="main-header" style="font-size: 5rem !important; font-weight: bold !important; color: #1f77b4 !important; margin: 0 !important; padding: 0 !important; line-height: 1.1 !important;">Polyurethane Observatory</h1>', unsafe_allow_html=True)
    except:
        st.markdown('<h1 class="main-header" style="font-size: 5rem !important; font-weight: bold !important; color: #1f77b4 !important; margin: 0 !important; padding: 0 !important; line-height: 1.1 !important;">Polyurethane Observatory</h1>', unsafe_allow_html=True)
    
    st.subheader("🔐 Report Generator Login")
    
    with st.form("login_form"):
        email = st.text_input("Email", placeholder="your.email@company.com")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login", type="primary")
        
        if submit:
            if email and password:
                email_lower = email.lower().strip()
                
                # Check if user is a member of any workspace
                from core.generator_db import get_user_workspaces
                from core.workspace_users import check_workspace_password, has_password_set
                
                try:
                    workspaces = get_user_workspaces(email_lower)
                    
                    if not workspaces:
                        st.error("❌ Access denied. You are not a member of any company. Please contact your administrator.")
                        return
                    
                    # Check if password is set
                    if not has_password_set(email_lower):
                        st.error("❌ No password set for this account. Please contact your administrator to set up your password.")
                        return
                    
                    # Verify password
                    if check_workspace_password(email_lower, password):
                        # Password correct - authenticate user
                        st.session_state.authenticated = True
                        st.session_state.user_email = email_lower
                        st.session_state.user_role = "member"  # Default role, actual role checked per workspace
                        st.success("✅ Login successful!")
                        st.rerun()
                    else:
                        st.error("❌ Invalid email or password.")
                except Exception as e:
                    st.error(f"❌ Error during login: {str(e)}")
            else:
                st.error("Please enter both email and password.")
    
    st.info("💡 Enter your email and password to access your intelligence reports. You must be a member of a company to proceed.")

