"""
V2 Evidence Engine: orchestrates source ingestion and web search, persists candidate_articles.
Run after run record is created (run_id exists). Metadata-only; no full article text.
"""

from typing import List, Dict, Any, Optional
from core.admin_db import get_all_sources
from core.generator_db import insert_candidate_articles
from core.url_tools import canonicalize_url, validate_url, VALID_2XX, VALID_3XX, RESTRICTED_403, NOT_CHECKED
from core.query_planner import build_query_plan
from core.search_providers.openai_web_search import OpenAIWebSearchProvider


def _company_aliases_from_spec(spec: Dict) -> List[str]:
    """Extract company names/aliases for query plan. Prefer DB (tracked_companies), else company_list.json."""
    aliases: List[str] = []
    try:
        from core.admin_db import get_tracked_companies
        tracked = get_tracked_companies(active_only=True)
        if tracked:
            for company in tracked:
                name = company.get("name")
                if name:
                    aliases.append(name.strip())
                for a in (company.get("aliases") or []):
                    if a and isinstance(a, str):
                        aliases.append(a.strip())
            return aliases[:50]
    except Exception:
        pass
    # Fallback: file-based company list
    try:
        from core.company_list_manager import load_company_list
        data = load_company_list()
        for company in data.get("companies", []) or []:
            if company.get("status") != "active":
                continue
            name = company.get("name")
            if name:
                aliases.append(name.strip())
            for a in (company.get("aliases") or []):
                if a and isinstance(a, str):
                    aliases.append(a.strip())
    except Exception:
        pass
    return aliases[:50]


def _ingest_sources(sources: List[Dict]) -> List[Dict[str, Any]]:
    """Run connectors for each enabled source; return flat list of candidates (url, title, ...)."""
    from core.connectors import rss as rss_conn
    from core.connectors import sitemap as sitemap_conn
    from core.connectors import html_list as html_list_conn

    out: List[Dict[str, Any]] = []
    for src in sources:
        if not src.get("enabled", True):
            continue
        stype = (src.get("source_type") or "").lower()
        name = src.get("source_name") or "unknown"
        sid = src.get("id")
        base = src.get("base_url") or ""

        if stype == "rss" and src.get("rss_url"):
            for item in rss_conn.fetch_rss(src["rss_url"], name):
                item["source_id"] = sid
                out.append(item)
        elif stype == "sitemap" and src.get("sitemap_url"):
            for item in sitemap_conn.fetch_sitemap(src["sitemap_url"], name):
                item["source_id"] = sid
                out.append(item)
        elif stype == "html_list" and src.get("list_url"):
            for item in html_list_conn.fetch_html_list(
                src["list_url"], name, src.get("selectors"), base
            ):
                item["source_id"] = sid
                out.append(item)
    return out


def run_evidence_engine(
    run_id: str,
    workspace_id: str,
    specification_id: str,
    spec: Dict,
    validate_urls: bool = True,
    search_provider: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Load enabled sources, ingest from RSS/sitemap/html_list, run query plan via search,
    canonicalize + validate + dedupe, insert candidate_articles.
    Returns summary: { "candidates_from_sources": int, "candidates_from_search": int, "inserted": int, "query_plan": [...] }.
    """
    summary: Dict[str, Any] = {
        "candidates_from_sources": 0,
        "candidates_from_search": 0,
        "inserted": 0,
        "query_plan": [],
    }
    all_candidates: List[Dict[str, Any]] = []

    # 1) Source ingestion
    sources = [s for s in (get_all_sources() or []) if s.get("enabled", True)]
    from_sources = _ingest_sources(sources)
    for c in from_sources:
        c["query_id"] = None
        c["query_text"] = None
    all_candidates.extend(from_sources)
    summary["candidates_from_sources"] = len(from_sources)

    # 2) Query plan + web search
    regions = spec.get("regions") or []
    categories = spec.get("categories") or []
    value_chain_links = spec.get("value_chain_links") or []
    company_aliases = _company_aliases_from_spec(spec)
    plan = build_query_plan(regions, categories, value_chain_links, company_aliases)
    summary["query_plan"] = [{"query_id": q.get("query_id"), "query_text": q.get("query_text"), "intent": q.get("intent")} for q in plan]

    provider = search_provider or OpenAIWebSearchProvider()
    from_search: List[Dict[str, Any]] = []
    for q in plan:
        qid = q.get("query_id")
        qtext = q.get("query_text")
        for item in provider.search(qtext or "", max_results=10):
            item["query_id"] = qid
            item["query_text"] = qtext
            item["source_id"] = None
            item["source_name"] = item.get("source_name") or "web_search"
            from_search.append(item)
    all_candidates.extend(from_search)
    summary["candidates_from_search"] = len(from_search)

    # 3) Canonicalize, validate, dedupe
    seen: set = set()
    to_insert: List[Dict[str, Any]] = []
    for c in all_candidates:
        url = (c.get("url") or "").strip()
        if not url or not url.startswith(("http://", "https://")):
            continue
        canonical = canonicalize_url(url)
        if not canonical or canonical in seen:
            continue
        seen.add(canonical)
        rec = {
            "url": url,
            "canonical_url": canonical,
            "title": c.get("title"),
            "snippet": c.get("snippet"),
            "published_at": c.get("published_at"),
            "source_id": c.get("source_id"),
            "source_name": c.get("source_name") or "unknown",
            "query_id": c.get("query_id"),
            "query_text": c.get("query_text"),
            "validation_status": NOT_CHECKED,
            "http_status": None,
        }
        if validate_urls:
            status, code = validate_url(url)
            rec["validation_status"] = status
            rec["http_status"] = code
        to_insert.append(rec)

    # 4) Persist
    inserted = insert_candidate_articles(run_id, workspace_id, specification_id, to_insert)
    summary["inserted"] = inserted
    return summary
