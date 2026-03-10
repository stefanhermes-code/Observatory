"""
V2 Query planner: builds search query plan from spec (code-only, no LLM).
Stable for same spec options. Outputs list of {query_id, query_text, intent}.
Every query anchors on PU materials so results are about the actual industry scope.
Uses base knowledge from taxonomy (PU materials, chemicals, value chain ecosystem).
"""

import os
from typing import List, Dict, Any, Set, Tuple

from core.taxonomy import PU_MATERIALS, PU_CHEMICALS

# Value chain link id -> ecosystem role (who does what). Queries use this so results reflect the PU industry ecosystem.
VALUE_CHAIN_ECOSYSTEM = {
    "raw_materials": f"chemical manufacturers produce chemicals for polyurethane materials {PU_CHEMICALS}",
    "system_houses": "system houses formulators mix chemicals produce polyurethane materials systems",
    "foam_converters": "foam manufacturers converters produce polyurethane foam flexible rigid moulded",
    "end_use": "end use polyurethane materials automotive mattresses construction appliances components",
}

# Category id -> search angle (prepended with PU_MATERIALS in the query)
CATEGORY_QUERY_TOKENS = {
    "company_news": "company news",
    "regional_monitoring": "market region",
    "industry_context": "industry supply demand margins",
    "value_chain": "value chain MDI TDI polyols",
    "value_chain_link": "value chain",
    "competitive": "producers competitive",
    "sustainability": "sustainability REACH decarbonization diisocyanates",
    "capacity": "capacity expansion plant",
    "m_and_a": "acquisition partnership M&A",
    "early_warning": "price demand utilization",
    "executive_briefings": "market briefing",
}


def _add_query(
    queries: List[Dict[str, Any]],
    seen: Set[Tuple[str, str]],
    max_queries: int,
    qid: str,
    text: str,
    intent: str,
) -> None:
    text = (text or "").strip()
    if not text:
        return
    key = (qid, text.lower())
    if key in seen or len(queries) >= max_queries:
        return
    seen.add(key)
    queries.append({"query_id": qid, "query_text": text, "intent": intent})


def _build_query_plan_current(
    regions: List[str],
    categories: List[str],
    value_chain_links: List[str],
    company_aliases: List[str],
    max_queries: int = 30,
) -> List[Dict[str, Any]]:
    """
    Original deterministic query plan from spec.
    Returns list of {"query_id": str, "query_text": str, "intent": str}.
    """
    queries: List[Dict[str, Any]] = []
    seen: Set[Tuple[str, str]] = set()

    # 1) Region-based: PU materials + region + news
    for r in (regions or [])[:8]:
        _add_query(
            queries,
            seen,
            max_queries,
            f"region_{r.replace(' ', '_')}",
            f"{PU_MATERIALS} {r} news",
            f"region:{r}",
        )

    # 2) Category-based: PU materials + category angle
    for cat in (categories or [])[:10]:
        angle = CATEGORY_QUERY_TOKENS.get(cat, "industry")
        _add_query(
            queries,
            seen,
            max_queries,
            f"cat_{cat}",
            f"{PU_MATERIALS} {angle}",
            f"category:{cat}",
        )

    # 3) Value chain: PU materials + ecosystem role (who does what in the PU industry)
    for vcl in (value_chain_links or [])[:4]:
        ecosystem = VALUE_CHAIN_ECOSYSTEM.get(vcl, vcl.replace("_", " "))
        _add_query(
            queries,
            seen,
            max_queries,
            f"vcl_{vcl}",
            f"{PU_MATERIALS} {ecosystem}",
            f"value_chain:{vcl}",
        )

    # 4) Company-specific: company + PU materials + news
    for alias in (company_aliases or [])[:15]:
        alias = (alias or "").strip()
        if not alias or len(alias) < 2:
            continue
        _add_query(
            queries,
            seen,
            max_queries,
            f"company_{hash(alias) % 10**6}",
            f"{alias} {PU_MATERIALS} news",
            "company",
        )

    # No generic fallback: only run queries that match the user's selection (regions, categories, value chain links, company).
    # Reporting links that were not part of the chosen scope would be wrong.

    return queries


