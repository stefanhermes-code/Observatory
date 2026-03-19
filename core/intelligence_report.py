"""
PU Observatory – Intelligence Report Generation.

Transforms classified signals into a customer-facing intelligence briefing: signal
grouping, development extraction, evidence anchoring, signal strength, and generated
Strategic Implications. Report is suitable for external distribution.
"""

from __future__ import annotations

import csv
import json
import re
import html
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# -----------------------------------------------------------------------------
# Section and theme configuration (report structure)
# -----------------------------------------------------------------------------

REPORT_SECTIONS = [
    "Market Developments",
    "Technology and Innovation",
    "Capacity and Investment Activity",
    "Corporate Developments",
    "Sustainability and Circular Economy",
    "Strategic Implications",
]

#
# NOTE: Run 9 changes decouple category from report section.
# The legacy CATEGORY_TO_SECTION / CONFIGURATOR_TO_CLASSIFIER mappings are kept for compatibility
# with older code paths, but this run uses flexible keyword-based mapping instead.
#
CATEGORY_TO_SECTION = {
    "Market Intelligence": "Market Developments",
    "Technology and Innovation": "Technology and Innovation",
    "Capacity Expansion": "Capacity and Investment Activity",
    "Sustainability and Circularity": "Sustainability and Circular Economy",
}

CONFIGURATOR_TO_CLASSIFIER = {
    "capacity": "Capacity Expansion",
    "sustainability": "Sustainability and Circularity",
    "m_and_a": "Market Intelligence",
    "company_news": "Market Intelligence",
    "regional_monitoring": "Market Intelligence",
    "industry_context": "Market Intelligence",
    "value_chain": "Market Intelligence",
    "competitive": "Market Intelligence",
    "early_warning": "Market Intelligence",
    "executive_briefings": "Market Intelligence",
}

# Theme keywords: (theme_id, theme_label) for grouping signals
# Order matters: first match wins for section override (e.g. corporate, capacity)
THEME_KEYWORDS: List[Tuple[str, str, List[str]]] = [
    ("corporate", "Corporate activity and restructuring", [
        "acquisition", "acquires", "merger", "joint venture", "partnership", "partners",
        "restructuring", "sale", "divest", "alliance", "collaboration", "acquired", "acquires",
        "announces pending sale", "strategic partnership", "joint venture", "mou",
    ]),
    ("capacity", "Capacity and investment activity", [
        "capacity", "expansion", "plant", "facility", "ground", "break ground",
        "production facility", "manufacturing facility", "new plant", "expands",
        "production capacity", "breaks ground", "inaugurate", "new facility",
    ]),
    ("pricing", "Pricing and cost pressures", [
        "price", "prices", "pricing", "cost", "costs", "increase", "forecast",
    ]),
    ("regulatory", "Regulatory and standards developments", [
        "epa", "regulatory", "regulation", "regulations", "standards", "compliance",
        "tsca", "dtsc", "certipur", "flammability standards",
    ]),
    ("demand_outlook", "Demand and market outlook", [
        "mdi", "tdi", "polyol", "polyols", "isocyanate", "isocyanates",
        "market size", "market share", "growth", "forecast", "outlook", "demand",
        "market analysis", "market report", "market trends", "cagr", "billion",
    ]),
    ("recycling_circular", "Recycling and circular economy", [
        "recycling", "recycled", "circular", "depolymerization", "closed-loop",
        "chemical recycling", "mechanical recycling", "recycle", "upcycling",
    ]),
    ("bio_based", "Bio-based and sustainable materials", [
        "bio-based", "biobased", "bio based", "renewable", "sustainable",
        "non-isocyanate", "without toxic", "green", "biomass balance",
    ]),
    ("applications", "Application and segment developments", [
        "automotive", "construction", "footwear", "insulation", "foam", "coating",
        "adhesive", "mattress", "elastomer", "spray foam", "rigid foam", "flexible foam",
    ]),
    ("technology", "Technology and process innovation", [
        "synthesis", "process", "technology", "raw material", "polyester polyol",
        "polyether", "catalyst", "additive", "formulation", "non-toxic", "innovation",
    ]),
]

# Fallback theme when no keyword matches
DEFAULT_THEME = ("general", "Industry developments")


def _normalize_text(t: str) -> str:
    if not t:
        return ""
    return " ".join(re.sub(r"\s+", " ", (t or "").lower().strip()).split())


def _section_from_theme_id(theme_id: str) -> str:
    if theme_id == "corporate":
        return "Corporate Developments"
    if theme_id == "capacity":
        return "Capacity and Investment Activity"
    if theme_id == "regulatory":
        return "Sustainability and Circular Economy"
    if theme_id == "technology":
        return "Technology and Innovation"
    if theme_id in ("recycling_circular", "bio_based"):
        return "Sustainability and Circular Economy"
    if theme_id in ("demand_outlook", "applications", "pricing"):
        return "Market Developments"
    return "Market Developments"


def _infer_theme_and_primary_section(article: Dict[str, Any]) -> Tuple[str, str, str]:
    """Returns (primary_section, theme_id, theme_label). Keyword-based, decoupled from category."""
    title = _normalize_text(article.get("title") or "")

    best: Tuple[int, str, str] = (0, DEFAULT_THEME[0], DEFAULT_THEME[1])
    for theme_id, theme_label, keywords in THEME_KEYWORDS:
        score = sum(1 for kw in keywords if kw in title)
        if score > best[0]:
            best = (score, theme_id, theme_label)

    _score, theme_id, theme_label = best
    if _score <= 0:
        theme_id, theme_label = DEFAULT_THEME
    primary_section = _section_from_theme_id(theme_id)
    return primary_section, theme_id, theme_label


def _assign_theme_and_section(article: Dict[str, Any]) -> Tuple[str, str, str]:
    """
    Returns (section, theme_id, theme_label).
    Run 9: category is NOT mapped to section; sections are keyword-derived and may be rebalanced.
    """
    if article.get("_balanced_section"):
        section = article.get("_balanced_section")
        theme_id = article.get("_theme_id")
        theme_label = article.get("_theme_label")
        if theme_id and theme_label:
            return section, theme_id, theme_label

    section, theme_id, theme_label = _infer_theme_and_primary_section(article)
    return section, theme_id, theme_label


def _cluster_key(article: Dict[str, Any]) -> Tuple[str, str]:
    section, theme_id, _ = _assign_theme_and_section(article)
    return (section, theme_id)


ALLOWED_RUN9_CATEGORIES = ["Capacity", "Technology", "Market", "Corporate", "Sustainability", "Other"]


