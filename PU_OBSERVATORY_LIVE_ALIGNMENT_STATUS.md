# PU Observatory – Live Application Alignment Status

Aligned to **PU_Observatory_Live_Application_Alignment_Plan_Final_For_CharlieC.txt**.

---

## Implemented (this session)

### §7 Customer filter – strict behavior
- **intelligence_report.apply_customer_filter**: Unset metadata no longer passes when the customer has constrained that dimension. Docstring updated to state strict behavior per plan §7.
- **customer_filter.filter_signals_by_spec** and **filter_candidates_by_spec** were already strict; live path uses them.

### §8 Filter before clustering
- **run_phase_extract_and_write**: Applies `filter_candidates_by_spec(candidates, run_specification)` before extraction. Extraction and downstream clustering therefore run on customer-filtered candidates in the phased UI flow.
- **execute_generator**: Already applied `filter_candidates_by_spec` before extraction.
- **generate_report_from_signals**: Filters signals with `filter_signals_by_spec` then runs `group_signals(filtered)` — clustering and development extraction use only filtered signals.

### §10 Phase 5 report – live path
- Phase 5 report (developments, Signal Map, Appendix A) is used when `USE_PHASE5_REPORT=true` (env or Streamlit secrets) or `spec.use_phase5_report` is True.
- **run_phase_extract_and_write**: Uses `_flag_from_secrets_or_env("USE_PHASE5_REPORT")` so Cloud can set the flag via Streamlit secrets.
- When Phase 5 is used, `generate_report_from_signals` is called with `write_html=True` and the returned HTML is stored.

### §16–17 Live integration and switching
- **Phase 5 HTML**: When Phase 5 runs, `writer_output["html"]` is set from `generate_report_from_signals(..., write_html=True)`. In both `execute_generator` and `run_phase_render_and_save`, if `writer_output.get("html")` is present, that HTML is used as the persisted report; otherwise the legacy `_render_html_from_content` path is used.
- Feature flag: `USE_PHASE5_REPORT` (env + Streamlit secrets) and optional per-spec `use_phase5_report`. Legacy report path remains available when the flag is off. Report path is shown in Generator UI (plan §17).

### Data flow (current live path with Phase 5)
1. Evidence engine persists **candidate_articles** for the run (with query_id, region, category, value_chain_link from query plan).
2. **get_master_signals_for_run(run_id)** returns run-scoped “master” view from candidate_articles (signal_id, title, url, date, source, query_id, category, region, value_chain_link).
3. **build_query_plan_map(run_specification)** builds query_id → {region, configurator_category, value_chain_link} from spec.
4. **generate_report_from_signals** applies **filter_signals_by_spec** (strict), then **group_signals** → **build_developments** → **render_report** (Signal Map + Appendix A per spec).

---

## Already in place (pre-session)

- Master signal view: **get_master_signals_for_run** (run-scoped; plan §6.1–6.2).
- Query metadata: **build_query_plan_map(spec)** (in-memory; plan §6.2).
- Phase 5 logic: developments, signal strength, business relevance, direction of impact, Signal Map, Appendix A in **intelligence_report**.
- Configurator category → classifier category: **CONFIGURATOR_TO_CLASSIFIER** in intelligence_report (documented as temporary fallback per plan §9).

---

## Remaining (per plan)

- **§6.1–6.3**: If a global persistent “master classified signal dataset” table (separate from run-scoped candidate_articles) is required, that would be a schema + pipeline addition. Current design uses run-scoped candidate_articles as the source for the report run.
- **§13–14**: Configurator/Admin — add or confirm spec fields: `report_period`, `report_title`, `included_sections`, `signal_map_enabled`, `evidence_appendix_enabled`, `minimum_signal_strength_in_report`, `company_signal_tracking_enabled`; ensure one source of truth for defaults (§15).
- **§19–20**: Full validation checklist and deliverable package (e.g. PU_OBSERVATORY_LIVE_ALIGNMENT_PACK.zip) when closing the task.

---

## Files changed (this session)

| File | Change |
|------|--------|
| `core/intelligence_report.py` | apply_customer_filter: strict filter (no “unset = match”); docstring updated. |
| `core/generator_execution.py` | execute_generator: use writer_output["html"] when present for Step 7. run_phase_extract_and_write: filter candidates by spec before extraction; USE_PHASE5_REPORT from _flag_from_secrets_or_env; Phase 5 sets writer_output["html"]. run_phase_render_and_save: use writer_output["html"] when present. |

---

*Last updated: 2026-02-08*
