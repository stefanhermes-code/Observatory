from datetime import datetime, timezone

from core.structural_categories import StructuralCategory
from core.structural_models import EvidenceItem, StructuralSignal
from core.report_renderer import render_structural_report


def _evidence(eid: str, title: str, cat: StructuralCategory) -> tuple[EvidenceItem, StructuralSignal]:
    ev = EvidenceItem(
        id=eid,
        source_type="lane_a",  # type: ignore[arg-type]
        title=title,
        url="https://example.com/article",
        snippet="Snippet",
        published_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
        ingested_at=datetime(2026, 2, 2, tzinfo=timezone.utc),
        region_tags=["EMEA"],
        raw_metadata={},
    )
    sig = StructuralSignal(
        id=f"sig-{eid}",
        title=f"Signal for {title}",
        structural_interpretation="Interpretation text.",
        primary_category=cat,
        regions=["EMEA"],
        companies=["Company A"],
        confidence_level=0.9,
        evidence_ids=[eid],
        evidence_count=1,
    )
    return ev, sig


def test_render_structural_report_basic() -> None:
    ev1, sig1 = _evidence("ev1", "Capacity expansion example", StructuralCategory.CAPACITY_EXPANSION)
    evidence_items = {ev1.id: ev1}
    classifications = {ev1.id: StructuralCategory.CAPACITY_EXPANSION}
    spec = {}

    md = render_structural_report([sig1], evidence_items, spec, classifications)

    assert "## Strategic Signal Layer" in md
    assert "## Structural Category Layer" in md
    assert "Capacity Expansion" in md
    assert "Capacity expansion example" in md

