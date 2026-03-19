"""
CHARLIEC – RUN 9 REPORT RESTRUCTURE + REGENERATION (NO PIPELINE RERUN)

What this does:
- Fetch Run 9's already-generated `metadata.report_content` from Supabase.
- Parse existing development blocks + appendix evidence signals from that markdown.
- Rebuild a new report with your required structure and display rules.
- Export:
  - Live Results/Run 9 Restructured Report.txt
  - Live Results/Run 9 Restructured Report.html
  - Live Results/Run 9 Report Restructure Check.txt

Constraints:
- No validation / mapping / clustering / signal selection rerun.
- This is report-writing only (reformat + rewrite text using existing facts).
"""

from __future__ import annotations

import os
import re
import sys
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
from datetime import datetime, timezone

# Ensure `core/` is importable when running from `development/`
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
os.chdir(REPO_ROOT)

from core.admin_db import get_run_by_id
from core.intelligence_report import markdown_to_simple_html

try:
    from core.openai_assistant import get_openai_client
except Exception:
    get_openai_client = None


RUN_ID = "304034cf-0454-4b14-a9d8-9b9e9f25090a"
OUTPUT_DIR_NAME = "Live Results"

OUT_TXT = "Run 9 Restructured Report.txt"
OUT_HTML = "Run 9 Restructured Report.html"
OUT_CHECK = "Run 9 Report Restructure Check.txt"


STRENGTH_ORDER = {"Weak": 1, "Moderate": 2, "Strong": 3}

DEEP_DIVE_SECTIONS = [
    "Market Developments",
    "Technology and Innovation",
    "Capacity and Investment Activity",
    "Corporate Developments",
    "Sustainability and Circular Economy",
]

FOUR_EXEC_SUMMARY_SECTIONS = {
    "Market Developments": "Market",
    "Capacity and Investment Activity": "Capacity",
    "Corporate Developments": "Corporate",
    "Sustainability and Circular Economy": "Sustainability",
}

SECTION_LANGUAGE = {
    "Market": ("demand", "pricing"),
    "Capacity": ("structural", "supply"),
    "Corporate": ("competitive", "positioning"),
    "Technology": ("innovation", "process"),
    "Sustainability": ("transition", "circularity"),
}


WEAK_WORDS = re.compile(r"\b(may|suggests|could|possibly|might)\b", re.IGNORECASE)


def directify(text: str) -> str:
    """
    Convert known weak phrasing patterns to direct language.
    This is intentionally lightweight and run only on report-writing outputs.
    """
    if not text:
        return text

    t = text.strip()

    # Targeted grammar fixes for the strings used in this repo's interpretation generators.
    replacements: List[Tuple[str, str]] = [
        (r"\bThis may strengthen\b", "This strengthens"),
        (r"\bThis may affect\b", "This affects"),
        (r"\bThis may support\b", "This supports"),
        (r"\bmay affect\b", "affect"),
        (r"\baffect margins\b", "affect margins"),
        (r"\bmay influence\b", "influence"),
        (r"\bmay reinforce\b", "reinforces"),
        (r"\bmay inform\b", "informs"),
        (r"\bIndustry participants may use\b", "Industry participants use"),
        (r"\bMultiple analyses point to\b", "Multiple analyses show"),
        (r"\bindustry participants may\b", "industry participants"),
        (r"\bsuggests\b", "shows"),
        (r"\bThese developments may\b", "These developments"),
        (r"\bGrowth .* may influence\b", None),  # handled below by generic cleanup
    ]

    for pat, rep in replacements:
        if rep is None:
            continue
        t = re.sub(pat, rep, t, flags=re.IGNORECASE)

    # Remove remaining weak words (keep whitespace sane).
    t = WEAK_WORDS.sub("", t)
    t = re.sub(r"\s{2,}", " ", t).strip()

    # Small cleanup for "This  strengthens" style double spaces after removal.
    t = t.replace(" ,", ",").replace(" .", ".")
    return t


def _norm_space(s: str) -> str:
    return re.sub(r"\s{2,}", " ", (s or "").strip())


@dataclass
class DevInfo:
    title: str
    section: str
    signal_strength: str
    signal_count: int
    direction_of_impact: List[str]
    explanation: str
    business_relevance: str
    interpretation: str


