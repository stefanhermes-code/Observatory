# PU Observatory Live Alignment – Plan Overview

**Source:** PU_Observatory_Live_Application_Alignment_Plan_Final_For_CharlieC.txt  
**Purpose:** Single overview of where we are vs the plan and what to do next.

---

## Plan section → Status

| § | Section | Status | Notes |
|---|---------|--------|--------|
| **1** | Target outcome | ✅ Done | Configurator → Admin → activation → Generator with filtered spec, Phase 5 report, signal map, evidence appendix. company_signal_tracking_enabled in spec for future. |
| **2** | Non‑negotiable principles | ✅ Done | A–G respected: SaaS flow intact, dev logic in live, filter before cluster, strict filter, in-memory path, content-based report, feature flag. |
| **3** | Scope (9 items) | ✅ Done | Master view, query map, customer filter, Phase 5, signal map, evidence appendix, Configurator fields, Admin persistence, safe switch all addressed. |
| **4** | What must not change | ✅ Done | Commercial flow, harvesting/classification scope, observatory model unchanged. |
| **5** | Live architecture | ✅ Done | Customer report path: load spec → load master view → query map → filter → cluster filtered → developments → report + map + appendix. |
| **6** | Data model | ✅ Done | **Chosen design (Option A):** Run-scoped master via `get_master_signals_for_run`; in-memory query map via `build_query_plan_map(spec)`. Documented in docs/DATA_MODEL_LIVE_DESIGN.md. No global persistent master/query_metadata table; design accepted for live. |
| **7** | Customer filter | ✅ Done | Strict: unset metadata does not pass when dimension constrained. `filter_signals_by_spec` / `filter_candidates_by_spec` / `apply_customer_filter` aligned. |
| **8** | Clustering / development extraction | ✅ Done | `group_signals(filtered_signals)`; development extraction and signal strength on filtered set only. |
| **9** | Classifier category source | ✅ Done | Phase 5 prefers `s.get("classifier_category")` when present; falls back to CONFIGURATOR_TO_CLASSIFIER. Ready for per-candidate classifier_category from Phase 2e/classification when available. |
| **10** | Phase 5 reporting | ✅ Done | Developments, evidence, strength (Weak/Moderate/Strong), Business Relevance, Direction of Impact, report sections, evidence appendix, signal map in live path when USE_PHASE5_REPORT. |
| **11** | Signal map | ✅ Done | Table by section/share **and** pie chart in HTML report (`_signal_map_pie_svg`, placeholder `<!-- SIGNAL_MAP_PIE -->` injected in markdown_to_simple_html). |
| **12** | Evidence appendix | ✅ Done | “Appendix A — Evidence Signals” with development title, signal title, source, URL, date, mapped category; no internal notes. |
| **13** | Configurator app | ✅ Done | report_period_days (numeric canonical, default 30), report_title, included_sections, signal_map_enabled, evidence_appendix_enabled, minimum_signal_strength_in_report, company_signal_tracking_enabled in spec and report_options on submit. Text report_period is deprecated and no longer used in logic. |
| **14** | Admin app | ✅ Done | Edit Specification shows numeric report_period_days as a derived label (e.g. `30-day window`) and supports report_title, included_sections, signal_map_enabled, evidence_appendix_enabled, minimum_signal_strength_in_report, company_signal_tracking_enabled; `update_specification(..., report_options=...)` persists report_period_days. |
| **15** | One source of truth | ✅ Done | `core/report_spec.py` DEFAULT_REPORT_SPEC; Configurator and get_specification_detail use it; no duplicated defaults. |
| **16** | Live integration approach | ✅ Done | In-memory path; no temp files as default for live report generation. |
| **17** | Live switching strategy | ✅ Done | Feature flag USE_PHASE5_REPORT (env + Streamlit secrets) and spec.use_phase5_report; legacy path when off; Generator UI shows active path. |
| **18** | Preparation for Phase 6 | ✅ Done | company_signal_tracking_enabled in spec and passed through; architecture ready to plug company layer after development extraction. |
| **19** | Validation checks A–N | ✅ Done | All 14 checks satisfied; see PU_OBSERVATORY_LIVE_ALIGNMENT_PACK/VALIDATION_CHECKLIST_S19.md. |
| **20** | Deliverables | ✅ Done | PU_OBSERVATORY_LIVE_ALIGNMENT_PACK.zip with code summary, file list, execution path, legacy path, validation note, temporary fallbacks; example report/signal map/appendix referenced (Live Results). |
| **21** | Completion standard | ✅ Met | Live has Phase 5, filter-before-cluster, strict filter, signal map and appendix, aligned spec/defaults, ready for go-live validation. |

---

## Summary

