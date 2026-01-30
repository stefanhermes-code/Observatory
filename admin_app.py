"""
Admin App - Owner Control Tower
A Streamlit application for provisioning, governance, and oversight of the newsletter platform.
Owner-only access.
"""

import streamlit as st
from datetime import datetime, timedelta
from collections import defaultdict
import sys
from pathlib import Path
import csv
import io

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from core.auth import require_owner_auth, login_page, logout
from core.admin_db import (
    get_pending_specification_requests,
    get_all_specification_requests,
    update_specification_request_status,
    get_all_workspaces,
    create_workspace,
    update_workspace,
    assign_request_to_workspace,
    update_specification,
    get_newsletter_specifications,
    update_specification_status,
    override_frequency_limit,
    get_recent_runs,
    get_audit_logs,
    log_audit_action
)
from core.pricing import calculate_price, format_price
from core.invoice_generator import generate_invoice_documents, is_thai_company
from urllib.parse import quote
from core.admin_users import (
    get_all_admin_users,
    add_admin_user,
    remove_admin_user,
    update_admin_password
)
from core.workspace_members import (
    get_workspace_members,
    add_workspace_member,
    remove_workspace_member,
    update_member_role
)
from core.taxonomy import PU_CATEGORIES, REGIONS, FREQUENCIES, VALUE_CHAIN_LINKS
from core.token_tracking import get_token_usage_by_workspace, get_token_usage_summary, format_token_cost

