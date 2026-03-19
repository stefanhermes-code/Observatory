"""
V2 Evidence Engine: orchestrates source ingestion and web search, persists candidate_articles.
Run after run record is created (run_id exists). Metadata-only; no full article text.
Date filtering: uses app date (reference_date) and cadence to only keep candidates within
lookback window. Never relies on LLM/model date.
"""

import os
import re
import time
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict, Counter
from datetime import datetime
from urllib.parse import urlparse

# Drop reason buckets for evidence funnel logging
DROP_DATE = "date"
DROP_URL = "url"
DROP_META_SNIPPET = "meta_snippet"
DROP_CANONICAL = "canonical"
DROP_URL_VALIDATION = "url_validation"  # validate_url failed (2xx check)
DROP_PU_ANCHOR_MISSING = "pu_anchor_missing"
DROP_REGION_PROVEN_JSONLD = "region_mismatch_proven_by_jsonld"
DROP_PU_PROVEN_JSONLD = "pu_not_relevant_proven_by_jsonld"
DROP_OTHER = "other"

from core.admin_db import get_all_sources
from core.run_dates import get_lookback_days, get_lookback_from_days, is_in_date_range, parse_published_at
from core.generator_db import insert_candidate_articles
from core.url_tools import canonicalize_url, validate_url, VALID_2XX, VALID_3XX, RESTRICTED_403, NOT_CHECKED, source_from_url
from core.query_planner import build_query_plan
from core.report_filters import is_meta_snippet, passes_region_relevance, passes_pu_relevance
from core.search_providers.openai_web_search import OpenAIWebSearchProvider
from core.jsonld_enrichment import enrich_candidate

# --- Phase X PU anchor configuration ---

# Primary material anchors (case-insensitive)
PU_PRIMARY_ANCHORS = [
    "polyurethane",
    "polyurethanes",
    "polyether polyol",
    "polyester polyol",
    "isocyanate",
    "methylene diphenyl diisocyanate",
    "toluene diisocyanate",
]

# Product-family anchors (case-insensitive)
PU_PRODUCT_ANCHORS = [
    "thermoplastic polyurethane",
    "polyurethane foam",
    "flexible polyurethane foam",
    "rigid polyurethane foam",
    "polyurethane elastomer",
    "polyurethane coating",
    "polyurethane adhesive",
    "polyurethane sealant",
]

# Application terms (only valid when polyurethane OR PU is also present)
PU_APPLICATION_TERMS = [
    "mattress",
    "furniture",
    "insulation",
    "automotive seating",
    "slabstock",
    "molded foam",
    "moulded foam",
]

# Trusted PU-only domains (canonical form, lowercased, no scheme, no path)
TRUSTED_PU_DOMAINS = {
    "polyurethanes.org",
    "urethane.org",
    "pu-world.com",
    "utech-polyurethane.com",
    "pu-magazine.com",
    "european-pu.com",
    "polyurethaneblog.com",
    "specialchem.com",
    "polyurethane-systems.com",
    "polyurethanefoam.org",
    "bpf.co.uk",
    "rigidfoam.com",
    "polyurethaneinsulation.org",
    "polyurethane.org.au",
    "polyurethaneasia.com",
    "polyurethaneconference.com",
    "polyurethanemarket.com",
    "chemicalweekly.com",
    "polyurethane-recycling.org",
    "polyurethane-sustainability.org",
    "pu-additives.com",
    "polyurethaneautomotive.com",
    "pu-furniture.com",
    "polyurethaneconstruction.org",
    "polyurethanecoatings.org",
}


def _get_domain_from_url(url: str) -> str:
    """Return canonical domain (no scheme, no path, stripped www.)."""
    if not url:
        return ""
    try:
        netloc = urlparse(url).netloc.lower()
    except Exception:
        return ""
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return netloc


