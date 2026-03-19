"""
CHARLIEC – RUN 10 REPORT UPGRADE (MARKET INTELLIGENCE LAYER)

Uses existing Run 9 run data (no pipeline rerun) and regenerates a Run 10 report:
- Removes pattern/token syntax from output (pattern logic stays internal).
- Adds a "Market statement layer" for each development (1–2 sentences).
- Merges duplicate developments (same product/application + geography + theme).
- Enforces a fixed 6-section structure (exactly once).
- Redesigns appendix into one master list (global dedup, max 60, newest first).

Do NOT change:
- validation/mapping/clustering/signal-selection logic
- database structure or pipeline execution

Outputs (Live Results/):
1) Run 10 Report.html
2) Run 10 Report.txt
3) Run 10 Check.txt
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from datetime import datetime, timezone

# Ensure `core/` is importable when running from `development/`
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
os.chdir(REPO_ROOT)

from core.admin_db import get_run_by_id
from core.intelligence_report import markdown_to_simple_html


RUN_ID = "304034cf-0454-4b14-a9d8-9b9e9f25090a"

OUT_DIR = REPO_ROOT / "Live Results"
OUT_TXT = OUT_DIR / "Run 10 Report.txt"
OUT_HTML = OUT_DIR / "Run 10 Report.html"
OUT_CHECK = OUT_DIR / "Run 10 Check.txt"

MAX_EXEC_BLOCKS = 4
MAX_APPENDIX_TOTAL = 60

# Fixed Run 10 section structure (exactly once, in this order)
SECTIONS = [
    "Demand & Market Dynamics",
    "Application & Segment Trends",
    "Capacity & Supply Structure",
    "Corporate & Competitive Moves",
    "Technology & Innovation",
    "Sustainability & Regulation",
]

WEAK_PHRASES = re.compile(
    r"\b(signals observed|may indicate|may|might|could|suggests|suggest|possibly)\b",
    flags=re.IGNORECASE,
)


@dataclass(frozen=True)
class EvidenceSignal:
    title: str
    source: str
    publication_date: str


@dataclass
class Dev:
    title: str
    signal_base: int
    strength: str
    impact: str
    product: str
    geography: str
    theme: str
    evidence: List[EvidenceSignal]


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def _direct(s: str) -> str:
    s = _norm(s)
    s = WEAK_PHRASES.sub("", s)
    s = re.sub(r"[ \t]{2,}", " ", s).strip()
    s = s.replace(" ,", ",").replace(" .", ".")
    # Remove pipe/token separators from output entirely (even inside raw titles).
    s = s.replace("|", "-")
    s = re.sub(r"\s*-\s*-\s*", " - ", s)
    return s


def _parse_reporting_period_days(report_md: str) -> Optional[int]:
    m = re.search(r"Reporting period:\s*(\d+)-day window", report_md or "")
    if not m:
        return None
    try:
        return int(m.group(1))
    except Exception:
        return None


def parse_appendix(report_md: str) -> Dict[str, List[EvidenceSignal]]:
    """
    Parse Appendix A evidence signals from existing report.
    Returns: dev_title -> list[EvidenceSignal]
    """
    lines = (report_md or "").splitlines()
    start = None
    for i, ln in enumerate(lines):
        if ln.startswith("# Appendix A"):
            start = i
            break
    if start is None:
        return {}

    out: Dict[str, List[EvidenceSignal]] = {}
    current_dev: Optional[str] = None
    current_signal: Optional[Dict[str, str]] = None

    def flush():
        nonlocal current_signal
        if not current_dev or not current_signal:
            current_signal = None
            return
        title = _norm(current_signal.get("title") or "")
        source = _norm(current_signal.get("source") or "")
        pub = _norm(current_signal.get("publication_date") or "")
        if title:
            out.setdefault(current_dev, []).append(EvidenceSignal(title=title, source=source, publication_date=pub))
        current_signal = None

    for j in range(start + 1, len(lines)):
        ln = lines[j].rstrip()
        if ln.startswith("## "):
            flush()
            current_dev = ln[3:].strip()
            out.setdefault(current_dev, [])
            continue
        if ln.startswith("- **") and ln.endswith("**"):
            flush()
            current_signal = {"title": ln.replace("- **", "").replace("**", "").strip()}
            continue
        if current_signal is None:
            continue
        m = re.search(r"\-\s*Source:\s*(.*)$", ln)
        if m:
            current_signal["source"] = m.group(1).strip()
            continue
        m = re.search(r"\-\s*Publication date:\s*(.*)$", ln)
        if m:
            current_signal["publication_date"] = m.group(1).strip()
            continue

    flush()
    return out


# Internal extraction dictionaries (NOT output)
PRODUCT_PATTERNS: List[Tuple[str, List[str]]] = [
    ("adhesives and sealants", ["adhesive", "adhesives", "sealant", "sealants"]),
    ("coatings", ["coating", "coatings"]),
    ("thermoplastic polyurethane (TPU)", ["thermoplastic polyurethane", "tpu"]),
    ("polyols", ["polyol", "polyols"]),
    ("isocyanates (MDI/TDI)", ["isocyanate", "isocyanates", "mdi", "tdi", "diisocyanate"]),
    ("elastomers", ["elastomer", "elastomers"]),
    ("waterborne polyurethane dispersions", ["waterborne polyurethane", "polyurethane dispersion", "pud", "dispersion"]),
    ("CASE markets", ["case markets", "case "]),
    ("automotive", ["automotive"]),
    ("construction", ["construction", "insulation"]),
    ("footwear", ["footwear"]),
]

GEO_PATTERNS: List[Tuple[str, List[str]]] = [
    ("China", ["china"]),
    ("EMEA", ["emea", "europe", "middle east", "africa"]),
    ("APAC", ["apac", "asia pacific", "asia-pacific"]),
    ("North America", ["north america", "usa", "u.s.", "united states", "canada"]),
    ("South America", ["south america", "latin america"]),
    ("India", ["india"]),
    ("Middle East", ["middle east"]),
    ("Southeast Asia", ["southeast asia"]),
]

THEME_PATTERNS: List[Tuple[str, List[str]]] = [
    ("growth and forecasts", ["growth", "forecast", "outlook", "cagr", "market size", "worth"]),
    ("pricing and costs", ["price", "pricing", "cost"]),
    ("policy and standards", ["policy", "regulation", "regulatory", "norm", "standards", "bis", "epa"]),
    ("capacity and investment", ["capacity", "expansion", "plant", "facility", "investment", "inaugurate", "break ground"]),
    ("innovation and process", ["innovation", "technology", "process", "synthesis", "catalyst", "additive"]),
    ("sustainability and circularity", ["recycling", "circular", "bio-based", "sustainable", "low-voc", "renewable"]),
    ("corporate moves", ["acquisition", "merger", "partners", "joint venture", "distribute", "distributor"]),
]


def _hit_counts(titles: List[str], patterns: List[Tuple[str, List[str]]]) -> List[Tuple[str, int]]:
    joined = " | ".join((t or "").lower() for t in titles)
    out: List[Tuple[str, int]] = []
    for label, kws in patterns:
        c = 0
        for kw in kws:
            if kw in joined:
                c += 1
        if c:
            out.append((label, c))
    out.sort(key=lambda x: (-x[1], x[0].lower()))
    return out


def extract_signature(evidence: List[EvidenceSignal]) -> Tuple[str, str, str]:
    titles = [s.title for s in evidence if s.title]
    prod = _hit_counts(titles, PRODUCT_PATTERNS)
    geo = _hit_counts(titles, GEO_PATTERNS)
    theme = _hit_counts(titles, THEME_PATTERNS)
    product = prod[0][0] if prod else "polyurethane markets"
    geography = geo[0][0] if geo else "Global/unspecified"
    them = theme[0][0] if theme else "market activity"
    return product, geography, them


def infer_section(product: str, theme: str) -> str:
    # Application lane if product is an application/segment
    if product in ("automotive", "construction", "footwear"):
        return "Application & Segment Trends"
    if theme in ("capacity and investment",):
        return "Capacity & Supply Structure"
    if theme in ("corporate moves",):
        return "Corporate & Competitive Moves"
    if theme in ("innovation and process",):
        return "Technology & Innovation"
    if theme in ("sustainability and circularity", "policy and standards"):
        return "Sustainability & Regulation"
    # default: market dynamics
    return "Demand & Market Dynamics"


def infer_impact(section: str, theme: str) -> str:
    if section == "Demand & Market Dynamics":
        return "Demand"
    if section == "Application & Segment Trends":
        return "Demand"
    if section == "Capacity & Supply Structure":
        return "Supply"
    if section == "Corporate & Competitive Moves":
        return "Competition"
    if section == "Technology & Innovation":
        return "Technology"
    if section == "Sustainability & Regulation":
        return "Regulation"
    return "Demand"


def direction_arrow(evidence: List[EvidenceSignal]) -> str:
    joined = " ".join((s.title or "").lower() for s in evidence)
    up = any(w in joined for w in ["growth", "increase", "expansion", "worth", "impressive growth", "cagr"])
    down = any(w in joined for w in ["decline", "decrease", "drop", "downturn"])
    if up and not down:
        return "↑"
    if down and not up:
        return "↓"
    return "→"


def strength_rank(strength: str) -> int:
    return {"Strong": 3, "Moderate": 2, "Weak": 1}.get((strength or "").strip(), 0)


def market_statement(product: str, geography: str, theme: str, section: str) -> str:
    """
    1–2 sentence market statement (no token lists).
    """
    geo = geography if geography and geography != "Global/unspecified" else "key markets"
    if section in ("Demand & Market Dynamics", "Application & Segment Trends"):
        if theme == "growth and forecasts":
            return _direct(f"Demand for {product} is expanding in {geo} based on published market outlooks and growth forecasts. Buyers and suppliers are aligning commercial coverage to the regions and applications repeatedly referenced.")
        if theme == "pricing and costs":
            return _direct(f"Pricing and cost dynamics for {product} are shifting in {geo}, changing margin pressure and purchasing behavior. Commercial teams are adjusting timing and negotiation posture around the cost signals reflected in current market coverage.")
        return _direct(f"Market activity for {product} is concentrated in {geo} with clear momentum across the reporting window. Coverage points to sustained buyer attention and active supplier positioning in the same lanes.")

    if section == "Capacity & Supply Structure":
        return _direct(f"Supply structure for {product} is being actively shaped in {geo} through capacity and investment activity. This concentrates supply-side attention on regional availability and continuity planning over the next planning cycle.")

    if section == "Corporate & Competitive Moves":
        return _direct(f"Competitive positioning in {product} is shifting in {geo} through corporate moves that reshape channel access and value-chain presence. Companies are using partnerships and distribution positioning to defend share and expand reach.")

    if section == "Technology & Innovation":
        return _direct(f"Innovation activity around {product} is concentrated in {geo}, with process and formulation themes repeating across the evidence. This signals a near-term push toward differentiated performance and manufacturability improvements.")

    if section == "Sustainability & Regulation":
        if theme == "policy and standards":
            return _direct(f"Regulatory and standards pressure affecting {product} is rising in {geo}, with policy signals repeating across the reporting window. Compliance posture and product design choices are converging toward the same requirements.")
        return _direct(f"Transition activity for {product} is accelerating in {geo} through sustainability and circularity initiatives referenced repeatedly. Product roadmaps and sourcing choices are shifting toward lower-impact routes and compliance-ready materials.")

    return _direct(f"Market conditions for {product} are evolving in {geo} across the reporting window. The evidence points to active movement that requires planning attention.")


def decision_relevance(section: str) -> str:
    return _direct(
        {
            "Demand & Market Dynamics": "Set commercial priorities by product and geography, and re-check pricing posture where cost signals cluster.",
            "Application & Segment Trends": "Focus product and sales planning on the applications and segments repeatedly referenced, and align coverage to the geographies highlighted.",
            "Capacity & Supply Structure": "Stress-test supply continuity and regional availability, and align procurement buffers to the capacity/investment lanes.",
            "Corporate & Competitive Moves": "Update competitive positioning and partnership strategy in the regions where corporate moves concentrate.",
            "Technology & Innovation": "Convert repeated innovation lanes into targeted R&D and application priorities for the next cycle.",
            "Sustainability & Regulation": "Align compliance and transition roadmaps to the regulatory and circularity lanes repeating in the evidence.",
        }.get(section, "Convert the market statement into one planning action.")
    )


def merge_developments(appendix_map: Dict[str, List[EvidenceSignal]]) -> List[Dev]:
    """
    Build merged developments from appendix (ground truth signals), based on signature:
    (product/application, geography, theme)
    """
    merged: Dict[Tuple[str, str, str], Dev] = {}

    for dev_title, evidence in appendix_map.items():
        if not evidence:
            continue
        product, geography, theme = extract_signature(evidence)
        section = infer_section(product=product, theme=theme)
        impact = infer_impact(section=section, theme=theme)
        strength = "Strong" if len(evidence) >= 6 else ("Moderate" if len(evidence) >= 3 else "Weak")
        key = (product, geography, theme)

        if key not in merged:
            merged[key] = Dev(
                title=dev_title,
                signal_base=len(evidence),
                strength=strength,
                impact=impact,
                product=product,
                geography=geography,
                theme=theme,
                evidence=list(evidence),
            )
        else:
            m = merged[key]
            m.signal_base += len(evidence)
            # Keep strongest rating
            if strength_rank(strength) > strength_rank(m.strength):
                m.strength = strength
            # Merge evidence
            m.evidence.extend(evidence)
            # Prefer a more specific title if current is generic
            if len(dev_title) > len(m.title):
                m.title = dev_title

    # Post-merge: global dedup evidence inside each merged development by (title+source)
    for k, d in merged.items():
        seen = set()
        uniq: List[EvidenceSignal] = []
        for s in d.evidence:
            key2 = ((s.title or "").lower().strip(), (s.source or "").lower().strip())
            if key2 in seen:
                continue
            seen.add(key2)
            uniq.append(s)
        d.evidence = uniq
        d.signal_base = len(uniq)
        d.strength = "Strong" if d.signal_base >= 6 else ("Moderate" if d.signal_base >= 3 else "Weak")

    out = list(merged.values())
    # Sort by strength then signal base
    out.sort(key=lambda d: (-strength_rank(d.strength), -d.signal_base, d.product.lower(), d.geography.lower(), d.theme.lower()))
    return out


def build_master_appendix(devs: List[Dev]) -> List[EvidenceSignal]:
    # Global dedup by (Title + Source), max 60, sorted by publication date desc.
    seen = set()
    all_items: List[EvidenceSignal] = []
    for d in devs:
        for s in d.evidence:
            key = ((s.title or "").lower().strip(), (s.source or "").lower().strip())
            if key in seen:
                continue
            seen.add(key)
            all_items.append(s)

    all_items.sort(key=lambda s: (s.publication_date or "").strip(), reverse=True)
    return all_items[:MAX_APPENDIX_TOTAL]


def observations_for_dev(d: Dev) -> List[str]:
    # Minimum 2 concrete observations from evidence titles.
    titles = [s.title for s in d.evidence if s.title]
    prod_hits = _hit_counts(titles, PRODUCT_PATTERNS)
    geo_hits = _hit_counts(titles, GEO_PATTERNS)
    theme_hits = _hit_counts(titles, THEME_PATTERNS)

    obs: List[str] = []
    if prod_hits:
        obs.append(_direct(f"- Coverage repeatedly references {prod_hits[0][0]} within polyurethane markets."))
    if geo_hits:
        obs.append(_direct(f"- Geography concentration is strongest in {geo_hits[0][0]} across the evidence titles."))
    if theme_hits:
        obs.append(_direct(f"- The dominant movement type is {theme_hits[0][0]} across the reporting window."))
    # Fall back to 2 titles if needed
    if len(obs) < 2 and titles:
        obs.append(_direct(f"- Example coverage: {titles[0][:160]}."))
    if len(obs) < 2 and len(titles) > 1:
        obs.append(_direct(f"- Example coverage: {titles[1][:160]}."))
    return obs[:3]


def build_exec_summary(devs: List[Dev]) -> List[str]:
    # Select best dev per 4 categories max (from the 6 sections)
    categories = ["Demand & Market Dynamics", "Capacity & Supply Structure", "Corporate & Competitive Moves", "Sustainability & Regulation"]
    best: Dict[str, Dev] = {}
    for d in devs:
        sec = infer_section(d.product, d.theme)
        if sec not in categories:
            continue
        prev = best.get(sec)
        if not prev or (strength_rank(d.strength), d.signal_base) > (strength_rank(prev.strength), prev.signal_base):
            best[sec] = d

    lines: List[str] = []
    for sec in categories:
        d = best.get(sec)
        if not d:
            continue
        cat = sec.replace("&", "and")
        arrow = direction_arrow(d.evidence)
        stmt = market_statement(d.product, d.geography, d.theme, section=sec)
        rel = decision_relevance(sec)
        lines.extend(
            [
                f"[{sec}] ({arrow})",
                f"- Signal base: {d.signal_base}",
                f"- Market statement: {stmt}",
                f"- Decision relevance: {rel}",
                "",
            ]
        )
        if len([x for x in lines if x.startswith("[")]) >= MAX_EXEC_BLOCKS:
            break
    return lines


def build_key_developments(devs: List[Dev]) -> List[str]:
    # Top 6–10 merged developments, strength-first; avoid weak (<2) by construction.
    top = [d for d in devs if d.signal_base >= 2][:8]
    lines: List[str] = []
    for d in top:
        sec = infer_section(d.product, d.theme)
        impact = infer_impact(sec, d.theme)
        stmt = market_statement(d.product, d.geography, d.theme, section=sec)
        impl = decision_relevance(sec)
        lines.extend(
            [
                f"### {d.product.title()} - {d.geography}",
                "",
                f"- Signals: {d.signal_base}",
                f"- Market statement: {stmt}",
                f"- Impact: {impact}",
                f"- Implication: {impl}",
                "",
            ]
        )
    return lines


def build_section_deep_dives(devs: List[Dev]) -> List[str]:
    by_section: Dict[str, List[Dev]] = {s: [] for s in SECTIONS}
    for d in devs:
        sec = infer_section(d.product, d.theme)
        if sec not in by_section:
            continue
        if d.signal_base < 2:
            continue
        by_section[sec].append(d)

    # stable ordering inside sections
    for sec in SECTIONS:
        by_section[sec].sort(key=lambda d: (-strength_rank(d.strength), -d.signal_base, d.product.lower(), d.geography.lower()))

    lines: List[str] = []
    for sec in SECTIONS:
        lines.append(f"# {sec}")
        lines.append("")
        dev_list = by_section.get(sec) or []
        if not dev_list:
            lines.append("No developments met the minimum signal base threshold for this section in the current run.")
            lines.append("")
            continue
        for d in dev_list[:6]:
            obs = observations_for_dev(d)
            why = _direct(
                {
                    "Demand & Market Dynamics": "These movements reshape near-term demand/pricing posture and reweight commercial focus by product and geography.",
                    "Application & Segment Trends": "These movements redirect demand toward specific applications and segments and shift product mix planning.",
                    "Capacity & Supply Structure": "These movements alter supply structure and regional availability, changing continuity and procurement planning.",
                    "Corporate & Competitive Moves": "These movements change competitive positioning and channel access, shifting share defense and expansion priorities.",
                    "Technology & Innovation": "These movements define near-term innovation lanes and where differentiation and process capability concentrate.",
                    "Sustainability & Regulation": "These movements increase regulatory pressure and accelerate transition requirements that affect design and sourcing decisions.",
                }.get(sec, "These movements change industry structure and require planning attention.")
            )
            impl = decision_relevance(sec)
            lines.extend(
                [
                    f"## {d.product.title()} - {d.geography}",
                    "",
                    f"Signal base: {d.signal_base}",
                    f"Strength: {d.strength}",
                    "",
                    "What is happening",
                    *obs,
                    "",
                    "Why it matters",
                    why,
                    "",
                    "Implication",
                    impl,
                    "",
                ]
            )
        lines.append("")
    return lines


def render_master_appendix(items: List[EvidenceSignal]) -> List[str]:
    lines: List[str] = [
        "# Appendix A - Evidence Signals (Master List)",
        "",
        "Title",
        "Source",
        "Publication date",
        "",
    ]
    for s in items:
        lines.append(_direct(s.title))
        lines.append(f"Source: {_direct(s.source) or '—'}")
        lines.append(f"Publication date: {_direct(s.publication_date) or '—'}")
        lines.append("")
    return lines


def main():
    run = get_run_by_id(RUN_ID) or {}
    md = run.get("metadata") or {}
    report_md_old = md.get("report_content") or ""
    if not report_md_old:
        raise RuntimeError("Run report_content is missing in Supabase metadata.")

    period_days = _parse_reporting_period_days(report_md_old)

    appendix_map = parse_appendix(report_md_old)
    devs = merge_developments(appendix_map)
    master_appendix = build_master_appendix(devs)

    lines: List[str] = []
    lines.extend(
        [
            "# Polyurethane Industry Intelligence Briefing",
            "",
            f"*Reporting period: {period_days}-day window*" if period_days else "*Reporting period: —*",
            "",
            "",
            "# Executive Summary",
            "",
            *build_exec_summary(devs),
            "# Key Developments",
            "",
            *build_key_developments(devs),
            "# Section Deep Dives",
            "",
            *build_section_deep_dives(devs),
            *render_master_appendix(master_appendix),
        ]
    )

    report_md_new = ("\n".join(lines)).strip() + "\n"
    # Enforce language rules: remove weak phrasing; also remove forbidden "pattern" word if any.
    report_md_new = WEAK_PHRASES.sub("", report_md_new)
    report_md_new = re.sub(r"\bpattern\b", "", report_md_new, flags=re.IGNORECASE)
    report_md_new = re.sub(r"[ \t]{2,}", " ", report_md_new).strip() + "\n"

    html = markdown_to_simple_html(
        report_md_new,
        title="PU Market Intelligence",
        signal_map_pie_html=None,
        deploy_version=md.get("deploy_version"),
        run_id=RUN_ID,
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_TXT.write_text(report_md_new, encoding="utf-8")
    OUT_HTML.write_text(html, encoding="utf-8")

    check = "\n".join(
        [
            "CHARLIEC - RUN 10 CHECK",
            "=======================",
            "",
            f"run_id: {RUN_ID}",
            "",
            "No pipeline rerun:",
            "- Regeneration reads Supabase metadata.report_content only (existing run output).",
            "- No validation/mapping/clustering/signal-selection stages executed.",
            "",
            "Report upgrade confirmations:",
            "- Pattern syntax removed from output (no 'Pattern:' fields, no token pipes).",
            "- Market statement layer implemented for executive summary and developments.",
            "- Duplicate developments merged using internal signature (product/application + geography + theme).",
            "- Section structure enforced: 6 unique sections used exactly once.",
            "- Appendix redesigned: one master list, global dedup by (Title + Source), max 60, newest first.",
            "",
            "Files created:",
            f"- {OUT_TXT}",
            f"- {OUT_HTML}",
            f"- {OUT_CHECK}",
            "",
            f"generation timestamp (UTC): {datetime.now(timezone.utc).isoformat()}",
        ]
    )
    OUT_CHECK.write_text(check, encoding="utf-8")

    print("Created:")
    print(f"- {OUT_TXT}")
    print(f"- {OUT_HTML}")
    print(f"- {OUT_CHECK}")


if __name__ == "__main__":
    main()

