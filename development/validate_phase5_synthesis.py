"""
Phase 5 validation: run Market Intelligence Synthesis for GLOBAL, REGION (APAC), REGION+SEGMENT (APAC raw_materials)
and print example reports. Confirm: 5 sections, 2–4 sentences per section, quantitative baseline when applicable.

Usage (from repo root):
  python -m development.validate_phase5_synthesis [run_id]
  If run_id omitted, uses latest generator run.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_latest_run_id():
    from core.generator_db import get_supabase_client
    supabase = get_supabase_client()
    r = supabase.table("newsletter_runs").select("id").limit(1).order("created_at", desc=True).execute()
    return (r.data or [{}])[0].get("id") if r.data else None

def main():
    run_id = (sys.argv[1:] or [None])[0]
    if not run_id:
        run_id = get_latest_run_id()
    if not run_id:
        print("No run_id provided and no newsletter run found. Exiting.")
        return 1
    print(f"Run ID: {run_id}\n")
    from core.market_intelligence_synthesis import (
        run_market_intelligence_synthesis,
        SCOPE_GLOBAL,
        SCOPE_REGION,
        SCOPE_REGION_SEGMENT,
    )
    for label, scope, region_macro, segment in [
        ("=== GLOBAL ===", SCOPE_GLOBAL, None, None),
        ("=== REGION (APAC) ===", SCOPE_REGION, "APAC", None),
        ("=== REGION + SEGMENT (APAC raw_materials) ===", SCOPE_REGION_SEGMENT, "APAC", "raw_materials"),
    ]:
        print(label)
        text, usage = run_market_intelligence_synthesis(run_id, scope=scope, region_macro=region_macro, segment=segment)
        if usage:
            print(f"[Tokens: in={usage.get('input_tokens')} out={usage.get('output_tokens')}]")
        if text:
            print(text)
        else:
            print("(No synthesis output)")
        print()
    return 0

if __name__ == "__main__":
    sys.exit(main())
