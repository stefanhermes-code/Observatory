"""
Phase 3 review – seed 20 synthetic candidate_articles for a single test run.
Use test namespace only: create one run, insert 20 candidates, print run_id for exports.
Requires: SUPABASE_URL, SUPABASE_ANON_KEY in env or .env. Optional: WORKSPACE_ID, SPEC_ID for an existing test spec.
"""
import os
import sys
from datetime import datetime, timezone

# Add project root so core can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

def main():
    from core.generator_db import get_supabase_client, create_newsletter_run, insert_candidate_articles

    workspace_id = os.getenv("WORKSPACE_ID") or os.getenv("PHASE3_WORKSPACE_ID")
    spec_id = os.getenv("SPEC_ID") or os.getenv("PHASE3_SPEC_ID")
    if not workspace_id or not spec_id:
        # Try to read first active spec from DB
        supabase = get_supabase_client()
        spec_row = supabase.table("newsletter_specifications").select("id, workspace_id").eq("status", "active").limit(1).execute()
        if spec_row.data and len(spec_row.data) > 0:
            spec_id = spec_row.data[0]["id"]
            workspace_id = spec_row.data[0]["workspace_id"]
        else:
            print("Set WORKSPACE_ID and SPEC_ID (or PHASE3_*) for a test spec, or ensure one active spec exists.")
            sys.exit(1)

    user_email = os.getenv("PHASE3_USER_EMAIL", "phase3_review@test.local")
    run = create_newsletter_run(
        spec_id=spec_id,
        workspace_id=workspace_id,
        user_email=user_email,
        status="running",
        frequency="monthly",
    )
    run_id = run.get("id")
    if not run_id:
        print("Failed to create run.")
        sys.exit(1)

    # Phase 3 stress-test seed: 20 differentiated articles (Groups A–E). R1–R5, N1–N5.
    base_ts = datetime.now(timezone.utc).isoformat()
    candidates = [
        # Group A: Capacity (8). A1–A3 same event (cluster test).
        {"url": "https://example.com/phase3-stress-a1", "canonical_url": "https://example.com/phase3-stress-a1",
         "title": "BASF to add MDI capacity in China", "snippet": "BASF announced expansion of MDI capacity in China. The company will add +300,000 TPA MDI capacity at its site. Raw materials segment.", "published_at": base_ts, "source_name": "phase3_synthetic", "query_id": "phase3_a1", "validation_status": "not_checked", "category": "market_intel", "region": "APAC", "value_chain_link": "production"},
        {"url": "https://example.com/phase3-stress-a2", "canonical_url": "https://example.com/phase3-stress-a2",
         "title": "BASF China MDI expansion confirmed", "snippet": "In China, BASF confirmed a new MDI line. Capacity increase of +300,000 TPA MDI. Raw materials (MDI).", "published_at": base_ts, "source_name": "phase3_synthetic", "query_id": "phase3_a2", "validation_status": "not_checked", "category": "market_intel", "region": "APAC", "value_chain_link": "production"},
        {"url": "https://example.com/phase3-stress-a3", "canonical_url": "https://example.com/phase3-stress-a3",
         "title": "BASF ups MDI capacity in China by 300,000 TPA", "snippet": "BASF in China: +300,000 TPA MDI capacity expansion. Raw materials segment.", "published_at": base_ts, "source_name": "phase3_synthetic", "query_id": "phase3_a3", "validation_status": "not_checked", "category": "market_intel", "region": "APAC", "value_chain_link": "production"},
        {"url": "https://example.com/phase3-stress-a4", "canonical_url": "https://example.com/phase3-stress-a4",
         "title": "Covestro Germany TDI capacity up 6%", "snippet": "Covestro in Germany reported TDI capacity increased by 6%. Raw materials (TDI).", "published_at": base_ts, "source_name": "phase3_synthetic", "query_id": "phase3_a4", "validation_status": "not_checked", "category": "market_intel", "region": "EMEA", "value_chain_link": "production"},
        {"url": "https://example.com/phase3-stress-a5", "canonical_url": "https://example.com/phase3-stress-a5",
         "title": "Wanhua adds 25,000 TPA MDI in China", "snippet": "Wanhua in China: +25,000 TPA MDI capacity. Raw materials (MDI).", "published_at": base_ts, "source_name": "phase3_synthetic", "query_id": "phase3_a5", "validation_status": "not_checked", "category": "market_intel", "region": "APAC", "value_chain_link": "production"},
        {"url": "https://example.com/phase3-stress-a6", "canonical_url": "https://example.com/phase3-stress-a6",
         "title": "Dow USA polyol unit permanent closure", "snippet": "Dow in the USA announced permanent closure of 30,000 TPA polyol unit. Raw materials (polyols).", "published_at": base_ts, "source_name": "phase3_synthetic", "query_id": "phase3_a6", "validation_status": "not_checked", "category": "market_intel", "region": "Americas", "value_chain_link": "production"},
        {"url": "https://example.com/phase3-stress-a7", "canonical_url": "https://example.com/phase3-stress-a7",
         "title": "Huntsman Netherlands MDI capacity reduced 7%", "snippet": "Huntsman in the Netherlands: MDI capacity reduced by 7%. Raw materials (MDI).", "published_at": base_ts, "source_name": "phase3_synthetic", "query_id": "phase3_a7", "validation_status": "not_checked", "category": "market_intel", "region": "EMEA", "value_chain_link": "production"},
        {"url": "https://example.com/phase3-stress-a8", "canonical_url": "https://example.com/phase3-stress-a8",
         "title": "Regional Foam Thailand polyol debottlenecking", "snippet": "Regional Foam Chemicals Ltd in Thailand: debottlenecking +5,000 TPA polyol. Raw materials (polyol).", "published_at": base_ts, "source_name": "phase3_synthetic", "query_id": "phase3_a8", "validation_status": "not_checked", "category": "market_intel", "region": "APAC", "value_chain_link": "production"},
        # Group B: Regulatory (4).
        {"url": "https://example.com/phase3-stress-b1", "canonical_url": "https://example.com/phase3-stress-b1",
         "title": "Belgium diisocyanate training requirement", "snippet": "In Belgium, mandatory worker training for diisocyanates will apply. Mixed segment.", "published_at": base_ts, "source_name": "phase3_synthetic", "query_id": "phase3_b1", "validation_status": "not_checked", "category": "market_intel", "region": "EMEA", "value_chain_link": "production"},
        {"url": "https://example.com/phase3-stress-b2", "canonical_url": "https://example.com/phase3-stress-b2",
         "title": "China HCFC-141b restriction rigid foam", "snippet": "China: restriction on HCFC-141b use in rigid foam effective from next year. Rigid foam segment.", "published_at": base_ts, "source_name": "phase3_synthetic", "query_id": "phase3_b2", "validation_status": "not_checked", "category": "market_intel", "region": "APAC", "value_chain_link": "production"},
        {"url": "https://example.com/phase3-stress-b3", "canonical_url": "https://example.com/phase3-stress-b3",
         "title": "Germany VOC emission limits foam manufacturing", "snippet": "Germany: new VOC emission limits for foam manufacturing lines. Flexible foam segment.", "published_at": base_ts, "source_name": "phase3_synthetic", "query_id": "phase3_b3", "validation_status": "not_checked", "category": "market_intel", "region": "EMEA", "value_chain_link": "production"},
        {"url": "https://example.com/phase3-stress-b4", "canonical_url": "https://example.com/phase3-stress-b4",
         "title": "USA hazard classification update impacts CASE", "snippet": "USA: updated hazard classification impacts labeling and handling requirements. CASE segment.", "published_at": base_ts, "source_name": "phase3_synthetic", "query_id": "phase3_b4", "validation_status": "not_checked", "category": "market_intel", "region": "Americas", "value_chain_link": "production"},
        # Group C: Tactical / operational (4).
        {"url": "https://example.com/phase3-stress-c1", "canonical_url": "https://example.com/phase3-stress-c1",
         "title": "Covestro Spain planned maintenance shutdown", "snippet": "Covestro in Spain: planned maintenance shutdown for 10 days. Raw materials. No capacity change.", "published_at": base_ts, "source_name": "phase3_synthetic", "query_id": "phase3_c1", "validation_status": "not_checked", "category": "market_intel", "region": "EMEA", "value_chain_link": "production"},
        {"url": "https://example.com/phase3-stress-c2", "canonical_url": "https://example.com/phase3-stress-c2",
         "title": "BASF France temporary halt utility outage", "snippet": "BASF in France: temporary halt at flexible foam site due to utility outage, restart expected within 72 hours. Flexible foam.", "published_at": base_ts, "source_name": "phase3_synthetic", "query_id": "phase3_c2", "validation_status": "not_checked", "category": "market_intel", "region": "EMEA", "value_chain_link": "production"},
        {"url": "https://example.com/phase3-stress-c3", "canonical_url": "https://example.com/phase3-stress-c3",
         "title": "Foam Systems Malaysia port congestion delays", "snippet": "Foam Systems Co. in Malaysia: port congestion delays shipments by 2 weeks. Flexible foam.", "published_at": base_ts, "source_name": "phase3_synthetic", "query_id": "phase3_c3", "validation_status": "not_checked", "category": "market_intel", "region": "APAC", "value_chain_link": "production"},
        {"url": "https://example.com/phase3-stress-c4", "canonical_url": "https://example.com/phase3-stress-c4",
         "title": "Covestro China new TPU grade automotive", "snippet": "Covestro in China launched new TPU grade for automotive interior applications. TPU segment. No capacity or capex.", "published_at": base_ts, "source_name": "phase3_synthetic", "query_id": "phase3_c4", "validation_status": "not_checked", "category": "market_intel", "region": "APAC", "value_chain_link": "production"},
        # Group D: Cyclical demand and price (2).
        {"url": "https://example.com/phase3-stress-d1", "canonical_url": "https://example.com/phase3-stress-d1",
         "title": "Germany automotive seating demand down YoY", "snippet": "Germany: automotive build volumes down 8% YoY impacting seating demand. Flexible foam (automotive seating). No capacity, no investment.", "published_at": base_ts, "source_name": "phase3_synthetic", "query_id": "phase3_d1", "validation_status": "not_checked", "category": "market_intel", "region": "EMEA", "value_chain_link": "production"},
        {"url": "https://example.com/phase3-stress-d2", "canonical_url": "https://example.com/phase3-stress-d2",
         "title": "China MDI spot price up month-on-month", "snippet": "China: MDI spot price up 6% month-on-month. Raw materials (MDI). No capacity, no investment.", "published_at": base_ts, "source_name": "phase3_synthetic", "query_id": "phase3_d2", "validation_status": "not_checked", "category": "market_intel", "region": "APAC", "value_chain_link": "production"},
        # Group E: Noise (2). No numbers; avoid capacity/demand/regulation/investment.
        {"url": "https://example.com/phase3-stress-e1", "canonical_url": "https://example.com/phase3-stress-e1",
         "title": "PU industry conference announced Dubai", "snippet": "In the UAE, a PU industry conference has been announced in Dubai.", "published_at": base_ts, "source_name": "phase3_synthetic", "query_id": "phase3_e1", "validation_status": "not_checked", "category": "market_intel", "region": "EMEA", "value_chain_link": "production"},
        {"url": "https://example.com/phase3-stress-e2", "canonical_url": "https://example.com/phase3-stress-e2",
         "title": "New CEO appointed at XYZ Foam USA", "snippet": "In the USA, new CEO appointed at XYZ Foam.", "published_at": base_ts, "source_name": "phase3_synthetic", "query_id": "phase3_e2", "validation_status": "not_checked", "category": "market_intel", "region": "Americas", "value_chain_link": "production"},
    ]

    inserted = insert_candidate_articles(run_id=run_id, workspace_id=workspace_id, specification_id=spec_id, candidates=candidates)
    print(f"run_id={run_id}")
    print(f"candidates_inserted={inserted}")
    print("Use this run_id for export scripts and the single full trace.")

if __name__ == "__main__":
    main()
