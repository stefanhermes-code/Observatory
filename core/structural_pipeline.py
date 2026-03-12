from __future__ import annotations

import logging
import os
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from collections import Counter
from urllib.parse import urlparse

from core.filtering import (
    apply_date_window,
    filter_invalid_urls,
    filter_meta_snippet_junk,
    DropRecord,
)
from core.enrichment import enrich_evidence_items
from core.full_article_fetch import fetch_and_extract_body
from core.governance_assertions import assert_structural_category_invariants
from core.structural_categories import StructuralCategory
from core.structural_classifier import classify_evidence
from core.structural_models import EvidenceItem, ClassificationResult
from core.signals import build_signals
from core.report_renderer import render_structural_report
from core.paid_listing_intel import is_paid_listing, extract_paid_listing_facts
from core.customer_filter import filter_candidates_by_spec

# Domains that are trusted short-content sources; full fetch is skipped for these.
TRUSTED_SHORT_CONTENT_DOMAINS: frozenset[str] = frozenset({
    "prnewswire.com", "globenewswire.com", "businesswire.com", "prnewswire.co.uk",
    "reuters.com", "apnews.com",
})
MAX_SELECTIVE_FULL_FETCHES_PER_RUN = 50
MIN_STRUCTURAL_SCORE_LENGTH = 50
SNIPPET_LENGTH_THRESHOLD = 500


def _parse_dt(value: Any, fallback: Optional[datetime]) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            # Handle typical ISO 8601 with or without Z
            v = value.replace("Z", "+00:00")
            return datetime.fromisoformat(v)
        except Exception:
            pass
    return fallback or datetime.now(timezone.utc)


def _wrap_candidates_as_evidence(
    candidates: List[Dict[str, Any]],
    reference_date: datetime,
) -> List[EvidenceItem]:
    items: List[EvidenceItem] = []
    for c in candidates:
        evid = str(c.get("id") or c.get("canonical_url") or c.get("url") or "")
        if not evid:
            continue
        source_type = "lane_c" if c.get("source_id") is not None else "lane_a"
        published_at = _parse_dt(c.get("published_at"), reference_date)
        ingested_at = _parse_dt(c.get("created_at"), reference_date)
        region = c.get("region")
        region_tags = [region] if region else []
        raw_metadata: Dict[str, Any] = {
            "source_name": c.get("source_name"),
            "source_id": c.get("source_id"),
            "category": c.get("category"),
            "value_chain_link": c.get("value_chain_link"),
            "validation_status": c.get("validation_status"),
            "http_status": c.get("http_status"),
        }
        items.append(
            EvidenceItem(
                id=evid,
                source_type=source_type,  # type: ignore[arg-type]
                title=(c.get("title") or "").strip(),
                url=(c.get("url") or c.get("canonical_url") or "").strip(),
                snippet=(c.get("snippet") or ""),
                published_at=published_at,
                ingested_at=ingested_at,
                region_tags=region_tags,
                raw_metadata=raw_metadata,
            )
        )
    return items


def _structural_score_heuristic(item: EvidenceItem) -> int:
    """Heuristic: 1 if item has enough combined text to classify, else 0. (structural_score > 0 for trigger.)"""
    title = (item.title or "").strip()
    snippet = (item.snippet or "").strip()
    enrichment = (item.raw_metadata or {}).get("enrichment")
    enriched = ""
    if isinstance(enrichment, dict):
        enriched = (enrichment.get("enriched_text") or "").strip()
    total = len(title) + len(snippet) + len(enriched)
    return 1 if total >= MIN_STRUCTURAL_SCORE_LENGTH else 0


def _canonical_url_valid(url: str) -> bool:
    """True if URL has http(s) scheme and non-empty netloc."""
    if not url or not isinstance(url, str):
        return False
    try:
        p = urlparse(url.strip())
        return p.scheme in ("http", "https") and bool((p.netloc or "").strip())
    except Exception:
        return False


def _domain_from_url(url: str) -> str:
    """Lowercase netloc for domain check."""
    try:
        return (urlparse(url.strip()).netloc or "").strip().lower()
    except Exception:
        return ""


