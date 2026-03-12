"""
Phase 5 – Market Intelligence Synthesis Engine.
Structured, baseline-aware, scope-selectable. Replaces executive summary from markdown body.
Inputs: clustered signals JSON + baseline snapshot JSON. Output: 5 fixed sections, 2–4 sentences each.
"""

from typing import Dict, List, Any, Optional, Tuple
import json
import time

SCOPE_GLOBAL = "GLOBAL"
SCOPE_REGION = "REGION"
SCOPE_REGION_SEGMENT = "REGION_SEGMENT"


def _norm_region_macro(r: Optional[str]) -> str:
    if not r:
        return "EMEA"
    u = (r or "").strip().upper()
    if u in ("EMEA", "APAC", "AMERICAS"):
        return "Americas" if u == "AMERICAS" else u
    if u in ("EU", "EUROPE"):
        return "EMEA"
    if u in ("APAC", "ASIA", "CHINA", "JAPAN"):
        return "APAC"
    if u in ("US", "USA", "AMERICAS"):
        return "Americas"
    return "EMEA"


def _clusters_for_synthesis(run_id: str, scope: str, region_macro: Optional[str] = None, segment: Optional[str] = None) -> List[Dict]:
    """Fetch signal_clusters for run, filter by scope, return list for JSON."""
    from core.generator_db import get_supabase_client
    supabase = get_supabase_client()
    result = supabase.table("signal_clusters").select(
        "id, region, segment, signal_type, final_classification, materiality_flag, "
        "aggregated_numeric_value, aggregated_numeric_unit, cluster_key"
    ).eq("run_id", run_id).execute()
    rows = result.data or []
    want_rm = _norm_region_macro(region_macro) if (scope == SCOPE_REGION or scope == SCOPE_REGION_SEGMENT) else None
    want_seg = (segment or "").strip().lower().replace("-", "_") if scope == SCOPE_REGION_SEGMENT else None
    out = []
    for r in rows:
        rm = _norm_region_macro(r.get("region"))
        seg = (r.get("segment") or "").strip().lower().replace("-", "_") or "raw_materials"
        if scope == SCOPE_REGION and want_rm and rm != want_rm:
            continue
        if scope == SCOPE_REGION_SEGMENT:
            if (want_rm and rm != want_rm) or (want_seg is not None and seg != want_seg):
                continue
        short_description = (r.get("cluster_key") or "")[:200] or f"{r.get('signal_type')} {seg} {rm}"
        out.append({
            "cluster_id": str(r.get("id") or ""),
            "region_macro": rm,
            "segment": seg,
            "signal_type": (r.get("signal_type") or "other").strip(),
            "final_classification": (r.get("final_classification") or "tactical").strip(),
            "materiality_flag": bool(r.get("materiality_flag")),
            "numeric_value": r.get("aggregated_numeric_value"),
            "numeric_unit": r.get("aggregated_numeric_unit"),
            "short_description": short_description,
        })
    return out


