from __future__ import annotations

from typing import Dict, List, Tuple

from core.jsonld_enrichment import enrich_candidate
from core.structural_models import EvidenceItem


def enrich_evidence_items(items: List[EvidenceItem]) -> Tuple[List[EvidenceItem], List[Dict[str, object]]]:
    """
    Enrich EvidenceItem objects with JSON-LD + meta/OG information.

    Returns:
        (updated_items, enrichment_logs)
    where enrichment_logs is a list of dicts containing:
        - evidence_id
        - enrichment_error (if any)
        - enriched_text_length
        - jsonld_types_found
    """
    updated: List[EvidenceItem] = []
    logs: List[Dict[str, object]] = []

    for item in items:
        enrichment = enrich_candidate(item.url)
        # Attach raw enrichment into metadata; region gating logic can consult this later.
        meta = dict(item.raw_metadata or {})
        meta["enrichment"] = enrichment

        updated.append(
            EvidenceItem(
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
        )

        logs.append(
            {
                "evidence_id": item.id,
                "enrichment_error": enrichment.get("enrichment_error"),
                "enriched_text_length": enrichment.get("enriched_text_length", 0),
                "jsonld_types_found": enrichment.get("jsonld_types_found", []),
            }
        )

    return updated, logs


def should_override_region(evidence_item: EvidenceItem, enriched_region: str) -> bool:
    """
    Decide whether to override region metadata based on enriched content.

    Governance rule:
    - Region is advisory unless enriched content clearly proves mismatch.
    - This helper only encodes the hook; concrete rules can be refined later.
    """
    if not enriched_region:
        return False

    existing = {r.lower() for r in evidence_item.region_tags or []}
    if not existing:
        # No prior region; allowing enrichment to set one is safe.
        return True

    # If enriched region contradicts all existing advisory tags, allow override.
    return enriched_region.lower() not in existing

