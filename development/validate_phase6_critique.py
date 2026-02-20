"""
Phase 6 validation: run synthesis → critique, print critique JSON.
Optionally test requires_revision path by passing --force-revision (feeds a weak draft to critique).
Usage (from repo root):
  python -m development.validate_phase6_critique [run_id]
  python -m development.validate_phase6_critique [run_id] --force-revision
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_latest_run_id():
    from core.generator_db import get_supabase_client
    supabase = get_supabase_client()
    r = supabase.table("newsletter_runs").select("id").limit(1).order("created_at", desc=True).execute()
    return (r.data or [{}])[0].get("id") if r.data else None


def main():
    run_id = None
    force_revision = "--force-revision" in sys.argv
    for a in sys.argv[1:]:
        if a != "--force-revision" and not a.startswith("-"):
            run_id = a
            break
    if not run_id:
        run_id = get_latest_run_id()
    if not run_id:
        print("No run_id and no newsletter run found.")
        return 1

    from core.market_intelligence_synthesis import run_market_intelligence_synthesis, SCOPE_GLOBAL
    from core.adversarial_critique import run_critique

    print(f"Run ID: {run_id}\n")

    if force_revision:
        print("=== Force revision test: weak draft -> critique (expect requires_revision=true) ===\n")
        weak_draft = (
            "Structural movements are significant across the industry. "
            "Cyclical pressures remain strong. Regulation is evolving. "
            "Competition is intense. Risks are elevated. "
            "The outlook is promising for key players."
        )
        result, usage = run_critique(weak_draft)
        if result:
            print("Critique JSON:")
            print(json.dumps(result, indent=2))
            print("\nrequires_revision:", result.get("requires_revision"))
        else:
            print("Critique failed.")
        return 0

    print("=== Synthesis (GLOBAL) ===\n")
    synthesis_text, _ = run_market_intelligence_synthesis(run_id=run_id, scope=SCOPE_GLOBAL)
    if not synthesis_text:
        print("No synthesis output.")
        return 1
    print(synthesis_text[:1200] + ("..." if len(synthesis_text) > 1200 else ""))
    print("\n=== Critique result ===\n")
    result, usage = run_critique(synthesis_text)
    if result:
        print("Critique JSON:")
        print(json.dumps(result, indent=2))
        if usage:
            print("\nUsage:", usage)
    else:
        print("Critique failed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
