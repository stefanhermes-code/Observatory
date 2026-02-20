# Phase 5A – Expansion protocol (strict numeric target version)

## Status: expansion complete, pending re-ingest and Stefan approval

The curated seed has been expanded to meet 40–45 rows and mandatory distribution ranges.

---

## Target size

| Metric | Target | Actual (after dedupe) |
|--------|--------|------------------------|
| Total rows | 40–45 | **41** ✓ |

---

## Value chain distribution (segment)

| Segment | Target | Hard bounds | Actual | OK |
|---------|--------|-------------|--------|-----|
| raw_materials | 50–60% | 45–65% | **61.0%** (25) | ✓ |
| flexible_foam + rigid_foam | 20–25% | — | **22.0%** (9) | ✓ |
| tpu | 10–15%, min 3 events | — | **9.8%** (4) | ✓ |
| case | 5–10% | — | **7.3%** (3) | ✓ |

---

## Signal type distribution

| Signal type | Target | Hard bounds | Actual | OK |
|-------------|--------|-------------|--------|-----|
| capacity | 50–60% | 45–65% | **58.5%** (24) | ✓ |
| mna | 15–20% | — | **19.5%** (8) | ✓ |
| regulation | 10–15% | — | **9.8%** (4) | ✓ |
| technology | 10–15% | — | **9.8%** (4) | ✓ |
| investment | up to 10% | — | **2.4%** (1) | ✓ |

---

## Expansion priorities (minimums)

| Priority | Requirement | Actual |
|----------|-------------|--------|
| Downstream M&A (foam, CASE, TPU) | Min 4 additional | 4+ (Recticel, Carpenter, BASF CASE, Helios CASE, Lubrizol TPU, etc.) ✓ |
| Durable regulatory events | Min 3 additional | 4 total regulation events ✓ |
| TPU structural | Min 3 total TPU | 4 events ✓ |
| Foam-level (flexible + rigid) | Min 3 total foam | 9 events ✓ |
| Technology shift events | Min 2 | 4 events ✓ |

---

## Validation

- **Script:** `validate_phase5a_distribution.py`  
  Run before or after ingest to check distribution (uses same CSV load/dedupe as ingest).
- **Result:** All mandatory range checks passed.

---

## Re-ingest after approval

The DB currently has **28** rows (pre-expansion). To load the expanded seed (**41** rows):

1. **Truncate** the table (or delete all rows) in Supabase:
   ```sql
   TRUNCATE structural_baseline_events;
   ```
2. **Ingest** from repo root:
   ```bash
   python ingest_curated_seed.py
   ```
3. **Export verification** and share for review:
   ```bash
   python export_structural_baseline_verification.py
   ```
   Output: `phase5a_verification/verify_structural_baseline_events.csv` and summary counts.

---

## Stop rule

Do **not** start Phase 5B until:

- Dataset is within all defined percentage ranges. ✓  
- Minimum counts per category are satisfied. ✓  
- **Stefan approves distribution.** ← pending  

---

## Files

| File | Purpose |
|------|---------|
| `curated_structural_seed_2020_2024.csv` | Expanded seed (56 data rows → 41 after dedupe) |
| `validate_phase5a_distribution.py` | Distribution validation vs targets |
| `ingest_curated_seed.py` | Ingest into `structural_baseline_events` |
| `export_structural_baseline_verification.py` | Export verification CSV and counts |