@dataclass
class EvidenceSignal:
    title: str
    source: str
    publication_date: str


def _strength_key(dev: DevInfo) -> Tuple[int, int, str]:
    return (STRENGTH_ORDER.get(dev.signal_strength, 0), dev.signal_count, dev.title.lower())


def _parse_signal_count_from_explanation(explanation: str) -> int:
    # Example: "This development is supported by 10 observed signals during the reporting period."
    m = re.search(r"supported by\s+(\d+)\s+observed\s+signal", explanation, flags=re.IGNORECASE)
    if m:
        try:
            return int(m.group(1))
        except Exception:
            return 0
    m = re.search(r"supported by\s+(\d+)\s+observed\s+signals", explanation, flags=re.IGNORECASE)
    if m:
        try:
            return int(m.group(1))
        except Exception:
            return 0
    return 0


def parse_developments_from_report_md(report_md: str) -> List[DevInfo]:
    lines = (report_md or "").splitlines()

    devs: List[DevInfo] = []
    current_section: Optional[str] = None

    i = 0
    while i < len(lines):
        line = lines[i].rstrip()

        if line.startswith("# "):
            heading = line[2:].strip()
            current_section = heading if heading in DEEP_DIVE_SECTIONS else None
            i += 1
            continue

        if current_section and line.startswith("### "):
            title = line[4:].strip()
            # Collect until next "### " or next "# " (top-level)
            block: List[str] = [line]
            i += 1
            while i < len(lines):
                ln = lines[i].rstrip()
                if ln.startswith("### ") and ln[4:].strip() != "":
                    break
                if ln.startswith("# ") and not ln.startswith("### "):
                    break
                block.append(ln)
                i += 1

            # Parse block fields
            explanation = ""
            signal_strength = "Weak"
            business_relevance = ""
            interpretation = ""
            direction_of_impact: List[str] = []

            # Pass 1: extract signal strength, direction, and locate markers.
            bs_idx = None
            bd_idx = None
            dir_idx = None

            for idx, bline in enumerate(block):
                if bline.strip().startswith("**Signal Strength:**"):
                    m = re.search(r"\*\*Signal Strength:\*\*\s*(\w+)", bline, flags=re.IGNORECASE)
                    if m:
                        signal_strength = m.group(1).strip()
                if bline.strip() == "**Business Relevance**":
                    bs_idx = idx
                if bline.strip().startswith("**Direction of Impact**"):
                    dir_idx = idx

            # Explanation: first non-empty line after title that isn't a marker.
            for idx in range(1, len(block)):
                ln = block[idx].strip()
                if not ln:
                    continue
                if ln.startswith("**"):
                    continue
                if ln.startswith("- "):
                    continue
                explanation = ln
                break

            # Business relevance: line(s) after "**Business Relevance**" until "**Direction of Impact**" or end.
            if bs_idx is not None:
                k = bs_idx + 1
                buf: List[str] = []
                while k < len(block):
                    ln = block[k].strip()
                    if not ln:
                        if buf:
                            break
                        k += 1
                        continue
                    if ln.startswith("**Direction of Impact**"):
                        break
                    if ln.startswith("**"):
                        break
                    buf.append(ln)
                    k += 1
                business_relevance = " ".join(buf).strip()

            # Direction and interpretation.
            if dir_idx is not None:
                dline = block[dir_idx].strip()
                # Example: "**Direction of Impact** Demand, Supply"
                m = re.sub(r"^\*\*Direction of Impact\*\*\s*", "", dline)
                direction_of_impact = [x.strip() for x in m.split(",") if x.strip()]

                # Interpretation: next non-empty line after direction line that isn't a marker.
                k = dir_idx + 1
                buf2: List[str] = []
                while k < len(block):
                    ln = block[k].strip()
                    if not ln:
                        if buf2:
                            break
                        k += 1
                        continue
                    if ln.startswith("**"):
                        break
                    if ln.startswith("- "):
                        k += 1
                        continue
                    buf2.append(ln)
                    k += 1
                interpretation = " ".join(buf2).strip()

            signal_count = _parse_signal_count_from_explanation(explanation)

            devs.append(
                DevInfo(
                    title=title,
                    section=current_section or "",
                    signal_strength=signal_strength,
                    signal_count=signal_count,
                    direction_of_impact=direction_of_impact,
                    explanation=explanation,
                    business_relevance=business_relevance,
                    interpretation=interpretation,
                )
            )

            # Continue without skipping: i already at block end.
            continue

        i += 1

    return devs


