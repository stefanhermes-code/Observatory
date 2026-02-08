"""
V2 Query planner: builds search query plan from spec (code-only, no LLM).
Stable for same spec options. Outputs list of {query_id, query_text, intent}.
"""

from typing import List, Dict, Any

# Category id -> search keywords for web search
CATEGORY_QUERY_TOKENS = {
    "company_news": "polyurethane company news",
    "regional_monitoring": "polyurethane market region",
    "industry_context": "polyurethane industry supply demand",
    "value_chain": "MDI TDI polyols polyurethane",
    "value_chain_link": "polyurethane value chain",
    "competitive": "polyurethane producers competitive",
    "sustainability": "polyurethane sustainability REACH decarbonization",
    "capacity": "polyurethane capacity expansion plant",
    "m_and_a": "polyurethane acquisition partnership M&A",
    "early_warning": "polyurethane price demand utilization",
    "executive_briefings": "polyurethane market briefing",
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

    # 1) Region-based queries (if any region selected)
    for r in (regions or [])[:8]:
        add(f"region_{r.replace(' ', '_')}", f"polyurethane {r} news", f"region:{r}")

    # 2) Category-based queries
    for cat in (categories or [])[:10]:
        tokens = CATEGORY_QUERY_TOKENS.get(cat, "polyurethane")
        add(f"cat_{cat}", tokens, f"category:{cat}")

    # 3) Value chain (optional)
    for vcl in (value_chain_links or [])[:4]:
        add(f"vcl_{vcl}", f"polyurethane {vcl.replace('_', ' ')}", f"value_chain:{vcl}")

    # 4) Company-specific (aliases from company list)
    for alias in (company_aliases or [])[:15]:
        alias = (alias or "").strip()
        if not alias or len(alias) < 2:
            continue
        add(f"company_{hash(alias) % 10**6}", f"{alias} polyurethane news", "company")

    # 5) One generic fallback if we have room
    add("generic", "polyurethane industry news", "generic")

    return queries