def _compute_pu_anchor_reason(anchor_text: str, domain: str) -> Optional[str]:
    """
    Phase X PU anchor decision:
    - term_primary:<matched_term>
    - term_product:<matched_term>
    - term_application:<matched_term>  (requires polyurethane or PU + application term)
    - trusted_domain_override
    Returns reason string if anchor passes, otherwise None.
    """
    if not anchor_text:
        return None

    # Trusted domain override
    if domain and domain in TRUSTED_PU_DOMAINS:
        return "trusted_domain_override"

    text_lower = anchor_text.lower()

    # A) Primary material anchors
    for term in PU_PRIMARY_ANCHORS:
        if term in text_lower:
            return f"term_primary:{term}"

    # B) Product-family anchors
    for term in PU_PRODUCT_ANCHORS:
        if term in text_lower:
            return f"term_product:{term}"

    # C) Polyurethane OR standalone PU + application term
    has_polyurethane_token = ("polyurethane" in text_lower) or ("polyurethanes" in text_lower)
    has_standalone_pu = bool(re.search(r"\\bPU\\b", anchor_text))
    if has_polyurethane_token or has_standalone_pu:
        for term in PU_APPLICATION_TERMS:
            if term in text_lower:
                return f"term_application:{term}"

    return None


def _looks_industrial_adjacent(text: str) -> bool:
    """
    Ultra-relaxed relevance gate:
    keep when content is plausibly in the industrial/chemical/materials/adjacent space,
    even if explicit PU anchoring or region proof is weak.
    """
    t = (text or "").lower()
    if not t.strip():
        return False

    material_terms = [
        "polyurethane",
        "polyurethanes",
        "polyol",
        "polyester polyol",
        "polyether",
        "isocyanate",
        "mdi",
        "tdi",
        "tpu",
        "foam",
        "elastomer",
        "mattress",
        "insulation",
        "adhesive",
        "sealant",
    ]
    activity_terms = [
        "capacity",
        "expansion",
        "plant",
        "facility",
        "ground",
        "manufacturing",
        "production",
        "break ground",
        "inaugurate",
        "new facility",
    ]
    adjacent_terms = [
        "automotive",
        "construction",
        "furniture",
        "recycling",
        "circular",
        "chemical",
        "materials",
        "technology",
        "innovation",
    ]

    score = 0
    if any(x in t for x in material_terms):
        score += 1
    if any(x in t for x in activity_terms):
        score += 1
    if any(x in t for x in adjacent_terms):
        score += 1
    return score >= 2


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
    report_period_days: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Load enabled sources, ingest from RSS/sitemap/html_list, run query plan via search,
    canonicalize + validate + dedupe, filter by date range, insert candidate_articles.
    reference_date defaults to datetime.utcnow(). Date window is derived exclusively from
    report_period_days: caller must pass the canonical value; if None/<=0, migration fallback
    uses get_lookback_days(spec.frequency). cadence_override only bypasses run limit.
    Returns summary: { "candidates_from_sources": int, "candidates_from_search": int, "inserted": int, "query_plan": [...], "lookback_date": iso, "reference_date": iso }.
    """
    ref_date = reference_date if reference_date is not None else datetime.utcnow()
    effective_days = report_period_days if (report_period_days is not None and report_period_days > 0) else get_lookback_days(spec.get("frequency", "monthly"))
    lookback_date, ref_date = get_lookback_from_days(effective_days, ref_date)
    cadence = f"{effective_days}d"
    lookback_days = effective_days

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
    web_search_usage_accum: Dict[str, int] = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    for q in plan:
        qid = q.get("query_id")
        qtext = q.get("query_text")
        result = provider.search(
            qtext or "",
            max_results=10,
            reference_date=ref_date,
            lookback_days=lookback_days,
        )
        if isinstance(result, tuple) and len(result) == 2:
            items_batch, usage = result[0], result[1]
            if usage:
                web_search_usage_accum["input_tokens"] += int(usage.get("input_tokens") or 0)
                web_search_usage_accum["output_tokens"] += int(usage.get("output_tokens") or 0)
                web_search_usage_accum["total_tokens"] += int(usage.get("total_tokens") or 0)
        else:
            items_batch = result
        for item in items_batch:
            item["query_id"] = qid
            item["query_text"] = qtext
            item["source_id"] = None
            # Prefer a real source name; if the search provider only gives a generic
            # label like "web_search", derive a readable publisher name from the URL.
            raw_source = (item.get("source_name") or "").strip()
            url_for_source = (item.get("url") or "").strip()
            if raw_source and raw_source.lower() != "web_search":
                source_name = raw_source
            else:
                inferred = source_from_url(url_for_source)
                source_name = inferred or "web_search"
            item["source_name"] = source_name
            from_search.append(item)
    if web_search_usage_accum.get("total_tokens") or web_search_usage_accum.get("input_tokens") or web_search_usage_accum.get("output_tokens"):
        summary["token_usage"] = {"web_search": {**web_search_usage_accum, "model": "gpt-4o"}}
    summary["timing_seconds"]["web_search"] = round(time.perf_counter() - t_search_start, 1)
    all_candidates.extend(from_search)
    summary["candidates_from_search"] = len(from_search)
    # Add web_search to per-source breakdown (for full picture we'd need to merge with by_source after dedupe; here we add search total as one row)
    if from_search:
        existing = summary.get("by_source") or []
        summary["by_source"] = existing + [{"source_name": "web_search", "count": len(from_search)}]

    # 3) Filter early: meta-snippet, URL, date, canonicalize; group by (canonical, title); funnel logging with drop reasons
    t_validate_start = time.perf_counter()
    drop_buckets: Counter = Counter()
    dropped_list: List[Tuple[Dict[str, Any], str]] = []

    def _snap(c: Dict[str, Any]) -> Dict[str, Any]:
        return {"title": (c.get("title") or "")[:80], "url": (c.get("url") or "")[:100], "snippet": (c.get("snippet") or "")[:60]}

    grouped: Dict[tuple, List[Dict[str, Any]]] = defaultdict(list)
    for c in all_candidates:
        url = (c.get("url") or "").strip()
        if not url or not url.startswith(("http://", "https://")):
            drop_buckets[DROP_URL] += 1
            dropped_list.append((_snap(c), DROP_URL))
            continue
        # Weak content: previously a hard drop. Controlled relaxation: keep unless clearly unusable.
        # We still track this as a diagnostic bucket, but we do NOT reject early.
        weak_content_signal = is_meta_snippet((c.get("title") or "").strip()) or is_meta_snippet((c.get("snippet") or "").strip())
        if weak_content_signal:
            drop_buckets[DROP_META_SNIPPET] += 1
            c["_weak_content_signal"] = True
        # B3: If date missing or unparseable, allow through with date_confidence=low and proxy for sorting.
        parsed_date = parse_published_at(c.get("published_at"))
        if not is_in_date_range(c.get("published_at"), lookback_date, ref_date):
            if parsed_date is not None:
                # Has parseable date but out of window → drop
                drop_buckets[DROP_DATE] += 1
                dropped_list.append((_snap(c), DROP_DATE))
                continue
            # Missing or unparseable date → keep; we will set published_at to ref_date and mark inferred
        canonical = canonicalize_url(url)
        if not canonical:
            drop_buckets[DROP_CANONICAL] += 1
            dropped_list.append((_snap(c), DROP_CANONICAL))
            continue
        title_norm = (c.get("title") or "").strip()
        grouped[(canonical, title_norm)].append(c)

    to_insert: List[Dict[str, Any]] = []
    jsonld_found_count = 0
    # Second-pass validation and enrichment; records that survive this block are
    # "valid_for_spec" for the purposes of downstream diagnostics.
    for (canonical, title_norm), list_c in grouped.items():
        c = list_c[0]
        url = (c.get("url") or "").strip()
        parsed_date = parse_published_at(c.get("published_at"))
        if validate_urls:
            status, code = validate_url(url)
            if status != VALID_2XX:
                drop_buckets[DROP_URL_VALIDATION] += 1
                dropped_list.append((_snap(c), DROP_URL_VALIDATION))
                continue
            validation_status, http_status = status, code
        else:
            validation_status, http_status = NOT_CHECKED, None

        # JSON-LD + meta enrichment (middle road): lightweight GET, metadata-only text
        enrichment = enrich_candidate(url)
        if enrichment.get("jsonld_found"):
            jsonld_found_count += 1
        enriched_text = (enrichment.get("enriched_text") or "").strip()
        enriched_len = enrichment.get("enriched_text_length") or 0
        jsonld_has_proof = enrichment.get("jsonld_found") is True and enriched_len >= 200

        # Controlled relaxation:
        # - PU anchor missing is soft-kept.
        # - Region mismatch is soft-kept when the content looks industrial/chemical/adjacent.
        # Company-lane items are still exempt (match_reason company_hit).
        is_company_hit = any(
            (x.get("query_id") or "").strip().startswith("company_")
            for x in list_c
        )
        # Always compute an anchor-text proxy for relevance gating.
        title_for_anchor = (c.get("title") or "").strip()
        snippet_for_anchor = (c.get("snippet") or "").strip()
        anchor_text = f"{title_for_anchor} {snippet_for_anchor} {enriched_text}".strip()
        looks_industrial = _looks_industrial_adjacent(anchor_text)

        if is_company_hit:
            pu_anchor_reason = "company_hit"
        else:
            source_domain = _get_domain_from_url(url)
            pu_anchor_reason = _compute_pu_anchor_reason(anchor_text, source_domain)
        pu_anchor_missing_soft_kept = False
        if not pu_anchor_reason:
            pu_anchor_missing_soft_kept = True
            drop_buckets[DROP_PU_ANCHOR_MISSING] += 1

        # Merge criteria from all query_ids that returned this (canonical, title)
        category_val, region_val, vcl_val = None, None, None
        for x in list_c:
            qid = (x.get("query_id") or "").strip()
            if not qid:
                continue
            if qid.startswith("cat_") and category_val is None:
                category_val = qid[4:]
            elif qid.startswith("region_") and region_val is None:
                region_val = qid[7:].replace("_", " ")
            elif qid.startswith("vcl_") and vcl_val is None:
                vcl_val = qid[4:]
            elif qid.startswith("company_") and category_val is None:
                category_val = "company_news"

        if region_val is None and regions:
            region_val = regions[0]
        missing_value_chain_soft_kept = False
        if vcl_val is None:
            missing_value_chain_soft_kept = True
            # Ultra-relaxed: value_chain is optional; do not force a placeholder string.
            vcl_val = ""
        missing_category_soft_kept = False
        if category_val is None:
            missing_category_soft_kept = True
            # Ultra-relaxed: category decided later; do not force a placeholder string.
            category_val = ""

        # Region: hard gate only when JSON-LD provides proof (enriched_text >= 200 chars),
        # but ultra-relaxed mode may soft-keep when content looks industrial/adjacent.
        if jsonld_has_proof and region_val and regions:
            if not passes_region_relevance(c.get("title"), c.get("snippet"), region_val, body=enriched_text):
                if looks_industrial:
                    region_confidence, region_proof = "low", "soft_jsonld_mismatch"
                else:
                    drop_buckets[DROP_REGION_PROVEN_JSONLD] += 1
                    dropped_list.append(({**_snap(c), "jsonld_used": True}, DROP_REGION_PROVEN_JSONLD))
                    continue
            else:
                region_confidence, region_proof = "high", "jsonld"
        else:
            region_confidence, region_proof = "low", "none"

        # PU relevance: hard drop only when JSON-LD provides proof
        if jsonld_has_proof:
            if not passes_pu_relevance(c.get("title"), c.get("snippet"), body=enriched_text):
                drop_buckets[DROP_PU_PROVEN_JSONLD] += 1
                dropped_list.append(({**_snap(c), "jsonld_used": True}, DROP_PU_PROVEN_JSONLD))
                continue
            pu_confidence = "high"
        else:
            pu_confidence = "low"

        weak_content_soft_kept = any(bool(x.get("_weak_content_signal")) for x in list_c)
        rec = {
            "url": url,
            "canonical_url": canonical,
            "title": c.get("title"),
            "snippet": c.get("snippet"),
            "published_at": c.get("published_at") if parsed_date is not None else (ref_date.isoformat() if hasattr(ref_date, "isoformat") else str(ref_date)),
            "date_inferred": parsed_date is None and (c.get("published_at") is None or not str(c.get("published_at") or "").strip()),
            "source_id": c.get("source_id"),
            "source_name": c.get("source_name") or "",
            "source_domain": source_domain,
            "query_id": c.get("query_id"),
            "query_text": c.get("query_text"),
            "validation_status": validation_status,
            "http_status": http_status,
            "category": category_val,
            "region": region_val,
            "value_chain_link": vcl_val,
            "enrichment_source": enrichment.get("enrichment_source"),
            "jsonld_found": enrichment.get("jsonld_found"),
            "jsonld_types_found": enrichment.get("jsonld_types_found") or [],
            "enriched_text_length": enriched_len,
            "enrichment_success": enrichment.get("enrichment_success"),
            "enrichment_error": enrichment.get("enrichment_error"),
            "region_confidence": region_confidence,
            "region_proof": region_proof,
            "pu_confidence": pu_confidence,
            "pu_anchor_reason": pu_anchor_reason,
            "pu_anchor_missing": pu_anchor_missing_soft_kept,
            "weak_content_signal": weak_content_soft_kept,
            "missing_category": missing_category_soft_kept,
            "missing_value_chain_link": missing_value_chain_soft_kept,
        }
        to_insert.append(rec)
    summary["timing_seconds"]["validate_dedupe"] = round(time.perf_counter() - t_validate_start, 1)

    # 4) Funnel and drop buckets (protocol: jsonld counts and new drop buckets)
    # Pre-insert drop breakdown: EXCLUSIVE counts for the stage between after_first_pass (265) and insert (35).
    # Only second-loop drops belong here; first-loop drops (url, meta_snippet, date, canonical, other) already
    # happened before after_first_pass, so they must not be counted in pre-insert counters.
    # Hard validation drops (minimal rejects only).
    hard_reject_region_mismatch = drop_buckets.get(DROP_REGION_PROVEN_JSONLD, 0)
    hard_reject_pu_not_relevant = drop_buckets.get(DROP_PU_PROVEN_JSONLD, 0)
    hard_reject_url_validation = drop_buckets.get(DROP_URL_VALIDATION, 0)
    drop_validation = hard_reject_region_mismatch + hard_reject_pu_not_relevant + hard_reject_url_validation

    # Soft-kept diagnostics (kept, not rejected).
    pu_anchor_missing_soft_kept_count = drop_buckets.get(DROP_PU_ANCHOR_MISSING, 0)
    weak_content_soft_kept_count = drop_buckets.get(DROP_META_SNIPPET, 0)
    missing_category_soft_kept_count = sum(1 for r in to_insert if r.get("missing_category") is True)
    missing_value_chain_soft_kept_count = sum(1 for r in to_insert if r.get("missing_value_chain_link") is True)

    # Backwards-compatible validation breakdown fields (now reflect true hard rejects only).
    validation_pu_anchor_missing = 0
    validation_region_mismatch = hard_reject_region_mismatch
    validation_value_chain_mismatch = 0
    validation_missing_category = 0
    validation_weak_content_signal = 0
    validation_other_hard_reject = hard_reject_pu_not_relevant + hard_reject_url_validation

    # Strong vs borderline passes among records that survive pre-insert validation.
    strong_pass = 0
    borderline_pass = 0
    for rec in to_insert:
        is_strong = (
            rec.get("pu_confidence") == "high"
            and rec.get("region_confidence") == "high"
            and rec.get("weak_content_signal") is not True
            and rec.get("pu_anchor_missing") is not True
            and rec.get("missing_category") is not True
            and rec.get("missing_value_chain_link") is not True
        )
        if is_strong:
            strong_pass += 1
        else:
            borderline_pass += 1

    summary["funnel"] = {
        "from_sources": summary["candidates_from_sources"],
        "from_search": summary["candidates_from_search"],
        "combined": len(all_candidates),
        "after_first_pass": len(grouped),
        "jsonld_fetch_attempted": len(grouped),
        "jsonld_found": jsonld_found_count,
        "inserted": len(to_insert),
        "drop_buckets": dict(drop_buckets),
        "drop_validation": drop_validation,
        "drop_empty_url": 0,
        "drop_dedup": 0,
        "drop_other": 0,
    }
    summary["validation_counters"] = {
        # Hard rejects (validation)
        "validation_region_mismatch": validation_region_mismatch,
        "validation_other_hard_reject": validation_other_hard_reject,
        # Soft-kept (validation)
        "pu_anchor_missing_soft_kept": pu_anchor_missing_soft_kept_count,
        "weak_content_soft_kept": weak_content_soft_kept_count,
        "missing_category_soft_kept": missing_category_soft_kept_count,
        "missing_value_chain_soft_kept": missing_value_chain_soft_kept_count,
        # Pass strength
        "strong_pass_count": strong_pass,
        "borderline_pass_count": borderline_pass,
        # Backwards-compatible keys (kept for existing consumers)
        "validation_pu_anchor_missing": validation_pu_anchor_missing,
        "validation_value_chain_mismatch": validation_value_chain_mismatch,
        "validation_missing_category": validation_missing_category,
        "validation_weak_content_signal": validation_weak_content_signal,
        "validation_other": validation_other_hard_reject,
        "validation_strong_pass_count": strong_pass,
        "validation_borderline_pass_count": borderline_pass,
    }
    summary["top10_kept"] = [
        {
            "title": r.get("title"),
            "url": r.get("url"),
            "jsonld_found": r.get("jsonld_found"),
            "enriched_text_length": r.get("enriched_text_length"),
            "region_confidence": r.get("region_confidence"),
        }
        for r in to_insert[:10]
    ]
    summary["top10_dropped"] = [
        {
            "title": snap.get("title"),
            "url": snap.get("url"),
            "reason": reason,
            "jsonld_used": snap.get("jsonld_used", reason in (DROP_REGION_PROVEN_JSONLD, DROP_PU_PROVEN_JSONLD)),
        }
        for snap, reason in dropped_list[:10]
    ]
    # Validation rejected examples: only true hard rejects at validation (not date-window drops).
    hard_reject_reasons = {DROP_REGION_PROVEN_JSONLD, DROP_PU_PROVEN_JSONLD, DROP_URL_VALIDATION}
    validation_rejected_examples = []
    for snap, reason in dropped_list:
        if reason not in hard_reject_reasons:
            continue
        validation_rejected_examples.append(
            {
                "title": snap.get("title"),
                "canonical_url": snap.get("url"),
                "reason": reason,
            }
        )
        if len(validation_rejected_examples) >= 30:
            break
    summary["top_validation_rejected_examples"] = validation_rejected_examples[:10]
    summary["all_dropped"] = [
        {"title": snap.get("title"), "url": snap.get("url"), "reason": reason}
        for snap, reason in dropped_list
    ]

    # 5) Persist (capture drop_empty_url and drop_dedup from insert at point of filter)
    t_persist_start = time.perf_counter()
    insert_result = insert_candidate_articles(run_id, workspace_id, specification_id, to_insert)
    summary["timing_seconds"]["persist"] = round(time.perf_counter() - t_persist_start, 1)
    inserted = insert_result.get("inserted", 0) if isinstance(insert_result, dict) else insert_result
    summary["inserted"] = inserted
    if isinstance(insert_result, dict):
        summary["funnel"]["drop_empty_url"] = insert_result.get("drop_empty_url", 0)
        summary["funnel"]["drop_dedup"] = insert_result.get("drop_dedup", 0)
        summary["funnel"]["signals_after_preinsert_validation"] = inserted
    summary["timing_seconds"]["total"] = round(time.perf_counter() - t0, 1)

    # Print funnel to stdout for run capture
    _print_funnel(summary)
    return summary


def _print_funnel(summary: Dict[str, Any]) -> None:
    """Print evidence funnel, drop buckets, and top 10 kept/dropped to stdout."""
    funnel = summary.get("funnel") or {}
    buckets = funnel.get("drop_buckets") or {}
    top10_kept = summary.get("top10_kept") or []
    top10_dropped = summary.get("top10_dropped") or []
    lines = [
        "",
        "--- Evidence funnel ---",
        f"  from_sources: {funnel.get('from_sources', 0)}",
        f"  from_search:  {funnel.get('from_search', 0)}",
        f"  combined:     {funnel.get('combined', 0)}",
        f"  after_first_pass (date/url/meta/canonical): {funnel.get('after_first_pass', 0)}",
        f"  jsonld_fetch_attempted: {funnel.get('jsonld_fetch_attempted', 0)}",
        f"  jsonld_found: {funnel.get('jsonld_found', 0)}",
        f"  inserted (kept): {funnel.get('inserted', 0)}",
        "  drop_buckets: " + ", ".join(f"{k}={v}" for k, v in sorted(buckets.items())),
        "--- Top 10 kept ---",
    ]
    for i, r in enumerate(top10_kept, 1):
        jf = r.get("jsonld_found")
        el = r.get("enriched_text_length")
        rc = r.get("region_confidence", "")
        lines.append(f"  {i}. {r.get('title', '')[:70]} | {r.get('url', '')[:60]}")
        lines.append(f"      jsonld_found={jf}, enriched_text_length={el}, region_confidence={rc}")
    if not top10_kept:
        lines.append("  (none)")
    lines.append("--- Top 10 dropped ---")
    for i, r in enumerate(top10_dropped, 1):
        ju = r.get("jsonld_used", False)
        lines.append(f"  {i}. [{r.get('reason', '')}] jsonld_used={ju} | {r.get('title', '')[:50]} | {r.get('url', '')[:50]}")
    if not top10_dropped:
        lines.append("  (none)")
    lines.append("---")
    print("\n".join(lines))