def parse_evidence_signals_from_report_md(report_md: str) -> Dict[str, List[EvidenceSignal]]:
    """
    Returns: dev_title -> list of evidence signals (title/source/publication_date).
    """
    lines = (report_md or "").splitlines()
    out: Dict[str, List[EvidenceSignal]] = {}

    appendix_start = None
    for idx, ln in enumerate(lines):
        if ln.startswith("# Appendix A"):
            appendix_start = idx
            break
    if appendix_start is None:
        return out

    current_dev_title: Optional[str] = None
    current_signal: Optional[Dict[str, str]] = None

    def flush_signal():
        nonlocal current_signal
        if not current_signal or not current_dev_title:
            return
        title = current_signal.get("title") or ""
        source = current_signal.get("source") or ""
        pub = current_signal.get("publication_date") or ""
        if not title and not source and not pub:
            current_signal = None
            return
        out.setdefault(current_dev_title, []).append(EvidenceSignal(title=title, source=source, publication_date=pub))
        current_signal = None

    for i in range(appendix_start + 1, len(lines)):
        ln = lines[i].rstrip()
        if ln.startswith("## "):
            flush_signal()
            current_dev_title = ln[3:].strip()
            out.setdefault(current_dev_title, [])
            continue

        if ln.startswith("- **") and ln.endswith("**"):
            flush_signal()
            current_signal = {"title": ln.replace("- **", "").replace("**", "").strip()}
            continue

        if current_signal is None:
            continue

        # Source and publication date lines.
        m = re.search(r"\-\s*Source:\s*(.*)$", ln)
        if m:
            current_signal["source"] = m.group(1).strip()
            continue
        m = re.search(r"\-\s*Publication date:\s*(.*)$", ln)
        if m:
            current_signal["publication_date"] = m.group(1).strip()
            continue

    flush_signal()
    return out


def infer_geography_from_dev_signals_hint(dev: DevInfo) -> Optional[str]:
    # Geography isn't present in the current development blocks produced by intelligence_report.py.
    # Keep this optional and return None when we can't infer reliably.
    return None


def generate_exec_summary(core_devs: List[DevInfo]) -> List[str]:
    """
    Max 4 blocks: Market, Capacity, Corporate, Sustainability
    Direct statements only. No weak phrasing.
    """
    by_section: Dict[str, List[DevInfo]] = {}
    for d in core_devs:
        by_section.setdefault(d.section, []).append(d)

    blocks: List[str] = []
    for section, label in FOUR_EXEC_SUMMARY_SECTIONS.items():
        candidates = by_section.get(section) or []
        if not candidates:
            continue
        candidates_sorted = sorted(candidates, key=lambda x: (-STRENGTH_ORDER.get(x.signal_strength, 0), -x.signal_count, x.title.lower()))
        top = candidates_sorted[0]
        dir_part = ", ".join(top.direction_of_impact) if top.direction_of_impact else "key impact areas"
        geo = infer_geography_from_dev_signals_hint(top)

        what_dir = SECTION_LANGUAGE.get(label, (label.lower(), ""))[0]
        # Keep wording direct and section-specific.
        if label == "Market":
            stmt = f"{top.title}. Demand and pricing themes were observed across the reporting window (signal base: {top.signal_count}). Impact direction: {dir_part}."
        elif label == "Capacity":
            stmt = f"{top.title}. Structural and supply-focused activity was observed across the reporting window (signal base: {top.signal_count}). Impact direction: {dir_part}."
        elif label == "Corporate":
            stmt = f"{top.title}. Competitive repositioning activity was observed across the reporting window (signal base: {top.signal_count}). Impact direction: {dir_part}."
        elif label == "Sustainability":
            stmt = f"{top.title}. Transition and circularity themes were observed across the reporting window (signal base: {top.signal_count}). Impact direction: {dir_part}."
        else:
            stmt = f"{top.title}. Signal base: {top.signal_count}."

        stmt = WEAK_WORDS.sub("", stmt)
        stmt = re.sub(r"\s{2,}", " ", stmt).strip()
        blocks.append(f"- **{label}** {stmt}")

    return blocks[:4]