# Page configuration
st.set_page_config(
    page_title="PU Observatory - Admin Control Tower",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main-header {
        font-size: 2rem;
        font-weight: bold;
        color: #d32f2f;
        margin-bottom: 0.5rem;
    }
    .metric-card {
        background-color: #f5f5f5;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #d32f2f;
    }
    .status-pending { color: #ff9800; font-weight: bold; }
    .status-approved { color: #4caf50; font-weight: bold; }
    .status-active { color: #4caf50; font-weight: bold; }
    .status-paused { color: #9e9e9e; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# Check authentication
if not require_owner_auth():
    login_page()
    st.stop()

# Main headline with logo
logo_path = "Logo in blue steel no BG.png"
try:
    # Check if logo exists
    from pathlib import Path
    if Path(logo_path).exists():
        col1, col2 = st.columns([4, 1])
        with col1:
            st.markdown('<h1 style="font-size: 2.5rem; font-weight: bold; color: #1f77b4; margin-bottom: 1rem;">PU Observatory - Administrator</h1>', unsafe_allow_html=True)
        with col2:
            st.image(logo_path, use_container_width=False, width=120)
    else:
        st.markdown('<h1 style="font-size: 2.5rem; font-weight: bold; color: #1f77b4; margin-bottom: 1rem;">PU Observatory - Administrator</h1>', unsafe_allow_html=True)
except:
    st.markdown('<h1 style="font-size: 2.5rem; font-weight: bold; color: #1f77b4; margin-bottom: 1rem;">PU Observatory - Administrator</h1>', unsafe_allow_html=True)

# Sidebar navigation
st.sidebar.title("⚙️ Admin Control Tower")
st.sidebar.markdown(f"**User:** {st.session_state.user_email}")
st.sidebar.markdown(f"**Role:** {st.session_state.user_role}")

if st.sidebar.button("🚪 Logout"):
    logout()

st.sidebar.markdown("---")
st.sidebar.markdown("### Navigation")

page = st.sidebar.radio(
    "Select Page",
    [
        "📊 Dashboard",
        "📥 Process Requests",
        "💰 Invoicing",
        "📰 Intelligence Specifications",
        "📈 Reporting",
        "🏢 Companies",
        "👤 Users",
        "🔐 Administrators",
        "📚 Generation History",
        "📋 Audit Log"
    ]
)

# Main content area
if page == "📊 Dashboard":
    st.markdown('<p class="main-header">Admin Dashboard</p>', unsafe_allow_html=True)
    
    # Get data
    all_requests = get_all_specification_requests()
    workspaces = get_all_workspaces()
    specifications = get_newsletter_specifications()
    all_runs = get_recent_runs(100)  # Get more for performance metrics
    recent_runs = all_runs[:5]
    
    # Calculate performance metrics
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)  # Use timezone-aware datetime
    last_24h = [r for r in all_runs if r.get('created_at') and (now - datetime.fromisoformat(r.get('created_at').replace('Z', '+00:00'))).total_seconds() < 86400]
    last_7d = [r for r in all_runs if r.get('created_at') and (now - datetime.fromisoformat(r.get('created_at').replace('Z', '+00:00'))).total_seconds() < 604800]
    last_30d = [r for r in all_runs if r.get('created_at') and (now - datetime.fromisoformat(r.get('created_at').replace('Z', '+00:00'))).total_seconds() < 2592000]
    
    active_specs = [s for s in specifications if s.get("status") == "active"]
    paused_specs = [s for s in specifications if s.get("status") == "paused"]
    
    # Count requests by status
    pending_requests = [r for r in all_requests if r.get('status') == 'pending_review']
    approved_pending_invoice = [r for r in all_requests if r.get('status') == 'approved_pending_invoice']
    invoiced = [r for r in all_requests if r.get('status') == 'invoiced']
    paid_activated = [r for r in all_requests if r.get('status') == 'paid_activated']
    rejected = [r for r in all_requests if r.get('status') == 'rejected']
    
    # Flags and Alerts
    flags = []
    if len(pending_requests) > 5:
        flags.append(("⚠️", f"{len(pending_requests)} pending requests need attention", "warning"))
    if len(approved_pending_invoice) > 0:
        flags.append(("💰", f"{len(approved_pending_invoice)} requests approved, pending invoice", "info"))
    if len(paused_specs) > 0:
        flags.append(("⏸️", f"{len(paused_specs)} specifications are paused", "info"))
    if len(workspaces) == 0:
        flags.append(("ℹ️", "No companies yet", "info"))
    
    if flags:
        st.subheader("🚩 Flags & Alerts")
        for icon, message, alert_type in flags:
            if alert_type == "warning":
                st.warning(f"{icon} {message}")
            else:
                st.info(f"{icon} {message}")
        st.markdown("---")
    
    # Performance Metrics
    st.subheader("📊 Overall Performance")
    perf_col1, perf_col2, perf_col3, perf_col4, perf_col5 = st.columns(5)
    
    with perf_col1:
        st.metric("Total Runs (30d)", len(last_30d))
    
    with perf_col2:
        st.metric("Runs (7d)", len(last_7d))
    
    with perf_col3:
        st.metric("Runs (24h)", len(last_24h))
    
    with perf_col4:
        success_runs = [r for r in last_30d if r.get('status') == 'success']
        success_rate = (len(success_runs) / len(last_30d) * 100) if last_30d else 0
        st.metric("Success Rate (30d)", f"{success_rate:.1f}%")
    
    with perf_col5:
        avg_runs_per_day = len(last_30d) / 30 if last_30d else 0
        st.metric("Avg Runs/Day", f"{avg_runs_per_day:.1f}")
    
    st.markdown("---")
    
    # Request Status Metrics
    st.subheader("📈 Request Status Metrics")
    req_col1, req_col2, req_col3, req_col4, req_col5, req_col6 = st.columns(6)
    
    with req_col1:
        st.metric("Pending Review", len(pending_requests))
    
    with req_col2:
        st.metric("Approved (Pending Invoice)", len(approved_pending_invoice))
    
    with req_col3:
        st.metric("Invoiced", len(invoiced))
    
    with req_col4:
        st.metric("Paid & Activated", len(paid_activated))
    
    with req_col5:
        st.metric("Rejected", len(rejected))
    
    with req_col6:
        st.metric("Total Requests", len(all_requests))
    
    st.markdown("---")
    
    # Core Metrics
    st.subheader("📈 Core Metrics")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Active Specifications", len(active_specs))
    
    with col2:
        st.metric("Companies", len(workspaces))
    
    with col3:
        st.metric("Recent Runs (24h)", len(last_24h))
    
    with col4:
        st.metric("Total Specifications", len(specifications))
    
    st.markdown("---")
    
    # Recent Activity - Show recent admin actions from audit log
    st.subheader("📈 Recent Activity")
    recent_audit_logs = get_audit_logs(10)
    if recent_audit_logs:
        for log in recent_audit_logs[:5]:
            action = log.get('action_type', 'unknown')
            timestamp = log.get('created_at', '')
            user = log.get('actor_email', 'Unknown')
            reason = log.get('details', {}).get('reason', '') if isinstance(log.get('details'), dict) else ''
            
            # Format timestamp
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    time_str = dt.strftime("%Y-%m-%d %H:%M")
                except:
                    time_str = timestamp[:16]
            else:
                time_str = "Unknown time"
            
            # Format action name
            action_display = action.replace('_', ' ').title()
            
            st.write(f"**{action_display}** by {user} - {time_str}")
            if reason:
                st.caption(f"  {reason}")
    else:
        st.info("No recent activity. Activity will appear here as you approve requests, generate invoices, and manage the platform.")

elif page == "📥 Process Requests":
    st.markdown('<p class="main-header">Process Requests</p>', unsafe_allow_html=True)
    
    # Filter by status
    status_filter = st.selectbox(
        "Filter by Status",
        ["All", "pending_review", "approved", "rejected", "on_hold"]
    )
    
    # Get ALL requests (not just pending)
    all_requests = get_all_specification_requests()
    
    # Apply status updates from session state (for simulation mode)
    if "request_status_updates" not in st.session_state:
        st.session_state.request_status_updates = {}
    
    # Update request statuses from session state
    for req in all_requests:
        req_id = req.get('id')
        if req_id in st.session_state.request_status_updates:
            req['status'] = st.session_state.request_status_updates[req_id]
    
    if status_filter != "All":
        all_requests = [r for r in all_requests if r.get("status") == status_filter]
    
    st.write(f"**Total:** {len(all_requests)} requests")
    st.markdown("---")
    
    # Display requests
    for req in all_requests:
        with st.expander(f"📋 {req.get('newsletter_name', 'Unnamed')} - Status: {req.get('status', 'unknown')}"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Newsletter Name:**", req.get('newsletter_name'))
                st.write("**Company:**", req.get('company_name'))
                st.write("**Contact Email:**", req.get('contact_email'))
                st.write("**Frequency:**", req.get('frequency', '').title())
            
            with col2:
                st.write("**Categories:**")
                cat_names = [c['name'] for c in PU_CATEGORIES if c['id'] in req.get('categories', [])]
                for cat in cat_names:
                    st.write(f"- {cat}")
                
                st.write("**Regions:**")
                for region in req.get('regions', []):
                    st.write(f"- {region}")
                
                st.write("**Submitted:**", req.get('submission_timestamp', '')[:19])
            
            st.markdown("---")
            
            # Assign to Company (if approved or paid_activated)
            if req.get('status') in ['approved_pending_invoice', 'approved', 'paid_activated']:
                workspaces = get_all_workspaces()
                if workspaces:
                    workspace_options = {ws.get('id'): f"{ws.get('name')} - {ws.get('company_name')}" for ws in workspaces}
                    selected_workspace = st.selectbox(
                        "Assign to Company",
                        options=[""] + list(workspace_options.keys()),
                        format_func=lambda x: workspace_options.get(x, "Select company..."),
                        key=f"assign_ws_{req.get('id')}"
                    )
                    if selected_workspace and st.button("Assign & Activate", key=f"assign_{req.get('id')}"):
                        if assign_request_to_workspace(req.get('id'), selected_workspace):
                            log_audit_action(
                                "assign_request_to_workspace",
                                st.session_state.user_email,
                                {"request_id": req.get('id'), "workspace_id": selected_workspace},
                                f"Assigned request to company"
                            )
                            st.success("Request assigned to company and activated!")
                            st.rerun()
                        else:
                            st.error("Failed to assign request")
                else:
                    st.info("No companies available. One will be created automatically when marking as paid.")
            st.markdown("---")
            
            # Actions
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if req.get('status') == 'pending_review':
                    if st.button("✅ Approve", key=f"approve_{req.get('id')}", type="primary"):
                        try:
                            request_id = req.get('id')
                            if not request_id:
                                st.error("Error: Request ID is missing")
                            else:
                                st.info("Updating request status...")
                                result = update_specification_request_status(request_id, "approved_pending_invoice")
                                if result:
                                    # Store status update in session state (for simulation mode persistence)
                                    if "request_status_updates" not in st.session_state:
                                        st.session_state.request_status_updates = {}
                                    st.session_state.request_status_updates[request_id] = "approved_pending_invoice"
                                    
                                    log_audit_action(
                                        "approve_request",
                                        st.session_state.user_email,
                                        {"request_id": request_id},
                                        "Approved specification request"
                                    )
                                    st.success("✅ Request approved! Status updated to 'approved_pending_invoice'")
                                    st.balloons()
                                    st.rerun()
                                else:
                                    st.error("❌ Failed to update request status. Check database connection.")
                                    st.info("If using simulation mode, check console output for details.")
                        except Exception as e:
                            st.error(f"❌ Error approving request: {e}")
                            import traceback
                            st.code(traceback.format_exc())
                else:
                    st.info(f"Status: {req.get('status', 'unknown').replace('_', ' ').title()}")
            
            with col2:
                # Only show "Mark Invoiced" for approved statuses, NOT for invoiced or paid_activated
                if req.get('status') in ['approved_pending_invoice', 'approved']:
                    if st.button("💰 Mark Invoiced", key=f"mark_invoiced_{req.get('id')}"):
                        request_id = req.get('id')
                        result = update_specification_request_status(request_id, "invoiced")
                        if result:
                            if "request_status_updates" not in st.session_state:
                                st.session_state.request_status_updates = {}
                            st.session_state.request_status_updates[request_id] = "invoiced"
                            log_audit_action(
                                "mark_invoiced",
                                st.session_state.user_email,
                                {"request_id": request_id},
                                "Marked request as invoiced"
                            )
                            st.success("Marked as invoiced!")
                            st.rerun()
                elif req.get('status') == 'invoiced':
                    st.info("Status: Invoiced")
                elif req.get('status') == 'paid_activated':
                    st.success("✅ Status: Paid & Activated")
            
            with col3:
                if req.get('status') == 'invoiced':
                    if st.button("✅ Activate", key=f"activate_{req.get('id')}"):
                        request_id = req.get('id')
                        result = update_specification_request_status(request_id, "paid_activated")
                        if result:
                            if "request_status_updates" not in st.session_state:
                                st.session_state.request_status_updates = {}
                            st.session_state.request_status_updates[request_id] = "paid_activated"
                            log_audit_action(
                                "activate_request",
                                st.session_state.user_email,
                                {"request_id": request_id},
                                "Activated specification"
                            )
                            st.success("Specification activated!")
                            st.rerun()
                elif req.get('status') == 'paid_activated':
                    st.info("Ready to assign to company")
            
            with col4:
                if st.button("❌ Reject", key=f"reject_{req.get('id')}"):
                    reason = st.text_input("Rejection reason", key=f"reason_{req.get('id')}")
                    if reason:
                        update_specification_request_status(req.get('id'), "rejected", reason)
                        log_audit_action(
                            "reject_request",
                            st.session_state.user_email,
                            {"request_id": req.get('id'), "reason": reason},
                            f"Rejected request: {reason}"
                        )
                        st.success("Request rejected!")
                        st.rerun()

elif page == "🏢 Companies":
    st.markdown('<p class="main-header">Company Management</p>', unsafe_allow_html=True)
    
    st.info("""
    **What is a Company?**
    
    A Company represents a customer organization that subscribes to PU intelligence sources. 
    Each company can have multiple members (users) and multiple intelligence specifications. 
    Companies allow you to:
    - Group related specifications under one customer account
    - Manage user access and permissions per company
    - Track billing and subscriptions per organization
    - Organize intelligence sources by customer
    
    When a specification request is approved and paid, a company is automatically created. 
    You can also manually create and manage companies here.
    """)
    
    st.markdown("---")
    
    # Create new company
    with st.expander("➕ Create New Company", expanded=False):
        with st.form("create_workspace"):
            company_name = st.text_input("Company Name", key="create_company_name")
            contact_email = st.text_input("Contact Email", key="create_contact_email")
            
            if st.form_submit_button("Create Company", type="primary"):
                if company_name and contact_email:
                    # Workspace name is auto-generated as "{Company Name} Company"
                    workspace_name = f"{company_name} Company"
                    workspace = create_workspace(workspace_name, company_name, contact_email)
                    log_audit_action(
                        "create_workspace",
                        st.session_state.user_email,
                        {"workspace_id": workspace.get('id')},
                        f"Created company: {ws_name}"
                    )
                    st.success(f"✅ Company '{company_name}' created!")
                    st.rerun()
                else:
                    st.error("Please fill in all fields")
    
    st.markdown("---")
    
    # List companies
    workspaces = get_all_workspaces()
    
    # Get all requests to find address details
    all_requests = get_all_specification_requests()
    
    if workspaces:
        for ws in workspaces:
            with st.expander(f"🏢 {ws.get('name', 'Unnamed')} - {ws.get('company_name', 'Unknown')}"):
                # Find matching request for address details
                matching_request = next(
                    (r for r in all_requests 
                     if r.get('company_name', '').lower() == ws.get('company_name', '').lower()),
                    None
                )
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Company Name:**", ws.get('name'))
                    st.write("**Company:**", ws.get('company_name'))
                    st.write("**Contact:**", ws.get('contact_email'))
                    
                    # Display address details if available
                    if matching_request:
                        st.markdown("---")
                        st.write("**Address:**")
                        address_parts = []
                        if matching_request.get('street'):
                            street = matching_request.get('street', '')
                            house_num = matching_request.get('house_number', '')
                            if house_num:
                                address_parts.append(f"{street} {house_num}")
                            else:
                                address_parts.append(street)
                        if matching_request.get('city'):
                            address_parts.append(matching_request.get('city', ''))
                        if matching_request.get('zip_code'):
                            address_parts.append(matching_request.get('zip_code', ''))
                        if matching_request.get('country'):
                            address_parts.append(matching_request.get('country', ''))
                        
                        if address_parts:
                            st.write(", ".join(address_parts))
                        else:
                            st.write("*No address on file*")
                        
                        if matching_request.get('vat_number'):
                            st.write("**VAT Number:**", matching_request.get('vat_number'))
                    
                    st.write("**Created:**", ws.get('created_at', '')[:10])
                
                with col2:
                    # Get specifications for this workspace
                    specs = get_newsletter_specifications(ws.get('id'))
                    st.write(f"**Specifications:** {len(specs)}")
                    
                    if st.button("View Specifications", key=f"view_specs_{ws.get('id')}"):
                        st.session_state.selected_workspace = ws.get('id')
                        st.session_state.page = "📰 Intelligence Specifications"
                        st.rerun()
                
                st.markdown("---")
                
                # Edit company
                with st.expander("✏️ Edit Company Details", expanded=False):
                    with st.form(f"edit_workspace_{ws.get('id')}"):
                        new_name = st.text_input("Company Name", value=ws.get('name', ''), key=f"name_{ws.get('id')}")
                        new_company = st.text_input("Company Name", value=ws.get('company_name', ''), key=f"company_{ws.get('id')}")
                        new_email = st.text_input("Contact Email", value=ws.get('contact_email', ''), key=f"email_{ws.get('id')}")
                        
                        if st.form_submit_button("Save Changes", type="primary"):
                            update_workspace(ws.get('id'), new_name, new_company, new_email)
                            log_audit_action(
                                "update_workspace",
                                st.session_state.user_email,
                                {"workspace_id": ws.get('id')},
                                f"Updated company details"
                            )
                            st.success("Company updated!")
                            st.rerun()
    else:
        st.info("No companies yet. Create one above!")
        
        # Quick add admin as user option
        st.markdown("---")
        st.subheader("Quick Setup: Add Admin as User")
        st.info("""
        **Quick Setup:** If you want to test the Generator app, you can quickly create a test company 
        and add yourself as a user. This is useful for testing purposes.
        """)
        
        if st.button("🚀 Create Test Company & Add Me as Owner", type="primary"):
            admin_email = st.session_state.user_email
            test_workspace_name = f"Test Company - {admin_email.split('@')[0]}"
            test_company_name = "HTC Global (Test)"
            
            # Create workspace
            workspace = create_workspace(test_workspace_name, test_company_name, admin_email)
            workspace_id = workspace.get('id')
            
            # Add admin as owner
            from core.workspace_members import add_workspace_member
            from core.workspace_users import set_workspace_user_password
            
            add_workspace_member(workspace_id, admin_email, role="owner", added_by=admin_email)
            
            # Set password (use admin password as default)
            set_workspace_user_password(admin_email, "Stefan2025", workspace_id)
            
            log_audit_action(
                "quick_setup_test_workspace",
                admin_email,
                {"workspace_id": workspace_id, "member_email": admin_email},
                f"Created test company and added {admin_email} as owner with password"
            )
            
            st.success(f"✅ Test company created! You can now log into the Generator app with:")
            st.code(f"Email: {admin_email}\nPassword: Stefan2025")
            st.info("**Note:** You'll need to create an intelligence specification before you can generate newsletters.")
            st.rerun()

elif page == "👤 Users":
    st.markdown('<p class="main-header">User Management</p>', unsafe_allow_html=True)
    
    # Select company
    workspaces = get_all_workspaces()
    
    if not workspaces:
        st.warning("No companies available. Create a company first.")
    else:
        workspace_options = {ws.get('id'): f"{ws.get('name')} - {ws.get('company_name')}" for ws in workspaces}
        selected_workspace_id = st.selectbox(
            "Select Company",
            options=list(workspace_options.keys()),
            format_func=lambda x: workspace_options[x]
        )
        
        if selected_workspace_id:
            st.markdown("---")
            
            # Add new member
            # Check if we just added a member (from session state)
            add_member_key = f"member_added_{selected_workspace_id}"
            if add_member_key in st.session_state:
                saved_info = st.session_state[add_member_key]
                st.success(f"✅ Added {saved_info['email']} to company with password set!")
                st.info(f"📧 **Password for {saved_info['email']}:** `{saved_info['password']}` - Please share this with the user securely.")
                
                # Mailto button to send password
                from urllib.parse import quote
                subject = quote("Your PU Observatory Login Credentials")
                body = quote(f"""Hello,

Your account has been created for the Polyurethane Observatory platform.

Login credentials:
Email: {saved_info['email']}
Password: {saved_info['password']}

Please change your password after your first login.

Access the Generator app at: https://observatory-user-access.streamlit.app/

Best regards,
PU Observatory Admin""")
                mailto_link = f"mailto:{saved_info['email']}?subject={subject}&body={body}"
                st.markdown(f'<a href="{mailto_link}" target="_blank" style="display: inline-block; padding: 0.5rem 1rem; background-color: #1f77b4; color: white; text-align: center; text-decoration: none; border-radius: 0.25rem; margin-top: 0.5rem;">📧 Email Password to User</a>', unsafe_allow_html=True)
                
                # Clear button to dismiss
                if st.button("✓ Done", key=f"clear_add_{selected_workspace_id}"):
                    del st.session_state[add_member_key]
                    st.rerun()
            
            with st.expander("➕ Add New Member", expanded=False):
                with st.form("add_member"):
                    member_email = st.text_input("Member Email", placeholder="user@company.com")
                    member_role = st.selectbox("Role", ["member", "manager", "owner"], help="Owner: full control, Manager: can generate, Member: view only")
                    member_password = st.text_input("Password", type="password", help="Set initial password for this user")
                    
                    if st.form_submit_button("Add Member", type="primary"):
                        if member_email:
                            if not member_password:
                                st.error("⚠️ Password is required. Please set an initial password for the user.")
                            else:
                                result = add_workspace_member(
                                    selected_workspace_id,
                                    member_email,
                                    member_role,
                                    st.session_state.user_email
                                )
                                
                                if result:
                                    # Set password for the user
                                    from core.workspace_users import set_workspace_user_password
                                    set_workspace_user_password(member_email, member_password, selected_workspace_id)
                                    
                                    log_audit_action(
                                        "add_workspace_member",
                                        st.session_state.user_email,
                                        {"workspace_id": selected_workspace_id, "member_email": member_email, "role": member_role},
                                        f"Added {member_email} as {member_role} to company with password"
                                    )
                                    # Store password info in session state
                                    st.session_state[add_member_key] = {
                                        "email": member_email,
                                        "password": member_password
                                    }
                                    st.rerun()
                        else:
                            st.error("Please enter an email address")
            
            st.markdown("---")
            
            # List members
            members = get_workspace_members(selected_workspace_id)
            
            if members:
                st.write(f"**Total Members:** {len(members)}")
                st.markdown("---")
                
                for member in members:
                    member_email = member.get('user_email', 'Unknown')
                    current_role = member.get('role', 'member')
                    
                    # Check if user has password set
                    from core.workspace_users import has_password_set
                    has_password = has_password_set(member_email)
                    
                    with st.expander(f"👤 {member_email} - {current_role.title()} {'🔒' if has_password else '⚠️ No Password'}"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write("**Email:**", member_email)
                            st.write("**Role:**", current_role.title())
                            st.write("**Added:**", member.get('added_at', '')[:10] if member.get('added_at') else 'Unknown')
                            st.write("**Password:**", "✅ Set" if has_password else "❌ Not set")
                        
                        with col2:
                            # Change role
                            new_role = st.selectbox(
                                "Change Role",
                                ["member", "manager", "owner"],
                                index=["member", "manager", "owner"].index(current_role) if current_role in ["member", "manager", "owner"] else 0,
                                key=f"role_{member.get('id')}"
                            )
                            
                            if new_role != current_role:
                                if st.button("Update Role", key=f"update_role_{member.get('id')}"):
                                    update_member_role(selected_workspace_id, member_email, new_role)
                                    log_audit_action(
                                        "update_member_role",
                                        st.session_state.user_email,
                                        {"workspace_id": selected_workspace_id, "member_email": member_email, "old_role": current_role, "new_role": new_role},
                                        f"Changed {member_email} role from {current_role} to {new_role}"
                                    )
                                    st.success(f"✅ Role updated!")
                                    st.rerun()
                            
                            # Set/Reset password
                            # Check if we just set a password (from session state)
                            password_key = f"password_set_{member.get('id')}"
                            if password_key in st.session_state:
                                saved_info = st.session_state[password_key]
                                st.success(f"✅ Password set for {saved_info['email']}!")
                                st.info(f"📧 **New password for {saved_info['email']}:** `{saved_info['password']}` - Please share this with the user securely.")
                                
                                # Mailto button to send password
                                from urllib.parse import quote
                                subject = quote("Your PU Observatory Password Has Been Reset")
                                body = quote(f"""Hello,

Your password for the Polyurethane Observatory platform has been reset.

New login credentials:
Email: {saved_info['email']}
Password: {saved_info['password']}

⚠️ IMPORTANT: Please change your password after your first login for security.

Access the Generator app at: https://observatory-user-access.streamlit.app/

If you did not request this password reset, please contact your administrator immediately.

Best regards,
PU Observatory Admin""")
                                mailto_link = f"mailto:{saved_info['email']}?subject={subject}&body={body}"
                                st.markdown(f'<a href="{mailto_link}" target="_blank" style="display: inline-block; padding: 0.5rem 1rem; background-color: #1f77b4; color: white; text-align: center; text-decoration: none; border-radius: 0.25rem; margin-top: 0.5rem;">📧 Email New Password to User</a>', unsafe_allow_html=True)
                                
                                # Clear button to dismiss
                                if st.button("✓ Done", key=f"clear_{member.get('id')}"):
                                    del st.session_state[password_key]
                                    st.rerun()
                            
                            with st.form(f"password_{member.get('id')}"):
                                new_password = st.text_input("Set/Reset Password", type="password", key=f"pwd_{member.get('id')}")
                                if st.form_submit_button("Set Password"):
                                    if new_password:
                                        from core.workspace_users import set_workspace_user_password
                                        set_workspace_user_password(member_email, new_password, selected_workspace_id)
                                        log_audit_action(
                                            "set_workspace_password",
                                            st.session_state.user_email,
                                            {"workspace_id": selected_workspace_id, "member_email": member_email},
                                            f"Set password for {member_email}"
                                        )
                                        # Store password info in session state
                                        st.session_state[password_key] = {
                                            "email": member_email,
                                            "password": new_password
                                        }
                                        st.rerun()
                                    else:
                                        st.error("Please enter a password")
                            
                            if st.button("Remove Member", key=f"remove_{member.get('id')}", type="secondary"):
                                remove_workspace_member(selected_workspace_id, member_email)
                                log_audit_action(
                                    "remove_workspace_member",
                                    st.session_state.user_email,
                                    {"workspace_id": selected_workspace_id, "member_email": member_email},
                                    f"Removed {member_email} from company"
                                )
                                st.success(f"✅ Removed {member_email}")
                                st.rerun()
            else:
                st.info("No members in this company yet. Add one above!")

elif page == "🔐 Administrators":
    st.markdown('<p class="main-header">Administrator Management</p>', unsafe_allow_html=True)
    
    # Add new admin user
    with st.expander("➕ Add New Admin User", expanded=False):
        with st.form("add_admin"):
            admin_email = st.text_input("Admin Email", placeholder="admin@company.com")
            admin_password = st.text_input("Password", type="password", help="Set a secure password for this admin user")
            confirm_password = st.text_input("Confirm Password", type="password")
            
            if st.form_submit_button("Add Admin User", type="primary"):
                if admin_email and admin_password:
                    if admin_password != confirm_password:
                        st.error("❌ Passwords do not match.")
                    elif len(admin_password) < 6:
                        st.error("❌ Password must be at least 6 characters.")
                    else:
                        if add_admin_user(admin_email, admin_password):
                            log_audit_action(
                                "add_admin_user",
                                st.session_state.user_email,
                                {"admin_email": admin_email},
                                f"Added new admin user: {admin_email}"
                            )
                            st.success(f"✅ Admin user {admin_email} added!")
                            st.rerun()
                        else:
                            st.error("❌ User already exists.")
                else:
                    st.error("Please fill in all fields.")
    
    st.markdown("---")
    
    # List admin users
    admin_users = get_all_admin_users()
    
    if admin_users:
        st.write(f"**Total Admin Users:** {len(admin_users)}")
        st.markdown("---")
        
        for user in admin_users:
            col1, col2, col3 = st.columns([3, 2, 2])
            
            with col1:
                st.write(f"**{user.get('email', 'Unknown')}**")
                if user.get('created_at'):
                    st.caption(f"Created: {user.get('created_at', '')[:10]}")
            
            with col2:
                # Change password
                with st.form(f"change_password_{user.get('email')}"):
                    new_password = st.text_input("New Password", type="password", key=f"new_pass_{user.get('email')}")
                    if st.form_submit_button("Change Password", use_container_width=True):
                        if new_password:
                            if len(new_password) < 6:
                                st.error("Password must be at least 6 characters.")
                            else:
                                admin_email = user.get('email')
                                update_admin_password(admin_email, new_password)
                                log_audit_action(
                                    "change_admin_password",
                                    st.session_state.user_email,
                                    {"admin_email": admin_email},
                                    f"Changed password for {admin_email}"
                                )
                                st.success("✅ Password updated!")
                                st.info(f"📧 **New password for {admin_email}:** `{new_password}` - Please share this with the user securely.")
                                
                                # Mailto button to send password
                                subject = quote("Your PU Observatory Admin Password Has Been Reset")
                                body = quote(f"""Hello,

Your admin password for the Polyurethane Observatory platform has been reset.

New login credentials:
Email: {admin_email}
Password: {new_password}

⚠️ IMPORTANT: Please change your password after your first login for security.

Access the Admin app at: https://observatory-admin.streamlit.app/

If you did not request this password reset, please contact the system administrator immediately.

Best regards,
PU Observatory Admin""")
                                mailto_link = f"mailto:{admin_email}?subject={subject}&body={body}"
                                st.markdown(f'<a href="{mailto_link}" target="_blank" style="display: inline-block; padding: 0.5rem 1rem; background-color: #1f77b4; color: white; text-align: center; text-decoration: none; border-radius: 0.25rem; margin-top: 0.5rem;">📧 Email New Password to Admin</a>', unsafe_allow_html=True)
                                
                                st.rerun()
            
            with col3:
                # Don't allow removing yourself
                if user.get('email').lower() == st.session_state.user_email.lower():
                    st.info("Current user")
                else:
                    if st.button("Remove", key=f"remove_admin_{user.get('email')}", type="secondary"):
                        remove_admin_user(user.get('email'))
                        log_audit_action(
                            "remove_admin_user",
                            st.session_state.user_email,
                            {"admin_email": user.get('email')},
                            f"Removed admin user: {user.get('email')}"
                        )
                        st.success(f"✅ Removed {user.get('email')}")
                        st.rerun()
            
            st.markdown("---")
    else:
        st.info("No admin users found.")

elif page == "📰 Intelligence Specifications":
    st.markdown('<p class="main-header">Intelligence Specifications</p>', unsafe_allow_html=True)
    
    st.info("""
    **Intelligence Specifications** are the active, approved configurations that define what intelligence 
    sources are being generated for each company. Each specification includes:
    - Categories to track (e.g., company news, capacity changes)
    - Regions to monitor (e.g., EMEA, Americas, Asia)
    - Generation frequency (daily, weekly, monthly)
    - Status (active, paused, cancelled)
    
    These specifications are used by the Generator app to create intelligence reports.
    """)
    
    st.markdown("---")
    
    # Filter options
    col1, col2 = st.columns(2)
    with col1:
        status_filter = st.selectbox("Filter by Status", ["All", "active", "paused"])
    with col2:
        workspace_filter = st.selectbox("Filter by Company", ["All"] + [ws.get('name') for ws in get_all_workspaces()])
    
    # Get specifications
    specifications = get_newsletter_specifications()
    
    if status_filter != "All":
        specifications = [s for s in specifications if s.get("status") == status_filter]
    
    st.write(f"**Total:** {len(specifications)} specifications")
    st.markdown("---")
    
    # Display specifications
    for spec in specifications:
        status = spec.get("status", "unknown")
        status_display = status.upper()
        
        with st.expander(f"📰 {spec.get('newsletter_name', 'Unnamed')} - {status_display}"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Newsletter Name:**", spec.get('newsletter_name'))
                st.write("**Frequency:**", spec.get('frequency', '').title())
                st.write("**Status:**", status)
                st.write("**Company:**", spec.get('workspace_id', 'Unknown'))
            
            with col2:
                st.write("**Categories:**", len(spec.get('categories', [])))
                cat_names = [c['name'] for c in PU_CATEGORIES if c['id'] in spec.get('categories', [])]
                if "value_chain_link" in spec.get('categories', []):
                    st.caption(f"Value chain links available: {', '.join([link['name'] for link in VALUE_CHAIN_LINKS])}")
                for cat in cat_names[:3]:
                    st.write(f"- {cat}")
                if len(cat_names) > 3:
                    st.write(f"- ... and {len(cat_names) - 3} more")
                
                st.write("**Regions:**", ', '.join(spec.get('regions', [])))
                st.write("**Last Run:**", spec.get('last_run_at', 'Never'))
            
            st.markdown("---")
            
            # Edit Specification
            with st.expander("✏️ Edit Specification", expanded=False):
                with st.form(f"edit_spec_{spec.get('id')}"):
                    new_name = st.text_input("Intelligence Source Name", value=spec.get('newsletter_name', ''), key=f"spec_name_{spec.get('id')}")
                    # Extract frequency values and labels for selectbox
                    frequency_values = [f["value"] for f in FREQUENCIES]
                    current_freq = spec.get('frequency', 'monthly')
                    # Find index of current frequency, default to 0 if not found
                    try:
                        freq_index = frequency_values.index(current_freq) if current_freq in frequency_values else 0
                    except (ValueError, AttributeError):
                        freq_index = 0
                    
                    # Create a mapping function for labels
                    def get_frequency_label(value):
                        for f in FREQUENCIES:
                            if f["value"] == value:
                                return f["label"]
                        return value  # Fallback to value if not found
                    
                    new_frequency = st.selectbox(
                        "Frequency",
                        options=frequency_values,
                        index=freq_index,
                        format_func=get_frequency_label,
                        key=f"spec_freq_{spec.get('id')}"
                    )
                    
                    st.write("**Categories:**")
                    current_cats = spec.get('categories', [])
                    available_cat_ids = [c['id'] for c in PU_CATEGORIES]
                    # Filter current_cats to only include valid category IDs
                    valid_current_cats = [cat_id for cat_id in current_cats if cat_id in available_cat_ids]
                    selected_cats = st.multiselect(
                        "Select Categories",
                        options=available_cat_ids,
                        default=valid_current_cats,
                        format_func=lambda x: next((c['name'] for c in PU_CATEGORIES if c['id'] == x), x),
                        key=f"spec_cats_{spec.get('id')}"
                    )
                    
                    # Value Chain Links selection (editable, same as categories/regions)
                    # Always show this section - it applies when "Link in the PU Value Chain" is selected in categories
                    st.write("**Value Chain Links:**")
                    # Check if value_chain_link is in current spec (for initial display)
                    has_value_chain_category = "value_chain_link" in valid_current_cats
                    if has_value_chain_category:
                        st.caption("Select which value chain links should be included:")
                    else:
                        st.caption("💡 Tip: Select 'Link in the PU Value Chain' in Categories above, then select value chain links here. Both will be saved together.")
                    
                    current_vcl = spec.get('value_chain_links', [])
                    # Filter to only include valid value chain link IDs
                    valid_current_vcl = [vcl_id for vcl_id in current_vcl if vcl_id in [l['id'] for l in VALUE_CHAIN_LINKS]]
                    # If no stored value chain links but category is/was selected, default to all
                    if not valid_current_vcl and has_value_chain_category:
                        valid_current_vcl = [l['id'] for l in VALUE_CHAIN_LINKS]
                    
                    # Use multiselect for consistency with categories/regions pattern
                    # Always show it - user can select links even if category not yet selected
                    selected_value_chain_links = st.multiselect(
                        "Select Value Chain Links",
                        options=[l['id'] for l in VALUE_CHAIN_LINKS],
                        default=valid_current_vcl,
                        format_func=lambda x: next((l['name'] for l in VALUE_CHAIN_LINKS if l['id'] == x), x),
                        key=f"spec_vcl_{spec.get('id')}"
                    )
                    
                    st.write("**Regions:**")
                    current_regions = spec.get('regions', [])
                    # Filter current_regions to only include valid regions
                    valid_current_regions = [r for r in current_regions if r in REGIONS]
                    selected_regions = st.multiselect(
                        "Select Regions",
                        options=REGIONS,
                        default=valid_current_regions,
                        key=f"spec_regions_{spec.get('id')}"
                    )
                    
                    if st.form_submit_button("Save Changes", type="primary"):
                        if new_name and selected_cats and selected_regions:
                            try:
                                update_specification(
                                    spec.get('id'),
                                    newsletter_name=new_name,
                                    categories=selected_cats,
                                    regions=selected_regions,
                                    frequency=new_frequency,
                                    value_chain_links=selected_value_chain_links if "value_chain_link" in selected_cats else []
                                )
                                log_audit_action(
                                    "update_specification",
                                    st.session_state.user_email,
                                    {"spec_id": spec.get('id')},
                                    f"Updated specification: {new_name}"
                                )
                                st.success("Specification updated!")
                                st.rerun()
                            except Exception as e:
                                error_msg = str(e).lower()
                                if "column" in error_msg and "value_chain_links" in error_msg:
                                    st.error("⚠️ Database migration required! Please run the migration SQL file `development/migration_add_value_chain_links.sql` in your Supabase SQL editor to add the value_chain_links column.")
                                    st.info("💡 The specification was updated, but value chain links couldn't be saved. Run the migration and try again.")
                                else:
                                    st.error(f"Error updating specification: {str(e)}")
                        else:
                            st.error("Please fill in all required fields")
            
            st.markdown("---")
            
            # Actions
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if status == "paused":
                    if st.button("▶️ Activate", key=f"activate_{spec.get('id')}", type="primary"):
                        update_specification_status(spec.get('id'), "active")
                        log_audit_action(
                            "activate_spec",
                            st.session_state.user_email,
                            {"spec_id": spec.get('id')},
                            "Activated intelligence specification"
                        )
                        st.success("Specification activated!")
                        st.rerun()
                else:
                    if st.button("⏸️ Pause", key=f"pause_{spec.get('id')}"):
                        reason = st.text_input("Reason for pausing", key=f"pause_reason_{spec.get('id')}")
                        if reason:
                            update_specification_status(spec.get('id'), "paused", reason)
                            log_audit_action(
                                "pause_spec",
                                st.session_state.user_email,
                                {"spec_id": spec.get('id')},
                                f"Paused specification: {reason}"
                            )
                            st.success("Specification paused!")
                            st.rerun()
            
            with col2:
                if st.button("🔄 Override Frequency Limit", key=f"override_{spec.get('id')}"):
                    reason = st.text_input("Override reason (required)", key=f"override_reason_{spec.get('id')}")
                    if reason:
                        override_frequency_limit(spec.get('id'), reason)
                        log_audit_action(
                            "override_frequency",
                            st.session_state.user_email,
                            {"spec_id": spec.get('id')},
                            f"Overrode frequency limit: {reason}"
                        )
                        st.success("Frequency limit overridden!")
                        st.rerun()
            
            with col3:
                # Show enforcement state
                st.info(f"**Enforcement:** {'Active' if status == 'active' else 'Paused'}")

elif page == "💰 Invoicing":
    st.markdown('<p class="main-header">Invoicing Management</p>', unsafe_allow_html=True)
    
    st.info("""
    **Invoicing Management** helps you track the billing status of requests and companies.
    Use this page to:
    - View requests by invoicing status
    - Generate invoices and receipts (HTML format)
    - Download invoices/receipts
    - Send invoices via email with attachments
    - Track payment status
    - Export billing data for accounting
    
    **Invoice Logic:**
    - Foreign companies (non-Thai): Commercial Invoice only, no VAT
    - Domestic companies (Thailand): Commercial Invoice + Tax Invoice/Receipt, with 7% VAT
    """)
    
    st.markdown("---")
    
    # Filter by invoicing status
    # If we just generated an invoice, override filter to show it
    default_filter = st.session_state.get('_invoice_filter_override', None)
    if default_filter:
        # Use the override, then clear it
        filter_index = ["All", "approved_pending_invoice", "invoiced", "paid_activated"].index(default_filter) if default_filter in ["All", "approved_pending_invoice", "invoiced", "paid_activated"] else 0
        invoice_status = st.selectbox(
            "Filter by Invoicing Status",
            ["All", "approved_pending_invoice", "invoiced", "paid_activated"],
            index=filter_index
        )
        # Clear the override after using it
        del st.session_state['_invoice_filter_override']
    else:
        invoice_status = st.selectbox(
            "Filter by Invoicing Status",
            ["All", "approved_pending_invoice", "invoiced", "paid_activated"]
        )
    
    # Clean up any invalid invoice data (booleans from old session state keys)
    for key in list(st.session_state.keys()):
        if key.startswith("invoice_") and not key.startswith("invoice_data_"):
            value = st.session_state[key]
            if not isinstance(value, dict):
                # Remove invalid boolean or other non-dict values
                del st.session_state[key]
    
    # Get requests
    all_requests = get_all_specification_requests()
    
    # If we just generated an invoice, ensure that request is visible even if status changed
    last_generated_id = st.session_state.get('last_generated_invoice_id')
    request_to_include = None
    if last_generated_id:
        # Find the request that was just invoiced
        request_to_include = next((r for r in all_requests if r.get('id') == last_generated_id), None)
    
    # Apply filter
    if invoice_status != "All":
        filtered_requests = [r for r in all_requests if r.get("status") == invoice_status]
        # If we have a request that was just invoiced but got filtered out, include it
        if request_to_include and request_to_include.get('status') == 'invoiced':
            if request_to_include not in filtered_requests:
                filtered_requests.append(request_to_include)
        all_requests = filtered_requests
    
    # Calculate pricing for each request
    invoicing_data = []
    for req in all_requests:
        price_info = calculate_price(
            req.get('categories', []),
            req.get('regions', []),
            req.get('frequency', 'monthly'),
            num_users=1  # Default, could be configurable
        )
        invoicing_data.append({
            **req,
            'price': price_info
        })
    
    st.write(f"**Total:** {len(invoicing_data)} requests")
    st.markdown("---")
    
    # Display invoicing table
    if invoicing_data:
        for item in invoicing_data:
            req = item
            price_info = item['price']
            
            # Define invoice_data_key before using it
            invoice_data_key = f"invoice_data_{req.get('id')}"
            
            # Auto-expand if this request has an invoice or was just generated
            should_expand = (
                invoice_data_key in st.session_state and 
                isinstance(st.session_state.get(invoice_data_key), dict) and
                'invoice_html' in st.session_state.get(invoice_data_key, {})
            ) or req.get('id') == st.session_state.get('last_generated_invoice_id')
            
            with st.expander(
                f"💰 {req.get('newsletter_name', 'Unnamed')} - {req.get('company_name', 'Unknown')} - Status: {req.get('status', 'unknown')}",
                expanded=should_expand
            ):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.write("**Company:**", req.get('company_name'))
                    st.write("**Contact:**", req.get('contact_email'))
                    st.write("**Intelligence Source:**", req.get('newsletter_name'))
                
                with col2:
                    st.write("**Frequency:**", req.get('frequency', '').title())
                    st.write("**Categories:**", len(req.get('categories', [])))
                    st.write("**Regions:**", len(req.get('regions', [])))
                
                with col3:
                    st.write("**Pricing:**")
                    st.write(f"- Per user/month: ${price_info['price_per_user_monthly']}")
                    st.write(f"- Per user/year: ${price_info['price_per_user_yearly']}")
                    st.write(f"- **Total/year: ${price_info['total_price']}**")
                    st.write("**Status:**", req.get('status', 'unknown'))
                
                # Get workspace data if available (for company address)
                workspace_data = None
                workspaces_list = get_all_workspaces()
                matching_workspace = next((ws for ws in workspaces_list if ws.get('company_name', '').lower() == req.get('company_name', '').lower()), None)
                if matching_workspace:
                    workspace_data = matching_workspace
                    # Add company_address if not present (use contact_email location as fallback)
                    if 'company_address' not in workspace_data:
                        workspace_data['company_address'] = workspace_data.get('contact_email', '')
                
                # Determine if Thai company (use country field if available)
                country = req.get('country', '')
                is_thai = is_thai_company(
                    workspace_data.get('company_address', '') if workspace_data else '',
                    req.get('company_name', ''),
                    country
                )
                
                # Show company type
                if is_thai:
                    st.info("🇹🇭 Thai Company - Invoice + Receipt with 7% VAT")
                else:
                    st.info("🌍 Foreign Company - Invoice only, no VAT")
                
                st.markdown("---")
                
                # Check if invoice already exists - do this ONCE and ensure docs is always set if invoice exists
                # invoice_data_key already defined above
                has_invoice = False
                docs = None
                
                if invoice_data_key in st.session_state:
                    stored_docs = st.session_state[invoice_data_key]
                    if isinstance(stored_docs, dict) and 'invoice_html' in stored_docs:
                        has_invoice = True
                        docs = stored_docs
                    else:
                        # Invalid data, clean it up
                        del st.session_state[invoice_data_key]
                
                # Actions
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    # Show button for approved_pending_invoice status OR if status is invoiced but no invoice data exists yet
                    current_status = req.get('status', '')
                    can_generate = (current_status == 'approved_pending_invoice' or current_status == 'invoiced') and not has_invoice
                    
                    if can_generate:
                        # Show button and handle click
                        button_key = f"gen_invoice_{req.get('id')}"
                        if st.button("💰 Generate Invoice", key=button_key, type="primary"):
                            # Store that button was clicked BEFORE any operations
                            st.session_state[f'_button_clicked_{req.get("id")}'] = True
                            
                            # Generate invoice documents
                            try:
                                # Verify we have the required data
                                if not req.get('company_name'):
                                    raise ValueError("Missing company_name in request data")
                                if not req.get('contact_email'):
                                    raise ValueError("Missing contact_email in request data")
                                
                                # Generate invoice
                                docs = generate_invoice_documents(req, workspace_data)
                                
                                # Validate that docs is a dictionary
                                if not isinstance(docs, dict):
                                    raise ValueError(f"generate_invoice_documents returned {type(docs)} instead of dict: {docs}")
                                
                                # Ensure we have required keys and HTML is actually generated
                                if 'invoice_html' not in docs:
                                    raise ValueError(f"Missing 'invoice_html' key. Got keys: {list(docs.keys())}")
                                if 'invoice_number' not in docs:
                                    raise ValueError(f"Missing 'invoice_number' key. Got keys: {list(docs.keys())}")
                                
                                # Validate HTML is not empty
                                html_content = docs.get('invoice_html', '')
                                if not html_content or len(html_content) < 100:
                                    raise ValueError(f"Invoice HTML is empty or too short. Length: {len(html_content)}")
                                
                                # Store invoice data IMMEDIATELY in session state
                                st.session_state[invoice_data_key] = docs
                                
                                # Update status
                                update_specification_request_status(req.get('id'), "invoiced")
                                
                                # Log audit action
                                log_audit_action(
                                    "generate_invoice",
                                    st.session_state.user_email,
                                    {"request_id": req.get('id'), "invoice_number": docs['invoice_number'], "amount": docs['total_amount']},
                                    f"Generated invoice {docs['invoice_number']} for {req.get('company_name')}"
                                )
                                
                                # Store the request ID so we can show it even if filtered out
                                st.session_state['last_generated_invoice_id'] = req.get('id')
                                
                                # Force rerun to show the invoice preview
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Error generating invoice: {str(e)}")
                                import traceback
                                st.code(traceback.format_exc())
                                if invoice_data_key in st.session_state:
                                    stored_value = st.session_state[invoice_data_key]
                                    if not isinstance(stored_value, dict):
                                        del st.session_state[invoice_data_key]
                    
                    # Show status if button was clicked but invoice generation is in progress
                    if st.session_state.get(f'_button_clicked_{req.get("id")}') and not has_invoice:
                        st.warning("Invoice generation in progress...")
                    elif has_invoice and docs:
                        st.success(f"✅ Invoice {docs['invoice_number']} Generated")
                    else:
                        st.caption(f"Status: {current_status}")
                        if current_status not in ['approved_pending_invoice', 'invoiced']:
                            st.info("Request must be approved first")
                
                with col2:
                    # Download invoice/receipt
                    if has_invoice and docs:
                        st.download_button(
                            "📥 Download Invoice",
                            data=docs['invoice_html'],
                            file_name=f"Invoice_{docs['invoice_number']}.html",
                            mime="text/html",
                            key=f"download_invoice_{req.get('id')}"
                        )
                        
                        if docs.get('receipt_html'):
                            st.download_button(
                                "📥 Download Receipt",
                                data=docs['receipt_html'],
                                file_name=f"Receipt_{docs['receipt_number']}.html",
                                mime="text/html",
                                key=f"download_receipt_{req.get('id')}"
                            )
                
                with col3:
                    # Send invoice via mailto link
                    if has_invoice and docs:
                        customer_email = req.get('contact_email', '')
                        
                        if customer_email:
                            # Generate email body
                            # Generate email body for mailto link
                            company_name = req.get('company_name', '')
                            first_name = req.get('first_name', '')
                            last_name = req.get('last_name', '')
                            contact_name = f"{first_name} {last_name}".strip() if (first_name or last_name) else ""
                            greeting = f"Dear {contact_name}," if contact_name else f"Dear {company_name},"
                            
                            invoice_number = docs['invoice_number']
                            amount = docs['total_amount']
                            is_thai = docs.get('is_thai', False)
                            has_receipt = bool(docs.get('receipt_html'))
                            
                            email_body = f"""{greeting}

Please find attached your invoice for PU Observatory Intelligence Source subscription.

Invoice Number: {invoice_number}
Amount: ${amount:,.2f} USD
"""
                            if is_thai and has_receipt:
                                email_body += "\nAlso attached is your tax invoice/receipt for accounting purposes.\n"
                            
                            email_body += """
Payment is due within 15 days. Please refer to the invoice for payment details.

If you have any questions, please don't hesitate to contact us.

Kind regards,
Stefan Hermes
Managing Director
HTC Global
"""
                            
                            subject = f"Invoice {docs['invoice_number']} - PU Observatory Intelligence Source"
                            
                            # Create mailto link
                            mailto_link = f"mailto:{quote(customer_email)}?cc={quote(st.session_state.user_email)}&subject={quote(subject)}&body={quote(email_body)}"
                            
                            st.markdown(f"""
                                <a href="{mailto_link}" style="
                                    display: inline-block;
                                    padding: 0.5rem 1rem;
                                    background-color: #1f77b4;
                                    color: white;
                                    text-decoration: none;
                                    border-radius: 0.25rem;
                                    font-weight: bold;
                                ">📧 Open Email Client</a>
                            """, unsafe_allow_html=True)
                            
                            st.info(f"**Instructions:**\n1. Download invoice/receipt files above\n2. Click 'Open Email Client' button\n3. Attach the downloaded HTML files\n4. Send email")
                        else:
                            st.info("No email address available")
                
                # Display invoice/receipt preview with print button
                # Double-check invoice exists in session state (in case it was just generated)
                if invoice_data_key in st.session_state:
                    check_docs = st.session_state[invoice_data_key]
                    if isinstance(check_docs, dict) and 'invoice_html' in check_docs:
                        has_invoice = True
                        docs = check_docs
                
                if has_invoice and docs:
                    st.markdown("---")
                    st.subheader("📄 Invoice Preview")
                    
                    # Add print button and enhanced HTML with print styles
                    print_styles = """
                    <style>
                    @media print {
                        body { margin: 0; padding: 20px; }
                        .no-print { display: none !important; }
                        @page { margin: 1cm; }
                    }
                    </style>
                    <script>
                    function printInvoice() {
                        window.print();
                    }
                    </script>
                    """
                    
                    print_button = '<div class="no-print" style="text-align: center; margin-bottom: 20px;"><button onclick="printInvoice()" style="padding: 0.75rem 2rem; background-color: #4CAF50; color: white; border: none; border-radius: 0.5rem; font-weight: bold; cursor: pointer; font-size: 1rem;">🖨️ Print Invoice</button></div>'
                    
                    invoice_html_with_print = docs['invoice_html'].replace('</head>', print_styles + '</head>').replace('<body>', '<body>' + print_button)
                    
                    # Display invoice HTML
                    st.components.v1.html(invoice_html_with_print, height=900, scrolling=True)
                    
                    # Display receipt if available
                    if docs.get('receipt_html'):
                        st.markdown("---")
                        st.subheader("📄 Receipt Preview")
                        
                        receipt_print_styles = """
                        <style>
                        @media print {
                            body { margin: 0; padding: 20px; }
                            .no-print { display: none !important; }
                            @page { margin: 1cm; }
                        }
                        </style>
                        <script>
                        function printReceipt() {
                            window.print();
                        }
                        </script>
                        """
                        
                        receipt_print_button = '<div class="no-print" style="text-align: center; margin-bottom: 20px;"><button onclick="printReceipt()" style="padding: 0.75rem 2rem; background-color: #4CAF50; color: white; border: none; border-radius: 0.5rem; font-weight: bold; cursor: pointer; font-size: 1rem;">🖨️ Print Receipt</button></div>'
                        
                        receipt_html_with_print = docs['receipt_html'].replace('</head>', receipt_print_styles + '</head>').replace('<body>', '<body>' + receipt_print_button)
                        
                        st.components.v1.html(receipt_html_with_print, height=900, scrolling=True)
                
                with col4:
                    if req.get('status') == 'invoiced':
                        if st.button("✅ Mark Paid", key=f"paid_{req.get('id')}"):
                            # Automatically create workspace if it doesn't exist, then assign
                            company_name = req.get('company_name', '')
                            contact_email = req.get('contact_email', '')
                            
                            if not company_name or not contact_email:
                                st.error("Missing company name or contact email")
                            else:
                                # Check if workspace exists for this company
                                workspaces = get_all_workspaces()
                                matching_workspace = next(
                                    (ws for ws in workspaces 
                                     if ws.get('company_name', '').lower() == company_name.lower()),
                                    None
                                )
                                
                                if not matching_workspace:
                                    # Auto-create workspace
                                    workspace_name = f"{company_name} Company"
                                    new_workspace = create_workspace(workspace_name, company_name, contact_email)
                                    workspace_id = new_workspace.get('id')
                                    
                                    # Automatically add the contact email as workspace owner
                                    add_workspace_member(workspace_id, contact_email, role="owner", added_by=st.session_state.user_email)
                                    
                                    # Set initial password (use a default or generate one)
                                    from core.workspace_users import set_workspace_user_password
                                    # Generate a default password: company name + "2025"
                                    default_password = f"{company_name.replace(' ', '')}2025"
                                    set_workspace_user_password(contact_email, default_password, workspace_id)
                                    
                                    log_audit_action(
                                        "auto_create_workspace",
                                        st.session_state.user_email,
                                        {"workspace_id": workspace_id, "company_name": company_name, "member_email": contact_email},
                                        f"Automatically created company for {company_name} and added {contact_email} as owner (default password: {default_password})"
                                    )
                                    st.success(f"✅ Company created and user added!")
                                    st.warning(f"⚠️ **IMPORTANT:** Default password for {contact_email} is: `{default_password}` - Please share this with the user securely. They should change it on first login.")
                                    
                                    # Mailto button to send password
                                    from urllib.parse import quote
                                    subject = quote("Your PU Observatory Login Credentials")
                                    body = quote(f"""Hello,

Your company account has been created for the Polyurethane Observatory platform.

Login credentials:
Email: {contact_email}
Password: {default_password}

⚠️ IMPORTANT: Please change your password after your first login.

Access the Generator app at: https://observatory-user-access.streamlit.app/

Best regards,
PU Observatory Admin""")
                                    mailto_link = f"mailto:{contact_email}?subject={subject}&body={body}"
                                    st.markdown(f'<a href="{mailto_link}" target="_blank" style="display: inline-block; padding: 0.5rem 1rem; background-color: #1f77b4; color: white; text-align: center; text-decoration: none; border-radius: 0.25rem; margin-top: 0.5rem;">📧 Email Password to User</a>', unsafe_allow_html=True)
                                else:
                                    workspace_id = matching_workspace.get('id')
                                    
                                    # Check if contact email is already a member, if not add them
                                    existing_members = get_workspace_members(workspace_id)
                                    member_emails = [m.get('user_email', '').lower() for m in existing_members]
                                    if contact_email.lower() not in member_emails:
                                        add_workspace_member(workspace_id, contact_email, role="owner", added_by=st.session_state.user_email)
                                        
                                        # Set initial password if user doesn't have one
                                        from core.workspace_users import has_password_set, set_workspace_user_password
                                        if not has_password_set(contact_email):
                                            default_password = f"{company_name.replace(' ', '')}2025"
                                            set_workspace_user_password(contact_email, default_password, workspace_id)
                                            st.warning(f"⚠️ **IMPORTANT:** Default password for {contact_email} is: `{default_password}` - Please share this with the user securely. They should change it on first login.")
                                            
                                            # Mailto button to send password
                                            from urllib.parse import quote
                                            subject = quote("Your PU Observatory Login Credentials")
                                            body = quote(f"""Hello,

Your account has been added to the Polyurethane Observatory platform.

Login credentials:
Email: {contact_email}
Password: {default_password}

⚠️ IMPORTANT: Please change your password after your first login.

Access the Generator app at: https://observatory-user-access.streamlit.app/

Best regards,
PU Observatory Admin""")
                                            mailto_link = f"mailto:{contact_email}?subject={subject}&body={body}"
                                            st.markdown(f'<a href="{mailto_link}" target="_blank" style="display: inline-block; padding: 0.5rem 1rem; background-color: #1f77b4; color: white; text-align: center; text-decoration: none; border-radius: 0.25rem; margin-top: 0.5rem;">📧 Email Password to User</a>', unsafe_allow_html=True)
                                        
                                        log_audit_action(
                                            "auto_add_member_to_existing_workspace",
                                            st.session_state.user_email,
                                            {"workspace_id": workspace_id, "member_email": contact_email},
                                            f"Added {contact_email} as owner to existing company for {company_name}"
                                        )
                                        st.info(f"✅ Added {contact_email} as owner to existing company")
                                
                                # Assign request to company (creates intelligence specification)
                                if assign_request_to_workspace(req.get('id'), workspace_id):
                                    # Update status to paid_activated
                                    update_specification_request_status(req.get('id'), "paid_activated")
                                    log_audit_action(
                                        "mark_paid_and_activate",
                                        st.session_state.user_email,
                                        {"request_id": req.get('id'), "workspace_id": workspace_id},
                                        f"Marked as paid, created company, and activated specification for {company_name}"
                                    )
                                    st.success(f"✅ Paid! Company created/assigned and intelligence specification activated for {company_name}")
                                    st.balloons()
                                    st.rerun()
                                else:
                                    st.error("Failed to assign request to company")
                    
                    # Show status for paid_activated requests
                    if req.get('status') == 'paid_activated':
                        st.success("✅ Paid & Activated - Intelligence specification is active")
                    
                    # Export invoice data
                    invoice_csv = f"Company,Contact,Intelligence Source,Frequency,Price/Year,Status\n"
                    invoice_csv += f"{req.get('company_name')},{req.get('contact_email')},{req.get('newsletter_name')},{req.get('frequency')},{price_info['total_price']},{req.get('status')}\n"
                    st.download_button(
                        "📊 Export Data",
                        data=invoice_csv,
                        file_name=f"invoice_data_{req.get('id')}.csv",
                        mime="text/csv",
                        key=f"export_data_{req.get('id')}"
                    )
    
    else:
        st.info("No requests found for selected invoicing status.")
    
    st.markdown("---")
    
    # Export all invoicing data
    if invoicing_data:
        all_invoices_csv = "Company,Contact,Intelligence Source,Frequency,Price/Year,Status,Submitted\n"
        for item in invoicing_data:
            req = item
            price_info = item['price']
            all_invoices_csv += f"{req.get('company_name')},{req.get('contact_email')},{req.get('newsletter_name')},{req.get('frequency')},{price_info['total_price']},{req.get('status')},{req.get('submission_timestamp', '')[:10]}\n"
        
        st.download_button(
            "📥 Export All Invoicing Data",
            data=all_invoices_csv,
            file_name=f"all_invoices_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

elif page == "📈 Reporting":
    st.markdown('<p class="main-header">Reporting & Analytics</p>', unsafe_allow_html=True)
    
    st.info("""
    **Reporting & Analytics** provides comprehensive insights into platform usage, performance, and business metrics.
    Generate reports for:
    - Platform usage statistics
    - Company activity
    - Generation performance
    - Generation history (with vector store usage tracking)
    - Token usage & costs (OpenAI API consumption by company)
    - Revenue and billing analytics
    """)
    
    st.markdown("---")
    
    # Report type selection
    report_type = st.selectbox(
        "Select Report Type",
        ["Platform Overview", "Company Activity", "Generation Performance", "Generation History", "Token Usage & Costs", "Revenue Analytics"]
    )
    
    # Get data
    workspaces = get_all_workspaces()
    specifications = get_newsletter_specifications()
    try:
        all_runs = get_recent_runs(1000)
    except Exception as e:
        st.warning(f"⚠️ Could not load all runs: {str(e)}. Using limited dataset.")
        all_runs = get_recent_runs(100)  # Fallback to smaller limit
    all_requests = get_all_specification_requests()
    active_specs = [s for s in specifications if s.get("status") == "active"]
    
    if report_type == "Platform Overview":
        st.subheader("Platform Overview Report")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Companies", len(workspaces))
        with col2:
            st.metric("Total Specifications", len(specifications))
        with col3:
            st.metric("Active Specifications", len(active_specs))
        with col4:
            st.metric("Total Generation Runs", len(all_runs))
        
        st.markdown("---")
        
        # Specifications by frequency
        st.subheader("Specifications by Frequency")
        freq_counts = {}
        for spec in specifications:
            freq = spec.get('frequency', 'unknown')
            freq_counts[freq] = freq_counts.get(freq, 0) + 1
        
        for freq, count in freq_counts.items():
            st.write(f"**{freq.title()}:** {count}")
        
        st.markdown("---")
        
        # Export platform overview
        platform_csv = "Metric,Value\n"
        platform_csv += f"Total Companies,{len(workspaces)}\n"
        platform_csv += f"Total Specifications,{len(specifications)}\n"
        platform_csv += f"Active Specifications,{len(active_specs)}\n"
        platform_csv += f"Total Generation Runs,{len(all_runs)}\n"
        for freq, count in freq_counts.items():
            platform_csv += f"Specifications - {freq},{count}\n"
        
        st.download_button(
            "📥 Export Platform Overview",
            data=platform_csv,
            file_name=f"platform_overview_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    
    elif report_type == "Company Activity":
        st.subheader("Company Activity Report")
        
        if workspaces:
            for ws in workspaces:
                specs = get_newsletter_specifications(ws.get('id'))
                members = get_workspace_members(ws.get('id'))
                ws_runs = [r for r in all_runs if r.get('workspace_id') == ws.get('id')]
                
                with st.expander(f"🏢 {ws.get('name')} - {ws.get('company_name')}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Specifications:** {len(specs)}")
                        st.write(f"**Members:** {len(members)}")
                    with col2:
                        st.write(f"**Generation Runs:** {len(ws_runs)}")
                        st.write(f"**Created:** {ws.get('created_at', '')[:10]}")
            
            # Export company activity
            workspace_csv = "Company,Company Name,Specifications,Members,Generation Runs,Created\n"
            for ws in workspaces:
                specs = get_newsletter_specifications(ws.get('id'))
                members = get_workspace_members(ws.get('id'))
                ws_runs = [r for r in all_runs if r.get('workspace_id') == ws.get('id')]
                workspace_csv += f"{ws.get('name')},{ws.get('company_name')},{len(specs)},{len(members)},{len(ws_runs)},{ws.get('created_at', '')[:10]}\n"
            
            st.download_button(
                "📥 Export Company Activity",
                data=workspace_csv,
                file_name=f"company_activity_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        else:
            st.info("No companies found.")
    
    elif report_type == "Generation Performance":
        st.subheader("Generation Performance Report")
        
        # Success rate
        success_runs = [r for r in all_runs if r.get('status') == 'success']
        failed_runs = [r for r in all_runs if r.get('status') == 'failed']
        success_rate = (len(success_runs) / len(all_runs) * 100) if all_runs else 0
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Runs", len(all_runs))
        with col2:
            st.metric("Success Rate", f"{success_rate:.1f}%")
        with col3:
            st.metric("Failed Runs", len(failed_runs))
        
        st.markdown("---")
        
        # Runs by date (last 30 days)
        from collections import defaultdict
        runs_by_date = defaultdict(int)
        for run in all_runs:
            if run.get('created_at'):
                date = run.get('created_at')[:10]
                runs_by_date[date] += 1
        
        st.subheader("Runs by Date (Last 30 Days)")
        for date, count in sorted(runs_by_date.items(), reverse=True)[:30]:
            st.write(f"**{date}:** {count} runs")
        
        # Export performance data
        performance_csv = "Date,Runs,Success,Failed\n"
        for date in sorted(runs_by_date.keys(), reverse=True)[:30]:
            date_runs = [r for r in all_runs if r.get('created_at', '')[:10] == date]
            date_success = len([r for r in date_runs if r.get('status') == 'success'])
            date_failed = len([r for r in date_runs if r.get('status') == 'failed'])
            performance_csv += f"{date},{len(date_runs)},{date_success},{date_failed}\n"
        
        st.download_button(
            "📥 Export Performance Data",
            data=performance_csv,
            file_name=f"generation_performance_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    
    elif report_type == "Generation History":
        st.subheader("Generation History Report")
        
        st.info("""
        **Generation History** shows all intelligence source generation runs with detailed information including vector store usage.
        Each entry shows whether the company list was retrieved from the vector store during generation.
        """)
        
        st.markdown("---")
        
        # Get recent runs (limit to 50 for display)
        # If all_runs failed to load, try direct call
        if not all_runs:
            try:
                recent_runs = get_recent_runs(50)
            except Exception as e:
                st.error(f"Error loading generation history: {str(e)}")
                recent_runs = []
        else:
            recent_runs = all_runs[:50]
        
        if recent_runs:
            st.write(f"**Total Runs:** {len(recent_runs)} (showing most recent 50)")
            
            for run in recent_runs:
                with st.expander(f"📄 {run.get('newsletter_name', 'Unknown')} - {run.get('created_at', '')[:19]} - {run.get('status', 'unknown').upper()}"):
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.write("**Intelligence Source:**", run.get('newsletter_name'))
                        st.write("**Status:**", run.get('status', 'unknown'))
                        st.write("**Created:**", run.get('created_at', '')[:19])
                    
                    with col2:
                        st.write("**Run ID:**", run.get('id'))
                        st.write("**HTML File:**", run.get('artifact_path', 'N/A'))
                        
                        # Display vector store usage (admin-only info)
                        metadata = run.get("metadata", {})
                        if isinstance(metadata, dict):
                            tool_usage = metadata.get("tool_usage", {})
                            if tool_usage:
                                st.markdown("---")
                                st.write("**🔍 Vector Store Usage:**")
                                if tool_usage.get("vector_store_used"):
                                    st.success(f"✅ Used ({tool_usage.get('file_search_count', 0)} file_search call(s))")
                                    if tool_usage.get("files_retrieved"):
                                        st.write(f"Files retrieved: {len(tool_usage['files_retrieved'])}")
                                else:
                                    st.warning("⚠️ No file_search detected")
                            else:
                                st.info("ℹ️ Tool usage data not available (older run)")
                        
                        if run.get('artifact_path'):
                            # Retrieve HTML from metadata (stored when run was created)
                            html_content = None
                            if isinstance(metadata, dict):
                                html_content = metadata.get("html_content")
                            
                            if html_content:
                                st.download_button(
                                    "📥 Download HTML",
                                    data=html_content,
                                    file_name=f"{run.get('newsletter_name', 'intelligence')}_{run.get('created_at', '')[:10]}.html",
                                    key=f"download_report_{run.get('id')}"
                                )
                            else:
                                st.warning("⚠️ HTML content not available for this run (older runs may not have stored HTML)")
                    
                    with col3:
                        # Display additional metadata
                        metadata = run.get("metadata", {})
                        if isinstance(metadata, dict):
                            st.write("**Model:**", metadata.get("model", "N/A"))
                            st.write("**Tokens Used:**", metadata.get("tokens_used", "N/A"))
                            if metadata.get("thread_id"):
                                st.write("**Thread ID:**", metadata.get("thread_id")[:20] + "...")
        else:
            st.info("No generation runs yet")
        
        st.markdown("---")
        
        # Export generation history
        if recent_runs:
            history_csv = "Intelligence Source,Status,Created,Run ID,Vector Store Used,File Search Calls,Artifact Path\n"
            for run in recent_runs:
                metadata = run.get("metadata", {})
                tool_usage = metadata.get("tool_usage", {}) if isinstance(metadata, dict) else {}
                vector_store_used = "Yes" if tool_usage.get("vector_store_used") else "No"
                file_search_count = tool_usage.get("file_search_count", 0)
                history_csv += f"{run.get('newsletter_name', 'Unknown')},{run.get('status', 'unknown')},{run.get('created_at', '')[:19]},{run.get('id', 'N/A')},{vector_store_used},{file_search_count},{run.get('artifact_path', 'N/A')}\n"
            
            st.download_button(
                "📥 Export Generation History",
                data=history_csv,
                file_name=f"generation_history_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
    
    elif report_type == "Token Usage & Costs":
        st.subheader("Token Usage & Cost Analysis")
        
        st.info("""
        **Token Usage & Costs** shows OpenAI API token consumption and estimated costs.
        Tokens are tracked for each successful report generation and aggregated by company.
        Costs are estimated based on OpenAI's published pricing (check OpenAI pricing page for current rates).
        """)
        
        st.markdown("---")
        
        # Date range filter
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start Date (optional)", value=None)
        with col2:
            end_date = st.date_input("End Date (optional)", value=None)
        
        start_dt = datetime.combine(start_date, datetime.min.time()) if start_date else None
        end_dt = datetime.combine(end_date, datetime.max.time()) if end_date else None
        
        if start_dt:
            start_dt = start_dt.replace(tzinfo=None)
        if end_dt:
            end_dt = end_dt.replace(tzinfo=None)
        
        # Get summary with limit to prevent timeout
        try:
            # Limit to last 10,000 runs to prevent database timeout
            # Note: limit parameter has default value of 10000 in the function
            summary = get_token_usage_summary(start_date=start_dt, end_date=end_dt)
            
            if summary.get("error"):
                st.warning(f"⚠️ Limited data available: {summary.get('error')}. Showing results from most recent 10,000 runs.")
            
            # Overall metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Tokens", f"{summary['total_tokens']:,}")
            with col2:
                st.metric("Total Runs", summary['total_runs'])
            with col3:
                st.metric("Total Cost (Est.)", f"${summary['total_cost']:.2f}")
            with col4:
                st.metric("Companies", summary['workspace_count'])
            
            st.markdown("---")
            
            # Model breakdown
            if summary['model_breakdown']:
                st.subheader("Usage by Model")
                model_data = []
                for model, stats in summary['model_breakdown'].items():
                    cost_info = format_token_cost(stats['tokens'], model)
                    model_data.append({
                        "Model": model,
                        "Tokens": stats['tokens'],
                        "Runs": stats['runs'],
                        "Est. Cost": f"${cost_info['total_cost']:.2f}"
                    })
                
                if model_data:
                    import pandas as pd
                    df_models = pd.DataFrame(model_data)
                    st.dataframe(df_models, use_container_width=True, hide_index=True)
            
            st.markdown("---")
            
            # Company breakdown
            st.subheader("Usage by Company")
            
            if summary['workspace_details']:
                company_data = []
                workspace_map = {ws['id']: ws for ws in workspaces}
                
                for ws_id, stats in summary['workspace_details'].items():
                    workspace = workspace_map.get(ws_id, {})
                    company_name = workspace.get('company_name', 'Unknown')
                    
                    # Calculate average tokens per run
                    avg_tokens = stats['total_tokens'] / stats['run_count'] if stats['run_count'] > 0 else 0
                    
                    company_data.append({
                        "Company": company_name,
                        "Total Tokens": stats['total_tokens'],
                        "Runs": stats['run_count'],
                        "Avg Tokens/Run": int(avg_tokens),
                        "Est. Cost": f"${stats['estimated_cost']:.2f}"
                    })
                
                # Sort by total tokens (descending)
                company_data.sort(key=lambda x: x['Total Tokens'], reverse=True)
                
                import pandas as pd
                df_companies = pd.DataFrame(company_data)
                st.dataframe(df_companies, use_container_width=True, hide_index=True)
                
                # Export
                st.markdown("---")
                csv_data = df_companies.to_csv(index=False)
                st.download_button(
                    "📥 Export Token Usage by Company",
                    data=csv_data,
                    file_name=f"token_usage_by_company_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
            else:
                st.info("No token usage data available yet. Token tracking starts with new report generations.")
            
            # Show warning if limit was reached
            if summary.get("limit_reached"):
                st.warning("⚠️ Query limited to most recent 10,000 runs to prevent timeout. Use date filters to see specific periods.")
        
        except Exception as e:
            error_msg = str(e)
            if "timeout" in error_msg.lower() or "57014" in error_msg:
                st.error("⏱️ Database query timed out. Try using date filters to narrow the date range, or the data may be too large to process at once.")
            else:
                st.error(f"Error loading token usage data: {error_msg}")
                import traceback
                st.code(traceback.format_exc())
    
    elif report_type == "Revenue Analytics":
        st.subheader("Revenue Analytics Report")
        
        # Calculate revenue from active specifications
        total_revenue = 0
        revenue_by_freq = {'monthly': 0, 'weekly': 0, 'daily': 0}
        
        for spec in active_specs:
            price_info = calculate_price(
                spec.get('categories', []),
                spec.get('regions', []),
                spec.get('frequency', 'monthly'),
                num_users=1
            )
            annual_price = price_info['total_price']
            total_revenue += annual_price
            freq = spec.get('frequency', 'monthly')
            if freq in revenue_by_freq:
                revenue_by_freq[freq] += annual_price
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Annual Revenue", f"${total_revenue:,.0f}")
        with col2:
            st.metric("Monthly Revenue", f"${revenue_by_freq['monthly']:,.0f}")
        with col3:
            st.metric("Weekly Revenue", f"${revenue_by_freq['weekly']:,.0f}")
        with col4:
            st.metric("Daily Revenue", f"${revenue_by_freq['daily']:,.0f}")
        
        st.markdown("---")
        
        # Revenue by company
        st.subheader("Revenue by Company")
        workspace_revenue = {}
        for ws in workspaces:
            ws_specs = get_newsletter_specifications(ws.get('id'))
            ws_total = 0
            for spec in ws_specs:
                if spec.get('status') == 'active':
                    price_info = calculate_price(
                        spec.get('categories', []),
                        spec.get('regions', []),
                        spec.get('frequency', 'monthly'),
                        num_users=1
                    )
                    ws_total += price_info['total_price']
            if ws_total > 0:
                workspace_revenue[ws.get('name')] = ws_total
        
        for ws_name, revenue in sorted(workspace_revenue.items(), key=lambda x: x[1], reverse=True):
            st.write(f"**{ws_name}:** ${revenue:,.0f}/year")
        
        # Export revenue data
        revenue_csv = "Company,Annual Revenue\n"
        for ws_name, revenue in sorted(workspace_revenue.items(), key=lambda x: x[1], reverse=True):
            revenue_csv += f"{ws_name},{revenue}\n"
        revenue_csv += f"\nTotal,{total_revenue}\n"
        
        st.download_button(
            "📥 Export Revenue Data",
            data=revenue_csv,
            file_name=f"revenue_analytics_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

elif page == "📚 Generation History":
    st.markdown('<p class="main-header">Generation History</p>', unsafe_allow_html=True)
    
    st.info("""
    **Generation History** shows all intelligence source generation runs across all workspaces. 
    Each entry represents one execution of the Generator app, including:
    - The intelligence source name and specification used
    - When it was generated
    - The status (success, failed, in progress)
    - The generated HTML file (stored as an artifact in Supabase Storage)
    
    You can download any generated HTML file for review or archival purposes.
    """)
    
    st.markdown("---")
    
    # Get recent runs
    recent_runs = get_recent_runs(50)
    
    if recent_runs:
        st.write(f"**Total Runs:** {len(recent_runs)}")
        
        for run in recent_runs:
            with st.expander(f"📄 {run.get('newsletter_name', 'Unknown')} - {run.get('created_at', '')[:19]}"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.write("**Intelligence Source:**", run.get('newsletter_name'))
                    st.write("**Status:**", run.get('status', 'unknown'))
                    st.write("**Created:**", run.get('created_at', '')[:19])
                
                with col2:
                    st.write("**Run ID:**", run.get('id'))
                    st.write("**HTML File:**", run.get('artifact_path', 'N/A'))
                    
                    # Display vector store usage (admin-only info)
                    metadata = run.get("metadata", {})
                    if isinstance(metadata, dict):
                        tool_usage = metadata.get("tool_usage", {})
                        if tool_usage:
                            st.markdown("---")
                            st.write("**🔍 Vector Store Usage:**")
                            if tool_usage.get("vector_store_used"):
                                st.success(f"✅ Used ({tool_usage.get('file_search_count', 0)} file_search call(s))")
                                if tool_usage.get("files_retrieved"):
                                    st.write(f"Files retrieved: {len(tool_usage['files_retrieved'])}")
                            else:
                                st.warning("⚠️ No file_search detected")
                        else:
                            st.info("ℹ️ Tool usage data not available (older run)")
                    
                    if run.get('artifact_path'):
                        # Retrieve HTML from metadata (stored when run was created)
                        html_content = None
                        if isinstance(metadata, dict):
                            html_content = metadata.get("html_content")
                        
                        if html_content:
                            st.download_button(
                                "📥 Download HTML",
                                data=html_content,
                                file_name=f"{run.get('newsletter_name', 'intelligence')}_{run.get('created_at', '')[:10]}.html",
                                key=f"download_{run.get('id')}"
                            )
                        else:
                            st.warning("⚠️ HTML content not available for this run (older runs may not have stored HTML)")
                
                with col3:
                    # Display additional metadata
                    metadata = run.get("metadata", {})
                    if isinstance(metadata, dict):
                        st.write("**Model:**", metadata.get("model", "N/A"))
                        st.write("**Tokens Used:**", metadata.get("tokens_used", "N/A"))
                        if metadata.get("thread_id"):
                            st.write("**Thread ID:**", metadata.get("thread_id")[:20] + "...")
    else:
        st.info("No generation runs yet")
    
    st.markdown("---")
    
    # Export generation history
    if recent_runs:
        history_csv = "Intelligence Source,Status,Created,Run ID,Artifact Path\n"
        for run in recent_runs:
            history_csv += f"{run.get('newsletter_name', 'Unknown')},{run.get('status', 'unknown')},{run.get('created_at', '')[:19]},{run.get('id', 'N/A')},{run.get('artifact_path', 'N/A')}\n"
        
        st.download_button(
            "📥 Export Generation History",
            data=history_csv,
            file_name=f"generation_history_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

elif page == "📋 Audit Log":
    st.markdown('<p class="main-header">Audit Log</p>', unsafe_allow_html=True)
    
    st.info("""
    **Audit Log** provides a complete, immutable record of all administrative actions taken in the platform. 
    Every critical action is automatically logged, including:
    - User management (adding/removing admin users or workspace members)
    - Specification management (approving, activating, pausing specifications)
    - Workspace operations (creating workspaces, changing member roles)
    - Frequency overrides and other administrative exceptions
    
    **How it works:**
    - Every action includes: who performed it, when, what action, and why (reason)
    - Logs are stored permanently and cannot be modified or deleted
    - This ensures accountability, traceability, and compliance
    - Use the audit log to investigate issues, track changes, and maintain security
    
    The audit log helps you answer questions like: "Who changed this specification?" or "When was this user added?"
    """)
    
    st.markdown("---")
    
    # Get audit logs
    audit_logs = get_audit_logs(100)
    
    if audit_logs:
        st.write(f"**Total Entries:** {len(audit_logs)}")
        st.markdown("---")
        
        for log in audit_logs:
            action = log.get('action_type', 'unknown')
            user = log.get('actor_email', 'unknown')
            timestamp = log.get('created_at', '')[:19] if log.get('created_at') else ''
            reason = log.get('details', {}).get('reason', 'No reason provided') if isinstance(log.get('details'), dict) else 'No reason provided'
            st.markdown(f"""
                **{action}** - {user}
                - *{timestamp}*
                - {reason}
            """)
            st.markdown("---")
    else:
        st.info("No audit log entries yet")
    
    st.markdown("---")
    
    # Export audit log
    if audit_logs:
        audit_csv = "Action,User Email,Timestamp,Reason\n"
        for log in audit_logs:
            action = log.get('action_type', 'unknown')
            user = log.get('actor_email', 'unknown')
            timestamp = log.get('created_at', '')[:19] if log.get('created_at') else ''
            reason = log.get('details', {}).get('reason', 'No reason provided') if isinstance(log.get('details'), dict) else 'No reason provided'
            audit_csv += f"{action},{user},{timestamp},{reason}\n"
        
        st.download_button(
            "📥 Export Audit Log",
            data=audit_csv,
            file_name=f"audit_log_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

# Footer
st.markdown("---")
st.markdown("""
    <div style="text-align: center; color: #666; font-size: 0.9rem; margin-top: 2rem;">
        <p><strong>Polyurethane Industry Observatory</strong> - Owner Control Tower</p>
        <p>All actions are logged and auditable</p>
    </div>
""", unsafe_allow_html=True)

