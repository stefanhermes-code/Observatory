"""
V2 Evidence Engine: orchestrates source ingestion and web search, persists candidate_articles.
Run after run record is created (run_id exists). Metadata-only; no full article text.
Date filtering: uses app date (reference_date) and cadence to only keep candidates within
lookback window. Never relies on LLM/model date.
"""

import time
from typing import List, Dict, Any, Optional
from datetime import datetime

from core.admin_db import get_all_sources
from core.run_dates import get_lookback_from_cadence, get_lookback_days, is_in_date_range
from core.generator_db import insert_candidate_articles
from core.url_tools import canonicalize_url, validate_url, VALID_2XX, VALID_3XX, RESTRICTED_403, NOT_CHECKED
from core.query_planner import build_query_plan
from core.report_filters import is_meta_snippet
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
    cadence_override: Optional[str] = None,
    reference_date: Optional[datetime] = None,
    lookback_days_override: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Load enabled sources, ingest from RSS/sitemap/html_list, run query plan via search,
    canonicalize + validate + dedupe, filter by date range (cadence + app date), insert candidate_articles.
    reference_date defaults to datetime.utcnow() so the app, not the model, defines "today".
    When lookback_days_override is set (e.g. 1, 7, 30 for builder), that defines the window; otherwise
    lookback is from spec frequency (daily=2, weekly=7, monthly=30). cadence_override only bypasses run limit.
    Returns summary: { "candidates_from_sources": int, "candidates_from_search": int, "inserted": int, "query_plan": [...], "lookback_date": iso, "reference_date": iso }.
    """
    ref_date = reference_date if reference_date is not None else datetime.utcnow()
    if lookback_days_override is not None and lookback_days_override > 0:
        from core.run_dates import get_lookback_from_days
        lookback_date, ref_date = get_lookback_from_days(lookback_days_override, ref_date)
        cadence = f"{lookback_days_override}d"
        lookback_days = lookback_days_override
    else:
        cadence = spec.get("frequency", "monthly")
        lookback_date, ref_date = get_lookback_from_cadence(cadence, ref_date)
        lookback_days = get_lookback_days(cadence)

    summary: Dict[str, Any] = {
        "candidates_from_sources": 0,
        "candidates_from_search": 0,
        "inserted": 0,
        "query_plan": [],
        "timing_seconds": {},
        "lookback_date": lookback_date.isoformat(),
        "reference_date": ref_date.isoformat(),
        "cadence": cadence,
    }
    all_candidates: List[Dict[str, Any]] = []
    t0 = time.perf_counter()

    # 1) Source ingestion
    sources = [s for s in (get_all_sources() or []) if s.get("enabled", True)]
    t_ingest_start = time.perf_counter()
    from_sources = _ingest_sources(sources)
    summary["timing_seconds"]["source_ingestion"] = round(time.perf_counter() - t_ingest_start, 1)
    for c in from_sources:
        c["query_id"] = None
        c["query_text"] = None
    all_candidates.extend(from_sources)
    summary["candidates_from_sources"] = len(from_sources)
    # Per-source productivity (count by source_id/source_name for ingested items)
    from collections import Counter
    source_counts: Counter = Counter()
    for c in from_sources:
        name = (c.get("source_name") or "unknown").strip()
        source_counts[name] += 1
    summary["by_source"] = [{"source_name": name, "count": count} for name, count in source_counts.most_common()]

    # 2) Query plan + web search
    regions = spec.get("regions") or []
    categories = spec.get("categories") or []
    value_chain_links = spec.get("value_chain_links") or []
    # Company list is OPTIONAL: only use it when the Company News category is selected.
    # If "company_news" is not in the spec categories, we skip company-specific aliases entirely.
    use_company_list = "company_news" in categories
    company_aliases = _company_aliases_from_spec(spec) if use_company_list else []
    plan = build_query_plan(regions, categories, value_chain_links, company_aliases)
    summary["query_plan"] = [{"query_id": q.get("query_id"), "query_text": q.get("query_text"), "intent": q.get("intent")} for q in plan]

    t_search_start = time.perf_counter()
    provider = search_provider or OpenAIWebSearchProvider()
    from_search: List[Dict[str, Any]] = []
    for q in plan:
        qid = q.get("query_id")
        qtext = q.get("query_text")
        for item in provider.search(
            qtext or "",
            max_results=10,
            reference_date=ref_date,
            lookback_days=lookback_days,
        ):
            item["query_id"] = qid
            item["query_text"] = qtext
            item["source_id"] = None
            item["source_name"] = item.get("source_name") or "web_search"
            from_search.append(item)
    summary["timing_seconds"]["web_search"] = round(time.perf_counter() - t_search_start, 1)
    all_candidates.extend(from_search)
    summary["candidates_from_search"] = len(from_search)
    # Add web_search to per-source breakdown (for full picture we'd need to merge with by_source after dedupe; here we add search total as one row)
    if from_search:
        existing = summary.get("by_source") or []
        summary["by_source"] = existing + [{"source_name": "web_search", "count": len(from_search)}]

    # 3) Filter early: meta-snippet, URL, date, then canonicalize, validate (2xx-only when validate_urls), dedupe by (url, title)
    # Dedupe by (canonical_url, title) so one URL (e.g. newsletter page) can have multiple candidates with different titles.
    t_validate_start = time.perf_counter()
    seen: set = set()  # (canonical_url, title_normalized)
    to_insert: List[Dict[str, Any]] = []
    for c in all_candidates:
        url = (c.get("url") or "").strip()
        if not url or not url.startswith(("http://", "https://")):
            continue
        # Meta-snippet filter: drop search-result preamble, not real news
        if is_meta_snippet((c.get("title") or "").strip()) or is_meta_snippet((c.get("snippet") or "").strip()):
            continue
        # Date filter: only keep candidates within [lookback_date, reference_date]; keep if no date
        if not is_in_date_range(c.get("published_at"), lookback_date, ref_date):
            continue
        canonical = canonicalize_url(url)
        if not canonical:
            continue
        title_norm = (c.get("title") or "").strip()
        dedupe_key = (canonical, title_norm)
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        # When validating URLs, only persist if link works (2xx) — so downstream does not need to re-check
        if validate_urls:
            status, code = validate_url(url)
            if status != VALID_2XX:
                continue  # dismiss non-working links early
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
                "validation_status": status,
                "http_status": code,
            }
        else:
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
        to_insert.append(rec)
    summary["timing_seconds"]["validate_dedupe"] = round(time.perf_counter() - t_validate_start, 1)

    # 4) Persist
    t_persist_start = time.perf_counter()
    inserted = insert_candidate_articles(run_id, workspace_id, specification_id, to_insert)
    summary["timing_seconds"]["persist"] = round(time.perf_counter() - t_persist_start, 1)
    summary["inserted"] = inserted
    summary["timing_seconds"]["total"] = round(time.perf_counter() - t0, 1)
    return summary
