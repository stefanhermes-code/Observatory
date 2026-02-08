"""
V2-LLM-01: Structured extraction from candidate_articles.
Input: candidate_articles rows for a run.
Output: normalized signals + signal_occurrences persisted (each references candidate_article_id).
"""

from typing import List, Dict, Any
from datetime import datetime

# Signal types from migration 001 (enum signal_type)
SIGNAL_TYPES = [
    "capacity_assets",
    "regulation_standards",
    "mna_partnerships",
    "pricing_feedstocks",
    "demand_enduse",
    "technology_recycling",
    "competitive_actions",
    "safety_incidents",
    "other",
]


def _normalize_signal_from_candidate(candidate: Dict) -> Dict[str, Any]:
    """
    Normalize one candidate_article into a signal record (no LLM).
    Uses title/snippet; signal_type default 'other'. Optional: add LLM later for signal_type/companies.
    """
    title = (candidate.get("title") or "").strip() or "Untitled"
    snippet = (candidate.get("snippet") or "").strip()
    summary = snippet if snippet else title
    canonical_url = (candidate.get("canonical_url") or candidate.get("url") or "").strip() or None
    return {
        "canonical_url": canonical_url,
        "title": title[:500] if title else "Untitled",
        "summary": (summary[:2000] if summary else title)[:2000],
        "signal_type": "other",
        "companies": [],
        "regions": [],
        "value_chain_links": [],
        "confidence": 3,
    }


def run_intelligence_extraction(
    run_id: str,
    workspace_id: str,
    specification_id: str,
    candidates: List[Dict],
) -> Dict[str, int]:
    """
    Extract signals from candidate_articles and persist signals + signal_occurrences.
    Each candidate yields one signal and one occurrence (occurrence references candidate_article_id).

    Args:
        run_id, workspace_id, specification_id: scope
        candidates: list of candidate_articles rows (must include 'id' for candidate_article_id)

    Returns:
        {"signals_created": N, "occurrences_created": N}
    """
    from core.generator_db import get_supabase_client

    if not candidates:
        return {"signals_created": 0, "occurrences_created": 0}

    supabase = get_supabase_client()
    now = datetime.utcnow().isoformat()
    signals_created = 0
    occurrences_created = 0

    for c in candidates:
        candidate_id = c.get("id")
        if not candidate_id:
            continue
        signal_row = _normalize_signal_from_candidate(c)
        signal_row["first_seen_at"] = now
        signal_row["last_seen_at"] = now

        try:
            ins = supabase.table("signals").insert(signal_row).execute()
            signal_data = ins.data[0] if ins.data else None
        except Exception:
            signal_data = None

        if not signal_data:
            continue

        signal_id = signal_data.get("id")
        occ_row = {
            "signal_id": signal_id,
            "workspace_id": workspace_id,
            "specification_id": specification_id,
            "run_id": run_id,
            "candidate_article_id": candidate_id,
        }
        try:
            supabase.table("signal_occurrences").insert(occ_row).execute()
            signals_created += 1
            occurrences_created += 1
        except Exception:
            pass

    return {"signals_created": signals_created, "occurrences_created": occurrences_created}