def _build_query_plan_sequential_simplified(
    regions: List[str],
    categories: List[str],
    value_chain_links: List[str],
    company_aliases: List[str],
    max_queries: int = 80,
) -> List[Dict[str, Any]]:
    """
    Simplified sequential query planner for long structural runs.
    Focuses on broad industry intents, application anchors, and company news.
    """
    del value_chain_links  # unused in this strategy (kept for signature compatibility)

    queries: List[Dict[str, Any]] = []
    seen: Set[Tuple[str, str]] = set()

    # F1: Polyurethane industry + intent
    f1_intents = [
        "news",
        "capacity expansion",
        "mergers acquisitions",
        "pricing",
        "regulation",
        "investment",
    ]
    for intent in f1_intents:
        _add_query(
            queries,
            seen,
            max_queries,
            f"seq_f1_{intent.replace(' ', '_')}",
            f"polyurethane industry {intent}",
            intent,
        )

    # F2: Application anchors + market news
    application_anchors = [
        "polyurethane foam",
        "polyurethane insulation",
        "polyurethane coatings",
        "polyurethane adhesives",
    ]
    for anchor in application_anchors:
        _add_query(
            queries,
            seen,
            max_queries,
            f"seq_f2_{anchor.replace(' ', '_')}",
            f"{anchor} market news",
            "application_market_news",
        )

    # F3: Company news (only when company_news is in categories)
    if "company_news" in (categories or []):
        company_intents = [
            "acquisition",
            "investment",
            "plant expansion",
            "capacity",
            "restructuring",
            "regulation",
        ]
        for alias in (company_aliases or [])[:80]:
            alias_clean = (alias or "").strip()
            if not alias_clean or len(alias_clean) < 2:
                continue
            for intent in company_intents:
                _add_query(
                    queries,
                    seen,
                    max_queries,
                    f"seq_f3_{hash(alias_clean) % 10**6}_{intent.replace(' ', '_')}",
                    f"{alias_clean} polyurethane {intent}",
                    f"company_{intent}",
                )

    # Coarse regional coverage
    coarse_regions = ["Europe", "Asia", "Americas"]
    for region in coarse_regions[:3]:
        _add_query(
            queries,
            seen,
            max_queries,
            f"seq_region_{region}",
            f"polyurethane industry {region} news",
            f"region_coarse:{region}",
        )

    return queries


# Phase 3: Simple two-word queries (anchor + topic) for signal harvest expansion.
# Every query contains a PU anchor; multiple simpler searches instead of complex AND queries.
PHASE3_PU_ANCHORS = [
    "polyurethane",
    "PU foam",
    "polyurethane foam",
    "PU insulation",
    "polyurethane elastomer",
    "polyurethane adhesive",
    "polyurethane coating",
    "MDI",
    "TDI",
    "polyol",
    "isocyanate",
]
PHASE3_TOPICS = [
    "market",
    "industry",
    "plant",
    "capacity",
    "foam",
    "technology",
    "recycling",
    "insulation",
    "automotive",
    "expansion",
    "acquisition",
    "investment",
    "sustainability",
    "regulation",
    "materials",
    "chemicals",
    "news",
    "demand",
    "pricing",
]


def build_query_plan_phase3_harvest(max_queries: int = 120) -> List[Dict[str, Any]]:
    """
    Phase 3 harvest expansion: multiple simpler searches, each with one PU anchor + one topic.
    Used by run_phase3_harvest_expansion; does not use regions/categories/company.
    """
    queries: List[Dict[str, Any]] = []
    seen: Set[Tuple[str, str]] = set()
    # Primary: polyurethane + each topic
    for topic in PHASE3_TOPICS:
        qtext = f"polyurethane {topic}"
        qid = f"p3_pu_{topic}"
        _add_query(queries, seen, max_queries, qid, qtext, f"topic:{topic}")
    # Additional anchors + selected topics for diversity
    for anchor in ["PU foam", "polyurethane foam", "MDI", "TDI", "polyol"]:
        for topic in ["market", "industry", "capacity", "news"]:
            qtext = f"{anchor} {topic}"
            qid = f"p3_{anchor.replace(' ', '_')}_{topic}"
            _add_query(queries, seen, max_queries, qid, qtext, f"anchor:{anchor}")
    return queries


