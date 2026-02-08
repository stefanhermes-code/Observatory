"""
Generator App - Authenticated Report Generator
A Streamlit application for workspace users to manually generate intelligence reports.
"""

import streamlit as st
from datetime import datetime
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from core.auth import login_page_workspace, logout
from core.generator_db import (
    get_user_workspaces,
    get_workspace_specifications,
    get_specification_detail,
    check_frequency_enforcement,
    create_newsletter_run,
    update_run_status,
    get_specification_history,
    get_last_successful_run
)
from core.generator_execution import execute_generator
from core.taxonomy import PU_CATEGORIES, REGIONS, FREQUENCIES, VALUE_CHAIN_LINKS

# Page configuration
st.set_page_config(
    page_title="PU Observatory - Report Generator",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main-header {
        font-size: 2rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    .status-active { color: #4caf50; font-weight: bold; }
    .status-paused { color: #9e9e9e; font-weight: bold; }
    .status-blocked { color: #ff9800; font-weight: bold; }
    .newsletter-card {
        background-color: #f5f5f5;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
        margin: 1rem 0;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user_email = None
    st.session_state.user_role = None
    st.session_state.selected_workspace = None
    st.session_state.selected_spec = None

# Check authentication
if not st.session_state.authenticated:
    login_page_workspace()
    st.stop()

# Sidebar
st.sidebar.title("📰 Report Generator")
st.sidebar.markdown(f"**User:** {st.session_state.user_email}")

if st.sidebar.button("🚪 Logout"):
    logout()

st.sidebar.markdown("---")

# Get user's workspaces
workspaces = get_user_workspaces(st.session_state.user_email)

if not workspaces:
    st.error("❌ You are not assigned to any company. Please contact your administrator.")
    st.stop()

# Company selection
if len(workspaces) > 1:
    workspace_options = {ws["id"]: ws.get('company_name', 'Unknown') for ws in workspaces}
    selected_ws_id = st.sidebar.selectbox(
        "Select Company",
        options=list(workspace_options.keys()),
        format_func=lambda x: workspace_options[x],
        index=0 if not st.session_state.selected_workspace else 
              list(workspace_options.keys()).index(st.session_state.selected_workspace) if st.session_state.selected_workspace in workspace_options else 0
    )
    st.session_state.selected_workspace = selected_ws_id
else:
    st.session_state.selected_workspace = workspaces[0]["id"]

# Get current workspace name
current_workspace = next((ws for ws in workspaces if ws["id"] == st.session_state.selected_workspace), None)

# Header with logo (same as Configurator) - show once at top
logo_path = "Background Documentation/PU Observatory logo V3.png"
try:
    from pathlib import Path
    if Path(logo_path).exists():
        col1, col2 = st.columns([4, 1])
        with col1:
            st.markdown('<h1 class="main-header" style="font-size: 5rem !important; font-weight: bold !important; color: #1f77b4 !important; margin: 0 !important; padding: 0 !important; line-height: 1.1 !important;">Polyurethane Observatory</h1>', unsafe_allow_html=True)
        with col2:
            st.image(logo_path, width=120)
    else:
        st.markdown('<h1 class="main-header" style="font-size: 5rem !important; font-weight: bold !important; color: #1f77b4 !important; margin: 0 !important; padding: 0 !important; line-height: 1.1 !important;">Polyurethane Observatory</h1>', unsafe_allow_html=True)
except:
    st.markdown('<h1 class="main-header" style="font-size: 5rem !important; font-weight: bold !important; color: #1f77b4 !important; margin: 0 !important; padding: 0 !important; line-height: 1.1 !important;">Polyurethane Observatory</h1>', unsafe_allow_html=True)

if current_workspace:
    st.markdown(f"**Company:** {current_workspace.get('company_name', 'Unknown')}")

st.markdown("---")

# Get specifications for selected workspace
specifications = get_workspace_specifications(st.session_state.selected_workspace)

if not specifications:
    st.info("📋 No active intelligence specifications found for this company. Contact your administrator to activate a specification.")
    st.stop()

# Page selection
if "page" not in st.session_state:
    st.session_state.page = "📊 Dashboard"

page_options = ["📊 Dashboard", "📰 Generate Report", "📚 History"]
current_index = page_options.index(st.session_state.page) if st.session_state.page in page_options else 0

page = st.sidebar.radio(
    "Navigation",
    page_options,
    index=current_index
)

# Update session state if radio selection changed
if page != st.session_state.page:
    st.session_state.page = page

if page == "📊 Dashboard":
    st.subheader("📊 Dashboard")
    
    for spec in specifications:
        # Get last successful run
        last_run = get_last_successful_run(spec["id"])
        
        # Check eligibility
        # Automatic infinite frequency backdoor for stefan.hermes@htcglobal.asia
        check_frequency = spec.get("frequency", "monthly")
        if st.session_state.user_email.lower() == "stefan.hermes@htcglobal.asia":
            check_frequency = "infinite"  # Always infinite for testing/marketing
        is_allowed, reason, next_date = check_frequency_enforcement(spec["id"], check_frequency, st.session_state.user_email)
        
        with st.expander(f"📰 {spec.get('newsletter_name', 'Unnamed')} - {spec.get('frequency', '').title()}"):
            col1, col2 = st.columns(2)
            
            with col1:
                # Show "Infinite" for stefan.hermes@htcglobal.asia, otherwise show actual frequency
                display_frequency = spec.get("frequency", "").title()
                if st.session_state.user_email.lower() == "stefan.hermes@htcglobal.asia":
                    display_frequency = "Infinite"
                st.write("**Frequency:**", display_frequency)
                st.write("**Status:**", f"<span class='status-active'>{spec.get('status', 'unknown').upper()}</span>", unsafe_allow_html=True)
                
                if last_run:
                    last_date = datetime.fromisoformat(last_run["created_at"].replace("Z", "+00:00"))
                    st.write("**Last Generated:**", last_date.strftime("%Y-%m-%d %H:%M"))
                else:
                    st.write("**Last Generated:**", "Never")
            
            with col2:
                st.write("**Categories:**", len(spec.get("categories", [])))
                # Show value chain when category is selected OR admin set value_chain_links on spec
                if "value_chain_link" in spec.get("categories", []) or spec.get("value_chain_links"):
                    vcl = spec.get("value_chain_links") or []
                    if vcl:
                        names = [next((l["name"] for l in VALUE_CHAIN_LINKS if l["id"] == id), id) for id in vcl]
                        st.write("**Value chain links:**", ", ".join(names))
                    else:
                        st.write("**Value chain links:**", "Link in the PU Value Chain (select which links on Generate Report)")
                st.write("**Regions:**", ", ".join(spec.get("regions", [])))
                
                if is_allowed:
                    st.success("✅ Ready to generate")
                else:
                    st.warning(f"⏸️ {reason}")
                    if next_date:
                        st.write("**Next Eligible:**", next_date.strftime("%Y-%m-%d %H:%M"))
            
            if st.button(f"View History", key=f"hist_{spec['id']}"):
                st.session_state.selected_spec = spec["id"]
                st.session_state.page = "📚 History"
                st.rerun()
            
            # Link to Generate Report page
            if st.button(f"Go to Generate Page", key=f"goto_{spec['id']}"):
                st.session_state.selected_spec = spec["id"]
                st.session_state.page = "📰 Generate Report"
                st.rerun()

elif page == "📰 Generate Report":
    st.subheader("📰 Generate Report")
    
    # Get selected specification or use first one
    if st.session_state.selected_spec:
        spec_id = st.session_state.selected_spec
    else:
        spec_id = specifications[0]["id"]
    
    spec = get_specification_detail(spec_id)
    
    if not spec:
        st.error("Specification not found")
        st.stop()
    
    st.subheader(f"Generate: {spec.get('newsletter_name', 'Unnamed')}")
    
    # Show specification details
    st.markdown("### Specification Details")
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Report Name:**", spec.get("newsletter_name"))
        # Show "Infinite" for stefan.hermes@htcglobal.asia, otherwise show actual frequency
        display_frequency = spec.get("frequency", "").title()
        if st.session_state.user_email.lower() == "stefan.hermes@htcglobal.asia":
            display_frequency = "Infinite"
        st.write("**Frequency:**", display_frequency)
        
        st.write("**Created:**", spec.get("created_at", "")[:10])
        if spec.get("activated_at"):
            st.write("**Activated:**", spec.get("activated_at", "")[:10])
    
    with col2:
        st.write("**Available in Specification:**")
        st.write(f"- {len(spec.get('categories', []))} categories")
        # Show value chain when category is selected OR admin set value_chain_links on spec
        if "value_chain_link" in spec.get("categories", []) or spec.get("value_chain_links"):
            vcl = spec.get("value_chain_links") or []
            if vcl:
                names = [next((l["name"] for l in VALUE_CHAIN_LINKS if l["id"] == id), id) for id in vcl]
                st.write(f"- **Value chain links:** {', '.join(names)} — *select which links below*")
            else:
                st.write("- **Value chain links:** Link in the PU Value Chain — *select which links below*")
        st.write(f"- {len(spec.get('regions', []))} regions")
    
    st.markdown("---")
    
    # Category, Region, and Value Chain Link selection for this report
    st.markdown("### Select Categories, Regions, and Value Chain Links for This Report")
    st.write("Choose which categories, regions, and value chain links to include (all selected by default). Use the checkboxes below:")
    
    # Initialize session state for selected categories/regions/value_chain_links for this spec if not exists
    spec_selection_key = f"selected_cats_regs_{spec_id}"
    # Spec has value chain when category "value_chain_link" is in categories OR admin set value_chain_links
    spec_has_value_chain = "value_chain_link" in spec.get("categories", []) or bool(spec.get("value_chain_links"))
    if spec_selection_key not in st.session_state:
        stored_vcl = spec.get("value_chain_links", [])
        if stored_vcl and spec_has_value_chain:
            default_vcl = stored_vcl.copy()
        elif spec_has_value_chain:
            default_vcl = [l["id"] for l in VALUE_CHAIN_LINKS]
        else:
            default_vcl = []
        st.session_state[spec_selection_key] = {
            "categories": spec.get("categories", []).copy(),
            "regions": spec.get("regions", []).copy(),
            "value_chain_links": default_vcl.copy()
        }
    
    # Category selection
    st.markdown("#### Categories")
    available_categories = [c for c in PU_CATEGORIES if c["id"] in spec.get("categories", [])]
    selected_categories = []
    
    cat_col1, cat_col2 = st.columns(2)
    for idx, category in enumerate(available_categories):
        col = cat_col1 if idx % 2 == 0 else cat_col2
        with col:
            current_selection = st.session_state[spec_selection_key].get("categories", [])
            is_checked = category["id"] in current_selection if current_selection else True
            
            if st.checkbox(
                f"**{category['name']}**",
                value=is_checked,
                help=category["description"],
                key=f"gen_cat_{spec_id}_{category['id']}"
            ):
                selected_categories.append(category["id"])
    
    st.session_state[spec_selection_key]["categories"] = selected_categories
    
    if len(selected_categories) == 0:
        st.warning("⚠️ Please select at least one category for this report.")
    
    # Value chain link selection — show when spec has category OR admin set value_chain_links
    selected_value_chain_links = []
    if spec_has_value_chain:
        st.markdown("#### Link in the PU Value Chain")
        st.caption("Select which value chain position(s) to include in this report (same style as categories and regions above):")
        vcl_col1, vcl_col2 = st.columns(2)
        # Use stored value_chain_links from spec as default, fallback to all if not set
        stored_vcl = spec.get("value_chain_links", [])
        default_vcl_all = [l["id"] for l in VALUE_CHAIN_LINKS]
        current_vcl = st.session_state[spec_selection_key].get("value_chain_links", stored_vcl if stored_vcl else default_vcl_all)
        for idx, link in enumerate(VALUE_CHAIN_LINKS):
            col = vcl_col1 if idx % 2 == 0 else vcl_col2
            with col:
                is_checked = link["id"] in current_vcl if current_vcl else True
                if st.checkbox(
                    link["name"],
                    value=is_checked,
                    help=link["description"],
                    key=f"gen_vcl_{spec_id}_{link['id']}"
                ):
                    selected_value_chain_links.append(link["id"])
        st.session_state[spec_selection_key]["value_chain_links"] = selected_value_chain_links
        if len(selected_value_chain_links) == 0:
            st.warning("⚠️ Please select at least one value chain link for this report.")
    
    # Region selection
    st.markdown("#### Regions")
    available_regions = spec.get("regions", [])
    selected_regions = []
    
    reg_col1, reg_col2 = st.columns(2)
    for idx, region in enumerate(available_regions):
        col = reg_col1 if idx % 2 == 0 else reg_col2
        with col:
            current_selection = st.session_state[spec_selection_key].get("regions", [])
            is_checked = region in current_selection if current_selection else True
            
            if st.checkbox(
                region,
                value=is_checked,
                key=f"gen_region_{spec_id}_{region}"
            ):
                selected_regions.append(region)
    
    st.session_state[spec_selection_key]["regions"] = selected_regions
    
    if len(selected_regions) == 0:
        st.warning("⚠️ Please select at least one region for this report.")
    
    st.markdown("---")
    
    # Check frequency enforcement (pre-check before allowing generation)
    # Automatic infinite frequency backdoor for stefan.hermes@htcglobal.asia
    check_frequency = spec.get("frequency", "monthly")
    if st.session_state.user_email.lower() == "stefan.hermes@htcglobal.asia":
        check_frequency = "infinite"  # Always infinite for testing/marketing
    is_allowed, reason, next_date = check_frequency_enforcement(spec_id, check_frequency, st.session_state.user_email)
    
    if not is_allowed:
        st.error(f"❌ Generation Blocked: {reason}")
        if next_date:
            st.info(f"⏰ Next eligible generation date: **{next_date.strftime('%Y-%m-%d %H:%M UTC')}**")
        st.stop()
    
    st.markdown("---")
    
    # Cadence override for stefan.hermes@htcglobal.asia
    override_cadence = None
    if st.session_state.user_email.lower() == "stefan.hermes@htcglobal.asia":
        st.markdown("### Testing/Marketing Options")
        cadence_override_options = ["Use Specification Cadence", "Daily", "Weekly", "Monthly"]
        selected_override = st.selectbox(
            "Override Cadence (for testing/marketing):",
            options=cadence_override_options,
            index=0,
            help="Select a different cadence to test how reports look with different frequencies"
        )
        if selected_override != "Use Specification Cadence":
            override_cadence = selected_override.lower()
            st.info(f"📊 Cadence override active: {selected_override} (specification cadence: {spec.get('frequency', '').title()})")
    
    st.markdown("---")
    
    # Generate button
    if st.button("🚀 Generate Report Now", type="primary", width="stretch"):
        # Validate selections
        if len(selected_categories) == 0:
            st.error("❌ Please select at least one category.")
            st.stop()
        if len(selected_regions) == 0:
            st.error("❌ Please select at least one region.")
            st.stop()
        
        # Value chain links override (only when value_chain_link is in selected categories)
        value_chain_links_override = None
        if spec_has_value_chain:
            value_chain_links_override = st.session_state[spec_selection_key].get("value_chain_links", [])
        
        with st.spinner("Generating report..."):
            # Execute canonical 7-step Generator execution pattern
            # Pass selected categories, regions, and value chain links as override
            success, error_message, result_data, artifact_path = execute_generator(
                spec_id=spec_id,
                workspace_id=st.session_state.selected_workspace,
                user_email=st.session_state.user_email,
                cadence_override=override_cadence,
                categories_override=selected_categories,
                regions_override=selected_regions,
                value_chain_links_override=value_chain_links_override
            )
            
            if not success:
                st.error(f"❌ Generation failed: {error_message}")
            else:
                # Success - display results
                html_content = result_data["html_content"]
                metadata = result_data.get("metadata", {})

                # Limited transparency: item count and comparison to previous run only (no sources, queries, or internal diagnostics)
                evidence_summary = metadata.get("evidence_summary") or {}
                item_count = evidence_summary.get("inserted", 0)
                coverage_low = metadata.get("coverage_low", False)

                st.success("✅ Report generated successfully.")
                st.markdown("### Report summary")
                if coverage_low:
                    st.info("This run had limited coverage; the report reflects the evidence available.")
                st.write(f"This report is based on **{item_count}** items.")
                try:
                    last_run = get_last_successful_run(spec_id)
                    if last_run and last_run.get("id") != result_data.get("run_id"):
                        prev_meta = (last_run.get("metadata") or {}) if isinstance(last_run.get("metadata"), dict) else {}
                        prev_inserted = (prev_meta.get("evidence_summary") or {}).get("inserted")
                        if prev_inserted is not None:
                            st.write(f"Previous run had **{prev_inserted}** items.")
                except Exception:
                    pass

                # Display preview
                st.markdown("### Preview")
                st.components.v1.html(html_content, height=600, scrolling=True)
                
                # Download and Print buttons side by side
                col1, col2 = st.columns(2)
                with col1:
                    st.download_button(
                        "📥 Download HTML",
                        data=html_content,
                        file_name=f"{spec.get('newsletter_name', 'report')}_{datetime.utcnow().strftime('%Y%m%d')}.html",
                        mime="text/html",
                        width="stretch"
                    )
                with col2:
                    # Print button - styled exactly like download button
                    print_clicked = st.button("🖨️ Print Report", width="stretch", type="primary")
                    if print_clicked:
                        # Inject JavaScript to trigger print
                        st.markdown("""
                            <script>
                            setTimeout(function() {
                                window.print();
                            }, 100);
                            </script>
                        """, unsafe_allow_html=True)

elif page == "📚 History":
    st.subheader("📚 History")
    
    # Get selected specification or use first one
    if st.session_state.selected_spec:
        spec_id = st.session_state.selected_spec
    else:
        spec_id = specifications[0]["id"]
    
    spec = get_specification_detail(spec_id)
    
    if not spec:
        st.error("Specification not found")
        st.stop()
    
    st.subheader(f"History: {spec.get('newsletter_name', 'Unnamed')}")
    
    # Get history
    history = get_specification_history(spec_id)
    
    if not history:
        st.info("No generation history yet. Generate your first report!")
    else:
        st.write(f"**Total Runs:** {len(history)}")
        st.markdown("---")
        
        for run in history:
            status = run.get("status", "unknown")
            status_color = "#4caf50" if status == "success" else "#f44336" if status == "failed" else "#ff9800"
            
            with st.expander(f"{'✅' if status == 'success' else '❌' if status == 'failed' else '⏳'} {run.get('created_at', '')[:19]} - {status.upper()}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Status:**", f"<span style='color: {status_color}; font-weight: bold;'>{status.upper()}</span>", unsafe_allow_html=True)
                    st.write("**Generated by:**", run.get("user_email", "Unknown"))
                
                with col2:
                    st.write("**Created:**", run.get("created_at", "")[:19])
                    if run.get("error_message"):
                        st.error(f"**Error:** {run.get('error_message')}")
                    # Limited transparency: item count only (no sources or queries)
                    if run.get("metadata") and isinstance(run.get("metadata"), dict):
                        meta = run.get("metadata", {})
                        inserted = (meta.get("evidence_summary") or {}).get("inserted")
                        if inserted is not None:
                            st.write("**Items:**", inserted)

                if status == "success":
                    html_content = None
                    if run.get("metadata") and isinstance(run.get("metadata"), dict):
                        html_content = run.get("metadata", {}).get("html_content")

                    if html_content:
                        st.download_button(
                            "📥 Download HTML",
                            data=html_content,
                            file_name=f"{spec.get('newsletter_name', 'report')}_{run.get('created_at', '')[:10]}.html",
                            key=f"download_{run.get('id')}"
                        )
                    else:
                        st.warning("⚠️ HTML content not available for this run (older runs may not have stored HTML)")

# Footer
st.markdown("---")
st.markdown("""
    <div style="text-align: center; color: #666; font-size: 0.9rem; margin-top: 2rem;">
        <p><strong>Polyurethane Industry Observatory</strong></p>
        <p>Curated and published by <strong>Global NewsPilot</strong>, a division of HTC Global</p>
    </div>
""", unsafe_allow_html=True)

