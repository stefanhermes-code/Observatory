"""
V2 Query planner: builds search query plan from spec (code-only, no LLM).
Stable for same spec options. Outputs list of {query_id, query_text, intent}.
Every query anchors on PU materials so results are about the actual industry scope.
Uses base knowledge from taxonomy (PU materials, chemicals, value chain ecosystem).
"""

from typing import List, Dict, Any

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


def build_query_plan(
    regions: List[str],
    categories: List[str],
    value_chain_links: List[str],
    company_aliases: List[str],
    max_queries: int = 30,
) -> List[Dict[str, Any]]:
    """
    Build deterministic query plan from spec.
    Returns list of {"query_id": str, "query_text": str, "intent": str}.
    """
    queries: List[Dict[str, Any]] = []
    seen: set = set()

    def add(qid: str, text: str, intent: str) -> None:
        key = (qid, text.strip().lower())
        if key in seen or len(queries) >= max_queries:
            return
        seen.add(key)
        queries.append({"query_id": qid, "query_text": text.strip(), "intent": intent})

    # 1) Region-based: PU materials + region + news
    for r in (regions or [])[:8]:
        add(f"region_{r.replace(' ', '_')}", f"{PU_MATERIALS} {r} news", f"region:{r}")

    # 2) Category-based: PU materials + category angle
    for cat in (categories or [])[:10]:
        angle = CATEGORY_QUERY_TOKENS.get(cat, "industry")
        add(f"cat_{cat}", f"{PU_MATERIALS} {angle}", f"category:{cat}")

    # 3) Value chain: PU materials + ecosystem role (who does what in the PU industry)
    for vcl in (value_chain_links or [])[:4]:
        ecosystem = VALUE_CHAIN_ECOSYSTEM.get(vcl, vcl.replace("_", " "))
        add(f"vcl_{vcl}", f"{PU_MATERIALS} {ecosystem}", f"value_chain:{vcl}")

    # 4) Company-specific: company + PU materials + news
    for alias in (company_aliases or [])[:15]:
        alias = (alias or "").strip()
        if not alias or len(alias) < 2:
            continue
        add(f"company_{hash(alias) % 10**6}", f"{alias} {PU_MATERIALS} news", "company")

    # No generic fallback: only run queries that match the user's selection (regions, categories, value chain links, company).
    # Reporting links that were not part of the chosen scope would be wrong.

    return queries
