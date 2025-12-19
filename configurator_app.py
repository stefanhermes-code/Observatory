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

from core.taxonomy import PU_CATEGORIES, REGIONS, FREQUENCIES, INDUSTRY_CODE
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
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if "step" not in st.session_state:
    st.session_state.step = 1
if "specification" not in st.session_state:
    st.session_state.specification = {
        "categories": [],
        "regions": [],
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
    
    1. **Define Intelligence Scope** - Select the categories of intelligence you want to track (e.g., Company News, Capacity Changes, Market Developments)
    
    2. **Select Regions** - Choose the geographic regions you want to monitor (e.g., EMEA, Americas, Asia)
    
    3. **Choose Frequency** - Select how often you want to receive updates:
       - **Monthly**: Strategic overview, themes, and outlook ($19/user/month)
       - **Weekly**: Operational monitoring with context ($39/user/month)
       - **Daily**: Continuous monitoring, early-warning signals ($119/user/month)
    
    4. **Name Your Intelligence Source** - Give your customized intelligence source a name
    
    5. **Provide Company Information** - Enter your company details and contact information
    
    6. **Review & Submit** - Review your selections and see the pricing, then submit your request
    
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
    st.markdown("Your selection of categories and regions determines your package tier:")
    
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
    
    st.markdown("**Note:** Scope determines your package tier, but all plans include access to the full Observatory platform and all deliverables.")
    
    st.markdown("#### Example Calculations")
    st.markdown("""
    <ul>
        <li><strong>Monthly</strong> with 3 categories, 1 region: $19/user/month = <strong>$228/user/year</strong></li>
        <li><strong>Weekly</strong> with 6 categories, 2 regions: $39/user/month = <strong>$468/user/year</strong></li>
        <li><strong>Daily</strong> with 9 categories, 4 regions: $119/user/month = <strong>$1,428/user/year</strong></li>
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
    # Step 1: Scope Definition (Categories) - 2 columns
    st.markdown('<p class="step-header">Step 1: Define Intelligence Scope</p>', unsafe_allow_html=True)
    st.write("Select one or more categories that your intelligence source should cover:")
    
    selected_categories = []
    
    # Display categories in 2 columns
    col1, col2 = st.columns(2)
    
    for idx, category in enumerate(categories_list):
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
    
    # Step 2: Region Selection - Checkboxes like categories
    st.markdown('<p class="step-header">Step 2: Select Regions</p>', unsafe_allow_html=True)
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
    
    if len(selected_regions) == 0:
        st.warning("⚠️ Please select at least one region to continue.")
    
    # Step 3: Frequency Selection
    st.markdown('<p class="step-header">Step 3: Choose Frequency</p>', unsafe_allow_html=True)
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
    
    # Real-time price estimate (prominently displayed) - shown once after step 3 is completed
    if len(st.session_state.specification.get("categories", [])) > 0 and len(st.session_state.specification.get("regions", [])) > 0:
        try:
            from core.pricing import calculate_price, format_price
            price_data = calculate_price(
                categories=st.session_state.specification.get("categories", []),
                regions=st.session_state.specification.get("regions", []),
                frequency=selected_frequency
            )
            st.markdown(f"""
                <div style="background-color: #e8f4f8; padding: 1rem; border-radius: 0.5rem; border-left: 4px solid #1f77b4; margin: 1rem 0;">
                    <strong style="color: #1f77b4; font-size: 1.1rem;">💰 Estimated Annual Price:</strong>
                    <div style="font-size: 2rem; font-weight: bold; color: #1f77b4; margin-top: 0.5rem;">
                        {format_price(price_data)}
                    </div>
                    <p style="color: #666; margin-top: 0.5rem; font-size: 0.9rem;">
                        {format_price(price_data, show_per_user=True)} ({selected_frequency.title()} cadence)
                    </p>
                </div>
            """, unsafe_allow_html=True)
        except Exception:
            pass
    
    st.markdown("---")
    
    # Step 4: Intelligence Source Name
    st.markdown('<p class="step-header">Step 4: Name Your Intelligence Source</p>', unsafe_allow_html=True)
    st.write("Give your intelligence source a name (this can be a newsletter, briefing, or any intelligence deliverable):")
    
    newsletter_name = st.text_input(
        "Intelligence Source Name",
        value=st.session_state.specification["newsletter_name"],
        placeholder="e.g., 'EMEA PU Market Weekly' or 'Strategic PU Intelligence Brief'",
        help="3-100 characters, letters, numbers, spaces, hyphens, and underscores only"
    )
    
    st.session_state.specification["newsletter_name"] = newsletter_name
    
    # Step 5: Company and Contact
    st.markdown('<p class="step-header">Step 5: Company and Contact Information</p>', unsafe_allow_html=True)
    
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
    
    # Step 6: Review and Submit
    st.markdown('<p class="step-header">Step 6: Review and Submit</p>', unsafe_allow_html=True)
    
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
            # Create or update specification request
            try:
                # Check if we're updating an existing request
                if st.session_state.get("request_id"):
                    # Update existing request
                    result = update_specification_request(
                        request_id=st.session_state.request_id,
                        newsletter_name=spec["newsletter_name"],
                        industry_code=INDUSTRY_CODE,
                        categories=spec["categories"],
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
                        categories=spec["categories"],
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
        frequency=spec["frequency"]
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
    spec_summary = f"""
Intelligence Source Name: {spec['newsletter_name']}
Company: {spec['company_name']}
Contact: {spec.get('first_name', '')} {spec.get('last_name', '')}
Contact Email: {spec['contact_email']}
Categories: {', '.join([cat['name'] for cat in categories_list if cat['id'] in spec['categories']])}
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

