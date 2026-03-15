"""
CHARLIEC – Section Mapping Diagnostic

For a given run_id: loads spec, candidates, applies scope filter to get records entering
section mapping, then replicates Phase 5 section mapping (query_plan_map filter + 
CATEGORY_TO_SECTION + included_sections). Produces per-record and summary diagnostics.

Output: Live Results/Section Mapping Check.txt

Usage: python development/section_mapping_check.py [run_id]
  run_id optional; if not provided uses RUN_ID_DEFAULT.
  Run ID can be short (e.g. 54525b97) or full UUID.
"""

import sys
from pathlib import Path
from collections import defaultdict

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

LIVE_RESULTS_DIR = REPO_ROOT / "Live Results"
OUTPUT_FILENAME = "Section Mapping Check.txt"

# Default: pass your run_id as first argument (e.g. run with 31 records after scope filter).
RUN_ID_DEFAULT = "292fb71c-1645-48a7-b92b-81c51c985c5f"


def _resolve_run_id(run_id: str) -> str:
    if len(run_id) == 36 and run_id.count("-") == 4:
        return run_id
    try:
        from core.admin_db import get_recent_runs
        runs, _ = get_recent_runs(limit=200)
        prefix = run_id.lower()
        matches = [r for r in runs if r.get("id") and str(r["id"]).lower().startswith(prefix)]
        if matches:
            return matches[0]["id"]
    except Exception:
        pass
    return run_id


