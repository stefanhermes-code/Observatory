"""
CHARLIEC – Generator Capacity Envelope – single run.
Run one matrix row (RUN 1..8). Called by run_capacity_envelope_tests.py with timeout.
Expects env: SPEC_ID, WORKSPACE_ID, RUN_NUMBER (1-8).
Writes JSON result to stdout (one line) for parent to capture.
"""
import os
import sys
import json
from pathlib import Path
from datetime import datetime, timezone

# Project root = parent of development/
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
os.chdir(REPO_ROOT)

# Load .streamlit/secrets.toml into os.environ so DB/OpenAI work without Streamlit
def _load_secrets_into_env():
    secrets_path = REPO_ROOT / ".streamlit" / "secrets.toml"
    if not secrets_path.exists():
        return
    data = None
    try:
        import tomllib
        with open(secrets_path, "rb") as f:
            data = tomllib.load(f)
    except ImportError:
        try:
            import toml
            with open(secrets_path, "r", encoding="utf-8") as f:
                data = toml.load(f)
        except Exception:
            pass
    if data:
        for k, v in (data.get("secrets") or {}).items():
            if isinstance(k, str) and k.isupper() and v is not None:
                os.environ.setdefault(k, str(v).strip())

_load_secrets_into_env()

# Fixed settings for all runs (CHARLIEC test plan)
INCLUDED_SECTIONS = [
    "Market Developments",
    "Technology and Innovation",
    "Capacity and Investment Activity",
    "Corporate Developments",
    "Sustainability and Circular Economy",
    "Strategic Implications",
]
MINIMUM_SIGNAL_STRENGTH = None
BUILDER_EMAIL = "stefan.hermes@htcglobal.asia"

# Test matrix: report_period_days, categories, regions, value_chain_links
MATRIX = [
    {"report_period_days": 7, "categories": ["industry_context", "regional_monitoring"], "regions": ["EMEA", "North America"], "value_chain_links": ["raw_materials"]},
    {"report_period_days": 30, "categories": ["industry_context", "regional_monitoring"], "regions": ["EMEA", "North America"], "value_chain_links": ["raw_materials"]},
    {"report_period_days": 60, "categories": ["industry_context", "regional_monitoring"], "regions": ["EMEA", "North America"], "value_chain_links": ["raw_materials"]},
    {"report_period_days": 120, "categories": ["industry_context", "regional_monitoring"], "regions": ["EMEA", "North America"], "value_chain_links": ["raw_materials"]},
    {"report_period_days": 30, "categories": ["capacity", "early_warning", "industry_context", "regional_monitoring", "value_chain_link"], "regions": ["China", "EMEA", "Middle East", "North America", "SEA"], "value_chain_links": ["raw_materials", "system_houses"]},
    {"report_period_days": 60, "categories": ["capacity", "early_warning", "industry_context", "regional_monitoring", "value_chain_link"], "regions": ["China", "EMEA", "Middle East", "North America", "SEA"], "value_chain_links": ["raw_materials", "system_houses"]},
    {"report_period_days": 60, "categories": ["capacity", "competitive", "early_warning", "executive_briefings", "industry_context", "m_and_a", "regional_monitoring", "sustainability", "value_chain", "value_chain_link"], "regions": ["China", "EMEA", "India", "Middle East", "NE Asia", "North America", "SEA", "South America"], "value_chain_links": ["raw_materials", "system_houses", "foam_converters", "end_use"]},
    {"report_period_days": 120, "categories": ["capacity", "competitive", "early_warning", "executive_briefings", "industry_context", "m_and_a", "regional_monitoring", "sustainability", "value_chain", "value_chain_link"], "regions": ["China", "EMEA", "India", "Middle East", "NE Asia", "North America", "SEA", "South America"], "value_chain_links": ["raw_materials", "system_houses", "foam_converters", "end_use"]},
    # Run 9 (ultra-relaxed + fixed classification)
    {"report_period_days": 120, "categories": ["capacity", "competitive", "early_warning", "executive_briefings", "industry_context", "m_and_a", "regional_monitoring", "sustainability", "value_chain", "value_chain_link"], "regions": ["China", "EMEA", "India", "Middle East", "NE Asia", "North America", "SEA", "South America"], "value_chain_links": ["raw_materials", "system_houses", "foam_converters", "end_use"]},
]


def _count_developments_in_report(report_content: str) -> int:
    """Count development blocks (### Title) in markdown report."""
    if not report_content:
        return 0
    return report_content.count("\n### ")


