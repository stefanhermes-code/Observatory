# PU Observatory Live Alignment – Validation Checklist (§19)

Per **PU_Observatory_Live_Application_Alignment_Plan_Final_For_CharlieC.txt**, section 19.

| Check | Requirement | Status | Notes |
|-------|--------------|--------|--------|
| **A** | Live master signal dataset exists and includes query_id | ✅ | `get_master_signals_for_run(run_id)` returns run-scoped signals with signal_id, title, url, date, source, query_id, category, region, value_chain_link. |
| **B** | Live query metadata exists and maps query_id to region / category / value chain | ✅ | `build_query_plan_map(run_specification)` builds query_id → {region, configurator_category, value_chain_link}. |
| **C** | Live customer filtering occurs before clustering | ✅ | In phased flow: `filter_candidates_by_spec` before extraction; in Phase 5 report: `filter_signals_by_spec` then `group_signals(filtered)`. |
| **D** | Unset metadata does not pass constrained filters by default | ✅ | `filter_signals_by_spec` and `filter_candidates_by_spec` use strict rule; `apply_customer_filter` in intelligence_report aligned to strict. |
| **E** | Clustering uses filtered signals only | ✅ | Phase 5: `group_signals(filtered)`; extraction phase uses filtered candidates when filter_candidates_by_spec is applied. |
| **F** | Report path uses the approved Phase 5 logic | ✅ | When USE_PHASE5_REPORT (env/secrets) or spec.use_phase5_report: `generate_report_from_signals` with developments, signal strength, Business Relevance, Direction of Impact, Signal Map, Appendix A. |
| **G** | Signal map appears in the live report | ✅ | `render_report(..., signal_map_enabled=True)`; spec can set signal_map_enabled. |
| **H** | Evidence appendix appears in the live report | ✅ | `render_report(..., evidence_appendix_enabled=True)`; Appendix A — Evidence Signals per development. |
| **I** | No internal system leakage in customer-facing report | ✅ | Phase 5 report is content-based; no pipeline/classifier labels in customer output. |
| **J** | Configurator fields persist correctly into the customer spec | ✅ | report_period, report_title, included_sections, signal_map_enabled, evidence_appendix_enabled, minimum_signal_strength_in_report, company_signal_tracking_enabled in session state and report_options on submit. |
| **K** | Admin validates and releases the spec correctly | ✅ | assign_request_to_workspace creates newsletter_specifications from request including report_options; update_specification supports report_options. |
| **L** | Payment / activation gating remains intact | ✅ | No change to approval/invoice/activation flow. |
| **M** | One source of truth for report defaults exists | ✅ | `core/report_spec.py` DEFAULT_REPORT_SPEC; get_specification_detail merges DEFAULT_REPORT_SPEC then DB then report_options. |
| **N** | The active live report path can be explicitly identified | ✅ | Generator UI shows "Report path: Phase 5" or "Legacy"; USE_PHASE5_REPORT / use_phase5_report control which path runs. |

---

**Validation date:** 2026-02-08  
**Plan reference:** PU_Observatory_Live_Application_Alignment_Plan_Final_For_CharlieC.txt §19