def _infer_allowed_category(article: Dict[str, Any]) -> str:
    """
    Run 9 classification:
    - category is neutral and MUST NOT leak into section mapping
    - allowed categories: Capacity, Technology, Market, Corporate, Sustainability, Other
    - "Unknown" must not appear anywhere: use "Other" as neutral fallback.
    """
    title = _normalize_text(article.get("title") or "")
    config_cat = (article.get("configurator_category") or "").strip()

    # Ultra-relaxed signals: if evidence is weak/ambiguous, default to Other
    weak_content = bool(article.get("weak_content_signal"))
    pu_anchor_missing = bool(article.get("pu_anchor_missing"))
    missing_category = bool(article.get("missing_category"))
    category_ambiguous = weak_content or pu_anchor_missing or missing_category

    # Dominant signal: infer a primary theme and map it to an allowed category.
    primary_section, theme_id, _theme_label = _infer_theme_and_primary_section(article)
    if theme_id == "capacity":
        inferred = "Capacity"
    elif theme_id == "technology":
        inferred = "Technology"
    elif theme_id == "corporate":
        inferred = "Corporate"
    elif theme_id == "regulatory" or theme_id in ("recycling_circular", "bio_based"):
        inferred = "Sustainability"
    elif theme_id in ("demand_outlook", "applications", "pricing"):
        inferred = "Market"
    else:
        inferred = ""

    # If theme inference failed (general), use configurator category.
    if not inferred:
        if config_cat == "capacity":
            inferred = "Capacity"
        elif config_cat == "sustainability":
            inferred = "Sustainability"
        elif config_cat in ("m_and_a", "executive_briefings", "competitive", "company_news"):
            inferred = "Corporate"
        elif config_cat in ("industry_context", "regional_monitoring", "early_warning", "value_chain", "value_chain_link", "value_chain_link"):
            inferred = "Market"
        else:
            inferred = "Other"

    # Neutral fallback when evidence is weak.
    if category_ambiguous and inferred not in ("Capacity", "Technology", "Corporate", "Sustainability"):
        return "Other"

    # Final guardrail: never return "Unknown".
    if not inferred or inferred == "unknown":
        return "Other"
    return inferred if inferred in ALLOWED_RUN9_CATEGORIES else "Other"


# -----------------------------------------------------------------------------
# Signal strength
# -----------------------------------------------------------------------------

def _signal_strength(count: int) -> str:
    if count <= 2:
        return "Weak"
    if count <= 5:
        return "Moderate"
    return "Strong"


# -----------------------------------------------------------------------------
# Evidence: one short descriptive line per signal (no raw article titles)
# -----------------------------------------------------------------------------

_TITLE_SUFFIXES = [
    r"\s*\|\s*Plastmatch News.*",
    r"\s*-\s*ScienceDirect.*",
    r"\s*\|\s*Springer Nature Link.*",
    r"\s*\(RSC Publishing\).*",
    r"\s*-\s*PubMed.*",
    r"\s*::\s*Huntsman.*",
    r"\s*-\s*News.*",
    r"\s*\|\s*PCI Magazine.*",
    r"\s*\|\s*Adhesives.*",
    r"\s*–\s*PR Times.*",
    r"\s*\|\s*LinkedIn.*",
    r"\s*\|\s*Springer.*",
    r"\s*-.*Report.*",
    r"\s*\[.*\].*",
]


def _title_to_evidence_line(title: str) -> str:
    """Traceable evidence summary: specific, no vague 'industry coverage suggests'."""
    if not (title or "").strip():
        return "Reported developments during the period support this theme."
    t = title.strip()
    for pat in _TITLE_SUFFIXES:
        t = re.sub(pat, "", t, flags=re.IGNORECASE).strip()
    t = re.sub(r"\s+", " ", t).strip()
    if not t:
        return "Reported developments during the period support this theme."
    lower = t.lower()
    if "mdi" in lower and ("market" in lower or "size" in lower or "growth" in lower):
        return "Forecasts published during the period project continued MDI demand growth and market expansion."
    if "tdi" in lower and ("market" in lower or "price" in lower or "forecast" in lower):
        return "Pricing and market commentary during the period highlighted TDI outlook and cost developments."
    if "polyol" in lower and ("market" in lower or "growth" in lower):
        return "Market reports during the period indicated polyol demand and growth outlook."
    if "isocyanate" in lower and ("market" in lower or "size" in lower):
        return "Market analysis published during the period reported on isocyanate market size and outlook."
    if "market" in lower and ("growth" in lower or "size" in lower or "forecast" in lower):
        return "Forecasts published during the period project demand growth for polyurethane and feedstocks."
    if "price" in lower or "pricing" in lower or "cost" in lower:
        return "Pricing commentary during the period highlighted cost and price developments in relevant markets."
    if "acquires" in lower or "acquisition" in lower or "acquired" in lower:
        return "Reported developments included corporate acquisition or merger activity in the polyurethane value chain."
    if "joint venture" in lower or "partnership" in lower:
        return "Reported developments included partnership or joint venture activity in the industry."
    if "recycling" in lower or "recycle" in lower or "circular" in lower or "depolymerization" in lower:
        return "Reported developments included new recycling initiatives and technologies for polyurethane materials."
    if "bio-based" in lower or "bio based" in lower or "sustainable" in lower:
        return "Reported developments included bio-based or sustainable polyurethane materials and production routes."
    if "capacity" in lower or "expansion" in lower or "plant" in lower or "facility" in lower or "ground" in lower:
        return "Reported developments included capacity expansion or new production facility announcements."
    if "epa" in lower or "regulatory" in lower or "regulation" in lower:
        return "Regulatory or standards developments affecting the industry were reported during the period."
    if "polyurethane" in lower:
        return "Reported developments during the period support this theme."
    return "Reported developments during the period support this theme."


# -----------------------------------------------------------------------------
# Direction of Impact (customer-facing only)
# -----------------------------------------------------------------------------

DIRECTION_OF_IMPACT_VALUES = ["Demand", "Supply", "Technology", "Competition", "Regulation", "Sustainability"]


def _direction_of_impact_for(section: str, theme_id: str) -> List[str]:
    """One or more of Demand, Supply, Technology, Competition, Regulation, Sustainability."""
    out: List[str] = []
    if section == "Market Developments":
        if theme_id in ("demand_outlook", "applications", "pricing"):
            out.append("Demand")
        if theme_id == "pricing":
            out.append("Supply")
    if section == "Technology and Innovation":
        out.append("Technology")
    if section == "Capacity and Investment Activity":
        out.append("Supply")
    if section == "Corporate Developments":
        out.append("Competition")
    if section == "Sustainability and Circular Economy":
        out.append("Sustainability")
        if theme_id == "regulatory":
            out.append("Regulation")
    if theme_id == "regulatory":
        out.append("Regulation")
    if not out:
        out.append("Demand")
    return list(dict.fromkeys(out))  # preserve order, dedupe


def _business_relevance_for(section: str, theme_id: str) -> str:
    """One sentence on commercial or strategic relevance."""
    if section == "Market Developments":
        if theme_id == "demand_outlook":
            return "This may strengthen medium-term demand expectations for polyurethane feedstocks and systems."
        if theme_id == "pricing":
            return "This may affect margins and competitive positioning for producers and downstream users."
        if theme_id == "applications":
            return "This may support demand for polyurethane in specific application segments."
        return "This may influence demand, pricing, or regional market dynamics."
    if section == "Technology and Innovation":
        return "This may influence future product capabilities and industry direction."
    if section == "Capacity and Investment Activity":
        return "This may influence future supply conditions and regional availability."
    if section == "Corporate Developments":
        return "This may affect competitive structure and regional presence in the value chain."
    if section == "Sustainability and Circular Economy":
        if theme_id == "regulatory":
            return "This may reinforce future compliance requirements for producers."
        return "This may influence product design, sourcing, and market expectations."
    return "This may inform strategic and commercial planning."