def _run_selective_full_fetch_rescue(
    enriched_items: List[EvidenceItem],
    evidence_map: Dict[str, EvidenceItem],
    primary_categories: Dict[str, StructuralCategory],
    classifications: List[ClassificationResult],
) -> Tuple[Dict[str, EvidenceItem], Dict[str, StructuralCategory], List[ClassificationResult], Dict[str, int]]:
    """
    For items with no category that meet trigger conditions: fetch full article, append to enriched_text,
    re-classify once. Max 50 fetches per run. Returns updated evidence_map, primary_categories, classifications, diagnostics.
    """
    diag: Dict[str, int] = {
        "full_fetch_attempted": 0,
        "full_fetch_success": 0,
        "full_fetch_structural_rescue": 0,
        "full_fetch_no_change": 0,
    }
    unclassified = [e for e in enriched_items if e.id not in primary_categories]
    candidates: List[EvidenceItem] = []
    for item in unclassified:
        if _structural_score_heuristic(item) <= 0:
            continue
        snippet_len = len((item.snippet or "").strip())
        if snippet_len >= SNIPPET_LENGTH_THRESHOLD:
            continue
        if not _canonical_url_valid(item.url or ""):
            continue
        domain = _domain_from_url(item.url or "")
        if domain in TRUSTED_SHORT_CONTENT_DOMAINS:
            continue
        candidates.append(item)

    fetch_count = 0
    new_results: List[ClassificationResult] = [r for r in classifications]
    for item in candidates:
        if fetch_count >= MAX_SELECTIVE_FULL_FETCHES_PER_RUN:
            break
        fetch_count += 1
        diag["full_fetch_attempted"] += 1
        body, err = fetch_and_extract_body(item.url or "")
        if err:
            logging.getLogger(__name__).warning(
                "Selective full fetch failed: evidence_id=%s url=%s error=%s",
                item.id, (item.url or "")[:100], err,
            )
            continue
        diag["full_fetch_success"] += 1
        # Append to enrichment
        meta = dict(item.raw_metadata or {})
        enrichment = dict(meta.get("enrichment") or {})
        existing = (enrichment.get("enriched_text") or "").strip()
        new_text = (existing + "\n" + body).strip() if existing else body
        enrichment["enriched_text"] = new_text
        enrichment["enriched_text_length"] = len(new_text)
        meta["enrichment"] = enrichment
        updated_item = EvidenceItem(
            id=item.id,
            source_type=item.source_type,
            title=item.title,
            url=item.url,
            snippet=item.snippet,
            published_at=item.published_at,
            ingested_at=item.ingested_at,
            region_tags=item.region_tags,
            raw_metadata=meta,
        )
        evidence_map[item.id] = updated_item
        # Re-classify once
        resc_results, _, _ = classify_evidence([updated_item])
        if resc_results:
            r = resc_results[0]
            primary_categories[r.evidence_id] = r.primary_category
            new_results.append(r)
            diag["full_fetch_structural_rescue"] += 1
        else:
            diag["full_fetch_no_change"] += 1

    return evidence_map, primary_categories, new_results, diag


