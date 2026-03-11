# PU Observatory – Live Data Model (Chosen Design)

Per **PU_Observatory_Live_Application_Alignment_Plan_Final_For_CharlieC.txt** §6, this document records the **chosen live design** for the master signal dataset and query intent metadata.

---

## Decision: Run-scoped master view + in-memory query map

The plan allows either:
- **Option A:** Keep run-scoped master view + in-memory query map; document as the chosen live design.
- **Option B:** Add global persistent master table and persisted query_metadata table.

**Chosen:** **Option A** for the current live system. This satisfies the behavioural requirements (filter by customer spec before clustering, strict filter, Phase 5 report from a “master” view with query intent) without a schema change. Option B remains available for a future phase if a single global master dataset across runs is required.

---

## 6.1 Master signal dataset (live)

- **Source of truth per run:** `candidate_articles` for that run (`run_id`).
- **Canonical view:** `get_master_signals_for_run(run_id)` returns a list of dicts with:
  - `signal_id`, `title`, `url`, `date`, `source`, `query_id`
  - `category` (configurator category from harvest)
  - `classifier_category` (when available from classification; else report layer uses fallback)
  - `region`, `value_chain_link` (from query plan at ingest)
  - `tier` (reserved)
- **Persistence:** Rows are persisted in `candidate_articles` by the evidence engine when the run is executed. No separate “master_signals” table; the master dataset for a run is the run’s `candidate_articles` with the canonical field set produced by `get_master_signals_for_run`.

---

## 6.2 Query intent metadata (live)

- **Source:** In-memory map built from the **customer specification** for the run.
- **Implementation:** `build_query_plan_map(run_specification)` in `core/query_planner.py` returns `query_id → { region, configurator_category, value_chain_link }`. The same spec used for the run is used to build this map, so query intent is consistent with the harvest.
- **Persistence:** No dedicated `query_metadata` table. Query plan is deterministic from spec (regions, categories, value_chain_links, company_aliases); rebuilding from spec at report time is the single source of truth.

---

## 6.3 Backward compatibility

- Legacy report path (non–Phase 5) remains available and is controlled by the `USE_PHASE5_REPORT` flag and/or per-spec `use_phase5_report`. Phase 5 path uses the run-scoped master view and in-memory query map above. Legacy path does not rely on a separate persisted master table.

---

*Document created: 2026-02-08. Plan reference: §6.*