def main():
    run_number = int(os.environ.get("RUN_NUMBER", "1"))
    spec_id = os.environ.get("SPEC_ID", "").strip()
    workspace_id = os.environ.get("WORKSPACE_ID", "").strip()
    if not spec_id or not workspace_id:
        out = {"error": "SPEC_ID and WORKSPACE_ID must be set", "run_number": run_number}
        print(json.dumps(out))
        sys.exit(1)
    if run_number < 1 or run_number > 9:
        out = {"error": "RUN_NUMBER must be 1..9", "run_number": run_number}
        print(json.dumps(out))
        sys.exit(1)

    row = MATRIX[run_number - 1]
    start_ts = datetime.now(timezone.utc).isoformat()
    start_sec = datetime.now(timezone.utc).timestamp()

    result = {
        "run_number": run_number,
        "report_period_days": row["report_period_days"],
        "categories_count": len(row["categories"]),
        "regions_count": len(row["regions"]),
        "value_chain_links_count": len(row["value_chain_links"]),
        "start_timestamp": start_ts,
        "end_timestamp": None,
        "elapsed_seconds": None,
        "status": "failure",
        "run_id": None,
        "html_generated": "no",
        "audit_generated": "no",
        "developments_visible": 0,
        "signals_after_query_plan": None,
        "stage_2_after_date_filter": None,
        "signals_after_preinsert_validation": None,
        "stage_3_after_customer_scope_filter": None,
        "stage_4_after_section_mapping": None,
        "stage_5_clusters_formed": None,
        "stage_6_developments_extracted": None,
        "stage_8_developments_written_to_report": None,
        # Extra audit fields for run 9
        "validation_pass_rate": None,
        "mapping_pass_rate": None,
        "overall_yield": None,
        "category_distribution": None,
        "section_distribution": None,
        "mapped_signals_count": None,
        "last_completed_stage": None,
        "failure_mode": None,
        "error_message": None,
    }

    try:
        from core.generator_execution import execute_generator

        success, error_message, result_data, artifact_path = execute_generator(
            spec_id=spec_id,
            workspace_id=workspace_id,
            user_email=BUILDER_EMAIL,
            cadence_override="infinite",
            lookback_override=row["report_period_days"],
            categories_override=row["categories"],
            regions_override=row["regions"],
            value_chain_links_override=row["value_chain_links"],
        )
        end_ts = datetime.now(timezone.utc).isoformat()
        end_sec = datetime.now(timezone.utc).timestamp()
        result["end_timestamp"] = end_ts
        result["elapsed_seconds"] = round(end_sec - start_sec, 1)
        result["error_message"] = error_message

        if success and result_data:
            result["run_id"] = result_data.get("run_id")
            result["html_generated"] = "yes" if result_data.get("html_content") else "no"
            result["developments_visible"] = _count_developments_in_report(
                result_data.get("report_content") or ""
            )
            meta = result_data.get("metadata") or {}
            run_audit = meta.get("run_audit") or {}
            result["audit_generated"] = "yes" if run_audit else "no"
            if run_audit:
                steps = run_audit.get("steps") or {}
                result["signals_after_query_plan"] = steps.get("query_plan_candidates_count")
                result["stage_2_after_date_filter"] = steps.get("candidates_after_date_filter_count")
                result["signals_after_preinsert_validation"] = run_audit.get("signals_after_preinsert_validation") or steps.get("candidates_after_date_filter_count")
                result["stage_3_after_customer_scope_filter"] = steps.get("candidates_after_customer_filter_count")
                result["stage_4_after_section_mapping"] = steps.get("candidates_after_section_filter_count")
                result["stage_5_clusters_formed"] = steps.get("grouped_clusters_count")
                result["stage_6_developments_extracted"] = steps.get("extracted_developments_count")
                result["stage_8_developments_written_to_report"] = steps.get("developments_written_to_report_count")

                # New fields for CharlieC / Run 9 reporting
                result["validation_pass_rate"] = run_audit.get("validation_pass_rate")
                result["mapping_pass_rate"] = run_audit.get("mapping_pass_rate")
                result["overall_yield"] = run_audit.get("overall_yield")
                result["category_distribution"] = run_audit.get("category_distribution")
                result["section_distribution"] = run_audit.get("mapping_success_by_section")
                result["mapped_signals_count"] = run_audit.get("mapping_attempts_total")
            result["status"] = "success" if success else "failure"
        else:
            result["status"] = "failure"
            result["last_completed_stage"] = "unknown"
            result["failure_mode"] = "unknown"
    except Exception as e:
        result["end_timestamp"] = datetime.now(timezone.utc).isoformat()
        result["elapsed_seconds"] = round(datetime.now(timezone.utc).timestamp() - start_sec, 1)
        result["error_message"] = str(e)[:500]
        result["status"] = "failure"
        result["failure_mode"] = "unknown"
        result["last_completed_stage"] = "unknown"

    print(json.dumps(result))
    sys.exit(0 if result["status"] == "success" else 1)


if __name__ == "__main__":
    main()