def render_key_developments(key_devs: List[DevInfo]) -> List[str]:
    lines: List[str] = []
    for d in key_devs:
        geo = infer_geography_from_dev_signals_hint(d)
        geo_part = f"Geography: {geo}" if geo else None
        impact = ", ".join(d.direction_of_impact) if d.direction_of_impact else "—"
        # Language variation by section
        if d.section == "Technology and Innovation":
            label = "Technology"
        elif d.section == "Market Developments":
            label = "Market"
        elif d.section == "Capacity and Investment Activity":
            label = "Capacity"
        elif d.section == "Corporate Developments":
            label = "Corporate"
        elif d.section == "Sustainability and Circular Economy":
            label = "Sustainability"
        else:
            label = "Other"
        implication = directify(
            f"{label}: Apply the observed {label.lower()} signal base from '{d.title}' to near-term decisions tied to polyurethane planning. "
            f"Impact direction: {impact}."
        )
        implication = WEAK_WORDS.sub("", implication).strip()[:200]
        lines.extend(
            [
                f"### {d.title}",
                f"Signal Count: {d.signal_count}",
                *( [geo_part] if geo_part else [] ),
                f"Impact Direction: {impact}",
                f"Implication: {implication}",
                "",
            ]
        )
    return lines


def render_deep_dive_block(d: DevInfo) -> List[str]:
    geo = infer_geography_from_dev_signals_hint(d)
    geo_part = f"Geography: {geo}" if geo else ""

    what = _norm_space(d.explanation)
    impact = ", ".join(d.direction_of_impact) if d.direction_of_impact else "—"
    # Section language variation: enforce per-section phrasing in report-writing.
    if d.section == "Technology and Innovation":
        lang_label = "Technology"
    elif d.section == "Market Developments":
        lang_label = "Market"
    elif d.section == "Capacity and Investment Activity":
        lang_label = "Capacity"
    elif d.section == "Corporate Developments":
        lang_label = "Corporate"
    elif d.section == "Sustainability and Circular Economy":
        lang_label = "Sustainability"
    else:
        lang_label = (FOUR_EXEC_SUMMARY_SECTIONS.get(d.section) or "Other")

    verb_a, noun_b = SECTION_LANGUAGE.get(lang_label, ("focus", "signals"))

    # Build direct statements (no weak phrasing) from existing facts.
    what = WEAK_WORDS.sub("", what)
    why = directify(
        f"'{d.title}' uses signal base to support {verb_a}/{noun_b} prioritization for polyurethane planning. "
        f"Impact direction: {impact}."
    )
    imp = directify(
        f"Implication for '{d.title}': convert the observed {noun_b} into an action-ready planning line for the reporting window."
    )
    why = WEAK_WORDS.sub("", why).strip()
    imp = WEAK_WORDS.sub("", imp).strip()

    lines = [
        f"### {d.title}",
        "",
        f"Signal base: {d.signal_count}",
    ]
    if geo_part:
        lines.append(geo_part)
    lines.extend(
        [
            f"Strength: {d.signal_strength}",
            "",
            "What is happening",
            f"{what}",
            "",
            "Why it matters",
            f"{why}",
            "",
            "Implication",
            f"{imp} (Impact direction: {impact})",
            "",
        ]
    )
    return lines


