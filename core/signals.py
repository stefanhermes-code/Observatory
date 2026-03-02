from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Iterable, List, Tuple

from core.governance_assertions import assert_signal_count_limit, assert_no_duplicate_evidence_ids
from core.structural_categories import StructuralCategory
from core.structural_models import EvidenceItem, StructuralSignal


@dataclass(frozen=True)
class SignalDiagnostics:
    ranked_signal_ids: List[str]
    scores: Dict[str, float]
    unclustered_evidence_ids: List[str]


CATEGORY_MULTIPLIER: Dict[StructuralCategory, float] = {
    StructuralCategory.CAPACITY_EXPANSION: 1.3,
    StructuralCategory.CAPACITY_REDUCTION_OR_SHUTDOWN: 1.3,
    StructuralCategory.MERGERS_AND_ACQUISITIONS: 1.25,
    StructuralCategory.INVESTMENTS: 1.2,
    StructuralCategory.JOINT_VENTURES_AND_STRATEGIC_PARTNERSHIPS: 1.15,
    StructuralCategory.REGULATION_AND_POLICY: 1.1,
    StructuralCategory.SUSTAINABILITY_AND_CIRCULARITY: 1.1,
    StructuralCategory.TECHNOLOGY_AND_INNOVATION: 1.05,
    StructuralCategory.MARKET_AND_PRICING: 1.0,
    StructuralCategory.CORPORATE_STRATEGY_AND_RESTRUCTURING: 1.1,
    StructuralCategory.DOWNSTREAM_APPLICATION_SHIFTS: 1.0,
}


def _theme_key(item: EvidenceItem) -> str:
    """Simple deterministic theme key based on normalized title prefix."""
    title = (item.title or "").strip().lower()
    if not title:
        return ""
    parts = title.split()
    return " ".join(parts[:6])


def _time_bucket(dt: datetime) -> str:
    """Coarse time bucket (year-month) for grouping."""
    return dt.strftime("%Y-%m")


def _companies_from_metadata(item: EvidenceItem) -> List[str]:
    meta = item.raw_metadata or {}
    companies = meta.get("companies")
    if isinstance(companies, list):
        return [str(c) for c in companies if c]
    return []


def _score_signal(signal: StructuralSignal) -> float:
    """
    Apply deterministic scoring per signal_scoring_spec.txt.

    base = evidence_count
          + distinct_company_count * 1.0
          + distinct_region_count * 0.5
    final = base * category_multiplier
    """
    evidence_count = signal.evidence_count
    distinct_company_count = len({c for c in signal.companies if c})
    distinct_region_count = len({r for r in signal.regions if r})

    weighted = (
        float(evidence_count)
        + float(distinct_company_count) * 1.0
        + float(distinct_region_count) * 0.5
    )
    multiplier = CATEGORY_MULTIPLIER.get(signal.primary_category, 1.0)
    return weighted * multiplier


def build_signals(
    evidence_items: Dict[str, EvidenceItem],
    primary_categories: Dict[str, StructuralCategory],
    max_signals: int = 7,
) -> Tuple[List[StructuralSignal], SignalDiagnostics]:
    """
    Build and score StructuralSignal objects from classified evidence.

    Inputs:
        evidence_items: mapping evidence_id -> EvidenceItem
        primary_categories: mapping evidence_id -> StructuralCategory

    Returns:
        (ranked_signals, diagnostics)
    """
    # Group evidence by (category, theme, time_bucket)
    buckets: Dict[Tuple[StructuralCategory, str, str], List[EvidenceItem]] = defaultdict(list)

    for evidence_id, category in primary_categories.items():
        item = evidence_items.get(evidence_id)
        if item is None:
            continue
        theme = _theme_key(item)
        ts = item.published_at or item.ingested_at
        bucket_key = (category, theme, _time_bucket(ts))
        buckets[bucket_key].append(item)

    signals: List[StructuralSignal] = []
    scores: Dict[str, float] = {}

    for (category, theme, bucket), items in buckets.items():
        evidence_ids = [i.id for i in items]
        regions: List[str] = []
        companies: List[str] = []
        for i in items:
            regions.extend(i.region_tags or [])
            companies.extend(_companies_from_metadata(i))

        title = theme or f"{category.value.replace('_', ' ').title()} activity"
        interpretation = (
            f"{len(items)} event(s) in {category.value.replace('_', ' ')} "
            f"during {bucket} across {len(set(regions))} region(s)."
        )

        signal = StructuralSignal(
            id=f"{category.value}:{bucket}:{theme or 'default'}",
            title=title,
            structural_interpretation=interpretation,
            primary_category=category,
            regions=list({r for r in regions if r}),
            companies=list({c for c in companies if c}),
            confidence_level=1.0,
            evidence_ids=evidence_ids,
            evidence_count=len(evidence_ids),
        )
        score = _score_signal(signal)
        signals.append(signal)
        scores[signal.id] = score

    # Rank signals by score
    signals.sort(key=lambda s: scores.get(s.id, 0.0), reverse=True)
    # Trim to governance limit, then assert on final set
    signals = signals[:max_signals]
    assert_signal_count_limit((s.id for s in signals), max_signals=max_signals)

    ranked_ids = [s.id for s in signals]
    all_evidence_ids: List[str] = []
    for s in signals:
        all_evidence_ids.extend(s.evidence_ids)
    assert_no_duplicate_evidence_ids(all_evidence_ids)

    # Unclustered = classified evidence ids that did not appear in any signal
    clustered: set[str] = set(all_evidence_ids)
    unclustered: List[str] = [
        eid for eid in primary_categories.keys() if eid not in clustered
    ]

    diagnostics = SignalDiagnostics(
        ranked_signal_ids=ranked_ids,
        scores={sid: scores[sid] for sid in ranked_ids},
        unclustered_evidence_ids=unclustered,
    )
    return signals, diagnostics

