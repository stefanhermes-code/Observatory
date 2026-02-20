# Phase 5A – Evidence pack (curated structural seed 2020–2024)

## Deliverables

| Item | Location |
|------|----------|
| **D1** Curated seed CSV | `curated_structural_seed_2020_2024.csv` |
| **D2** Ingestion script | `ingest_curated_seed.py` |
| **D3** DB migration | `development/migrations/013_structural_baseline_events.sql` |
| **D4** Verification export script | `export_structural_baseline_verification.py` |
| Verify migration | `development/migrations/verify_013_structural_baseline_events.sql` |

## Execution order

1. **Apply migration 013** in Supabase SQL Editor (create table `structural_baseline_events`).
2. **Verify table**: run `verify_013_structural_baseline_events.sql` in Supabase; all checks should return `true`.
3. **Ingest seed**: from repo root run  
   `python ingest_curated_seed.py`  
   (Use `python ingest_curated_seed.py --dry-run` to validate CSV only.)
4. **Export verification**: run  
   `python export_structural_baseline_verification.py`  
   Output: `phase5a_verification/verify_structural_baseline_events.csv` and summary counts + 5 sample rows per `signal_type` in console.

## Evidence (after ingestion)

- **Verification CSV**: `phase5a_verification/verify_structural_baseline_events.csv`  
  Columns: event_date, year, company_name, region_macro, country, segment, signal_type, numeric_value, numeric_unit, description.
- **Summary counts**: printed by the export script:
  - count by year
  - count by region_macro
  - count by segment
  - count by signal_type
- **5 sample rows per signal_type**: printed by the export script for spot check.

## Notes

- Seed CSV has 41 rows; after in-file deduplication the ingestion script inserts **28 rows** (duplicates by company_name, event_date ±7d, signal_type, country/region_macro, numeric_value are skipped).
- Do not start Phase 5B until Phase 5A is complete, verification export and summary counts are provided, and Stefan review approves the dataset.
- Exported run artifacts (e.g. `phase5a_verification/`) are not committed unless explicitly requested as fixtures.