- **Fully done:** §§1–21 (all plan sections). Target outcome, principles, scope, architecture, data model (documented run-scoped choice), filter, clustering, classifier category wiring, Phase 5, signal map table + pie, appendix, Configurator, Admin report options (including report_period), one source of truth, integration, switching, Phase 6 prep, validation, deliverables, completion standard.
- **Optional follow-ups (not blocking go-live):**
  - **§9** – When Phase 2e/classification outputs per-candidate `classifier_category`, Phase 5 will use it automatically; no code change needed.
  - **§6** – If you later want a global persistent master table or query_metadata store, that would be a new design iteration; current run-scoped design is documented in docs/DATA_MODEL_LIVE_DESIGN.md.

---

## What to do next (prioritised)

1. **Go-live**
   - Set USE_PHASE5_REPORT=true (or use_phase5_report on specs) where Phase 5 should be the default.
   - Run through a full Configurator → Admin → Generator flow and confirm report, signal map (table + pie), and Appendix A.
   - When satisfied, treat Phase 5 as the standard live path and document the default in runbooks.

2. **Optional later**
   - Populate per-candidate classifier_category from Phase 2e/classification when that pipeline is in place (Phase 5 already consumes it when present).
   - If desired: add global persistent master/query_metadata tables and document in docs/DATA_MODEL_LIVE_DESIGN.md as an evolution.

---

## Key files (reference)

| Role | Files |
|------|--------|
| Plan / status | development/PU_Observatory_Live_Application_Alignment_Plan_Final_For_CharlieC.txt, PU_OBSERVATORY_LIVE_ALIGNMENT_STATUS.md, this file |
| Deliverables | PU_OBSERVATORY_LIVE_ALIGNMENT_PACK.zip, PU_OBSERVATORY_LIVE_ALIGNMENT_PACK/VALIDATION_CHECKLIST_S19.md, README_IMPLEMENTATION_PACKAGE.md |
| One source of truth | core/report_spec.py |
| Live report path | core/generator_execution.py, core/intelligence_report.py, core/customer_filter.py |
| Data model (live design) | docs/DATA_MODEL_LIVE_DESIGN.md |
| Spec / report options | configurator_app.py (report_options), admin_app.py (Edit Specification report_period + report options), core/admin_db.py (update_specification), core/generator_db.py (get_specification_detail) |

---

## Report-period normalization (canonical `report_period_days`)

Runtime date filtering is driven **exclusively** by the canonical value **`report_period_days`**. No low-level date-window logic depends on cadence, lookback_override, legacy text fields, or fallback logic except for backward-compatible migration before the value is persisted.

### Low-level functions

| Module | Change |
|--------|--------|
| **core/run_dates.py** | **`get_lookback_from_days(report_period_days, reference_date)`** is the sole function used for date-window computation. **`get_lookback_from_cadence`** is deprecated (migration/backward-compat only, not used in live path). |
| **core/evidence_engine.py** | **`run_evidence_engine(..., report_period_days=...)`**; internally uses **`get_lookback_from_days(effective_days, ref_date)`** only. Migration fallback: if `report_period_days` is None/≤0, uses `get_lookback_days(spec.frequency)` to obtain effective_days, then `get_lookback_from_days(effective_days, ref_date)`. |

### Callers

| Caller | Change |
|--------|--------|
| **core/generator_execution.py** | **`execute_generator`**: sets **`run_specification["report_period_days"]`** once (builder override or spec value or `get_lookback_days(frequency)`); passes **`report_period_days=run_specification["report_period_days"]`** to **`run_evidence_engine`**; uses **`get_lookback_from_days(run_specification["report_period_days"], ref_date)`** only in **`run_phase_extract_and_write`** (no `get_lookback_from_cadence`). **`run_phase_evidence`**: resolves and sets **`run_specification["report_period_days"]`** before calling **`run_evidence_engine`**. |
| **generator_app.py** | Before Phase 1, sets **`run_spec["report_period_days"]`** from spec or **`get_lookback_days(spec.frequency)`**, with builder **lookback_override** applied when allowed. Phases then use **run_spec["report_period_days"]** only. |
| **core/content_pipeline.py** | When **lookback_date** / **reference_date** are missing, resolves **report_period_days** from **spec** (**spec.get("report_period_days")** or **get_lookback_days(spec.frequency)**) and calls **`get_lookback_from_days(report_period_days, ref_date)`** only (no **get_lookback_from_cadence**). |

### Confirmation

- **Runtime date filtering is driven exclusively by `report_period_days`.**
- All date-window computation goes through **`get_lookback_from_days(report_period_days, reference_date)`**.
- Cadence, lookback_override, and legacy text fields are not inputs to low-level date logic; they are only used at the caller layer to *derive* or *override* the single value **`report_period_days`** before it is passed in.

---

*Last updated: 2026-02-08 (after §6 doc, §9 classifier_category, §11 pie chart, §14 Admin report_period; report-period normalization completed)*
