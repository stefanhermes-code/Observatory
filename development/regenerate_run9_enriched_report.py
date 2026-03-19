"""
CHARLIEC – RUN 9 REPORT ENRICHMENT (CONTENT EXTRACTION LAYER)

Objective:
- Use existing Run 9 data (Supabase `newsletter_runs.metadata.report_content`) and regenerate a new report
  with a report-writing-level content extraction layer.

Do NOT change:
- validation logic, mapping logic, clustering logic, signal selection logic
- database structure, pipeline execution

Only change:
- report-writing logic, phrasing rules, appendix filtering/dedup/capping

Outputs (in Live Results/):
1) Run 9 Enriched Report.html
2) Run 9 Enriched Report.txt
3) Run 9 Enrichment Check.txt
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
OUT_TXT = OUT_DIR / "Run 9 Enriched Report.txt"
OUT_HTML = OUT_DIR / "Run 9 Enriched Report.html"
OUT_CHECK = OUT_DIR / "Run 9 Enrichment Check.txt"

MAX_EXEC_BLOCKS = 4
MAX_KEY_DEVS = 8
MIN_KEY_DEVS = 5
MAX_APPENDIX_PER_DEV = 12

SECTION_TO_CATEGORY = {
    "Market Developments": "Market",
    "Capacity and Investment Activity": "Capacity",
    "Corporate Developments": "Corporate",
    "Technology and Innovation": "Technology",
    "Sustainability and Circular Economy": "Sustainability",
}

IMPACT_PRIORITY = ["Demand", "Supply", "Competition", "Technology", "Regulation", "Sustainability"]

WEAK_PHRASES = re.compile(
    r"\b(signals observed|may indicate|may|might|could|suggests|suggest|possibly)\b",
    flags=re.IGNORECASE,
)


@dataclass(frozen=True)
class EvidenceSignal:
    title: str
    source: str
    publication_date: str


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def _direct(s: str) -> str:
    s = _norm(s)
    s = WEAK_PHRASES.sub("", s)
    s = re.sub(r"\s{2,}", " ", s).strip()
    s = s.replace(" ,", ",").replace(" .", ".")
    return s


def _parse_reporting_period_days(report_md: str) -> Optional[int]:
    m = re.search(r"Reporting period:\s*(\d+)-day window", report_md or "")
    if not m:
        return None
    try:
        return int(m.group(1))
    except Exception:
        return None


def _parse_date_key(s: EvidenceSignal) -> str:
    # ISO dates sort lexicographically; fallback to empty.
    return (s.publication_date or "").strip()


def parse_developments_and_appendix(report_md: str) -> Tuple[List[Dict[str, str]], Dict[str, List[EvidenceSignal]]]:
    """
    Parse development list from the existing report, plus Appendix A evidence items.

    Returns:
    - devs: list of dicts with keys: section, title, strength, signal_base (int as str), impact (str)
    - appendix_map: dev_title -> list[EvidenceSignal]
    """
    lines = (report_md or "").splitlines()

    # ---- Parse developments from section blocks ----
    devs: List[Dict[str, str]] = []
    current_section: Optional[str] = None

    i = 0
    while i < len(lines):
        ln = lines[i].rstrip()
        if ln.startswith("# "):
            h = ln[2:].strip()
            current_section = h if h in SECTION_TO_CATEGORY else None
            i += 1
            continue

        if current_section and ln.startswith("### "):
            title = ln[4:].strip()
            block: List[str] = []
            i += 1
            while i < len(lines):
                b = lines[i].rstrip()
                if b.startswith("### ") or b.startswith("# "):
                    break
                block.append(b)
                i += 1

            strength = "Weak"
            impact = ""
            signal_base = ""

            # Signal strength line
            for b in block:
                m = re.search(r"\*\*Signal Strength:\*\*\s*(\w+)", b, flags=re.IGNORECASE)
                if m:
                    strength = m.group(1).strip()
                    break

            # Impact direction line
            for b in block:
                if b.strip().startswith("**Direction of Impact**"):
                    raw = re.sub(r"^\*\*Direction of Impact\*\*\s*", "", b.strip())
                    impact = raw.split(",")[0].strip() if raw else ""
                    break

            # Explanation line contains "supported by X observed signals"
            for b in block:
                b2 = b.strip()
                if not b2:
                    continue
                m = re.search(r"supported by\s+(\d+)\s+observed\s+signal", b2, flags=re.IGNORECASE)
                if m:
                    signal_base = m.group(1)
                    break

            devs.append(
                {
                    "section": current_section,
                    "title": title,
                    "strength": strength,
                    "signal_base": signal_base or "0",
                    "impact": impact,
                }
            )
            continue

        i += 1

    # ---- Parse Appendix A evidence signals ----
    appendix_map: Dict[str, List[EvidenceSignal]] = {}
    appendix_start = None
    for idx, ln in enumerate(lines):
        if ln.startswith("# Appendix A"):
            appendix_start = idx
            break
    if appendix_start is None:
        return devs, appendix_map

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
            appendix_map.setdefault(current_dev, []).append(EvidenceSignal(title=title, source=source, publication_date=pub))
        current_signal = None

    for j in range(appendix_start + 1, len(lines)):
        ln = lines[j].rstrip()
        if ln.startswith("## "):
            flush()
            current_dev = ln[3:].strip()
            appendix_map.setdefault(current_dev, [])
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
    return devs, appendix_map


def dedupe_and_cap_appendix(appendix_map: Dict[str, List[EvidenceSignal]]) -> Dict[str, List[EvidenceSignal]]:
    out: Dict[str, List[EvidenceSignal]] = {}
    global_seen = set()

    for dev_title, items in appendix_map.items():
        # Deduplicate within development by (title+source)
        seen_local = set()
        deduped: List[EvidenceSignal] = []
        for s in items:
            key = ((s.title or "").lower().strip(), (s.source or "").lower().strip())
            if key in seen_local:
                continue
            seen_local.add(key)
            deduped.append(s)

        # Remove duplicates across developments
        filtered: List[EvidenceSignal] = []
        for s in deduped:
            key = ((s.title or "").lower().strip(), (s.source or "").lower().strip())
            if key in global_seen:
                continue
            global_seen.add(key)
            filtered.append(s)

        # Keep most recent if exceeding cap (ISO date sorts descending)
        filtered_sorted = sorted(filtered, key=_parse_date_key, reverse=True)
        out[dev_title] = filtered_sorted[:MAX_APPENDIX_PER_DEV]

    return out


PRODUCT_PATTERNS = [
    ("adhesives & sealants", ["adhesive", "adhesives", "sealant", "sealants"]),
    ("coatings", ["coating", "coatings"]),
    ("TPU", ["thermoplastic polyurethane", "tpu"]),
    ("polyols", ["polyol", "polyols"]),
    ("isocyanates (MDI/TDI)", ["isocyanate", "isocyanates", "mdi", "tdi", "diisocyanate"]),
    ("elastomers", ["elastomer", "elastomers"]),
    ("waterborne PU", ["waterborne polyurethane", "polyurethane dispersion", "pud", "dispersion"]),
    ("CASE", ["case markets", "case "]),
]

GEO_PATTERNS = [
    ("China", ["china"]),
    ("EMEA", ["emea", "europe", "middle east", "africa"]),
    ("APAC", ["apac", "asia pacific", "asia-pacific"]),
    ("North America", ["north america", "usa", "u.s.", "united states", "canada"]),
    ("South America", ["south america", "latin america"]),
    ("India", ["india"]),
    ("Middle East", ["middle east"]),
    ("SEA", ["sea", "southeast asia"]),
]

THEME_PATTERNS = [
    ("growth forecasts", ["growth", "forecast", "outlook", "cagr", "market size", "worth"]),
    ("pricing/cost", ["price", "pricing", "cost"]),
    ("policy/standards", ["policy", "regulation", "regulatory", "norm", "standards", "bis", "epa"]),
    ("capacity/investment", ["capacity", "expansion", "plant", "facility", "investment", "inaugurate", "break ground"]),
    ("innovation/process", ["innovation", "technology", "process", "new", "synthesis", "catalyst", "additive"]),
    ("transition/circularity", ["recycling", "circular", "bio-based", "sustainable", "low-voc", "renewable"]),
]


def _count_hits(titles: List[str], patterns: List[Tuple[str, List[str]]]) -> List[Tuple[str, int]]:
    counts: List[Tuple[str, int]] = []
    joined = " | ".join((x or "").lower() for x in titles)
    for label, kws in patterns:
        c = 0
        for kw in kws:
            if kw in joined:
                c += 1
        if c:
            counts.append((label, c))
    counts.sort(key=lambda x: (-x[1], x[0].lower()))
    return counts


def extract_pattern(evidence: List[EvidenceSignal], category: str) -> str:
    titles = [s.title for s in evidence if s.title]
    if not titles:
        return "No extractable pattern from titles."

    prod = _count_hits(titles, PRODUCT_PATTERNS)[:2]
    geo = _count_hits(titles, GEO_PATTERNS)[:2]
    theme = _count_hits(titles, THEME_PATTERNS)[:2]

    parts: List[str] = []
    if prod:
        parts.append(", ".join([p[0] for p in prod]))
    if geo:
        parts.append(", ".join([g[0] for g in geo]))
    if theme:
        parts.append(", ".join([t[0] for t in theme]))

    if not parts:
        return "Recurring market-report coverage across the reporting window."

    # Category language constraint
    if category == "Market":
        lead = "Demand/pricing pattern:"
    elif category == "Capacity":
        lead = "Supply/structure pattern:"
    elif category == "Corporate":
        lead = "Competition/positioning pattern:"
    elif category == "Technology":
        lead = "Innovation/process pattern:"
    elif category == "Sustainability":
        lead = "Transition/regulation pattern:"
    else:
        lead = "Pattern:"

    return _direct(f"{lead} " + " | ".join(parts))


def pick_impact(impact_raw: str, category: str) -> str:
    # Normalize to required output: Demand/Supply/Competition/Technology
    raw = (impact_raw or "").strip()
    if raw in ("Demand", "Supply", "Competition", "Technology"):
        return raw
    # Derive by category
    if category == "Market":
        return "Demand"
    if category == "Capacity":
        return "Supply"
    if category == "Corporate":
        return "Competition"
    if category == "Technology":
        return "Technology"
    if category == "Sustainability":
        return "Competition"
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


def build_exec_summary(devs: List[Dict[str, str]], appendix_map: Dict[str, List[EvidenceSignal]]) -> List[str]:
    # Max 4 blocks: Market, Capacity, Corporate, Sustainability (only if present)
    wanted = ["Market", "Capacity", "Corporate", "Sustainability"]

    # choose strongest dev per category
    best: Dict[str, Dict[str, str]] = {}
    for d in devs:
        cat = SECTION_TO_CATEGORY.get(d.get("section", ""), "")
        if cat not in wanted:
            continue
        if d.get("title") not in appendix_map:
            continue
        prev = best.get(cat)
        if not prev:
            best[cat] = d
            continue
        if (strength_rank(d.get("strength")) , int(d.get("signal_base") or 0)) > (strength_rank(prev.get("strength")), int(prev.get("signal_base") or 0)):
            best[cat] = d

    blocks: List[str] = []
    for cat in wanted:
        d = best.get(cat)
        if not d:
            continue
        evidence = appendix_map.get(d["title"], [])
        arrow = direction_arrow(evidence)
        signal_base = int(d.get("signal_base") or 0)
        pattern = extract_pattern(evidence, category=cat)
        relevance = _direct(
            {
                "Market": "Use demand/pricing concentration to prioritize commercial focus and regional coverage.",
                "Capacity": "Align supply planning to capacity and structural activity signaled in the window.",
                "Corporate": "Adjust positioning and partnership priorities based on competitive moves in the value chain.",
                "Sustainability": "Integrate transition and regulation signals into sourcing, compliance, and product design.",
            }.get(cat, "Convert the extracted pattern into a planning decision.")
        )
        blocks.extend(
            [
                f"[{cat}] ({arrow})",
                f"- Signal base: {signal_base}",
                f"- Pattern: {pattern}",
                f"- Decision relevance: {relevance}",
                "",
            ]
        )
    return blocks[: (MAX_EXEC_BLOCKS * 5)]


def build_key_devs(devs: List[Dict[str, str]], appendix_map: Dict[str, List[EvidenceSignal]]) -> List[str]:
    # Top 5-8 by strength then signal base.
    devs2 = [d for d in devs if int(d.get("signal_base") or 0) >= 2 and d.get("title") in appendix_map]
    devs2.sort(key=lambda d: (-strength_rank(d.get("strength")), -int(d.get("signal_base") or 0), (d.get("title") or "").lower()))
    if len(devs2) >= MIN_KEY_DEVS:
        chosen = devs2[: min(MAX_KEY_DEVS, len(devs2))]
    else:
        chosen = devs2

    lines: List[str] = []
    for d in chosen:
        section = d.get("section", "")
        cat = SECTION_TO_CATEGORY.get(section, "Other")
        evidence = appendix_map.get(d["title"], [])
        pattern = extract_pattern(evidence, category=cat)
        impact = pick_impact(d.get("impact", ""), category=cat)
        implication = _direct(
            {
                "Market": "Lock commercial priorities to the dominant demand/pricing pattern and the geographies highlighted.",
                "Capacity": "Re-check supply posture and regional availability against capacity/investment signals.",
                "Corporate": "Reassess competitive positioning and partner/competitor moves highlighted in the pattern.",
                "Technology": "Translate recurring innovation/process themes into near-term R&D and application focus.",
                "Sustainability": "Prioritize compliance and transition roadmaps aligned to regulation/circularity coverage.",
            }.get(cat, "Convert the pattern into a single planning decision.")
        )
        lines.extend(
            [
                f"### {d['title']}",
                f"- Signals: {int(d.get('signal_base') or 0)}",
                f"- Pattern: {pattern}",
                f"- Impact: {impact}",
                f"- Implication: {implication}",
                "",
            ]
        )
    return lines


def build_deep_dives(devs: List[Dict[str, str]], appendix_map: Dict[str, List[EvidenceSignal]]) -> List[str]:
    # Deep dive only on key developments chosen logic (same ranking).
    devs2 = [d for d in devs if int(d.get("signal_base") or 0) >= 2 and d.get("title") in appendix_map]
    devs2.sort(key=lambda d: (-strength_rank(d.get("strength")), -int(d.get("signal_base") or 0), (d.get("title") or "").lower()))
    if len(devs2) >= MIN_KEY_DEVS:
        chosen = devs2[: min(MAX_KEY_DEVS, len(devs2))]
    else:
        chosen = devs2

    lines: List[str] = []
    for d in chosen:
        title = d["title"]
        section = d.get("section", "")
        cat = SECTION_TO_CATEGORY.get(section, "Other")
        evidence = appendix_map.get(title, [])
        signal_base = int(d.get("signal_base") or 0)
        strength = d.get("strength") or "Weak"

        titles = [s.title for s in evidence if s.title]
        prod = _count_hits(titles, PRODUCT_PATTERNS)[:2]
        geo = _count_hits(titles, GEO_PATTERNS)[:2]
        theme = _count_hits(titles, THEME_PATTERNS)[:2]

        # Minimum 2 concrete observations from titles (not generic).
        obs: List[str] = []
        if prod:
            obs.append(f"- Product focus repeats: {', '.join([p[0] for p in prod])}.")
        if geo:
            obs.append(f"- Geography repeats: {', '.join([g[0] for g in geo])}.")
        if theme:
            obs.append(f"- Theme repeats: {', '.join([t[0] for t in theme])}.")
        if len(obs) < 2 and titles:
            obs.append(f"- Coverage includes: {titles[0][:140]}.")
        if len(obs) < 2 and len(titles) > 1:
            obs.append(f"- Coverage includes: {titles[1][:140]}.")
        obs = obs[:3]

        why = _direct(
            {
                "Market": "The combined product + geography pattern sets near-term demand/pricing priorities and highlights where to focus commercial coverage.",
                "Capacity": "The combined capacity/structure pattern defines supply posture, regional availability, and where to stress-test continuity plans.",
                "Corporate": "The combined competition/positioning pattern clarifies where the value chain is consolidating and where competitive pressure concentrates.",
                "Technology": "The combined innovation/process pattern clarifies which technology lanes are active and what to prioritize in R&D and applications.",
                "Sustainability": "The combined transition/regulation pattern clarifies compliance pressure points and which sustainability lanes to accelerate.",
            }.get(cat, "Translate the extracted pattern into industry meaning.")
        )

        implication = _direct(
            {
                "Market": "Set commercial focus by the dominant demand/pricing lane and the geographies repeated in the evidence titles.",
                "Capacity": "Rebalance supply planning and regional availability based on the repeated capacity/structure lane in the evidence.",
                "Corporate": "Update competitive positioning and partnership posture based on repeated corporate themes in the evidence.",
                "Technology": "Convert the repeated innovation/process lane into a targeted roadmap and application focus for the next cycle.",
                "Sustainability": "Prioritize compliance and transition initiatives aligned to the regulation/circularity lane repeated in the evidence.",
            }.get(cat, "Convert the extracted pattern into a single planning direction.")
        )

        lines.extend(
            [
                f"### {title}",
                "",
                f"Signal base: {signal_base}",
                f"Strength: {strength}",
                "",
                "What is happening",
                *[_direct(x) for x in obs],
                "",
                "Why it matters",
                f"{why}",
                "",
                "Implication",
                f"{implication}",
                "",
            ]
        )
    return lines


def render_appendix(appendix_map: Dict[str, List[EvidenceSignal]], dev_order: List[str]) -> List[str]:
    lines: List[str] = [
        "# Appendix A - Evidence Signals",
        "",
        "Title",
        "Source",
        "Publication date",
        "",
    ]
    for dev_title in dev_order:
        items = appendix_map.get(dev_title) or []
        if not items:
            continue
        lines.append(f"## {dev_title}")
        lines.append("")
        for s in items:
            lines.append(_direct(s.title))
            lines.append(f"Source: {_direct(s.source) or '—'}")
            lines.append(f"Publication date: {_direct(s.publication_date) or '—'}")
            lines.append("")
        lines.append("")
    return lines


def main():
    run = get_run_by_id(RUN_ID) or {}
    md = run.get("metadata") or {}
    report_md_old = md.get("report_content") or ""
    if not report_md_old:
        raise RuntimeError("Run 9 report_content is missing in Supabase metadata.")

    report_period_days = _parse_reporting_period_days(report_md_old)
    devs, appendix_map_raw = parse_developments_and_appendix(report_md_old)
    appendix_map = dedupe_and_cap_appendix(appendix_map_raw)

    # Remove weak developments (<2 signals) from core
    core_devs = [d for d in devs if int(d.get("signal_base") or 0) >= 2]

    # Determine ordering for appendix grouping (use same ranking as key devs)
    core_devs_sorted = sorted(core_devs, key=lambda d: (-strength_rank(d.get("strength")), -int(d.get("signal_base") or 0), (d.get("title") or "").lower()))
    appendix_order = [d["title"] for d in core_devs_sorted if d.get("title") in appendix_map]

    # Build report
    lines: List[str] = []
    lines.extend(
        [
            "# Polyurethane Industry Intelligence Briefing",
            "",
            f"*Reporting period: {report_period_days}-day window*" if report_period_days else "*Reporting period: —*",
            "",
            "",
            "# Executive Summary",
            "",
        ]
    )
    lines.extend(build_exec_summary(core_devs, appendix_map))

    lines.extend(["# Key Developments", "", *build_key_devs(core_devs, appendix_map)])

    lines.extend(["# Section Deep Dives", "", *build_deep_dives(core_devs, appendix_map)])

    # Strategic Implications is now embedded in the “decision relevance” logic; keep concise, executive tone.
    lines.extend(
        [
            "# Strategic Implications",
            "",
            "- **Commercial focus:** Align demand/pricing actions to the recurring product and geography lanes extracted above.",
            "- **Supply posture:** Stress-test regional availability against the capacity/structure lanes that repeat in the evidence.",
            "- **Competitive moves:** Update positioning and partnerships where corporate themes cluster in the evidence titles.",
            "- **Innovation roadmap:** Convert repeated process/technology lanes into a targeted R&D and application plan.",
            "- **Transition readiness:** Prioritize compliance and circularity where regulation/transition lanes repeat.",
            "",
        ]
    )

    lines.extend(render_appendix(appendix_map, dev_order=appendix_order))

    # Preserve line breaks; apply weak-phrase filtering without flattening paragraphs.
    report_md_new = ("\n".join(lines)).strip() + "\n"
    report_md_new = WEAK_PHRASES.sub("", report_md_new)
    # Clean up occasional double-spaces introduced by phrase removal, but do not touch newlines.
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
            "CHARLIEC - RUN 9 ENRICHMENT CHECK",
            "================================",
            "",
            f"run_id: {RUN_ID}",
            "",
            "No pipeline rerun:",
            "- Regeneration reads Supabase metadata.report_content only (existing Run 9).",
            "- No validation/mapping/clustering/signal-selection stages executed.",
            "",
            "Report-writing enrichment implemented:",
            "- Pattern extraction scans signal titles for recurring products, geographies, and themes.",
            "- Executive Summary rewritten into decision blocks with Pattern + Decision relevance.",
            "- Key Developments rewritten with Pattern + Impact + Implication (distinct per category).",
            "- Section Deep Dives rewritten with >=2 concrete observations from titles (no 'supported by X signals' narrative).",
            "",
            "Phrasing rules:",
            "- Removed: 'signals observed', 'suggests', 'may indicate', and other weak phrasing terms.",
            "",
            "Appendix cleanup:",
            "- Deduplicated by (Title + Source).",
            "- Removed duplicates across developments.",
            f"- Capped at max {MAX_APPENDIX_PER_DEV} items per development; kept most recent when exceeding cap.",
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