def _interpretation_for(section: str, theme_id: str, signal_count: int) -> str:
    """One short paragraph interpreting what the development suggests for the industry."""
    strength = _signal_strength(signal_count)
    if section == "Market Developments":
        if theme_id == "demand_outlook":
            return "Multiple analyses point to sustained demand for polyurethane feedstocks and systems across key applications. Industry participants may use these outlooks to inform capacity and commercial planning."
        if theme_id == "pricing":
            return "Pricing and cost developments may affect margins and competitive positioning. Monitoring raw material and energy costs remains relevant for planning."
        if theme_id == "applications":
            return "Application-level coverage suggests continued diversification of polyurethane use across segments. Growth in specific applications may influence product and regional strategy."
        return "Market-related signals indicate ongoing interest in demand, pricing, and regional dynamics in the polyurethane industry."
    if section == "Technology and Innovation":
        if theme_id == "recycling_circular" or theme_id == "bio_based":
            return "Advances in recycling and bio-based routes support a shift toward more sustainable and differentiated products. These developments may influence future product portfolios and regulatory alignment."
        return "Technological developments suggest continued innovation in materials, processes, and applications. These may affect future product capabilities and industry direction."
    if section == "Capacity and Investment Activity":
        return "Capacity and investment activity indicates industry confidence in medium-term demand and a focus on supply security and regional presence. These developments may influence future supply conditions."
    if section == "Corporate Developments":
        return "Corporate activity suggests ongoing consolidation and repositioning in the polyurethane value chain, with implications for competitive structure and regional coverage."
    if section == "Sustainability and Circular Economy":
        if theme_id == "regulatory":
            return "Regulatory and standards developments may shape product design, sourcing, and compliance requirements in the medium term."
        return "Sustainability and circular economy developments are likely to influence product design, sourcing, and market expectations. Recycling and bio-based initiatives remain central to industry evolution."
    return "These developments reflect observable industry activity during the reporting period and may inform strategic discussion."


def _development_title_for(section: str, theme_id: str, theme_label: str) -> str:
    return theme_label


# -----------------------------------------------------------------------------
# Development block
# -----------------------------------------------------------------------------

@dataclass
class Development:
    section: str
    title: str
    explanation: str
    signal_strength: str  # Weak | Moderate | Strong
    evidence_lines: List[str]
    business_relevance: str
    direction_of_impact: List[str]  # Demand | Supply | Technology | Competition | Regulation | Sustainability
    interpretation: str
    signal_count: int = 0
    signals: List[Dict[str, Any]] = field(default_factory=list)  # raw articles for appendix


# -----------------------------------------------------------------------------
# Load data
# -----------------------------------------------------------------------------

def load_classified_articles(path: Path) -> List[Dict[str, Any]]:
    """Load from classified_articles.csv (legacy). Returns list with keys title, url, category, tier, date, source."""
    articles: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            cat = (row.get("category") or "").strip()
            if not cat:
                continue
            articles.append({
                "title": (row.get("title") or "").strip(),
                "url": (row.get("url") or "").strip(),
                "category": cat,
                "tier": row.get("tier"),
                "date": (row.get("date") or "").strip(),
                "source": (row.get("source") or "").strip(),
            })
    return articles


def load_signals(path: Path) -> List[Dict[str, Any]]:
    """
    Load from signals.csv (master signal dataset).
    Returns list with keys title, url, category, tier, date, source, query_id
    (category from classifier_category for compatibility with clustering).
    """
    signals: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            cat = (row.get("classifier_category") or "").strip()
            if not cat:
                continue
            signals.append({
                "title": (row.get("title") or "").strip(),
                "url": (row.get("url") or "").strip(),
                "category": cat,
                "tier": row.get("tier"),
                "date": (row.get("date") or "").strip(),
                "source": (row.get("source") or "").strip(),
                "query_id": (row.get("query_id") or "").strip(),
            })
    return signals