def build_query_plan_phase3b(max_queries: int = 80) -> List[Dict[str, Any]]:
    """
    Phase 3B: Query expansion test.
    Explicit short queries across four areas:
      - Polyurethane raw materials
      - Polyurethane applications
      - Sustainability and recycling
      - Corporate and capacity activity
    All queries contain a polyurethane anchor term; no AND-style long queries.
    """
    queries: List[Dict[str, Any]] = []
    seen: Set[Tuple[str, str]] = set()

    # A. Polyurethane raw materials
    raw_material_queries = [
        "polyurethane MDI",
        "polyurethane TDI",
        "polyurethane polyol",
        "MDI market polyurethane",
        "TDI market polyurethane",
        "polyol production polyurethane",
        "isocyanate market polyurethane",
        "polyurethane raw materials",
        "polyurethane chemicals",
        "polyurethane feedstock",
        "polyurethane diisocyanate",
        "polyurethane polyether polyol",
        "polyurethane polyester polyol",
    ]

    # B. Polyurethane applications
    application_queries = [
        "polyurethane automotive",
        "polyurethane automotive materials",
        "polyurethane construction",
        "polyurethane construction materials",
        "polyurethane insulation",
        "polyurethane building insulation",
        "polyurethane footwear",
        "polyurethane shoe materials",
        "polyurethane adhesives",
        "polyurethane coatings",
        "polyurethane elastomer",
        "polyurethane foam furniture",
        "polyurethane mattress foam",
        "polyurethane appliance insulation",
        "polyurethane seating foam",
    ]

    # C. Sustainability and recycling
    sustainability_queries = [
        "polyurethane recycling",
        "polyurethane foam recycling",
        "polyurethane circular economy",
        "polyurethane closed loop",
        "bio polyol polyurethane",
        "bio-based polyurethane polyol",
        "chemical recycling polyurethane",
        "polyurethane waste recycling",
        "sustainable polyurethane materials",
        "low carbon polyurethane",
        "polyurethane emissions reduction",
    ]

    # D. Corporate and capacity activity
    corporate_queries = [
        "polyurethane plant",
        "polyurethane factory",
        "polyurethane capacity expansion",
        "polyurethane capacity increase",
        "polyurethane investment",
        "polyurethane capex",
        "polyurethane production facility",
        "polyurethane plant expansion",
        "polyurethane greenfield plant",
        "polyurethane brownfield expansion",
        "polyurethane joint venture plant",
    ]

    def _add_phase3b_group(group_id: str, qs: List[str]) -> None:
        for i, qtext in enumerate(qs, start=1):
            q = (qtext or "").strip()
            if not q:
                continue
            key = (group_id, q.lower())
            if key in seen or len(queries) >= max_queries:
                continue
            seen.add(key)
            queries.append(
                {
                    "query_id": f"p3b_{group_id}_{i}",
                    "query_text": q,
                    "intent": group_id,
                }
            )

    _add_phase3b_group("raw_materials", raw_material_queries)
    _add_phase3b_group("applications", application_queries)
    _add_phase3b_group("sustainability", sustainability_queries)
    _add_phase3b_group("corporate", corporate_queries)

    return queries


# Adjustment run: extra sustainability and corporate queries to improve coverage of those categories.
ADJUSTMENT_SUSTAINABILITY_QUERIES = [
    "polyurethane recycling",
    "polyurethane recycling plant",
    "polyurethane chemical recycling",
    "polyurethane circular economy",
    "polyurethane waste recycling",
    "polyurethane life cycle analysis",
    "polyurethane sustainability initiative",
    "polyurethane decarbonization",
    "bio polyol polyurethane",
    "bio-based polyurethane materials",
]
ADJUSTMENT_CORPORATE_QUERIES = [
    "polyurethane acquisition",
    "polyurethane merger",
    "polyurethane investment",
    "polyurethane strategic partnership",
    "polyurethane joint venture",
    "polyurethane business unit",
    "polyurethane division restructuring",
    "polyurethane plant acquisition",
    "chemical company polyurethane investment",
    "polyurethane company expansion",
]