def run_structural_pipeline(
    run_id: str,
    spec: Dict[str, Any],
    candidates: List[Dict[str, Any]],
    lookback_date: datetime,
    reference_date: datetime,
) -> Dict[str, Any]:
    """
    Structural pipeline wiring (Milestone 6).

    Intake (Search + RSS) is handled upstream by evidence_engine.
    This function starts from candidate_articles and runs:
      EvidenceItem wrapping → Filtering → Enrichment → Structural Classification
      → Signal Processing → Hybrid Renderer.
    """
    assert_structural_category_invariants()

    # Customer filter: apply spec to candidates BEFORE structural processing.
    # This ensures clustering and development extraction operate only on the
    # filtered subset that matches the approved customer specification.
    filtered_candidates = filter_candidates_by_spec(candidates, spec)

    # EvidenceItem wrapping
    evidence_items = _wrap_candidates_as_evidence(filtered_candidates, reference_date)

    # Filtering
    lookback_days = max(1, int((reference_date - lookback_date).days or 1))
    kept, drops_date = apply_date_window(evidence_items, reference_date, lookback_days)
    kept, drops_url = filter_invalid_urls(kept)
    kept, drops_snippet = filter_meta_snippet_junk(kept)
    drop_records: List[DropRecord] = []
    drop_records.extend(drops_date)
    drop_records.extend(drops_url)
    drop_records.extend(drops_snippet)

    # Enrichment
    enriched_items, enrichment_logs = enrich_evidence_items(kept)

    # Structural classification
    classifications, classification_logs, unclassified_lane_c = classify_evidence(enriched_items)

    evidence_map: Dict[str, EvidenceItem] = {e.id: e for e in enriched_items}
    primary_categories: Dict[str, StructuralCategory] = {
        r.evidence_id: r.primary_category for r in classifications
    }
    full_fetch_diag: Dict[str, int] = {
        "full_fetch_attempted": 0,
        "full_fetch_success": 0,
        "full_fetch_structural_rescue": 0,
        "full_fetch_no_change": 0,
    }

    # Selective full-article fetch rescue (Phase 2): only when flag ON, after classification, before final drop.
    use_selective_full_fetch = os.getenv("USE_SELECTIVE_FULL_FETCH", "").strip().lower() == "true"
    if use_selective_full_fetch:
        evidence_map, primary_categories, classifications, full_fetch_diag = _run_selective_full_fetch_rescue(
            enriched_items, evidence_map, primary_categories, classifications
        )

    # Signal processing
    signals, signal_diag = build_signals(evidence_map, primary_categories, max_signals=7)

    # Post-score / final stage: only items with a structural category appear in the report.
    # "kept_after_scoring" = evidence_after_filtering (items that passed date/url/snippet and enrichment).
    # "kept_final" = count of items that have a classification AND are in evidence_map (actually rendered).
    classified_ids = set(primary_categories.keys())
    kept_final_ids = [eid for eid in classified_ids if eid in evidence_map]
    kept_final_count = len(kept_final_ids)
    kept_after_scoring_count = len(enriched_items)

    # Dropped after scoring = passed filtering + enrichment but not classified (no structural category match).
    dropped_after_scoring: List[Dict[str, Any]] = []
    for ev in enriched_items:
        if ev.id not in classified_ids:
            dropped_after_scoring.append({
                "reason": "no_structural_category",
                "url": (ev.url or "")[:200],
                "title": (ev.title or "")[:200],
            })
    dropped_after_scoring_count = len(dropped_after_scoring)
    dropped_after_scoring_reasons = Counter(dr["reason"] for dr in dropped_after_scoring)
    dropped_after_scoring_sample = dropped_after_scoring[:20]
    drop_reason_counts = Counter(dr.reason for dr in drop_records)

    empty_report_diagnostics: Optional[Dict[str, Any]] = None
    if kept_final_count == 0:
        empty_report_diagnostics = {
            "candidates_total": len(candidates),
            "kept_after_scoring": kept_after_scoring_count,
            "kept_final": 0,
            "top_5_drop_buckets": dict(drop_reason_counts.most_common(5)),
            "dropped_after_scoring_count": dropped_after_scoring_count,
            "dropped_after_scoring_reasons": dict(dropped_after_scoring_reasons),
            "dropped_after_scoring_sample": dropped_after_scoring_sample,
        }

    # Paid listing intel: detect classified items that are paid report listings, extract facts, render as non-clickable bullets
    paid_listing_evidence_ids: set = set()
    paid_listing_facts: Dict[str, Dict[str, Any]] = {}
    for ev in enriched_items:
        if ev.id not in primary_categories:
            continue
        enrichment = (ev.raw_metadata or {}).get("enrichment") or {}
        enriched_text = (enrichment.get("enriched_text") or "").strip()
        combined = f"{(ev.title or '')} {(ev.snippet or '')} {enriched_text}".strip()
        if not is_paid_listing(ev.url or "", ev.title or "", ev.snippet or "", enriched_text):
            continue
        facts = extract_paid_listing_facts(combined)
        if not any(facts.get(k) for k in ("market_size", "cagr", "base_year", "regions", "segments", "key_players")):
            continue
        paid_listing_evidence_ids.add(ev.id)
        paid_listing_facts[ev.id] = facts

    # Hybrid renderer
    report_content = render_structural_report(
        signals=signals,
        evidence_items=evidence_map,
        spec=spec,
        classifications=primary_categories,
        empty_report_diagnostics=empty_report_diagnostics,
        paid_listing_evidence_ids=paid_listing_evidence_ids,
        paid_listing_facts=paid_listing_facts,
    )

    # Diagnostics bundle (for governance & UI if desired)
    lane_counts_all = Counter(e.source_type for e in evidence_items)
    lane_counts_kept = Counter(e.source_type for e in kept)
    category_counts = Counter(primary_categories.values())
    signal_evidence_counts = {s.id: s.evidence_count for s in signals}

    diagnostics: Dict[str, Any] = {
        "run_id": run_id,
        "evidence_wrapped": len(evidence_items),
        "evidence_after_filtering": len(kept),
        "kept_after_scoring": kept_after_scoring_count,
        "kept_final": kept_final_count,
        "dropped_after_scoring_count": dropped_after_scoring_count,
        "dropped_after_scoring_reasons": dict(dropped_after_scoring_reasons),
        "dropped_after_scoring_sample": dropped_after_scoring_sample,
        "lane_counts_all": dict(lane_counts_all),
        "lane_counts_after_filtering": dict(lane_counts_kept),
        "classification_count": len(classifications),
        "category_distribution": {cat.value: count for cat, count in category_counts.items()},
        "unclassified_lane_c": list(unclassified_lane_c),
        "drop_records": [asdict(dr) for dr in drop_records],
        "drop_reason_counts": dict(drop_reason_counts),
        "enrichment_logs": enrichment_logs,
        "signal_count": len(signals),
        "signal_evidence_counts": signal_evidence_counts,
        "signal_diagnostics": {
            "ranked_signal_ids": signal_diag.ranked_signal_ids,
            "scores": signal_diag.scores,
            "unclustered_evidence_ids": signal_diag.unclustered_evidence_ids,
        },
        "full_fetch_attempted": full_fetch_diag["full_fetch_attempted"],
        "full_fetch_success": full_fetch_diag["full_fetch_success"],
        "full_fetch_structural_rescue": full_fetch_diag["full_fetch_structural_rescue"],
        "full_fetch_no_change": full_fetch_diag["full_fetch_no_change"],
        "paid_listing_intel_count": len(paid_listing_evidence_ids),
    }
    if empty_report_diagnostics is not None:
        diagnostics["empty_report_diagnostics"] = empty_report_diagnostics

    return {
        "report_content": report_content,
        "signals": [s.to_dict() for s in signals],
        "diagnostics": diagnostics,
    }

