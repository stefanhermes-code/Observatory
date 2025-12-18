"""
Core taxonomy definitions for the PU Observatory platform.
Contains the 11-category model and region lists.
"""

# The 10 deliverable categories for PU Observatory
PU_CATEGORIES = [
    {
        "id": "company_news",
        "name": "Company News Tracking",
        "description": "Latest verified news on PU-relevant companies across the value chain"
    },
    {
        "id": "regional_monitoring",
        "name": "Regional Market Monitoring",
        "description": "Aggregated updates by region (EMEA, Middle East, China, NE Asia, SEA, India)"
    },
    {
        "id": "industry_context",
        "name": "Industry Context & Insight",
        "description": "Interpretation of news: supply/demand impact, margin pressure, trade flow shifts"
    },
    {
        "id": "value_chain",
        "name": "PU Value-Chain Analysis",
        "description": "Analysis by product: MDI, TDI, polyether/polyester polyols, systems, additives"
    },
    {
        "id": "competitive",
        "name": "Competitive Intelligence",
        "description": "Side-by-side comparison of major producers' actions and positioning"
    },
    {
        "id": "sustainability",
        "name": "Sustainability & Regulation Tracking",
        "description": "Decarbonization projects, low-PCF products, REACH/diisocyanates compliance"
    },
    {
        "id": "capacity",
        "name": "Capacity & Asset Moves",
        "description": "New plants, expansions, shutdowns, mothballing, asset sales"
    },
    {
        "id": "m_and_a",
        "name": "M&A and Partnerships",
        "description": "Acquisitions, JVs, strategic partnerships relevant to PU"
    },
    {
        "id": "early_warning",
        "name": "Early-Warning Signals",
        "description": "Subtle indicators (price moves, utilization comments, restructuring language)"
    },
    {
        "id": "executive_briefings",
        "name": "Executive-Ready Briefings",
        "description": "Condensed, decision-focused summaries (1-2 page briefing or slide-ready bullets)"
    }
]

# Available regions for selection
REGIONS = [
    "EMEA",
    "Middle East",
    "China",
    "NE Asia",
    "SEA",
    "India",
    "North America",
    "South America"
]

# Frequency options
FREQUENCIES = [
    {
        "value": "daily",
        "label": "Daily",
        "description": "Continuous monitoring, early-warning signals, rapid insight"
    },
    {
        "value": "weekly",
        "label": "Weekly",
        "description": "Operational monitoring with context and implications"
    },
    {
        "value": "monthly",
        "label": "Monthly",
        "description": "Strategic overview, themes, and outlook"
    }
]

# Industry code
INDUSTRY_CODE = "PU"

