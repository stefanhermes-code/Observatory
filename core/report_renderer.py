from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from core.structural_categories import StructuralCategory, all_structural_categories, display_label
from core.structural_models import EvidenceItem, StructuralSignal


def _format_signal(signal: StructuralSignal) -> str:
    regions = ", ".join(signal.regions) if signal.regions else "Global/unspecified"
    companies = ", ".join(signal.companies) if signal.companies else "Various / unspecified"
    return (
        f"- **{signal.title}**  \n"
        f"  Category: {display_label(signal.primary_category)}  \n"
        f"  Regions: {regions}  \n"
        f"  Companies: {companies}  \n"
        f"  Confidence: {signal.confidence_level:.2f}  \n"
        f"  Evidence count: {signal.evidence_count}  \n"
        f"  Interpretation: {signal.structural_interpretation}"
    )


def _format_event_line(ev: EvidenceItem, one_line_interpretation: str) -> str:
    company = ""
    meta = ev.raw_metadata or {}
    companies_meta = meta.get("companies")
    if isinstance(companies_meta, list) and companies_meta:
        company = str(companies_meta[0])
    region = ", ".join(ev.region_tags) if ev.region_tags else ""
    url = ev.url or ""
    parts: List[str] = []
    if company:
        parts.append(company)
    if region:
        parts.append(region)
    meta_str = " | ".join(parts) if parts else ""
    prefix = f"- **{ev.title}**"
    if meta_str:
        prefix += f" — {meta_str}"
    if one_line_interpretation:
        prefix += f" — {one_line_interpretation}"
    if url:
        prefix += f"  \n  {url}"
    return prefix


def _format_paid_listing_intel(ev: EvidenceItem, facts: Dict) -> str:
    """Format paid listing as non-clickable intel bullets (no URL)."""
    bullets: List[str] = []
    if facts.get("market_size"):
        bullets.append(f"Market size: {facts['market_size']}")
    if facts.get("cagr"):
        bullets.append(f"CAGR: {facts['cagr']}")
    if facts.get("base_year"):
        bullets.append(f"Base year: {facts['base_year']}")
    if facts.get("regions"):
        r = facts["regions"]
        bullets.append(f"Regions: {', '.join(r) if isinstance(r, list) else r}")
    if facts.get("segments"):
        s = facts["segments"]
        bullets.append(f"Segments: {', '.join(s[:5]) if isinstance(s, list) else s}")
    if facts.get("key_players"):
        k = facts["key_players"]
        bullets.append(f"Key players: {', '.join(k[:5]) if isinstance(k, list) else k}")
    if not bullets:
        return f"- **{ev.title or 'Market report listing'}** — (paid listing; no structured facts extracted)"
    title_line = f"- **{ev.title or 'Market report listing'}** — Market report listing (paid). Visible intel:"
    return title_line + "\n  " + "\n  ".join(f"- {b}" for b in bullets[:7])


def render_structural_report(
    signals: List[StructuralSignal],
    evidence_items: Dict[str, EvidenceItem],
    spec: Dict,
    classifications: Dict[str, StructuralCategory],
    empty_report_diagnostics: Optional[Dict] = None,
    paid_listing_evidence_ids: Optional[set] = None,
    paid_listing_facts: Optional[Dict[str, Dict]] = None,
) -> str:
    """
    Render hybrid structural report as markdown text.

    Level 1: Strategic Signal Layer (top 5–7 signals, already scored/limited upstream).
    Level 2: Structural Category Layer (11 categories, fixed order, hide-empty).

    When kept_final==0, if empty_report_diagnostics is provided, prepend an explicit
    "Empty report diagnostics" block (candidates_total, kept_after_scoring, kept_final, top 5 drop buckets).
    """
    lines: List[str] = []

    # Empty report diagnostics block (top section when no events published)
    if empty_report_diagnostics:
        lines.append("## Empty report diagnostics")
        lines.append("")
        lines.append(
            f"- **candidates_total:** {empty_report_diagnostics.get('candidates_total', '—')}"
        )
        lines.append(
            f"- **kept_after_scoring:** {empty_report_diagnostics.get('kept_after_scoring', '—')}"
        )
        lines.append(
            f"- **kept_final:** {empty_report_diagnostics.get('kept_final', 0)}"
        )
        top5 = empty_report_diagnostics.get("top_5_drop_buckets") or {}
        if top5:
            lines.append("- **top_5_drop_buckets:** " + ", ".join(f"{k}={v}" for k, v in sorted(top5.items())))
        if empty_report_diagnostics.get("dropped_after_scoring_count", 0) > 0:
            lines.append(
                f"- **dropped_after_scoring_count:** {empty_report_diagnostics.get('dropped_after_scoring_count')}"
            )
            sample = empty_report_diagnostics.get("dropped_after_scoring_sample") or []
            for i, s in enumerate(sample[:10], 1):
                lines.append(f"  {i}. [{s.get('reason', '')}] {s.get('title', '')[:60]} | {s.get('url', '')[:50]}")
        lines.append("")
        lines.append("---")
        lines.append("")

    # Level 1 – Strategic Signal Layer
    lines.append("## Strategic Signal Layer")
    lines.append("")
    if not signals:
        lines.append("No structural signals identified for this cycle.")
    else:
        for sig in signals:
            lines.append(_format_signal(sig))
            lines.append("")

    # Level 2 – Structural Category Layer
    lines.append("")
    lines.append("## Structural Category Layer")
    lines.append("")

    # Group evidence by primary category
    by_category: Dict[StructuralCategory, List[EvidenceItem]] = defaultdict(list)
    for evidence_id, category in classifications.items():
        ev = evidence_items.get(evidence_id)
        if ev is None:
            continue
        by_category[category].append(ev)

    # Ordering: newest first within category (by published_at, then ingested_at)
    for cat in all_structural_categories():
        events = by_category.get(cat, [])
        if not events:
            continue

        events.sort(
            key=lambda e: (e.published_at or e.ingested_at, e.ingested_at),
            reverse=True,
        )

        lines.append(f"### {display_label(cat)}")
        lines.append("")

        # Structural snapshot paragraph (simple deterministic summary)
        total_events = len(events)
        regions = {r for ev in events for r in (ev.region_tags or [])}
        region_part = ", ".join(sorted(regions)) if regions else "Global/unspecified regions"
        lines.append(
            f"{total_events} structural event(s) classified under {display_label(cat)} "
            f"across {region_part}."
        )
        lines.append("")
        lines.append("#### Events")
        lines.append("")

        paid_ids = paid_listing_evidence_ids or set()
        paid_facts = paid_listing_facts or {}
        for ev in events:
            if ev.id in paid_ids:
                lines.append(_format_paid_listing_intel(ev, paid_facts.get(ev.id) or {}))
            else:
                one_line = f"{display_label(cat)} event."
                lines.append(_format_event_line(ev, one_line))
            lines.append("")

    return "\n".join(lines)

