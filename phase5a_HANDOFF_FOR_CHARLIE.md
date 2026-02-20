# Phase 5A – Handoff for Charlie

## Status: Phase 5A implementation complete

- Curated seed CSV exists and has been ingested.
- Migration 013 applied; table `structural_baseline_events` exists.
- Ingestion run: **28 rows** in DB (from 41 CSV rows after deduplication).
- Verification export and summary counts have been generated.

---

## For Charlie / Stefan review

1. **Review the dataset**
   - Open `phase5a_verification/verify_structural_baseline_events.csv` (or re-run `python export_structural_baseline_verification.py` for fresh counts).
   - Check summary: by year (2020–2024), region_macro, segment, signal_type.
   - Spot-check: 5 sample rows per signal_type (capacity, mna, regulation, technology, investment) – see script console output or sample from the CSV.

2. **Decide**
   - Is the curated seed acceptable for use as the structural baseline (2020–2024)?
   - Any edits to the seed CSV? If yes → change `curated_structural_seed_2020_2024.csv`, then re-run ingestion (consider clearing the table or using an idempotent re-ingest strategy if we add one).

3. **Approve**
   - **Stefan approval** of the dataset is the gate before starting Phase 5B (per instruction stop rule).

---

## Next: Phase 5B (after approval)

Once Phase 5A is approved:

- **Phase 5B** = build **annual baseline tables** from `structural_baseline_events` (deterministic aggregation by year, region, segment, signal_type, etc., as per Charlie’s Phase 5B spec).
- Do **not** start Phase 5B until Stefan has approved the Phase 5A dataset.

---

## Quick reference

| What | Where |
|------|--------|
| Seed CSV | `curated_structural_seed_2020_2024.csv` |
| Ingest | `python ingest_curated_seed.py` |
| Export verification | `python export_structural_baseline_verification.py` |
| Verification CSV | `phase5a_verification/verify_structural_baseline_events.csv` |
| Evidence pack | `phase5a_evidence_pack.md` |
