"""
Core taxonomy definitions for the PU Observatory platform.
Contains the 10-category model, region lists, and PU industry base knowledge.
Base knowledge (materials, value chain, chemicals) is used for search queries and for API context
so the Response API / Assistant can give accurate answers.
"""

# --- PU industry base knowledge (single source of truth for queries and API) ---

# PU materials in scope of the PU industry (what the industry produces)
PU_MATERIALS = "flexible foam rigid foam moulded foam TPU thermoplastic polyurethane CASE coatings adhesives sealants elastomers polyurethane"

# Chemicals needed and/or used in all types of PU materials (flexible foam, rigid foam, moulded foam, TPU, CASE).
# Plain list for API context; PU_CHEMICALS below is the space-separated form for search queries.
PU_CHEMICALS_LIST = """
Primary reactants:
  Isocyanates: MDI, TDI, HDI, H12MDI, IPDI (aromatic and aliphatic isocyanates).
  Polyols: polyether polyols, polyester polyols, acrylic polyols.

Processing and performance:
  Catalysts: amine catalysts, tin catalysts (drive isocyanate-polyol reaction).
  Blowing agents: used to create foam structure (flexible, rigid, moulded foam).
  Surfactants: silicones and others for foam structure and processing.
  Chain extenders: modify polymer properties and structure.

Additives and modifiers:
  Flame retardants.
  Fillers, pigments.
  Mold release agents.
  Solvents (where used in formulations).
"""

# Space-separated form for search queries (from the list above)
PU_CHEMICALS = "MDI TDI HDI polyols isocyanates silicones amines catalysts blowing agents surfactants chain extenders flame retardants additives"

# Value chain ecosystem: who does what in the PU industry (plain text, no markdown)
PU_VALUE_CHAIN_ECOSYSTEM = """
Chemical manufacturers (raw materials / intermediates): produce chemicals for PU materials (isocyanates, polyols, silicones, amines, catalysts, blowing agents, surfactants, additives, etc.).
System houses: mix chemicals to produce PU materials and systems (formulations, systems for foam, CASE, TPU).
Foam manufacturers and converters: produce PU foam (flexible, rigid, moulded).
End users: use PU materials in their components and end products (e.g. automotive, mattresses, construction, appliances).
"""

# Full base knowledge block: sent to the API (plain text, no markdown)
PU_INDUSTRY_BASE_KNOWLEDGE = """
PU materials (in scope): Flexible foam, rigid foam, moulded foam, TPU (thermoplastic polyurethane), CASE (coatings, adhesives, sealants, elastomers). These are the PU materials the industry produces.

Chemicals for PU materials (needed and/or used in all types of PU materials):
Primary reactants: Isocyanates (MDI, TDI, HDI, H12MDI, IPDI). Polyols (polyether, polyester, acrylic polyols).
Processing and performance: Catalysts (amine, tin). Blowing agents. Surfactants (silicones and others). Chain extenders.
Additives and modifiers: Flame retardants, fillers, pigments, mold release agents, solvents where used.
Chemical manufacturers produce these; it is not only MDI/TDI/polyols but also silicones, amines, catalysts, blowing agents, surfactants, and related intermediates.

Value chain (ecosystem):
""" + PU_VALUE_CHAIN_ECOSYSTEM.strip()

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
        "id": "value_chain_link",
        "name": "Link in the PU Value Chain",
        "description": "Intelligence tagged by value chain position: raw materials/intermediates, system houses, foam manufacturers & converters, end-use (e.g. automotive, mattresses)"
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

# Value chain link options for Step 2 (separate from categories)
VALUE_CHAIN_LINKS = [
    {"id": "raw_materials", "name": "Raw materials / Intermediates", "description": "Chemical manufacturers produce chemicals for PU materials: MDI, TDI, polyols, silicones, amines, catalysts, additives, blowing agents, and related intermediates"},
    {"id": "system_houses", "name": "System houses", "description": "Formulators and system providers"},
    {"id": "foam_converters", "name": "Foam manufacturers & converters", "description": "Foam production, moulding, conversion"},
    {"id": "end_use", "name": "End-use", "description": "e.g. automotive, mattresses, construction, appliances"}
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

# Region keywords/aliases for content-based relevance filter. A candidate is kept only if title or snippet
# contains at least one of these for the assigned region (so we do not keep "China" articles in a SEA-only report).
REGION_KEYWORDS = {
    "EMEA": ["EMEA", "Europe", "European", "EU", "Germany", "France", "UK", "Italy", "Spain", "Netherlands", "Belgium", "Poland"],
    "Middle East": ["Middle East", "Gulf", "UAE", "Saudi", "Qatar", "Bahrain", "Kuwait", "Oman", "Iran", "Iraq"],
    "China": ["China", "Chinese", "PRC", "mainland China"],
    "NE Asia": ["NE Asia", "Northeast Asia", "Japan", "Japanese", "Korea", "Korean", "Taiwan", "Hong Kong"],
    "SEA": ["SEA", "Southeast Asia", "ASEAN", "Singapore", "Malaysia", "Thailand", "Indonesia", "Vietnam", "Philippines", "Myanmar", "Cambodia", "Laos"],
    "India": ["India", "Indian"],
    "North America": ["North America", "USA", "US ", "United States", "Canada", "American", "Mexico"],
    "South America": ["South America", "Brazil", "Brazilian", "Argentina", "Chile", "Colombia", "Latin America"],
}

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