def load_query_plan(path: Path) -> Dict[str, Dict[str, str]]:
    """
    Load query_plan.csv: query_id -> {region, configurator_category, value_chain_link}.
    Used to join with signals for post-classification customer filter.
    """
    plan_map: Dict[str, Dict[str, str]] = {}
    with path.open("r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            qid = (row.get("query_id") or "").strip()
            if not qid:
                continue
            plan_map[qid] = {
                "region": (row.get("region") or "").strip(),
                "configurator_category": (row.get("configurator_category") or "").strip(),
                "value_chain_link": (row.get("value_chain_link") or "").strip(),
            }
    return plan_map


def apply_customer_filter(
    signals: List[Dict[str, Any]],
    query_plan_map: Dict[str, Dict[str, str]],
    spec: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Filter signals by customer specification (regions, categories, value_chain_links).
    Signal is kept only if it explicitly matches the spec. Unset metadata (empty string)
    does NOT pass when the customer has constrained that dimension (strict behavior per
    live alignment plan §7).
    """
    regions = spec.get("regions") or []
    categories = spec.get("categories") or []
    value_chain_links = spec.get("value_chain_links") or []
    if not regions and not categories and not value_chain_links:
        return list(signals)

    filtered: List[Dict[str, Any]] = []
    for s in signals:
        qid = s.get("query_id") or ""
        meta = query_plan_map.get(qid) or {}
        region = meta.get("region") or ""
        config_cat = meta.get("configurator_category") or ""
        vcl = meta.get("value_chain_link") or ""

        ok_region = not regions or region in regions
        ok_cat = not categories or config_cat in categories
        ok_vcl = not value_chain_links or vcl in value_chain_links
        if ok_region and ok_cat and ok_vcl:
            filtered.append(s)
    return filtered


def generate_report_from_signals(
    signals: List[Dict[str, Any]],
    query_plan_map: Dict[str, Dict[str, str]],
    spec: Dict[str, Any],
    write_metrics: bool = False,
    write_html: bool = True,
    report_period_days: Optional[int] = None,
    run_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate Phase 5 report from in-memory master signals and query plan map (live path).
    Applies strict post-classification customer filter, then group_signals, build_developments,
    render_report. No file I/O for inputs. Returns dict with report_text, html (optional), metrics (optional),
    run_audit_metrics (step counts and drop_reason_counts for per-run audit).
    spec: regions, categories, value_chain_links (filter); included_sections, minimum_signal_strength_in_report,
    report_title (for HTML).
    """
    from core.customer_filter import filter_signals_by_spec_with_stats

    # Normalize to article format.
    # Run 9: classification is light/neutral and returns one of:
    # Capacity, Technology, Market, Corporate, Sustainability, Other
    # and MUST NOT return "Unknown".
    articles: List[Dict[str, Any]] = []
    missing_classifier_count = 0
    for s in signals:
        config_cat = (s.get("category") or "").strip()
        base: Dict[str, Any] = {
            "title": s.get("title") or "",
            "url": s.get("url") or "",
            "date": s.get("date") or "",
            "source": s.get("source") or "",
            "query_id": s.get("query_id") or "",
            "region": s.get("region") or "",
            "value_chain_link": s.get("value_chain_link") or "",
            "configurator_category": config_cat,
            # Evidence-engine flags for neutral classification
            "pu_anchor_missing": bool(s.get("pu_anchor_missing")),
            "weak_content_signal": bool(s.get("weak_content_signal")),
            "missing_category": bool(s.get("missing_category")),
            "missing_value_chain_link": bool(s.get("missing_value_chain_link")),
        }
        base["category"] = _infer_allowed_category(base)
        articles.append(base)

    filtered, customer_filter_stats = filter_signals_by_spec_with_stats(articles, query_plan_map, spec or {})

    # Section filter: count signals that map to included_sections and capture mapping diagnostics
    included_sections = (spec or {}).get("included_sections")
    section_list = list(included_sections) if included_sections else None
    after_section_count = 0
    drop_section_count = 0

    # Run 9 mapping:
    # - decouple category from section
    # - assign a primary section from keyword theme
    # - rebalance section distribution so no single section exceeds 60%
    from collections import defaultdict as _defaultdict, Counter as _Counter

    category_distribution: Dict[str, int] = dict(_Counter(a.get("category") for a in filtered if a.get("category")))

    mapping_attempts_total = len(filtered)
    mapping_success_by_section: Dict[str, int] = _defaultdict(int)
    mapping_fail_no_matching_section_rule = 0
    mapping_fail_category_not_linked_to_section = 0
    mapping_fail_value_chain_not_linked = 0
    mapping_fail_multi_match_conflict = 0
    mapping_fail_other = 0
    signals_unmapped_but_categorized = 0
    top_unmapped_signals_sample: List[Dict[str, Any]] = []

    # 1) Primary section assignment (keyword-based)
    section_counts: Dict[str, int] = _defaultdict(int)
    buckets: Dict[str, List[int]] = _defaultdict(list)
    for idx, a in enumerate(filtered):
        primary_section, theme_id, theme_label = _infer_theme_and_primary_section(a)
        a["_theme_id"] = theme_id
        a["_theme_label"] = theme_label
        a["_balanced_section"] = primary_section
        section_counts[primary_section] += 1
        buckets[primary_section].append(idx)

    # 2) Rebalance section dominance (>60%)
    total_mapped = max(1, len(filtered))
    max_allowed_per_section = int(0.6 * total_mapped)
    if max_allowed_per_section < 1:
        max_allowed_per_section = 1

    included_set = set(section_list) if section_list is not None else set(section_counts.keys())
    included_set = included_set or set(section_counts.keys())
    # Yield optimization: we avoid pushing signals into "Strategic Implications" during rebalance,
    # because downstream development extraction currently skips that section.
    included_set.discard("Strategic Implications")

    # Deterministic order: iterate until counts are within target.
    while True:
        dominant = None
        dominant_count = 0
        for sec, cnt in section_counts.items():
            if sec in included_set and cnt > dominant_count:
                dominant, dominant_count = sec, cnt
        if dominant is None or dominant_count <= max_allowed_per_section:
            break

        # Pick the least-filled alternative section that can accept more.
        target = None
        for sec in sorted(included_set):
            if sec == dominant:
                continue
            if section_counts.get(sec, 0) < max_allowed_per_section:
                if target is None or section_counts.get(sec, 0) < section_counts.get(target, 0):
                    target = sec
        if not target:
            break

        # Reassign one deterministic item from the dominant bucket.
        if not buckets.get(dominant):
            break
        idx_to_move = buckets[dominant].pop(0)
        filtered[idx_to_move]["_balanced_section"] = target
        section_counts[dominant] -= 1
        section_counts[target] += 1
        buckets[target].append(idx_to_move)

    # 3) Count final mapped-to-section outcomes
    for a in filtered:
        sec = a.get("_balanced_section") or "Market Developments"
        if section_list is None or sec in section_list:
            after_section_count += 1
            mapping_success_by_section[sec] += 1
        else:
            drop_section_count += 1
            reason = "section_not_in_included_sections"
            mapping_fail_no_matching_section_rule += 1

            config_cat = (a.get("configurator_category") or "").strip()
            vcl = (a.get("value_chain_link") or "").strip()
            if config_cat and vcl:
                signals_unmapped_but_categorized += 1
                if len(top_unmapped_signals_sample) < 10:
                    top_unmapped_signals_sample.append(
                        {
                            "title": a.get("title") or "",
                            "category": config_cat,
                            "value_chain_link": vcl,
                            "reason": reason,
                        }
                    )

    clusters = group_signals(filtered)
    developments_before_strength = build_developments(clusters)

    # No cluster formed: signals in Strategic Implications (we skip that section in build_developments)
    no_cluster_count = sum(len(sigs) for (sec, _), sigs in clusters.items() if sec == "Strategic Implications")

    included_sections_set = set(included_sections or [])
    min_strength = (spec or {}).get("minimum_signal_strength_in_report")
    order = {"Weak": 0, "Moderate": 1, "Strong": 2}
    if min_strength and isinstance(min_strength, str):
        threshold = order.get(min_strength, 0)
        developments_after_strength = [d for d in developments_before_strength if order.get(d.signal_strength, 0) >= threshold]
        drop_strength_count = len(developments_before_strength) - len(developments_after_strength)
    else:
        developments_after_strength = list(developments_before_strength)
        drop_strength_count = 0

    developments_written = [d for d in developments_after_strength if not included_sections_set or d.section in included_sections_set]
    written_count = len(developments_written)

    developments = developments_after_strength
    signal_map_enabled = (spec or {}).get("signal_map_enabled", True)
    evidence_appendix_enabled = (spec or {}).get("evidence_appendix_enabled", True)
    report_text = render_report(
        developments,
        included_sections=included_sections,
        signal_map_enabled=signal_map_enabled,
        evidence_appendix_enabled=evidence_appendix_enabled,
        report_period_days=report_period_days,
        spec=spec,
    )

    run_audit_metrics: Dict[str, Any] = {
        "master_signals_loaded_count": len(signals),
        "candidates_after_customer_filter_count": len(filtered),
        "candidates_after_section_filter_count": after_section_count,
        "category_distribution": category_distribution,
        "grouped_clusters_count": len(clusters),
        "extracted_developments_count": len(developments_before_strength),
        "developments_after_strength_threshold_count": len(developments_after_strength),
        "developments_written_to_report_count": written_count,
        "drop_failed_region_filter": customer_filter_stats.get("failed_region_filter", 0),
        "drop_failed_value_chain_filter": customer_filter_stats.get("failed_value_chain_filter", 0),
        "drop_no_mapped_category": customer_filter_stats.get("no_mapped_category", 0),
        "drop_failed_section_filter": drop_section_count,
        "drop_no_cluster_formed": no_cluster_count,
        "drop_below_minimum_strength": drop_strength_count,
        "drop_missing_classifier_category": missing_classifier_count,
        "mapping_stats": {
            "mapping_attempts_total": mapping_attempts_total,
            "mapping_success_by_section": dict(mapping_success_by_section),
            "mapping_fail_no_matching_section_rule": mapping_fail_no_matching_section_rule,
            "mapping_fail_category_not_linked_to_section": mapping_fail_category_not_linked_to_section,
            "mapping_fail_value_chain_not_linked": mapping_fail_value_chain_not_linked,
            "mapping_fail_multi_match_conflict": mapping_fail_multi_match_conflict,
            "mapping_fail_other": mapping_fail_other,
            "signals_unmapped_but_categorized": signals_unmapped_but_categorized,
            "top_unmapped_signals_sample": top_unmapped_signals_sample,
        },
    }

    out: Dict[str, Any] = {"report_text": report_text, "run_audit_metrics": run_audit_metrics}
    if write_html:
        title = (spec or {}).get("report_title") or "Polyurethane Industry Intelligence Briefing"
        # Build pie chart for signal map (§11)
        signal_map_sections = [
            "Market Developments",
            "Technology and Innovation",
            "Capacity and Investment Activity",
            "Corporate Developments",
            "Sustainability and Circular Economy",
            "Regulatory Developments",
        ]
        if (spec or {}).get("included_sections"):
            signal_map_sections = [s for s in signal_map_sections if s in (spec or {}).get("included_sections", [])]
        by_sec: Dict[str, int] = defaultdict(int)
        for d in developments:
            by_sec[d.section] += 1
        pie_html = _signal_map_pie_svg(by_sec, len(developments), signal_map_sections)
        try:
            from core.app_version import get_deploy_version
            _deploy = get_deploy_version()
        except Exception:
            _deploy = None
        out["html"] = markdown_to_simple_html(
            report_text,
            title=title,
            signal_map_pie_html=pie_html if pie_html else None,
            deploy_version=_deploy,
            run_id=run_id,
        )
    if write_metrics:
        out["metrics"] = build_report_metrics(len(filtered), developments)
    return out


def load_category_counts(path: Path) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    with path.open("r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            cat = (row.get("category") or "").strip()
            if cat:
                try:
                    counts[cat] = int(row.get("items_classified") or row.get("number_of_signals") or 0)
                except ValueError:
                    pass
    return counts


# -----------------------------------------------------------------------------
# Group signals into clusters (same section + same theme)
# -----------------------------------------------------------------------------

def group_signals(articles: List[Dict[str, Any]]) -> Dict[Tuple[str, str], List[Dict[str, Any]]]:
    clusters: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for a in articles:
        key = _cluster_key(a)
        clusters[key].append(a)
    return dict(clusters)


# -----------------------------------------------------------------------------
# Build development from cluster
# -----------------------------------------------------------------------------

def build_developments(clusters: Dict[Tuple[str, str], List[Dict[str, Any]]]) -> List[Development]:
    developments: List[Development] = []
    for (section, theme_id), signals in clusters.items():
        if not signals or section == "Strategic Implications":
            continue
        _, theme_label = next(
            ((tid, tlab) for tid, tlab, _ in THEME_KEYWORDS if tid == theme_id),
            DEFAULT_THEME,
        )
        title = _development_title_for(section, theme_id, theme_label)
        count = len(signals)
        strength = _signal_strength(count)
        evidence_lines = [_title_to_evidence_line(s.get("title") or "") for s in signals]
        explanation = f"This development is supported by {count} observed signal{'s' if count != 1 else ''} during the reporting period."
        interpretation = _interpretation_for(section, theme_id, count)
        business_relevance = _business_relevance_for(section, theme_id)
        direction_of_impact = _direction_of_impact_for(section, theme_id)
        developments.append(Development(
            section=section,
            title=title,
            explanation=explanation,
            signal_strength=strength,
            evidence_lines=evidence_lines,
            business_relevance=business_relevance,
            direction_of_impact=direction_of_impact,
            interpretation=interpretation,
            signal_count=count,
            signals=list(signals),
        ))
    return developments


# -----------------------------------------------------------------------------
# Strategic Implications — generated from developments (no fixed placeholder)
# -----------------------------------------------------------------------------

def generate_strategic_implications(
    developments: List[Development],
    report_period_days: Optional[int] = None,
    spec: Optional[Dict[str, Any]] = None,
) -> Tuple[List[str], Optional[Dict[str, Any]]]:
    """
    Generate the Strategic Implications section from the report developments via LLM.
    Returns (list of markdown lines for the section body, usage_dict or None).
    On failure or empty developments, returns ([], None); caller can omit the section.
    """
    if not developments:
        return [], None
    period = f"{report_period_days}-day" if isinstance(report_period_days, int) and report_period_days > 0 else "reporting"
    summary_parts = []
    for d in developments[:40]:  # cap input size
        summary_parts.append(f"- [{d.section}] {d.title} ({d.signal_strength}): {d.interpretation[:180]}{'...' if len(d.interpretation) > 180 else ''}")
    context = "\n".join(summary_parts)[:8000]
    try:
        from core.openai_assistant import get_openai_client
        client = get_openai_client()
        if not client:
            return [], None
    except Exception:
        return [], None
    system = (
        "You are a polyurethane industry strategist. Based only on the listed developments from the report, "
        "write a short Strategic Implications section for the polyurethane industry. "
        "Output exactly 3–5 bullet points. Each line must start with '- **Label:** ' (e.g. **Demand:** or **Technology:**) "
        "followed by 1–2 sentences. Use only the themes and facts from the developments; do not add generic or unsupported claims. "
        "Output plain text, no extra headings or markdown beyond the bullet list."
    )
    user = (
        f"Reporting period: {period} window.\n\nDevelopments in this report:\n{context}\n\n"
        "Write 3–5 strategic implication bullets. Each line: '- **Label:** sentence.'"
    )
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.25,
            max_tokens=800,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        )
        choice = resp.choices[0] if resp.choices else None
        text = (choice.message.content or "").strip() if choice else ""
        usage = None
        if getattr(resp, "usage", None):
            usage = {
                "input_tokens": getattr(resp.usage, "input_tokens", 0),
                "output_tokens": getattr(resp.usage, "output_tokens", 0),
                "total_tokens": getattr(resp.usage, "total_tokens", 0),
                "model": getattr(resp, "model", None) or "gpt-4o-mini",
            }
        if not text:
            return [], usage
        # Parse into lines; ensure each line is a bullet
        out_lines = []
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if not line.startswith("-"):
                line = "- " + line
            out_lines.append(line)
        return out_lines, usage
    except Exception:
        return [], None


# -----------------------------------------------------------------------------
# Render report (development blocks; Executive Summary without evidence lists)
# -----------------------------------------------------------------------------

def _render_development_block(d: Development) -> List[str]:
    lines = [
        f"### {d.title}",
        "",
        d.explanation,
        "",
        f"**Signal Strength:** {d.signal_strength}",
        "",
        "**Evidence Signals**",
    ]
    seen: set = set()
    for line in d.evidence_lines:
        if line not in seen:
            seen.add(line)
            lines.append(f"- {line}")
    lines.extend([
        "",
        f"**Business Relevance**",
        d.business_relevance,
        "",
        f"**Direction of Impact** {', '.join(d.direction_of_impact)}",
        "",
        d.interpretation,
        "",
    ])
    return lines


def render_report(
    developments: List[Development],
    included_sections: Optional[List[str]] = None,
    signal_map_enabled: bool = True,
    evidence_appendix_enabled: bool = True,
    report_period_days: Optional[int] = None,
    spec: Optional[Dict[str, Any]] = None,
) -> str:
    by_section: Dict[str, List[Development]] = defaultdict(list)
    for d in developments:
        by_section[d.section].append(d)
    if included_sections:
        by_section = {k: v for k, v in by_section.items() if k in included_sections}

    # Human-readable reporting period label: derive strictly from numeric days, never from free-text fields.
    if isinstance(report_period_days, int) and report_period_days > 0:
        period_label = f"{report_period_days}-day window"
    else:
        period_label = "90-day window"

    def _fmt_list(values: Optional[Iterable[str]]) -> str:
        vals = [str(v) for v in (values or []) if str(v).strip()]
        return ", ".join(sorted(vals)) if vals else "All"

    lines: List[str] = [
        "# Polyurethane Industry Intelligence Briefing",
        "",
        f"*Reporting period: {period_label}*",
        "",
    ]

    # Optional visible Run Scope block at the top of the report
    if spec is not None:
        categories = (spec or {}).get("categories") or []
        regions = (spec or {}).get("regions") or []
        value_chain_links = (spec or {}).get("value_chain_links") or []
        included_sections_scope = (spec or {}).get("included_sections") or []
        min_strength = (spec or {}).get("minimum_signal_strength_in_report") or "None"
        lines.extend(
            [
                "## Run Scope",
                "",
                f"- **Reporting period**: {period_label}",
                f"- **Included categories**: {_fmt_list(categories)}",
                f"- **Included regions**: {_fmt_list(regions)}",
                f"- **Included value chain links**: {_fmt_list(value_chain_links)}",
                f"- **Included sections**: {_fmt_list(included_sections_scope)}",
                f"- **Minimum signal strength**: {min_strength}",
                "",
                "---",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "This briefing summarises notable developments in the polyurethane industry observed during the reporting period. It is intended to support strategic decision-making and does not constitute investment or commercial advice.",
                "",
                "---",
                "",
            ]
        )

    lines.extend(
        [
            "# Executive Summary",
            "",
        ]
    )

    # Executive Summary: narrative highlights only; no evidence lists or article references
    strong = [d for d in developments if d.signal_strength == "Strong"]
    moderate = [d for d in developments if d.signal_strength == "Moderate"]
    seen_titles: set = set()
    summary_bullets = []
    for d in strong[:10]:
        if d.title not in seen_titles:
            seen_titles.add(d.title)
            summary_bullets.append(f"- **{d.title}** ({d.signal_strength}): {d.interpretation[:120]}{'...' if len(d.interpretation) > 120 else ''}")
    for d in moderate[:4]:
        if d.title not in seen_titles:
            seen_titles.add(d.title)
            summary_bullets.append(f"- **{d.title}** ({d.signal_strength}): {d.interpretation[:120]}{'...' if len(d.interpretation) > 120 else ''}")
    if not summary_bullets:
        for d in developments[:6]:
            summary_bullets.append(f"- **{d.title}** ({d.signal_strength}): {d.interpretation[:120]}{'...' if len(d.interpretation) > 120 else ''}")
    lines.extend(summary_bullets)
    lines.append("")
    lines.append("The following sections present each development with supporting evidence and interpretation.")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Signal Map: distribution of developments by section (percentage) — optional per spec
    if signal_map_enabled:
        total_devs = len(developments)
        signal_map_sections = [
            "Market Developments",
            "Technology and Innovation",
            "Capacity and Investment Activity",
            "Corporate Developments",
            "Sustainability and Circular Economy",
            "Regulatory Developments",
        ]
        if included_sections:
            signal_map_sections = [s for s in signal_map_sections if s in included_sections]
        lines.append("# Signal Map")
        lines.append("")
        lines.append("Distribution of reportable developments by theme.")
        lines.append("")
        lines.append("| Section | Developments | Share |")
        lines.append("| --- | --- | --- |")
        for sec in signal_map_sections:
            count = len(by_section.get(sec, []))
            pct = round(100 * count / total_devs, 1) if total_devs else 0
            lines.append(f"| {sec} | {count} | {pct}% |")
        lines.append("")
        lines.append("<!-- SIGNAL_MAP_PIE -->")
        lines.append("")
        lines.append("---")
        lines.append("")

    # Sections with development blocks (order from REPORT_SECTIONS, excluding Strategic Implications;
    # Strategic Implications should be generated by a model, not a fixed placeholder here)
    section_order = [s for s in REPORT_SECTIONS if s != "Strategic Implications"]
    if included_sections:
        section_order = [s for s in section_order if s in included_sections]
    for section in section_order:
        devs = by_section.get(section, [])
        if not devs:
            continue
        lines.append(f"# {section}")
        lines.append("")
        for d in devs:
            lines.extend(_render_development_block(d))
        lines.append("")

    # Strategic Implications — generated from developments (no fixed text)
    si_lines, _ = generate_strategic_implications(
        developments, report_period_days=report_period_days, spec=spec
    )
    if si_lines:
        lines.append("# Strategic Implications")
        lines.append("")
        lines.append("Taken together, the developments observed suggest the following for the polyurethane industry:")
        lines.append("")
        lines.extend(si_lines)
        lines.append("")
        lines.append("This briefing is based on openly reported developments during the reporting period and is intended to support strategic discussion. For specific decisions, further verification and expert advice are recommended.")
        lines.append("")
        lines.append("---")
        lines.append("")

    # Appendix A — Evidence Signals (traceability) — optional per spec
    if evidence_appendix_enabled:
        lines.append("# Appendix A — Evidence Signals")
        lines.append("")
        lines.append("Supporting signals for each development. Source and URL allow verification.")
        lines.append("")
        for d in developments:
            lines.append(f"## {d.title}")
            lines.append("")
            for s in d.signals:
                title = (s.get("title") or "").strip()[:200]
                source = (s.get("source") or "").strip()
                url = (s.get("url") or "").strip()
                date = (s.get("date") or "").strip()
                category = (s.get("category") or "").strip()
                lines.append(f"- **{title}**")
                lines.append(f"  - Source: {source or '—'}")
                lines.append(f"  - URL: {url or '—'}")
                lines.append(f"  - Publication date: {date or '—'}")
                lines.append(f"  - Mapped category: {category or '—'}")
                lines.append("")
            lines.append("")
    return "\n".join(lines).strip() + "\n"


# -----------------------------------------------------------------------------
# Metrics (internal only; not exposed in customer-facing report)
# -----------------------------------------------------------------------------

def build_report_metrics(
    total_classified_signals: int,
    developments: List[Development],
) -> Dict[str, Any]:
    by_section: Dict[str, int] = defaultdict(int)
    strength_dist: Dict[str, int] = defaultdict(int)
    for d in developments:
        by_section[d.section] += 1
        strength_dist[d.signal_strength] += 1
    return {
        "total_classified_signals": total_classified_signals,
        "total_developments_generated": len(developments),
        "developments_per_section": dict(by_section),
        "signal_strength_distribution": dict(strength_dist),
        "report_generation_timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _signal_map_pie_svg(
    by_section_counts: Dict[str, int],
    total: int,
    section_order: List[str],
) -> str:
    """Build an SVG pie chart for signal map (§11). Percentage shares by development theme."""
    if total <= 0:
        return ""
    import math
    colors = [
        "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b",
        "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
    ]
    radius = 80
    cx, cy = 100, 100
    cumulative = 0.0
    segments = []
    for i, sec in enumerate(section_order):
        count = by_section_counts.get(sec, 0)
        if count <= 0:
            continue
        pct = count / total
        start_angle = cumulative * 360.0
        end_angle = (cumulative + pct) * 360.0
        cumulative += pct
        start_rad = math.radians(start_angle - 90)
        end_rad = math.radians(end_angle - 90)
        x1 = cx + radius * math.cos(start_rad)
        y1 = cy + radius * math.sin(start_rad)
        x2 = cx + radius * math.cos(end_rad)
        y2 = cy + radius * math.sin(end_rad)
        large = 1 if (end_angle - start_angle) > 180 else 0
        d = f"M {cx} {cy} L {x1:.2f} {y1:.2f} A {radius} {radius} 0 {large} 1 {x2:.2f} {y2:.2f} Z"
        color = colors[i % len(colors)]
        segments.append(f'<path d="{d}" fill="{color}" stroke="#fff" stroke-width="1"/>')
    if not segments:
        return ""
    svg_inner = "\n".join(segments)
    return f'<div class="signal-map-pie" style="margin:1em 0;"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="200" height="200">{svg_inner}</svg></div>'


def markdown_to_simple_html(
    md_text: str,
    title: str = "Intelligence Report",
    signal_map_pie_html: Optional[str] = None,
    deploy_version: Optional[str] = None,
    run_id: Optional[str] = None,
) -> str:
    """
    Render a constrained Markdown-like report into clean HTML suitable for external use.

    Supported:
    - Headings: #, ##, ###
    - Horizontal rule: ---
    - Bullet lists: - item
    - Tables: GitHub-style pipe tables
    - Inline bold/italic: **bold**, *italic*
    - Signal map pie placeholder: <!-- SIGNAL_MAP_PIE --> replaced with provided HTML
    - deploy_version: if set, shown in the report header for traceability.
    - run_id: if set, shown in the report header so Admin History can be matched to the HTML file.
    """

    lines = md_text.splitlines()
    html_parts: List[str] = []
    i = 0

    def _escape(text: str) -> str:
        return html.escape(text, quote=False)

    def _inline(text: str) -> str:
        # Escape HTML, then apply simple Markdown inline formatting
        escaped = _escape(text)
        escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
        escaped = re.sub(r"\*(.+?)\*", r"<em>\1</em>", escaped)
        return escaped

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Skip empty lines early
        if not stripped:
            i += 1
            continue

        # Signal map pie placeholder: inject raw HTML
        if stripped == "<!-- SIGNAL_MAP_PIE -->" and signal_map_pie_html:
            html_parts.append(signal_map_pie_html)
            i += 1
            continue

        # Headings (#, ##, ###)
        if stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip("#"))
            level = max(1, min(level, 3))
            text = stripped[level:].strip()
            html_parts.append(f"<h{level}>{_inline(text)}</h{level}>")
            i += 1
            continue

        # Horizontal rule
        if stripped == "---":
            html_parts.append("<hr>")
            i += 1
            continue

        # Tables (pipe syntax with separator row)
        if "|" in stripped and i + 1 < len(lines) and set(lines[i + 1].replace("|", "").strip()) <= set("-: "):
            header_line = stripped
            separator_line = lines[i + 1]
            header_cells = [c.strip() for c in header_line.strip().strip("|").split("|")]
            i += 2
            rows: List[List[str]] = []
            while i < len(lines) and "|" in lines[i]:
                row_cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                rows.append(row_cells)
                i += 1
            table_html = ["<table>"]
            table_html.append("<thead><tr>" + "".join(f"<th>{_inline(c)}</th>" for c in header_cells) + "</tr></thead>")
            if rows:
                table_html.append("<tbody>")
                for row in rows:
                    # Pad row to header length
                    padded = row + [""] * (len(header_cells) - len(row))
                    table_html.append("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in padded[:len(header_cells)]) + "</tr>")
                table_html.append("</tbody>")
            table_html.append("</table>")
            html_parts.append("\n".join(table_html))
            continue

        # Bullet list (- item)
        if stripped.lstrip().startswith("- "):
            list_items: List[str] = []
            while i < len(lines) and lines[i].strip().lstrip().startswith("- "):
                item_text = lines[i].strip().lstrip()[2:].strip()
                list_items.append(f"<li>{_inline(item_text)}</li>")
                i += 1
            html_parts.append("<ul>")
            html_parts.extend(list_items)
            html_parts.append("</ul>")
            continue

        # Paragraph: collect consecutive text lines
        para_lines: List[str] = []
        while i < len(lines):
            current = lines[i]
            curr_stripped = current.strip()
            if not curr_stripped:
                i += 1
                break
            if curr_stripped.startswith("#") or curr_stripped == "---":
                break
            if "|" in curr_stripped and i + 1 < len(lines) and set(lines[i + 1].replace("|", "").strip()) <= set("-: "):
                break
            if curr_stripped.lstrip().startswith("- "):
                break
            para_lines.append(curr_stripped)
            i += 1
        if para_lines:
            paragraph = " ".join(para_lines)
            html_parts.append(f"<p>{_inline(paragraph)}</p>")

    body_html = "\n".join(html_parts)

    # Extract "Run Scope" block (if present) into a dedicated summary/meta panel
    report_meta_html = ""
    scope_match = re.search(
        r"(<h2>Run Scope</h2>\\s*<ul>.*?</ul>)",
        body_html,
        flags=re.DOTALL,
    )
    if scope_match:
        scope_block = scope_match.group(1)
        report_meta_html = f'<div class="report-meta">{scope_block}</div>'
        body_html = body_html[: scope_match.start()] + body_html[scope_match.end() :]

    # Remove the first <h1> from body_html (title now lives in the header block)
    body_html = re.sub(r"<h1>.*?</h1>", "", body_html, count=1, flags=re.DOTALL)

    # Use styling and layout similar to the HTC HTML template (Calibri, header with logo, summary block)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(title, quote=False)}</title>
    <style>
        @media print {{
            .no-print {{ display: none !important; }}
            body {{ margin: 0; padding: 20px; }}
            @page {{ margin: 1cm; }}
        }}
        body {{
            font-family: Calibri, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            font-size: 10pt;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            color: #333;
            line-height: 1.6;
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
        }}
        .header-logo {{
            max-width: 150px;
            height: auto;
        }}
        .header-title {{
            flex: 1;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 24px;
            font-weight: bold;
        }}
        .header-deploy {{
            margin: 4px 0 0 0;
            font-size: 0.85em;
            color: #666;
        }}
        .report-meta {{
            background-color: #f5f5f5;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 30px;
            font-size: 0.9em;
        }}
        .report-meta p {{
            margin: 5px 0;
        }}
        h1 {{
            color: #333;
            padding-bottom: 10px;
            margin-top: 30px;
            font-size: 20px;
            border-bottom: 1px solid #ddd;
        }}
        h2 {{
            color: #333;
            margin-top: 30px;
            font-size: 18px;
            font-weight: bold;
        }}
        h3 {{
            color: #555;
            margin-top: 20px;
            font-size: 16px;
        }}
        p {{
            margin: 10px 0;
        }}
        ul {{
            margin: 10px 0 10px 25px;
        }}
        li {{
            margin-bottom: 4px;
        }}
        table {{
            border-collapse: collapse;
            margin: 15px 0;
            width: 100%;
        }}
        th, td {{
            border: 1px solid #ccc;
            padding: 4px 6px;
            text-align: left;
            font-size: 9pt;
        }}
        th {{
            background-color: #f5f5f5;
        }}
        .signal-map-pie {{
            margin: 1em 0;
        }}
        a {{
            color: #1f77b4;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    <div class="header">
        <!-- Inline logo (same image as HTC Global Market Intelligence_20260217.html) -->
        <img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAABAAAAAQACAIAAADwf7zUAADiGGNhQlgAAOIYanVtYgAAAB5qdW1kYzJwYQARABCAAACqADibcQNjMnBhAAAANvpqdW1iAAAAR2p1bWRjMm1hABEAEIAAAKoAOJtxA3VybjpjMnBhOmRiMzU5MGYxLTJkZWEtNGE0Mi1iYjg3LTFkM2VjYWY1MjM3NwAAAAHBanVtYgAAAClqdW1kYzJhcwARABCAAACqADibcQNjMnBhLmFzc2VydGlvbnMAAAAA5Wp1bWIAAAApanVtZGNib3IAEQAQgAAAqgA4m3EDYzJwYS5hY3Rpb25zLnYyAAAAALRjYm9yoWdhY3Rpb25zgqNmYWN0aW9ubGMycGEuY3JlYXRlZG1zb2Z0d2FyZUFnZW50v2RuYW1lZkdQVC00b/9xZGlnaXRhbFNvdXJjZVR5cGV4Rmh0dHA6Ly9jdi5pcHRjLm9yZy9uZXdzY29kZXMvZGlnaXRhbHNvdXJjZXR5cGUvdHJhaW5lZEFsZ29yaXRobWljTWVkaWGhZmFjdGlvbm5jMnBhLmNvbnZlcnRlZAAAAKtqdW1iAAAAKGp1bWRjYm9yABEAEIAAAKoAOJtxA2MycGEuaGFzaC5kYXRhAAAAAHtjYm9ypWpleGNsdXNpb25zgaJlc3RhcnQYIWZsZW5ndGgZNyxkbmFtZW5qdW1iZiBtYW5pZmVzdGNhbGdmc2hhMjU2ZGhhc2hYIJereHhizg/H0mK/SB01vzCpI2wy35EoqksTMVitcmBxY3BhZEgAAAAAAAAAAAAAAe1qdW1iAAAAJ2p1bWRjMmNsABEAEIAAAKoAOJtxA2MycGEuY2xhaW0udjIAAAABvmNib3Kmamluc3RhbmNlSUR4LHhtcDppaWQ6Njk4YzI5NjMtNjkyYy00ZTRiLWI1MzQtYTUzMzMyNTY4M2M0" class="header-logo" alt="PU Observatory logo">
        <div class="header-title">
            <h1>{html.escape(title, quote=False)}</h1>
            {f'<p class="header-deploy">Deploy: {html.escape(deploy_version, quote=False)}</p>' if deploy_version else ''}
            {f'<p class="header-deploy">Run ID: {html.escape(run_id, quote=False)}</p>' if run_id else ''}
        </div>
        <div style="width: 120px;"></div>
    </div>
    {report_meta_html}
{body_html}
</body>
</html>
"""


# -----------------------------------------------------------------------------
# Main API: generate report from input directory
# -----------------------------------------------------------------------------

def generate_report(
    input_dir: Path,
    output_path: Optional[Path] = None,
    report_filename: str = "intelligence_report.md",
    spec: Optional[Dict[str, Any]] = None,
    write_metrics: bool = True,
    write_html: bool = True,
) -> Path:
    """
    Load classified data from input_dir, then:

    - If signals.csv and query_plan.csv exist: load master signals, join query metadata,
      apply customer specification filter (regions, categories, value_chain_links from spec),
      then cluster filtered signals, extract developments, generate report.
    - Else if classified_articles.csv exists: load all, cluster, extract developments (no filter).

    Clustering and development extraction always run on the (optionally filtered) signal set.
    spec can include regions, categories, value_chain_links (customer filter);
    report_period, report_title, included_sections, minimum_signal_strength_in_report (presentation).
    Returns the path of the written report file.
    """
    input_dir = Path(input_dir)
    signals_path = input_dir / "signals.csv"
    query_plan_path = input_dir / "query_plan.csv"
    classified_path = input_dir / "classified_articles.csv"
    counts_path = input_dir / "category_hit_counts.csv"

    spec = spec or {}

    # Prefer master signal dataset + post-classification customer filter
    if signals_path.exists() and query_plan_path.exists():
        signals = load_signals(signals_path)
        query_plan_map = load_query_plan(query_plan_path)
        articles = apply_customer_filter(signals, query_plan_map, spec)
        # Clustering and development extraction run only on filtered signals
    elif classified_path.exists():
        articles = load_classified_articles(classified_path)
    else:
        raise FileNotFoundError(f"Missing input: need signals.csv+query_plan.csv or {classified_path}")

    if counts_path.exists():
        load_category_counts(counts_path)

    clusters = group_signals(articles)
    developments = build_developments(clusters)

    included_sections = spec.get("included_sections") if spec else None
    min_strength = spec.get("minimum_signal_strength_in_report") if spec else None
    if min_strength and isinstance(min_strength, str):
        order = {"Weak": 0, "Moderate": 1, "Strong": 2}
        threshold = order.get(min_strength, 0)
        developments = [d for d in developments if order.get(d.signal_strength, 0) >= threshold]
    signal_map_enabled = spec.get("signal_map_enabled", True) if spec else True
    evidence_appendix_enabled = spec.get("evidence_appendix_enabled", True) if spec else True
    report_text = render_report(
        developments,
        included_sections=included_sections,
        signal_map_enabled=signal_map_enabled,
        evidence_appendix_enabled=evidence_appendix_enabled,
        spec=spec,
    )

    if output_path is None:
        out_dir = input_dir
        report_path = input_dir / report_filename
    else:
        output_path = Path(output_path)
        if output_path.suffix != ".md" and output_path.suffix != ".html":
            out_dir = output_path
            report_path = output_path / report_filename
        else:
            out_dir = output_path.parent
            report_path = output_path
    out_dir = report_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report_text, encoding="utf-8")

    if write_metrics:
        metrics = build_report_metrics(len(articles), developments)
        metrics_path = out_dir / "intelligence_report_metrics.json"
        metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    if write_html:
        title = spec.get("report_title") or "Polyurethane Industry Intelligence Briefing"
        html_text = markdown_to_simple_html(report_text, title=title)
        html_path = out_dir / report_filename.replace(".md", ".html")
        html_path.write_text(html_text, encoding="utf-8")

    return report_path