def build_query_plan_adjustment_sustainability_corporate() -> List[Dict[str, Any]]:
    """
    Adjustment run: additional queries for Sustainability and Circularity and Corporate Moves coverage.
    Append to Phase 3B plan for a combined harvest. All queries contain a PU anchor; short and simple.
    """
    queries: List[Dict[str, Any]] = []
    for i, qtext in enumerate(ADJUSTMENT_SUSTAINABILITY_QUERIES, start=1):
        q = (qtext or "").strip()
        if q:
            queries.append(
                {"query_id": f"adj_sustainability_{i}", "query_text": q, "intent": "sustainability"},
            )
    for i, qtext in enumerate(ADJUSTMENT_CORPORATE_QUERIES, start=1):
        q = (qtext or "").strip()
        if q:
            queries.append(
                {"query_id": f"adj_corporate_{i}", "query_text": q, "intent": "corporate"},
            )
    return queries


def build_query_plan(
    regions: List[str],
    categories: List[str],
    value_chain_links: List[str],
    company_aliases: List[str],
    max_queries: int = 30,
) -> List[Dict[str, Any]]:
    """
    Build deterministic query plan from spec.

    Strategy is selected via QUERY_STRATEGY env var:
      - QUERY_STRATEGY=sequential_simplified -> sequential long-run plan
      - anything else (default) -> current category/region/value-chain plan
    """
    strategy = os.getenv("QUERY_STRATEGY", "").strip()
    if strategy == "sequential_simplified":
        # Ensure long sequential runs have enough queries.
        effective_max = max(max_queries, 80)
        return _build_query_plan_sequential_simplified(
            regions,
            categories,
            value_chain_links,
            company_aliases,
            max_queries=effective_max,
        )

    return _build_query_plan_current(
        regions,
        categories,
        value_chain_links,
        company_aliases,
        max_queries=max_queries,
    )


# -----------------------------------------------------------------------------
# Query plan metadata for post-classification customer filter
# -----------------------------------------------------------------------------

# Intent (Phase 3B / adjustment) -> configurator_category or value_chain_link for filter
INTENT_TO_CONFIGURATOR_CATEGORY = {
    "sustainability": "sustainability",
    "corporate": "m_and_a",
    "raw_materials": "",
    "applications": "industry_context",
}
INTENT_TO_VALUE_CHAIN_LINK = {
    "raw_materials": "raw_materials",
    "applications": "end_use",
    "sustainability": "",
    "corporate": "",
}


def plan_to_query_metadata(plan: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Convert a query plan to rows for query_plan.csv.
    Each row: query_id, region, configurator_category, value_chain_link, query_text.
    Intent may be "region:X", "category:Y", "value_chain:Z" (customer plan) or
    "raw_materials" / "applications" / "sustainability" / "corporate" (Phase 3B / adjustment).
    """
    rows: List[Dict[str, Any]] = []
    for q in plan or []:
        qid = (q.get("query_id") or "").strip()
        qtext = (q.get("query_text") or "").strip()
        intent = (q.get("intent") or "").strip()
        region = ""
        configurator_category = ""
        value_chain_link = ""
        if intent.startswith("region:"):
            region = intent.replace("region:", "").strip()
        elif intent.startswith("category:"):
            configurator_category = intent.replace("category:", "").strip()
        elif intent.startswith("value_chain:"):
            value_chain_link = intent.replace("value_chain:", "").strip()
        else:
            configurator_category = INTENT_TO_CONFIGURATOR_CATEGORY.get(intent, "")
            value_chain_link = INTENT_TO_VALUE_CHAIN_LINK.get(intent, "")
        rows.append({
            "query_id": qid,
            "region": region,
            "configurator_category": configurator_category,
            "value_chain_link": value_chain_link,
            "query_text": qtext,
        })
    return rows


def build_query_plan_map(spec: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
    """
    Build in-memory query intent map from run specification (live path).
    Returns query_id -> {region, configurator_category, value_chain_link}.
    Used for post-classification customer filter and Phase 5 report.
    """
    regions = spec.get("regions") or []
    categories = spec.get("categories") or []
    value_chain_links = spec.get("value_chain_links") or []
    company_aliases = spec.get("company_aliases") or []
    plan = build_query_plan(regions, categories, value_chain_links, company_aliases)
    rows = plan_to_query_metadata(plan)
    plan_map: Dict[str, Dict[str, str]] = {}
    for row in rows:
        qid = (row.get("query_id") or "").strip()
        if not qid:
            continue
        plan_map[qid] = {
            "region": (row.get("region") or "").strip(),
            "configurator_category": (row.get("configurator_category") or "").strip(),
            "value_chain_link": (row.get("value_chain_link") or "").strip(),
        }
    return plan_map

