"""
Configurator App - Public Specification Builder
A Streamlit application for collecting newsletter specifications from users.
"""

import streamlit as st
from datetime import datetime
import sys
from pathlib import Path
from urllib.parse import quote

# Add current directory to path to import core modules
sys.path.insert(0, str(Path(__file__).parent))

from core.taxonomy import PU_CATEGORIES, REGIONS, FREQUENCIES, INDUSTRY_CODE, VALUE_CHAIN_LINKS
from core.validation import validate_specification
from core.database import create_specification_request, update_specification_request, get_taxonomy_data
from core.pricing import calculate_price, format_price

# Page configuration
st.set_page_config(
    page_title="PU Observatory - Newsletter Configurator",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .header-container {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 1rem;
    }
    .main-header {
        font-size: 5rem !important;
        font-weight: bold !important;
        color: #1f77b4 !important;
        margin-bottom: 0.5rem !important;
        margin-top: 0 !important;
        padding: 0 !important;
        line-height: 1.1 !important;
    }
    h1.main-header {
        font-size: 5rem !important;
    }
    .logo-container {
        margin-left: 2rem;
    }
    .logo-container img {
        max-height: 80px;
        width: auto;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .step-header {
        font-size: 1.5rem;
        font-weight: 600;
        color: #1f77b4;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }
    .info-box {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
        margin: 1rem 0;
    }
    .floating-price-box {
        position: fixed;
        top: 80px;
        right: 20px;
        background-color: #e8f4f8;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        z-index: 999;
        min-width: 250px;
        max-width: 300px;
    }
    @media (max-width: 768px) {
        .floating-price-box {
            position: relative;
            top: auto;
            right: auto;
            margin: 1rem 0;
        }
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if "step" not in st.session_state:
    st.session_state.step = 1
if "specification" not in st.session_state:
    st.session_state.specification = {
        "categories": [],
        "value_chain_links": [],  # Step 2: selected value chain link IDs
        "regions": [],
        "package_tier": "",  # Explicit package tier selection
        "frequency": "",
        "newsletter_name": "",
        "company_name": "",
        "contact_email": "",
        "first_name": "",
        "last_name": "",
        "street": "",
        "house_number": "",
        "city": "",
        "zip_code": "",
        "country": "",
        "vat_number": ""
    }
if "submitted" not in st.session_state:
    st.session_state.submitted = False
if "request_id" not in st.session_state:
    st.session_state.request_id = None

# Header with logo
logo_path = "Background Documentation/PU Observatory logo V3.png"
try:
    # Check if logo exists
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

st.markdown("""
    <div class="info-box">
        <strong>Get Customized PU Industry Intelligence</strong><br>
        Configure your intelligence source to track the categories and regions that matter most to your business. 
        Receive timely updates on company news, market developments, capacity changes, and strategic insights 
        tailored to your specific needs and delivered on your preferred schedule.
    </div>
""", unsafe_allow_html=True)

# How it works section
with st.expander("📖 How It Works", expanded=False):
    st.markdown("""
    ### Step-by-Step Process
    
    1. **Intelligence Scope** - Select the categories of intelligence you want to track (e.g., Company News, Capacity Changes, Market Developments)
    
    2. **Value Chain Link** - Select which part(s) of the PU value chain to focus on (raw materials, system houses, foam/converters, end-use)
    
    3. **Select Regions** - Choose the geographic regions you want to monitor (e.g., EMEA, Americas, Asia)
    
    4. **Choose Frequency** - Select how often you want to receive updates:
       - **Monthly**: Strategic overview, themes, and outlook ($19/user/month)
       - **Weekly**: Operational monitoring with context ($39/user/month)
       - **Daily**: Continuous monitoring, early-warning signals ($119/user/month)
    
    5. **Tier level** - Confirm or choose your package tier
    
    6. **Name Your Intelligence Source** - Give your customized intelligence source a name
    
    7. **Provide Company Information** - Enter your company details and contact information
    
    8. **Review & Submit** - Review your selections and see the pricing, then submit your request
    
    ### What Happens Next?
    
    - Your request will be reviewed by our team
    - You'll receive an invoice via email
    - After payment, your intelligence source will be activated
    - You'll receive login credentials to access the Generator app
    - Start generating customized intelligence reports on your schedule
    """)

# Pricing Guide section
with st.expander("💰 Pricing Guide", expanded=False):
    st.markdown("### How Pricing Works")
    st.markdown("**Pricing is per user, per month** - All plans include full Observatory platform access.")
    
    st.markdown("#### Cadence Pricing (Core)")
    st.markdown("The frequency you choose determines the base price:")
    
    # Cadence pricing table using HTML
    st.markdown("""
    <table style="width: 100%; border-collapse: collapse; margin: 1rem 0;">
        <thead>
            <tr style="background-color: #1f77b4; color: white;">
                <th style="padding: 0.75rem; text-align: left; border: 1px solid #ddd;">Frequency</th>
                <th style="padding: 0.75rem; text-align: left; border: 1px solid #ddd;">Description</th>
                <th style="padding: 0.75rem; text-align: right; border: 1px solid #ddd;">Price per User/Month</th>
                <th style="padding: 0.75rem; text-align: right; border: 1px solid #ddd;">Price per User/Year</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td style="padding: 0.75rem; border: 1px solid #ddd;"><strong>Monthly</strong></td>
                <td style="padding: 0.75rem; border: 1px solid #ddd;">Strategic overview, themes, and outlook</td>
                <td style="padding: 0.75rem; text-align: right; border: 1px solid #ddd;">$19</td>
                <td style="padding: 0.75rem; text-align: right; border: 1px solid #ddd;">$228</td>
            </tr>
            <tr style="background-color: #f9f9f9;">
                <td style="padding: 0.75rem; border: 1px solid #ddd;"><strong>Weekly</strong></td>
                <td style="padding: 0.75rem; border: 1px solid #ddd;">Operational monitoring with context</td>
                <td style="padding: 0.75rem; text-align: right; border: 1px solid #ddd;">$39</td>
                <td style="padding: 0.75rem; text-align: right; border: 1px solid #ddd;">$468</td>
            </tr>
            <tr>
                <td style="padding: 0.75rem; border: 1px solid #ddd;"><strong>Daily</strong></td>
                <td style="padding: 0.75rem; border: 1px solid #ddd;">Continuous monitoring, early-warning signals</td>
                <td style="padding: 0.75rem; text-align: right; border: 1px solid #ddd;">$119</td>
                <td style="padding: 0.75rem; text-align: right; border: 1px solid #ddd;">$1,428</td>
            </tr>
        </tbody>
    </table>
    """, unsafe_allow_html=True)
    
    st.markdown("#### Scope Packages")
    st.markdown("**Your selection of categories and regions determines your package tier, which affects the price:**")
    
    # Scope packages table using HTML
    st.markdown("""
    <table style="width: 100%; border-collapse: collapse; margin: 1rem 0;">
        <thead>
            <tr style="background-color: #1f77b4; color: white;">
                <th style="padding: 0.75rem; text-align: left; border: 1px solid #ddd;">Package</th>
                <th style="padding: 0.75rem; text-align: center; border: 1px solid #ddd;">Categories</th>
                <th style="padding: 0.75rem; text-align: center; border: 1px solid #ddd;">Regions</th>
                <th style="padding: 0.75rem; text-align: left; border: 1px solid #ddd;">Description</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td style="padding: 0.75rem; border: 1px solid #ddd;"><strong>Starter</strong></td>
                <td style="padding: 0.75rem; text-align: center; border: 1px solid #ddd;">Up to 3</td>
                <td style="padding: 0.75rem; text-align: center; border: 1px solid #ddd;">1</td>
                <td style="padding: 0.75rem; border: 1px solid #ddd;">Focused coverage</td>
            </tr>
            <tr style="background-color: #f9f9f9;">
                <td style="padding: 0.75rem; border: 1px solid #ddd;"><strong>Medium</strong></td>
                <td style="padding: 0.75rem; text-align: center; border: 1px solid #ddd;">Up to 6</td>
                <td style="padding: 0.75rem; text-align: center; border: 1px solid #ddd;">2</td>
                <td style="padding: 0.75rem; border: 1px solid #ddd;">Balanced coverage</td>
            </tr>
            <tr>
                <td style="padding: 0.75rem; border: 1px solid #ddd;"><strong>Pro</strong></td>
                <td style="padding: 0.75rem; text-align: center; border: 1px solid #ddd;">Up to 9</td>
                <td style="padding: 0.75rem; text-align: center; border: 1px solid #ddd;">Up to 4</td>
                <td style="padding: 0.75rem; border: 1px solid #ddd;">Comprehensive coverage</td>
            </tr>
            <tr style="background-color: #f9f9f9;">
                <td style="padding: 0.75rem; border: 1px solid #ddd;"><strong>Enterprise</strong></td>
                <td style="padding: 0.75rem; text-align: center; border: 1px solid #ddd;">Custom</td>
                <td style="padding: 0.75rem; text-align: center; border: 1px solid #ddd;">Custom</td>
                <td style="padding: 0.75rem; border: 1px solid #ddd;">Full customization</td>
            </tr>
        </tbody>
    </table>
    """, unsafe_allow_html=True)
    
    st.markdown("**Note:** The package tier is automatically determined by your category and region selections. All plans include access to the full Observatory platform and all deliverables.")
    
    st.markdown("#### Example Calculations")
    st.markdown("""
    <ul>
        <li><strong>Monthly Starter</strong> (3 categories, 1 region): $19 × 1.0 = <strong>$19/user/month</strong> = <strong>$228/user/year</strong></li>
        <li><strong>Weekly Medium</strong> (6 categories, 2 regions): $39 × 1.2 = <strong>$47/user/month</strong> = <strong>$564/user/year</strong></li>
        <li><strong>Daily Pro</strong> (9 categories, 4 regions): $119 × 1.5 = <strong>$179/user/month</strong> = <strong>$2,148/user/year</strong></li>
        <li><strong>Monthly Enterprise</strong> (10+ categories, 5+ regions): $19 × 2.0 = <strong>$38/user/month</strong> = <strong>$456/user/year</strong></li>
    </ul>
    """, unsafe_allow_html=True)
    
    st.markdown("#### What's Included")
    st.markdown("All plans include access to:")
    st.markdown("- News Digest")
    st.markdown("- Industry Context & Insight")
    st.markdown("- Capacity & Asset Moves")
    st.markdown("- Competitive Developments")
    st.markdown("- Regulation & Sustainability")
    st.markdown("- Executive Briefings (where applicable)")

# Get taxonomy data
taxonomy_data = get_taxonomy_data()
categories_list = taxonomy_data["categories"]
regions_list = taxonomy_data["regions"]

# Main form - Step by step
# Show form if not submitted, success page if submitted
if not st.session_state.submitted:
    # Normal form flow - only rendered if NOT submitted
    # Step 1: Intelligence Scope (categories only; Value Chain Link is Step 2)
    categories_list_scope = [c for c in categories_list if c["id"] != "value_chain_link"]
    st.markdown('<p class="step-header">Step 1: Intelligence Scope</p>', unsafe_allow_html=True)
    st.write("Select one or more categories that your intelligence source should cover:")
    
    selected_categories = []
    
    # Display categories in 2 columns
    col1, col2 = st.columns(2)
    
    for idx, category in enumerate(categories_list_scope):
        col = col1 if idx % 2 == 0 else col2
        with col:
            if st.checkbox(
                f"**{category['name']}**",
                value=category["id"] in st.session_state.specification["categories"],
                help=category["description"],
                key=f"cat_{category['id']}"
            ):
                selected_categories.append(category["id"])
    
    st.session_state.specification["categories"] = selected_categories
    
    if len(selected_categories) == 0:
        st.warning("⚠️ Please select at least one category to continue.")
    
    # Step 2: Value Chain Link
    st.markdown('<p class="step-header">Step 2: Value Chain Link</p>', unsafe_allow_html=True)
    st.write("Select which part(s) of the PU value chain to focus on (optional):")
    
    selected_value_chain_links = []
    vc_col1, vc_col2 = st.columns(2)
    for idx, link in enumerate(VALUE_CHAIN_LINKS):
        col = vc_col1 if idx % 2 == 0 else vc_col2
        with col:
            if st.checkbox(
                f"**{link['name']}**",
                value=link["id"] in st.session_state.specification.get("value_chain_links", []),
                help=link["description"],
                key=f"vcl_{link['id']}"
            ):
                selected_value_chain_links.append(link["id"])
    
    st.session_state.specification["value_chain_links"] = selected_value_chain_links
    
    # Step 3: Region Selection
    st.markdown('<p class="step-header">Step 3: Select Regions</p>', unsafe_allow_html=True)
    st.write("Select one or more regions to monitor:")
    
    selected_regions = []
    
    # Display regions in 2 columns with checkboxes
    reg_col1, reg_col2 = st.columns(2)
    
    for idx, region in enumerate(regions_list):
        col = reg_col1 if idx % 2 == 0 else reg_col2
        with col:
            if st.checkbox(
                region,
                value=region in st.session_state.specification["regions"],
                key=f"region_{region}"
            ):
                selected_regions.append(region)
    
    st.session_state.specification["regions"] = selected_regions
    
    # Show package tier indicator after regions are selected (uses categories + value_chain_link if any links selected)
    categories_for_scope = list(st.session_state.specification.get("categories", []))
    if st.session_state.specification.get("value_chain_links"):
        if "value_chain_link" not in categories_for_scope:
            categories_for_scope.append("value_chain_link")
    if len(categories_for_scope) > 0 and len(selected_regions) > 0:
        try:
            from core.pricing import calculate_price
            price_data = calculate_price(
                categories=categories_for_scope,
                regions=selected_regions,
                frequency=st.session_state.specification.get("frequency", "monthly"),
                package_tier=st.session_state.specification.get("package_tier")
            )
            scope_tier = price_data["breakdown"]["scope"]["tier"]
            st.info(f"📦 **Package Tier:** {scope_tier} - Based on {len(categories_for_scope)} categories and {len(selected_regions)} regions")
        except Exception:
            pass
    
    if len(selected_regions) == 0:
        st.warning("⚠️ Please select at least one region to continue.")
    
    # Step 4: Frequency Selection
    st.markdown('<p class="step-header">Step 4: Choose Frequency</p>', unsafe_allow_html=True)
    st.write("Select how often you want to receive your newsletter:")
    
    frequency_options = {freq["value"]: f"{freq['label']} - {freq['description']}" for freq in FREQUENCIES}
    
    selected_frequency = st.radio(
        "Frequency",
        options=list(frequency_options.keys()),
        format_func=lambda x: frequency_options[x],
        index=0 if not st.session_state.specification["frequency"] else 
              list(frequency_options.keys()).index(st.session_state.specification["frequency"]),
        help="This becomes a hard limit on how often newsletters can be generated"
    )
    
    st.session_state.specification["frequency"] = selected_frequency
    
    # Step 5: Tier level
    st.markdown('<p class="step-header">Step 5: Tier level</p>', unsafe_allow_html=True)
    st.write("Choose your package tier:")
    
    categories_for_tier = list(st.session_state.specification.get("categories", []))
    if st.session_state.specification.get("value_chain_links"):
        if "value_chain_link" not in categories_for_tier:
            categories_for_tier.append("value_chain_link")
    
    suggested_tier = None
    if len(categories_for_tier) > 0 and len(selected_regions) > 0:
        try:
            from core.pricing import calculate_price
            price_data = calculate_price(
                categories=categories_for_tier,
                regions=selected_regions,
                frequency=st.session_state.specification.get("frequency", "monthly"),
                package_tier=None
            )
            suggested_tier = price_data["breakdown"]["scope"]["tier"]
        except Exception:
            pass
    
    package_options = {
        "Starter": {"multiplier": 1.0, "description": "Focused coverage (Up to 3 categories, 1 region)"},
        "Medium": {"multiplier": 1.2, "description": "Balanced coverage (Up to 6 categories, 2 regions)"},
        "Pro": {"multiplier": 1.5, "description": "Comprehensive coverage (Up to 9 categories, up to 4 regions)"},
        "Enterprise": {"multiplier": 2.0, "description": "Full customization (10+ categories, 5+ regions)"}
    }
    default_tier = st.session_state.specification.get("package_tier") or suggested_tier or "Starter"
    num_cats = len(categories_for_tier)
    num_regs = len(selected_regions)
    tier_limits = {
        "Starter": {"max_categories": 3, "max_regions": 1},
        "Medium": {"max_categories": 6, "max_regions": 2},
        "Pro": {"max_categories": 9, "max_regions": 4},
        "Enterprise": {"max_categories": 999, "max_regions": 999}
    }
    tier_order = ["Starter", "Medium", "Pro", "Enterprise"]
    available_tiers = []
    if suggested_tier and suggested_tier in tier_order:
        suggested_index = tier_order.index(suggested_tier)
        available_tiers = [t for t in tier_order if tier_order.index(t) >= suggested_index]
    else:
        available_tiers = list(package_options.keys())
    
    selected_package_tier = st.radio(
        "Package Tier",
        options=available_tiers,
        index=available_tiers.index(default_tier) if default_tier in available_tiers else 0,
        format_func=lambda x: f"{x} - {package_options[x]['description']}",
        help="Package tier must match or exceed your selections."
    )
    st.session_state.specification["package_tier"] = selected_package_tier
    
    selected_limits = tier_limits.get(selected_package_tier, {"max_categories": 0, "max_regions": 0})
    if num_cats > selected_limits["max_categories"] or num_regs > selected_limits["max_regions"]:
        st.error(f"❌ Your selections ({num_cats} categories, {num_regs} regions) exceed **{selected_package_tier}** limits. Reduce selections or choose a higher tier.")
    
    st.markdown("---")
    
    # Real-time price estimate (floating window)
    if len(categories_for_tier) > 0 and len(st.session_state.specification.get("regions", [])) > 0:
        try:
            from core.pricing import calculate_price, format_price
            price_data = calculate_price(
                categories=categories_for_tier,
                regions=st.session_state.specification.get("regions", []),
                frequency=selected_frequency,
                package_tier=st.session_state.specification.get("package_tier")
            )
            scope_tier = price_data["breakdown"]["scope"]["tier"]
            st.markdown(f"""
                <div class="floating-price-box">
                    <strong style="color: #1f77b4; font-size: 1rem; display: block; margin-bottom: 0.5rem;">💰 Estimated Price</strong>
                    <div style="font-size: 1.75rem; font-weight: bold; color: #1f77b4; margin-bottom: 0.25rem;">
                        {format_price(price_data)}
                    </div>
                    <p style="color: #666; font-size: 0.85rem; margin: 0;">
                        {format_price(price_data, show_per_user=True)}
                    </p>
                    <p style="color: #666; font-size: 0.75rem; margin-top: 0.25rem; margin-bottom: 0;">
                        {selected_frequency.title()} • {scope_tier}
                    </p>
                </div>
            """, unsafe_allow_html=True)
        except Exception:
            pass
    
    st.markdown("---")
    
    # Step 6: Intelligence Source Name
    st.markdown('<p class="step-header">Step 6: Name Your Intelligence Source</p>', unsafe_allow_html=True)
    st.write("Give your intelligence source a name (this can be a newsletter, briefing, or any intelligence deliverable):")
    
    newsletter_name = st.text_input(
        "Intelligence Source Name",
        value=st.session_state.specification["newsletter_name"],
        placeholder="e.g., 'EMEA PU Market Weekly' or 'Strategic PU Intelligence Brief'",
        help="3-100 characters, letters, numbers, spaces, hyphens, and underscores only"
    )
    
    st.session_state.specification["newsletter_name"] = newsletter_name
    
    # Step 7: Company and Contact
    st.markdown('<p class="step-header">Step 7: Company and Contact Information</p>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        company_name = st.text_input(
            "Company Name",
            value=st.session_state.specification["company_name"],
            placeholder="Your company name"
        )
        st.session_state.specification["company_name"] = company_name
    
    with col2:
        contact_email = st.text_input(
            "Contact Email",
            value=st.session_state.specification["contact_email"],
            placeholder="your.email@company.com",
            type="default"
        )
        st.session_state.specification["contact_email"] = contact_email
    
    col3, col4 = st.columns(2)
    with col3:
        first_name = st.text_input(
            "First Name",
            value=st.session_state.specification.get("first_name", ""),
            placeholder="Your first name"
        )
        st.session_state.specification["first_name"] = first_name
    
    with col4:
        last_name = st.text_input(
            "Last Name",
            value=st.session_state.specification.get("last_name", ""),
            placeholder="Your last name"
        )
        st.session_state.specification["last_name"] = last_name
    
    st.markdown("**Company Address:**")
    col5, col6 = st.columns([3, 1])
    with col5:
        street = st.text_input(
            "Street",
            value=st.session_state.specification.get("street", ""),
            placeholder="Street name"
        )
        st.session_state.specification["street"] = street
    
    with col6:
        house_number = st.text_input(
            "House Number",
            value=st.session_state.specification.get("house_number", ""),
            placeholder="123"
        )
        st.session_state.specification["house_number"] = house_number
    
    col7, col8, col9 = st.columns(3)
    with col7:
        city = st.text_input(
            "City",
            value=st.session_state.specification.get("city", ""),
            placeholder="City"
        )
        st.session_state.specification["city"] = city
    
    with col8:
        zip_code = st.text_input(
            "ZIP Code",
            value=st.session_state.specification.get("zip_code", ""),
            placeholder="12345"
        )
        st.session_state.specification["zip_code"] = zip_code
    
    with col9:
        country = st.text_input(
            "Country",
            value=st.session_state.specification.get("country", ""),
            placeholder="Country"
        )
        st.session_state.specification["country"] = country
    
    vat_number = st.text_input(
        "VAT Number (Optional)",
        value=st.session_state.specification.get("vat_number", ""),
        placeholder="VAT/Tax ID number"
    )
    st.session_state.specification["vat_number"] = vat_number
    
    # Step 8: Review and Submit
    st.markdown('<p class="step-header">Step 8: Review and Submit</p>', unsafe_allow_html=True)
    
    # Show summary
    st.markdown("### Specification Summary")
    
    spec = st.session_state.specification
    
    summary_col1, summary_col2 = st.columns(2)
    
    with summary_col1:
        st.write("**Intelligence Source Name:**")
        st.write(spec["newsletter_name"] or "*Not set*")
        
        st.write("**Selected Categories:**")
        if spec["categories"]:
            selected_cat_names = [cat["name"] for cat in categories_list if cat["id"] in spec["categories"]]
            for cat_name in selected_cat_names:
                st.write(f"- {cat_name}")
        else:
            st.write("*None selected*")
        
        st.write("**Value Chain Link(s):**")
        if spec.get("value_chain_links"):
            vcl_names = [l["name"] for l in VALUE_CHAIN_LINKS if l["id"] in spec["value_chain_links"]]
            for name in vcl_names:
                st.write(f"- {name}")
        else:
            st.write("*None selected*")
        
        st.write("**Selected Regions:**")
        if spec["regions"]:
            for region in spec["regions"]:
                st.write(f"- {region}")
        else:
            st.write("*None selected*")
    
    with summary_col2:
        st.write("**Frequency:**")
        freq_label = next((f["label"] for f in FREQUENCIES if f["value"] == spec["frequency"]), "Not selected")
        st.write(freq_label)
        
        st.write("**Company:**")
        st.write(spec["company_name"] or "*Not set*")
        
        st.write("**Contact Email:**")
        st.write(spec["contact_email"] or "*Not set*")
        
        st.write("**Contact Name:**")
        contact_name = f"{spec.get('first_name', '')} {spec.get('last_name', '')}".strip()
        st.write(contact_name or "*Not set*")
        
        st.write("**Company Address:**")
        address_parts = []
        if spec.get('street'):
            address_parts.append(spec.get('street'))
        if spec.get('house_number'):
            address_parts.append(spec.get('house_number'))
        if address_parts:
            st.write(f"{', '.join(address_parts)}")
        if spec.get('city'):
            city_line = spec.get('city')
            if spec.get('zip_code'):
                city_line += f" {spec.get('zip_code')}"
            st.write(city_line)
        if spec.get('country'):
            st.write(spec.get('country'))
        if not any([spec.get('street'), spec.get('city'), spec.get('country')]):
            st.write("*Not set*")
        
        if spec.get('vat_number'):
            st.write("**VAT Number:**", spec.get('vat_number'))
    
    # Submit button
    st.markdown("---")
    
    if st.button("Submit Specification Request", type="primary", use_container_width=True):
        # Validate all fields
        is_valid, errors = validate_specification(
            spec["categories"],
            spec["regions"],
            spec["frequency"],
            spec["newsletter_name"],
            spec["company_name"],
            spec["contact_email"]
        )
        
        if not is_valid:
            st.error("Please fix the following errors:")
            for error in errors:
                st.error(f"• {error}")
        else:
            # Categories to save: include value_chain_link if user selected any value chain links
            categories_to_save = list(spec["categories"])
            if spec.get("value_chain_links"):
                if "value_chain_link" not in categories_to_save:
                    categories_to_save.append("value_chain_link")
            try:
                # Check if we're updating an existing request
                if st.session_state.get("request_id"):
                    # Update existing request
                    result = update_specification_request(
                        request_id=st.session_state.request_id,
                        newsletter_name=spec["newsletter_name"],
                        industry_code=INDUSTRY_CODE,
                        categories=categories_to_save,
                        regions=spec["regions"],
                        frequency=spec["frequency"],
                        company_name=spec["company_name"],
                        contact_email=spec["contact_email"],
                        first_name=spec.get("first_name", ""),
                        last_name=spec.get("last_name", ""),
                        street=spec.get("street", ""),
                        house_number=spec.get("house_number", ""),
                        city=spec.get("city", ""),
                        zip_code=spec.get("zip_code", ""),
                        country=spec.get("country", ""),
                        vat_number=spec.get("vat_number", "")
                    )
                    st.success("✅ Specification updated successfully!")
                else:
                    # Create new request
                    result = create_specification_request(
                        newsletter_name=spec["newsletter_name"],
                        industry_code=INDUSTRY_CODE,
                        categories=categories_to_save,
                        regions=spec["regions"],
                        frequency=spec["frequency"],
                        company_name=spec["company_name"],
                        contact_email=spec["contact_email"],
                        first_name=spec.get("first_name", ""),
                        last_name=spec.get("last_name", ""),
                        street=spec.get("street", ""),
                        house_number=spec.get("house_number", ""),
                        city=spec.get("city", ""),
                        zip_code=spec.get("zip_code", ""),
                        country=spec.get("country", ""),
                        vat_number=spec.get("vat_number", "")
                    )
                
                # Store the request ID for confirmation
                st.session_state.request_id = result.get("id", "unknown")
                if "submission_timestamp" in result:
                    st.session_state.submission_timestamp = result.get("submission_timestamp")
                elif not st.session_state.get("submission_timestamp"):
                    st.session_state.submission_timestamp = datetime.utcnow().isoformat()
                st.session_state.submitted = True
                # Don't rerun - let the success content render immediately below
                
            except Exception as e:
                st.error(f"Error submitting specification: {str(e)}")
                st.exception(e)

# Show success page BELOW the submit button if submitted
if st.session_state.submitted:
    spec = st.session_state.specification
    
    # Calculate price
    price_data = calculate_price(
        categories=spec["categories"],
        regions=spec["regions"],
        frequency=spec["frequency"],
        package_tier=spec.get("package_tier")
    )
    
    if st.session_state.get("request_id") and st.session_state.get("submission_timestamp"):
        # Check if this is an update (has updated_at different from submission_timestamp)
        st.success("✅ Your specification request has been updated successfully!")
    else:
        st.success("✅ Your specification request has been submitted successfully!")
    
    # Edit Specification button
    col_edit1, col_edit2, col_edit3 = st.columns([1, 2, 1])
    with col_edit2:
        if st.button("✏️ Edit Specification", type="secondary", use_container_width=True):
            st.session_state.submitted = False
            st.rerun()
    
    st.markdown("---")
    
    # Show confirmation details
    request_id = st.session_state.get("request_id", "N/A")
    submission_time = st.session_state.get("submission_timestamp", "")
    
    st.markdown("---")
    st.markdown("### 📋 Request Confirmation")
    
    col1, col2 = st.columns(2)
    with col1:
        st.write("**Request ID:**")
        st.code(request_id, language=None)
        st.caption("Save this ID for your records")
    
    with col2:
        if submission_time:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(submission_time.replace('Z', '+00:00'))
                formatted_time = dt.strftime("%Y-%m-%d %H:%M UTC")
            except:
                formatted_time = submission_time[:19] if len(submission_time) > 19 else submission_time
            st.write("**Submitted:**", formatted_time)
        st.write("**Status:**", "Pending Review")
    
    st.info("""
        **Your request has been saved and will be reviewed by our team.**
        You will receive email updates at **{}** regarding the status of your request.
    """.format(spec["contact_email"]))
    
    st.markdown("---")
    st.markdown("### 💰 Pricing")
    
    # Display price prominently
    st.markdown(f"""
        <div style="background-color: #f0f2f6; padding: 2rem; border-radius: 0.5rem; text-align: center; margin: 2rem 0;">
            <h2 style="color: #1f77b4; margin-bottom: 0.5rem;">Annual Price</h2>
            <div style="font-size: 3rem; font-weight: bold; color: #1f77b4; margin: 1rem 0;">
                {format_price(price_data)}
            </div>
            <p style="color: #666; margin-top: 1rem;">
                {format_price(price_data, show_per_user=True)} ({spec['frequency']} cadence)
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    # Price breakdown
    with st.expander("📊 View Price Breakdown"):
        breakdown = price_data["breakdown"]
        cadence_info = breakdown["cadence"]
        scope_info = breakdown["scope"]
        
        st.write(f"**Cadence:** {cadence_info['label']}")
        st.write(f"  - Per user per month: ${cadence_info['price_per_user_monthly']:,.0f}")
        st.write(f"  - Per user per year: ${cadence_info['price_per_user_yearly']:,.0f}")
        st.write(f"**Users:** {breakdown['users']['count']} ({breakdown['users']['note']})")
        st.write(f"**Scope:** {scope_info['tier']} tier")
        st.write(f"  - Categories: {scope_info['categories_count']}")
        st.write(f"  - Regions: {scope_info['regions_count']}")
        st.write(f"  - {scope_info['note']}")
        st.markdown("---")
        st.write(f"**Monthly Total:** ${breakdown['total_monthly']:,.0f}")
        st.write(f"**Annual Total:** **{format_price(price_data)}**")
    
    st.markdown("---")
    
    # Order Now button with mailto
    vcl_names = ', '.join([l['name'] for l in VALUE_CHAIN_LINKS if l['id'] in spec.get('value_chain_links', [])]) or 'None'
    spec_summary = f"""
Intelligence Source Name: {spec['newsletter_name']}
Company: {spec['company_name']}
Contact: {spec.get('first_name', '')} {spec.get('last_name', '')}
Contact Email: {spec['contact_email']}
Categories: {', '.join([cat['name'] for cat in categories_list if cat['id'] in spec['categories']])}
Value Chain Links: {vcl_names}
Regions: {', '.join(spec['regions'])}
Frequency: {spec['frequency'].title()}
Annual Price: {format_price(price_data)}
"""
    
    mailto_subject = f"Order Request: {spec['newsletter_name']}"
    mailto_body = f"Please process my order for the following PU Observatory intelligence specification:\n\n{spec_summary}"
    
    # Properly encode mailto link with customer email in CC
    customer_email = spec['contact_email']
    mailto_link = f"mailto:stefan.hermes@htcglobal.asia?cc={quote(customer_email)}&subject={quote(mailto_subject)}&body={quote(mailto_body)}"
    
    st.markdown(f"""
        <div style="text-align: center; margin: 2rem 0;">
            <a href="{mailto_link}" style="background-color: #1f77b4; color: white; padding: 1rem 2rem; text-decoration: none; border-radius: 0.5rem; font-size: 1.2rem; font-weight: bold; display: inline-block;">
                📧 Order Now
            </a>
        </div>
    """, unsafe_allow_html=True)
    
    st.info("""
        **What happens next?**
        1. Click "Order Now" to send your order request via email
        2. We'll review your specification and prepare an invoice
        3. After payment confirmation, your intelligence source will be activated
        4. You'll receive access credentials to generate content
    """)
    
    st.markdown("---")
    st.markdown("### 📄 Specification Summary")
    
    col1, col2 = st.columns(2)
    with col1:
        st.write("**Intelligence Source Name:**", spec["newsletter_name"])
        st.write("**Company:**", spec["company_name"])
        contact_name = f"{spec.get('first_name', '')} {spec.get('last_name', '')}".strip()
        if contact_name:
            st.write("**Contact:**", contact_name)
        st.write("**Contact Email:**", spec["contact_email"])
    
    with col2:
        st.write("**Frequency:**", spec["frequency"].title())
        st.write("**Categories:**", len(spec["categories"]), "selected")
        if spec.get("value_chain_links"):
            st.write("**Value Chain Links:**", ", ".join([l["name"] for l in VALUE_CHAIN_LINKS if l["id"] in spec["value_chain_links"]]))
        st.write("**Regions:**", len(spec["regions"]), "selected")
    
    # Show where to view status
    st.markdown("---")
    st.markdown("### 📍 Where is my request stored?")
    st.write("""
        Your specification request has been saved to our database with the following details:
        - **Request ID:** `{}`
        - **Status:** Pending Review
        - **Contact Email:** {}
        
        **What happens next:**
        1. Our admin team will review your request
        2. You'll receive updates via email at the address provided
        3. Once approved, you'll receive an invoice and payment instructions
        4. After payment, your intelligence source will be activated
        
        **Note:** You can reference your Request ID when contacting us about this specification.
    """.format(request_id, spec["contact_email"]))

# Footer
st.markdown("---")
st.markdown("""
    <div style="text-align: center; color: #666; font-size: 0.9rem; margin-top: 2rem;">
        <p>Polyurethane Industry Observatory</p>
        <p>Curated and published by <strong>Global NewsPilot</strong>, a division of HTC Global</p>
    </div>
""", unsafe_allow_html=True)