def llm_strategic_implications(core_devs: List[DevInfo], report_period_days: Optional[int]) -> Optional[List[str]]:
    if not get_openai_client:
        return None
    try:
        client = get_openai_client()
        if not client:
            return None
    except Exception:
        return None

    if not core_devs:
        return None

    period = "reporting period"
    if isinstance(report_period_days, int) and report_period_days > 0:
        period = f"{report_period_days}-day window"

    # Provide compact facts.
    core_sorted = sorted(core_devs, key=lambda x: (-STRENGTH_ORDER.get(x.signal_strength, 0), -x.signal_count, x.title.lower()))[:12]
    dev_lines = []
    for d in core_sorted:
        dir_part = ", ".join(d.direction_of_impact) if d.direction_of_impact else "—"
        why = directify(d.business_relevance)[:160] if d.business_relevance else ""
        dev_lines.append(f"- [{d.section}] {d.title} | Strength={d.signal_strength} | Signals={d.signal_count} | Impact={dir_part} | Why={why}")
    context = "\n".join(dev_lines)

    system = (
        "You are writing executive-level polyurethane industry strategic implications. "
        "Use ONLY the provided developments as factual inputs. "
        "Output 3-5 bullet points. Each bullet must start with '- **Label:** '. "
        "No weak phrasing: do not use these words: may, suggests, could, possibly, might, can, possibly. "
        "Keep bullets concise and direct (1-2 sentences each)."
    )
    user = (
        f"Reporting window: {period}\n\nDevelopments:\n{context}\n\n"
        "Write 3-5 strategic implication bullets."
    )

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.2,
            max_tokens=420,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        )
        text = (resp.choices[0].message.content or "").strip() if resp.choices else ""
        if not text:
            return None
        out_lines: List[str] = []
        for raw in text.splitlines():
            ln = raw.strip()
            if not ln:
                continue
            if not ln.startswith("-"):
                ln = "- " + ln
            ln = WEAK_WORDS.sub("", ln)
            out_lines.append(ln)
        return out_lines[:5]
    except Exception:
        return None


def render_appendix(core_devs: List[DevInfo], appendix_map: Dict[str, List[EvidenceSignal]]) -> List[str]:
    core_titles = {d.title for d in core_devs}

    lines: List[str] = [
        "# Appendix A - Evidence Signals",
        "",
        "Supporting signals grouped by development (Title, Source, Publication date).",
        "",
    ]

    # Stable order: section order then strength then title.
    core_sorted = sorted(
        [d for d in core_devs if d.title in core_titles],
        key=lambda x: (DEEP_DIVE_SECTIONS.index(x.section) if x.section in DEEP_DIVE_SECTIONS else 999, -STRENGTH_ORDER.get(x.signal_strength, 0), -x.signal_count, x.title.lower()),
    )

    for d in core_sorted:
        signals = appendix_map.get(d.title) or []
        if not signals:
            continue
        lines.append(f"## {d.title}")
        lines.append("")
        for s in signals:
            lines.append(s.title)
            lines.append(f"Source: {s.source or '—'}")
            lines.append(f"Publication date: {s.publication_date or '—'}")
            lines.append("")
        lines.append("")
    return lines


def extract_reporting_period_days_from_old_scope(report_md: str) -> Optional[int]:
    # In old report: "*Reporting period: 120-day window*"
    m = re.search(r"Reporting period:\s*(\d+)-day window", report_md)
    if not m:
        return None
    try:
        return int(m.group(1))
    except Exception:
        return None