def _baseline_for_scope(scope: str, region_macro: Optional[str] = None, segment: Optional[str] = None) -> List[Dict]:
    """Fetch latest anchor_year from v_structural_rolling_3y/5y and return baseline snapshot(s) per scope."""
    from core.generator_db import get_supabase_client
    supabase = get_supabase_client()
    r3 = supabase.table("v_structural_rolling_3y").select("anchor_year").order("anchor_year", desc=True).limit(1).execute()
    latest_year = (r3.data or [{}])[0].get("anchor_year") if r3.data else 2024
    if scope == SCOPE_GLOBAL:
        rows_3 = supabase.table("v_structural_rolling_3y").select("*").eq("anchor_year", latest_year).eq("segment", "ALL").execute()
        rows_5 = supabase.table("v_structural_rolling_5y").select("*").eq("anchor_year", latest_year).eq("segment", "ALL").execute()
        out = []
        for r in (rows_3.data or []):
            r5 = next((x for x in (rows_5.data or []) if x.get("region_macro") == r.get("region_macro")), {})
            out.append({
                "region_macro": r.get("region_macro"),
                "segment": "ALL",
                "capacity_net_tpa_3y": r.get("capacity_net_tpa_3y"),
                "capacity_net_tpa_5y": r5.get("capacity_net_tpa_5y"),
                "event_count_total_3y": r.get("event_count_total_3y"),
                "event_count_capacity_3y": r.get("event_count_capacity_3y"),
                "event_count_mna_3y": r.get("event_count_mna_3y"),
                "event_count_regulation_3y": r.get("event_count_regulation_3y"),
                "event_count_technology_3y": r.get("event_count_technology_3y"),
                "event_count_total_5y": r5.get("event_count_total_5y"),
            })
        return out
    if scope == SCOPE_REGION:
        seg_filter = "ALL"
        rm = _norm_region_macro(region_macro)
        r3 = supabase.table("v_structural_rolling_3y").select("*").eq("anchor_year", latest_year).eq("region_macro", rm).eq("segment", seg_filter).execute()
        r5 = supabase.table("v_structural_rolling_5y").select("*").eq("anchor_year", latest_year).eq("region_macro", rm).eq("segment", seg_filter).execute()
        a, b = (r3.data or [{}])[0], (r5.data or [{}])[0]
        return [{
            "region_macro": rm,
            "segment": seg_filter,
            "capacity_net_tpa_3y": a.get("capacity_net_tpa_3y"),
            "capacity_net_tpa_5y": b.get("capacity_net_tpa_5y"),
            "event_count_total_3y": a.get("event_count_total_3y"),
            "event_count_capacity_3y": a.get("event_count_capacity_3y"),
            "event_count_mna_3y": a.get("event_count_mna_3y"),
            "event_count_regulation_3y": a.get("event_count_regulation_3y"),
            "event_count_technology_3y": a.get("event_count_technology_3y"),
            "event_count_total_5y": b.get("event_count_total_5y"),
        }]
    if scope == SCOPE_REGION_SEGMENT:
        seg = (segment or "raw_materials").strip().lower().replace("-", "_")
        rm = _norm_region_macro(region_macro)
        r3 = supabase.table("v_structural_rolling_3y").select("*").eq("anchor_year", latest_year).eq("region_macro", rm).eq("segment", seg).execute()
        r5 = supabase.table("v_structural_rolling_5y").select("*").eq("anchor_year", latest_year).eq("region_macro", rm).eq("segment", seg).execute()
        a, b = (r3.data or [{}])[0], (r5.data or [{}])[0]
        return [{
            "region_macro": rm,
            "segment": seg,
            "capacity_net_tpa_3y": a.get("capacity_net_tpa_3y"),
            "capacity_net_tpa_5y": b.get("capacity_net_tpa_5y"),
            "event_count_total_3y": a.get("event_count_total_3y"),
            "event_count_capacity_3y": a.get("event_count_capacity_3y"),
            "event_count_mna_3y": a.get("event_count_mna_3y"),
            "event_count_regulation_3y": a.get("event_count_regulation_3y"),
            "event_count_technology_3y": a.get("event_count_technology_3y"),
            "event_count_total_5y": b.get("event_count_total_5y"),
        }]
    return []


