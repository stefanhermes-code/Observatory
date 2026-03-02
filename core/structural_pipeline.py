from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Optional
from collections import Counter

from core.filtering import (
    apply_date_window,
    filter_invalid_urls,
    filter_meta_snippet_junk,
    DropRecord,
)
from core.enrichment import enrich_evidence_items
from core.governance_assertions import assert_structural_category_invariants
from core.structural_categories import StructuralCategory
from core.structural_classifier import classify_evidence
from core.structural_models import EvidenceItem
from core.signals import build_signals
from core.report_renderer import render_structural_report


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

    # EvidenceItem wrapping
    evidence_items = _wrap_candidates_as_evidence(candidates, reference_date)

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
    dropped_after_scoring_sample = dropped_after_scoring[:10]

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

    # Hybrid renderer
    report_content = render_structural_report(
        signals=signals,
        evidence_items=evidence_map,
        spec=spec,
        classifications=primary_categories,
        empty_report_diagnostics=empty_report_diagnostics,
    )

    # Diagnostics bundle (for governance & UI if desired)
    lane_counts_all = Counter(e.source_type for e in evidence_items)
    lane_counts_kept = Counter(e.source_type for e in kept)
    category_counts = Counter(primary_categories.values())
    drop_reason_counts = Counter(dr.reason for dr in drop_records)
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
    }
    if empty_report_diagnostics is not None:
        diagnostics["empty_report_diagnostics"] = empty_report_diagnostics

    return {
        "report_content": report_content,
        "signals": [s.to_dict() for s in signals],
        "diagnostics": diagnostics,
    }