def main():
    run = get_run_by_id(RUN_ID) or {}
    md = run.get("metadata") or {}
    report_md = md.get("report_content") or ""
    if not report_md:
        raise RuntimeError("Run 9 report_content is missing in Supabase metadata.")

    report_period_days = extract_reporting_period_days_from_old_scope(report_md)

    # Parse developments and appendix evidence from the existing report.
    devs = parse_developments_from_report_md(report_md)
    appendix_map = parse_evidence_signals_from_report_md(report_md)

    # Remove weak developments (<2 signals)
    core_devs = [d for d in devs if d.signal_count >= 2]

    # Key developments: top 5-8 by strength then signal base
    core_sorted = sorted(core_devs, key=lambda x: (-STRENGTH_ORDER.get(x.signal_strength, 0), -x.signal_count, x.title.lower()))
    if len(core_sorted) >= 5:
        key_devs = core_sorted[: min(8, len(core_sorted))]
    else:
        key_devs = core_sorted

    # Exec summary blocks
    exec_blocks = generate_exec_summary(core_devs)

    # Strategic implications (rewrite)
    si_lines = llm_strategic_implications(core_devs, report_period_days=report_period_days)

    if not si_lines:
        # Deterministic fallback: 3 bullets made from top 3 key developments.
        si_lines = []
        for d in key_devs[:3]:
            dir_part = ", ".join(d.direction_of_impact) if d.direction_of_impact else "industry direction"
            imp = directify(d.interpretation or d.business_relevance or d.explanation)
            imp = WEAK_WORDS.sub("", imp)[:160]
            label = FOUR_EXEC_SUMMARY_SECTIONS.get(d.section, "Market")
            si_lines.append(f"- **{label}:** {d.title}. {imp}")
        si_lines = si_lines[:5]

    # Rebuild markdown output with required structure.
    report_lines: List[str] = []
    report_lines.extend(
        [
            "# Polyurethane Industry Intelligence Briefing",
            "",
            f"*Reporting period: {report_period_days or '—'}-day window*"
            if report_period_days
            else "*Reporting period: —*",
            "",
            "",
            "# Executive Summary",
            "",
        ]
    )
    report_lines.extend(exec_blocks)
    report_lines.append("")

    report_lines.append("# Key Developments")
    report_lines.append("")
    report_lines.extend(render_key_developments(key_devs))

    report_lines.append("# Section Deep Dives")
    report_lines.append("")

    # Deep dives for the same key developments, grouped by report section order.
    section_order = [
        "Market Developments",
        "Capacity and Investment Activity",
        "Corporate Developments",
        "Technology and Innovation",
        "Sustainability and Circular Economy",
    ]
    key_by_section: Dict[str, List[DevInfo]] = {}
    for d in key_devs:
        key_by_section.setdefault(d.section, []).append(d)
    for sec in section_order:
        for d in sorted(key_by_section.get(sec) or [], key=lambda x: (-STRENGTH_ORDER.get(x.signal_strength, 0), -x.signal_count, x.title.lower())):
            report_lines.extend(render_deep_dive_block(d))

    report_lines.append("# Strategic Implications")
    report_lines.append("")
    report_lines.append("Executive-level summary of the polyurethane industry direction based on the developments above.")
    report_lines.append("")
    report_lines.extend(si_lines)
    report_lines.append("")

    # Appendix (compressed)
    report_lines.extend(render_appendix(core_devs, appendix_map))

    report_md_new = "\n".join(report_lines).strip() + "\n"

    # Convert to HTML using existing constrained renderer.
    html_title = "PU Market Intelligence"
    html = markdown_to_simple_html(
        report_md_new,
        title=html_title,
        signal_map_pie_html=None,
        deploy_version=md.get("deploy_version"),
        run_id=RUN_ID,
    )

    output_dir = Path(__file__).resolve().parent.parent / OUTPUT_DIR_NAME
    output_dir.mkdir(parents=True, exist_ok=True)
    txt_path = output_dir / OUT_TXT
    html_path = output_dir / OUT_HTML
    check_path = output_dir / OUT_CHECK

    txt_path.write_text(report_md_new, encoding="utf-8")
    html_path.write_text(html, encoding="utf-8")

    # Generation check file
    created_paths = [str(txt_path), str(html_path)]
    # Files created are deterministic; include the generated HTML and markdown.
    check_text = "\n".join(
        [
            "CHARLIEC – RUN 9 REPORT RESTRUCTURE CHECK",
            "==========================================",
            "",
            f"run_id: {RUN_ID}",
            "",
            "No pipeline rerun:",
            "- This script only reads Supabase metadata.report_content (existing Run 9 output).",
            "- It does not call evidence_engine, customer filtering, mapping, or clustering phases.",
            "",
            "No intelligence changes beyond report-writing:",
            "- Development blocks are parsed from the existing report and re-presented in the new required layout.",
            "- Weak phrasing restrictions are enforced at report-writing time (directify + word filtering).",
            "- Strategic Implications are regenerated as a report-writing rewrite using the already-generated development facts.",
            "",
            "Formatting changes summary:",
            "- New section order: Executive Summary -> Key Developments -> Section Deep Dives -> Strategic Implications -> Appendix A.",
            "- Executive Summary reduced to <=4 direct blocks (Market/Capacity/Corporate/Sustainability).",
            "- Key Developments ranked and displayed with signal count, impact direction, and a single implication line.",
            "- Section Deep Dives rewritten using the required field layout (Signal base/Geography/Strength/What/Why/Implication).",
            "- Appendix A compressed and grouped by development; URL and category lines removed.",
            "",
            "Files created:",
            f"- {txt_path}",
            f"- {html_path}",
            f"- {check_path}",
            "",
            f"generation timestamp (UTC): {datetime.now(timezone.utc).isoformat()}",
        ]
    )
    check_path.write_text(check_text, encoding="utf-8")

    print(f"Created:\n- {txt_path}\n- {html_path}\n- {check_path}")


if __name__ == "__main__":
    main()