def run_market_intelligence_synthesis(
    run_id: str,
    scope: str = SCOPE_GLOBAL,
    region_macro: Optional[str] = None,
    segment: Optional[str] = None,
    critique_issues: Optional[List[str]] = None,
) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """
    Produce Market Intelligence Report from structured signals + baseline.
    scope: GLOBAL | REGION | REGION_SEGMENT. For REGION/REGION_SEGMENT pass region_macro (and segment).
    critique_issues: optional list of diagnostic strings from Phase 6 critique; when set, prompt asks for revision addressing these.
    Returns (report_text, usage_dict). Report has exactly 5 sections, 2–4 sentences each, no markdown.
    """
    clusters = _clusters_for_synthesis(run_id, scope, region_macro, segment)
    baseline_list = _baseline_for_scope(scope, region_macro, segment)

    from core.openai_assistant import get_openai_client
    client = get_openai_client()
    if not client:
        return None, None

    signals_json = json.dumps(clusters, indent=0)[:12000]
    baseline_json = json.dumps(baseline_list, indent=0)[:4000]

    scope_label = scope
    if scope == SCOPE_REGION and region_macro:
        scope_label = f"REGION {region_macro}"
    elif scope == SCOPE_REGION_SEGMENT and region_macro and segment:
        scope_label = f"REGION {region_macro} SEGMENT {segment}"

    system = (
        "You are a polyurethane industry strategist. Produce executive-grade market intelligence. "
        "Base conclusions only on the provided structured signals and baseline. "
        "Do not use generic commentary, unsupported claims, or emotive language. "
        "Do not output markdown, bullet points, or section numbers. "
        "Output plain text only: exactly 5 sections in this order, each starting with the section name on its own line: "
        "Structural Movements, Cyclical Pressures, Regulatory and Capital Shifts, Competitive Implications, Forward Risk Signals. "
        "After each section name, write 2–4 sentences. Separate each section with a single blank line. "
        "If baseline data exists and is non-zero, quantify deviations versus the 3Y rolling baseline where possible. "
        "If baseline net is zero, state clearly that no structural expansion baseline exists in the period. "
        "If no relevant signals exist in a category, explicitly state absence of activity; do not speculate."
    )
    revision_note = ""
    if critique_issues:
        revision_note = (
            "\n\nRevision request: The following quality issues were identified. Address them in this draft:\n"
            + "\n".join(f"- {s}" for s in critique_issues[:15])
            + "\n\n"
        )
    user = (
        f"Scope: {scope_label}\n\n"
        f"Clustered Signals (JSON):\n{signals_json}\n\n"
        f"Baseline Snapshot (JSON):\n{baseline_json}\n\n"
        f"{revision_note}"
        "Write the 5 sections. Start each section with its name on a single line (Structural Movements, then Cyclical Pressures, then Regulatory and Capital Shifts, then Competitive Implications, then Forward Risk Signals), then 2–4 sentences. No numbering, no markdown. Separate sections with a single blank line."
    )

    try:
        t0 = time.monotonic()
        resp = client.chat.completions.create(
            model="gpt-4o",
            temperature=0.25,
            max_tokens=1500,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        )
        response_time_ms = int((time.monotonic() - t0) * 1000)
        choice = resp.choices[0] if resp.choices else None
        text = (choice.message.content or "").strip() if choice else ""
        usage = None
        if getattr(resp, "usage", None):
            usage = {
                "input_tokens": getattr(resp.usage, "input_tokens", 0),
                "output_tokens": getattr(resp.usage, "output_tokens", 0),
                "total_tokens": getattr(resp.usage, "total_tokens", 0),
                "model": resp.model or "gpt-4o",
            }
        try:
            from core.performance_logger import log_llm_call, get_current_run_id
            if get_current_run_id():
                log_llm_call(
                    stage_name="synthesis",
                    call_type="synthesis",
                    model_name=getattr(resp, "model", None) or "gpt-4o",
                    temperature=0.25,
                    usage=resp.usage,
                    response_time_ms=response_time_ms,
                    call_status="success",
                    request_id=getattr(resp, "id", None),
                )
        except Exception:
            pass
        return text, usage
    except Exception as e:
        try:
            from core.performance_logger import log_llm_call, get_current_run_id
            if get_current_run_id():
                log_llm_call(
                    stage_name="synthesis",
                    call_type="synthesis",
                    model_name="gpt-4o",
                    temperature=0.25,
                    usage=None,
                    response_time_ms=0,
                    call_status="fail",
                    error_type=type(e).__name__,
                    error_message=str(e)[:500],
                )
        except Exception:
            pass
        return None, None
