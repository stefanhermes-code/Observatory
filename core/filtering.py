from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Tuple
from urllib.parse import urlparse

from core.structural_models import EvidenceItem
from core.url_tools import validate_url, ERROR_OTHER


@dataclass(frozen=True)
class DropRecord:
    evidence_id: str
    reason: str


def apply_date_window(
    items: List[EvidenceItem],
    reference_dt: datetime,
    lookback_days: int,
) -> Tuple[List[EvidenceItem], List[DropRecord]]:
    """
    Keep items whose published_at/ingested_at is within [reference_dt - lookback_days, reference_dt].
    Region is advisory only; no region gating here.
    """
    cutoff = reference_dt - timedelta(days=lookback_days)
    kept: List[EvidenceItem] = []
    dropped: List[DropRecord] = []

    for item in items:
        ts = item.published_at or item.ingested_at
        if ts < cutoff:
            dropped.append(
                DropRecord(
                    evidence_id=item.id,
                    reason=f"date_out_of_window:{ts.isoformat()}<{cutoff.isoformat()}",
                )
            )
        else:
            kept.append(item)
    return kept, dropped


def filter_invalid_urls(
    items: List[EvidenceItem],
    skip_network: bool = False,
) -> Tuple[List[EvidenceItem], List[DropRecord]]:
    """
    Remove items with clearly invalid URLs.

    Rules:
    - URL must have http/https scheme and a netloc.
    - When skip_network is False: use url_tools.validate_url for reachability; 403 is NOT dropped.
    - When skip_network is True (e.g. offline snapshot test): only format check, no HTTP calls.
    - No silent drops: every removal produces a DropRecord.
    """
    kept: List[EvidenceItem] = []
    dropped: List[DropRecord] = []

    for item in items:
        url = (item.url or "").strip()
        p = urlparse(url)
        if p.scheme not in ("http", "https") or not p.netloc:
            dropped.append(DropRecord(evidence_id=item.id, reason="invalid_url_format"))
            continue

        if not skip_network:
            status, _code = validate_url(url)
            if status == ERROR_OTHER:
                dropped.append(DropRecord(evidence_id=item.id, reason=f"url_validation_error:{status}"))
                continue

        kept.append(item)

    return kept, dropped


JUNK_SNIPPET_PATTERNS = (
    "enable javascript",
    "cookies to improve your experience",
    "sign in to read",
    "subscribe to read",
    "accept cookies",
)


def filter_meta_snippet_junk(items: List[EvidenceItem]) -> Tuple[List[EvidenceItem], List[DropRecord]]:
    """
    Filter out obvious meta-snippet junk.

    Heuristics (conservative, can be tightened later):
    - Empty or very short snippet (< 20 characters).
    - Snippet dominated by boilerplate cookie/login text.
    """
    kept: List[EvidenceItem] = []
    dropped: List[DropRecord] = []

    for item in items:
        snippet = (item.snippet or "").strip()
        if len(snippet) < 20:
            dropped.append(DropRecord(evidence_id=item.id, reason="snippet_too_short"))
            continue

        lower = snippet.lower()
        if any(pat in lower for pat in JUNK_SNIPPET_PATTERNS):
            dropped.append(DropRecord(evidence_id=item.id, reason="snippet_junk_pattern"))
            continue

        kept.append(item)

    return kept, dropped