def main() -> None:
    run_id_arg = sys.argv[1].strip() if len(sys.argv) > 1 else RUN_ID_DEFAULT
    run_id = _resolve_run_id(run_id_arg)

    from core.generator_db import get_candidate_articles_for_run, get_specification_detail, get_master_signals_for_run
    from core.admin_db import get_run_by_id
    from core.query_planner import build_query_plan_map
    from core.customer_filter import filter_candidates_by_spec
    from core.intelligence_report import (
        CATEGORY_TO_SECTION,
        CONFIGURATOR_TO_CLASSIFIER,
    )

    run = get_run_by_id(run_id)
    if not run:
        print(f"Run not found: {run_id}")
        sys.exit(1)
    spec_id = run.get("specification_id")
    if not spec_id:
        print("Run has no specification_id")
        sys.exit(1)

    spec = get_specification_detail(spec_id)
    if not spec:
        print(f"Spec not found: {spec_id}")
        sys.exit(1)

    # Candidates from DB (all inserted for this run)
    candidates = get_candidate_articles_for_run(run_id)
    # Apply scope filter to get records that "enter section mapping" (same as pipeline)
    entering_section_mapping = filter_candidates_by_spec(candidates, spec)
    total_entering = len(entering_section_mapping)

    included_sections = list(spec.get("included_sections") or [])
    section_list = included_sections if included_sections else None
    query_plan_map = build_query_plan_map(spec)

    # Build "articles" as in generate_report_from_signals: category = classifier
    rows = []
    unmapped_reasons: defaultdict = defaultdict(int)

    for s in entering_section_mapping:
        title = (s.get("title") or "").strip()
        config_cat = (s.get("category") or "").strip()
        value_chain_link = (s.get("value_chain_link") or "").strip()
        classifier_cat = (s.get("classifier_category") or "").strip()
        if not classifier_cat:
            classifier_cat = CONFIGURATOR_TO_CLASSIFIER.get(config_cat, "Market Intelligence")

        # Would this signal pass filter_signals_by_spec_with_stats?
        # Current code uses only query_plan_map; when qid missing or not in map, meta={} so all fail.
        qid = (s.get("query_id") or "").strip()
        meta = query_plan_map.get(qid) if qid else None
        if meta:
            region = (meta.get("region") or "").strip()
            meta_config_cat = (meta.get("configurator_category") or "").strip()
            meta_vcl = (meta.get("value_chain_link") or "").strip()
        else:
            # Fallback: use signal's own metadata (candidate_articles have category, region, value_chain_link)
            region = (s.get("region") or "").strip()
            meta_config_cat = config_cat
            meta_vcl = value_chain_link

        regions_spec = spec.get("regions") or []
        categories_spec = spec.get("categories") or []
        vcl_spec = spec.get("value_chain_links") or []
        ok_region = (not regions_spec) or (region in regions_spec)
        ok_cat = (not categories_spec) or (meta_config_cat in categories_spec)
        ok_vcl = (not vcl_spec) or (meta_vcl in vcl_spec)
        passes_phase5_filter = ok_region and ok_cat and ok_vcl

        if not passes_phase5_filter:
            target_section = ""
            mapping_status = "rejected by mapping rule"
            if not qid or qid not in query_plan_map:
                reason = "query_id_missing_or_not_in_plan"
            elif not ok_region:
                reason = "region_not_in_spec"
            elif not ok_cat:
                reason = "configurator_category_not_in_spec"
            else:
                reason = "value_chain_link_not_in_spec"
            unmapped_reasons[reason] += 1
        else:
            # Map to section (same as intelligence_report)
            sec = CATEGORY_TO_SECTION.get(classifier_cat, "Market Developments")
            if section_list is None or sec in section_list:
                target_section = sec
                mapping_status = "mapped"
            else:
                target_section = sec
                mapping_status = "rejected by mapping rule"
                reason = "section_not_in_included_sections"
                unmapped_reasons[reason] += 1

        rows.append({
            "title": title[:70] if title else "",
            "category": config_cat,
            "classifier_category": classifier_cat,
            "value_chain_link": value_chain_link,
            "query_id": qid or "(none)",
            "target_section": target_section,
            "mapping_status": mapping_status,
        })

    # Section mapping summary: section -> count (among mapped only)
    section_counts = defaultdict(int)
    for r in rows:
        if r["mapping_status"] == "mapped" and r["target_section"]:
            section_counts[r["target_section"]] += 1

    # Build output
    lines = [
        "Section Mapping Check",
        "=" * 70,
        "",
        f"Run ID: {run_id}",
        f"Specification ID: {spec_id}",
        f"Total records entering section mapping: {total_entering}",
        "",
        "Field used for mapping: category (configurator) -> CONFIGURATOR_TO_CLASSIFIER -> classifier_category;",
        "then CATEGORY_TO_SECTION[classifier_category] -> report section.",
        "Phase 5 also filters by query_plan_map (query_id -> region, configurator_category, value_chain_link);",
        "if query_id is missing or not in plan, the record is dropped before section mapping.",
        "",
        "Per-record mapping:",
        "-" * 70,
    ]
    fmt = "{:<52} | {:<18} | {:<22} | {:<12} | {:<28} | {:<24}"
    lines.append(fmt.format("title", "category", "classifier_category", "value_chain", "target_section", "mapping_status"))
    lines.append("-" * 160)
    for r in rows:
        lines.append(fmt.format(
            (r["title"] or "")[:52],
            (r["category"] or "")[:18],
            (r["classifier_category"] or "")[:22],
            (r["value_chain_link"] or "")[:12],
            (r["target_section"] or "")[:28],
            (r["mapping_status"] or "")[:24],
        ))

    lines.extend([
        "",
        "SECTION MAPPING SUMMARY",
        "-" * 70,
        "section | count",
        "-" * 70,
    ])
    for sec in sorted(section_counts.keys()):
        lines.append(f"{sec} | {section_counts[sec]}")
    if not section_counts:
        lines.append("(none mapped)")

    lines.extend([
        "",
        "UNMAPPED REASONS SUMMARY",
        "-" * 70,
        "reason | count",
        "-" * 70,
    ])
    for reason in sorted(unmapped_reasons.keys()):
        lines.append(f"{reason} | {unmapped_reasons[reason]}")
    if not unmapped_reasons:
        lines.append("(none)")

    mapped_count = sum(1 for r in rows if r["mapping_status"] == "mapped")
    lines.extend([
        "",
        "Conclusion:",
        f"  Records entering section mapping: {total_entering}",
        f"  Records mapped into a section: {mapped_count}",
        f"  Records rejected: {total_entering - mapped_count}",
        "",
        "Primary cause of 31 -> 0:",
    ])
    if unmapped_reasons:
        top = max(unmapped_reasons.items(), key=lambda x: x[1])
        lines.append(f"  {top[0]!r} (count={top[1]}).")
    else:
        lines.append("  (all mapped; check included_sections or section list.)")

    LIVE_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = LIVE_RESULTS_DIR / OUTPUT_FILENAME
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out_path}")
    print(f"  Entering section mapping: {total_entering}, Mapped: {mapped_count}, Rejected: {total_entering - mapped_count}")
    print(f"  Unmapped reasons: {dict(unmapped_reasons)}")


if __name__ == "__main__":
    main()
