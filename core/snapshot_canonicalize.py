from __future__ import annotations

import json
import hashlib
from dataclasses import asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Tuple

from core.filtering import (
    apply_date_window,
    filter_invalid_urls,
    filter_meta_snippet_junk,
    DropRecord,
)
from core.governance_assertions import assert_structural_category_invariants
from core.structural_categories import StructuralCategory, all_structural_categories, display_label
from core.structural_classifier import classify_evidence
from core.structural_models import EvidenceItem
from core.signals import build_signals
from core.url_tools import canonicalize_url


FIXTURE_DIR = Path("development/fixtures/pu_observatory_snapshot")


def _normalize_text(s: str) -> str:
    """Collapse internal whitespace to single space, strip. Used for deterministic snapshot."""
    if not s or not isinstance(s, str):
        return ""
    return " ".join((s or "").split()).strip()


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _parse_iso_date(date_str: str) -> datetime:
    # Expect YYYY-MM-DD, fall back to full ISO
    try:
        return datetime.strptime(date_str[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except Exception:
        try:
            s = date_str.replace("Z", "+00:00")
            return datetime.fromisoformat(s)
        except Exception:
            return datetime(1970, 1, 1, tzinfo=timezone.utc)


def _evidence_from_sources(
    sources: List[Dict[str, Any]],
    now_utc: datetime,
) -> List[EvidenceItem]:
    items: List[EvidenceItem] = []
    for src in sources:
        evid = str(src.get("evidence_id") or "").strip()
        if not evid:
            continue
        url = (src.get("url") or "").strip()
        title = _normalize_text(src.get("title") or "")
        snippet = _normalize_text(src.get("snippet") or "")
        published_date = (src.get("published_date") or "").strip()
        published_at = _parse_iso_date(published_date) if published_date else now_utc
        lane = (src.get("lane") or "A").upper()
        if lane == "C":
            source_type = "lane_c"
        elif lane == "B":
            source_type = "lane_b"
        else:
            source_type = "lane_a"
        region = (src.get("region") or "").strip()
        region_tags = [region] if region else []
        raw_metadata: Dict[str, Any] = {
            "source_name": src.get("source_name"),
            "lane": lane,
        }
        items.append(
            EvidenceItem(
                id=evid,
                source_type=source_type,  # type: ignore[arg-type]
                title=title,
                url=url,
                snippet=snippet,
                published_at=published_at,
                ingested_at=now_utc,
                region_tags=region_tags,
                raw_metadata=raw_metadata,
            )
        )
    return items


def _lane_label(source_type: str) -> str:
    if source_type == "lane_c":
        return "C"
    if source_type == "lane_b":
        return "B"
    return "A"


def _canonical_item_sort_key(
    score: float,
    published_at: datetime,
    url: str,
) -> Tuple[float, str, str]:
    # For descending score and date we invert in the sort call; key is simple here.
    return (score, published_at.isoformat(), url)


def build_canonical_output(
    sources_input: List[Dict[str, Any]],
    customer_spec: Dict[str, Any],
    run_config: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Offline, deterministic structural pipeline snapshot, canonicalized per Milestone 8.
    """
    assert_structural_category_invariants()

    now_utc_str = run_config.get("now_utc") or "2026-02-27T00:00:00Z"
    now_utc = datetime.fromisoformat(now_utc_str.replace("Z", "+00:00")).replace(tzinfo=timezone.utc)
    lookback_days = int(run_config.get("lookback_days") or 30)
    lookback_date = now_utc - timedelta(days=lookback_days)

    # 1) Wrap sources as EvidenceItem
    evidence_items_all = _evidence_from_sources(sources_input, now_utc)

    # 2) Filtering (date, url format, snippet junk) — offline: no network URL validation
    kept, drops_date = apply_date_window(evidence_items_all, now_utc, lookback_days)
    kept, drops_url = filter_invalid_urls(kept, skip_network=True)
    kept, drops_snippet = filter_meta_snippet_junk(kept)
    drop_records: List[DropRecord] = []
    drop_records.extend(drops_date)
    drop_records.extend(drops_url)
    drop_records.extend(drops_snippet)

    # 3) Structural classification (rule-first)
    classifications, _logs, unclassified_lane_c = classify_evidence(kept)

    evidence_map: Dict[str, EvidenceItem] = {e.id: e for e in kept}
    primary_categories: Dict[str, StructuralCategory] = {
        r.evidence_id: r.primary_category for r in classifications
    }

    # 4) Signal processing – to derive scores per signal and evidence
    signals, diag = build_signals(evidence_map, primary_categories, max_signals=7)

    # Map evidence_id -> score (signal score)
    evidence_scores: Dict[str, float] = {}
    for sig in signals:
        sig_score = diag.scores.get(sig.id, 0.0)
        for evid in sig.evidence_ids:
            evidence_scores[evid] = sig_score

    # 5) Build canonical categories structure
    categories_out: List[Dict[str, Any]] = []
    total_candidates = len(evidence_items_all)
    total_kept = len(primary_categories)
    lane_counts_kept: Dict[str, int] = {}
    category_counts_kept: Dict[str, int] = {}

    # Precompute lane per evidence
    lane_by_evid: Dict[str, str] = {
        ev.id: _lane_label(ev.source_type) for ev in kept
    }

    for order_idx, cat in enumerate(all_structural_categories(), start=1):
        # Collect items in this category
        items_for_cat: List[Tuple[EvidenceItem, float]] = []
        for evid, pc in primary_categories.items():
            if pc is not cat:
                continue
            ev = evidence_map.get(evid)
            if not ev:
                continue
            score = float(evidence_scores.get(evid, 0.0))
            items_for_cat.append((ev, score))

        if not items_for_cat:
            continue

        # Sort within category: score DESC, published_date DESC, url ASC
        items_for_cat.sort(
            key=lambda pair: (
                -pair[1],
                -(pair[0].published_at or pair[0].ingested_at).timestamp(),
                canonicalize_url(pair[0].url or "") or (pair[0].url or ""),
            )
        )

        cat_id = cat.value
        cat_name = display_label(cat)
        category_counts_kept[cat_id] = len(items_for_cat)

        items_out: List[Dict[str, Any]] = []
        for ev, score in items_for_cat:
            lane = lane_by_evid.get(ev.id, _lane_label(ev.source_type))
            lane_counts_kept[lane] = lane_counts_kept.get(lane, 0) + 1
            url_norm = canonicalize_url(ev.url or "") or (ev.url or "")
            pub = ev.published_at or ev.ingested_at
            published_date = pub.date().isoformat()

            items_out.append(
                {
                    "evidence_id": ev.id,
                    "title": _normalize_text(ev.title or ""),
                    "url": url_norm,
                    "published_date": published_date,
                    "lane": lane,
                    "primary_category_id": cat_id,
                    "score": float(score),
                    "company_match": False,
                }
            )

        categories_out.append(
            {
                "category_id": cat_id,
                "category_name": cat_name,
                "order": order_idx,
                "items": items_out,
            }
        )

    # 6) Build meta + summary
    # Compute hashes
    spec_bytes = json.dumps(customer_spec, sort_keys=True, separators=(",", ":")).encode("utf-8")
    spec_hash = hashlib.sha256(spec_bytes).hexdigest()
    input_bytes = json.dumps(sources_input, sort_keys=True, separators=(",", ":")).encode("utf-8")
    input_hash = hashlib.sha256(input_bytes).hexdigest()

    total_dropped = total_candidates - total_kept

    canonical: Dict[str, Any] = {
        "meta": {
            "snapshot_version": "1.0",
            "now_utc": now_utc_str,
            "spec_hash": spec_hash,
            "input_hash": input_hash,
        },
        "results": {
            "categories": categories_out,
        },
        "summary": {
            "total_candidates": total_candidates,
            "total_kept": total_kept,
            "total_dropped": total_dropped,
            "kept_by_lane": lane_counts_kept,
            "kept_by_category": category_counts_kept,
        },
    }
    return canonical


def canonical_json_bytes(obj: Dict[str, Any]) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run_snapshot(base_dir: Path | None = None) -> Tuple[Dict[str, Any], str]:
    """
    Load fixture from base_dir (or default), build canonical output, and return (canonical_obj, sha256_hex).
    """
    base = base_dir or FIXTURE_DIR
    sources_path = base / "sources_input.json"
    spec_path = base / "customer_spec.json"
    cfg_path = base / "run_config.json"

    if not sources_path.exists() or not spec_path.exists() or not cfg_path.exists():
        raise FileNotFoundError(
            f"Snapshot fixture missing required files in {base}. "
            f"Expected sources_input.json, customer_spec.json, run_config.json."
        )

    sources_input = _load_json(sources_path)
    customer_spec = _load_json(spec_path)
    run_config = _load_json(cfg_path)

    canonical = build_canonical_output(
        sources_input=sources_input,
        customer_spec=customer_spec,
        run_config=run_config,
    )
    data = canonical_json_bytes(canonical)
    return canonical, sha256_hex(data)

