# PU Observatory Live Alignment – Implementation Package (§20)

**Package name:** PU_OBSERVATORY_LIVE_ALIGNMENT_PACK  
**Plan reference:** PU_Observatory_Live_Application_Alignment_Plan_Final_For_CharlieC.txt §20

---

## 1. Code changes summary

- **Customer filter (strict):** Unset metadata no longer passes when the customer has constrained a dimension; applied in `intelligence_report.apply_customer_filter` and consistently in `customer_filter.filter_signals_by_spec` / `filter_candidates_by_spec`.
- **Filter before clustering:** Phased UI flow applies `filter_candidates_by_spec` before extraction; Phase 5 report applies `filter_signals_by_spec` then clusters only filtered signals.
- **Phase 5 as live path:** When `USE_PHASE5_REPORT` (env or Streamlit secrets) or `spec.use_phase5_report` is set, the live report uses Phase 5 logic (developments, Signal Map, Appendix A). Phase 5 HTML is generated and stored when available; otherwise legacy `_render_html_from_content` is used.
- **Configurator/Admin (§13–15):** All plan §13 fields supported: report_period, report_title, included_sections, signal_map_enabled, evidence_appendix_enabled, minimum_signal_strength_in_report, company_signal_tracking_enabled. Single source of truth: `core/report_spec.py` DEFAULT_REPORT_SPEC; Configurator and get_specification_detail use it.

---

## 2. Modules/files changed

### PU Observatory live app
- `core/generator_execution.py` – Phase 5 HTML in writer_output; use it in Step 7 and in run_phase_render_and_save; filter candidates before extraction in run_phase_extract_and_write; USE_PHASE5_REPORT from secrets/env in phased flow.
- `core/intelligence_report.py` – apply_customer_filter strict (unset does not pass when dimension constrained).
- `generator_app.py` – (existing) Phase 5 flag and report path indicator.

### Configurator app
- `configurator_app.py` – report_period in session state and in Report options expander; report_period included in report_options on submit.

### Admin app
- No code change required for §13–14: Admin already creates spec from request with report_options; update_specification(spec_id, report_options=...) exists. Optional: add UI to edit report options per spec (future).

### One source of truth
- `core/report_spec.py` – already defines DEFAULT_REPORT_SPEC with all report fields including report_period.
- `core/generator_db.py` – get_specification_detail already merges DEFAULT_REPORT_SPEC and report_options.

---

## 3. Live execution path after migration

1. **Configurator:** Customer selects regions, categories, value_chain_links and report options (report_period, report_title, sections, signal map, evidence appendix, min strength, company_signal_tracking_enabled). Submitted as specification_requests with report_options.
2. **Admin:** Approves request, assigns to workspace → creates newsletter_specifications row with report_options. Payment/activation gating unchanged.
3. **Generator (customer):** User runs report. Evidence engine ingests candidates (with query_id, region, category, value_chain_link). Phased flow: filter_candidates_by_spec → extraction → clustering → classification → doctrine. If Phase 5: get_master_signals_for_run(run_id), build_query_plan_map(spec), filter_signals_by_spec(signals, query_plan_map, spec), group_signals(filtered), build_developments, render_report (Signal Map + Appendix A per spec). Result HTML from Phase 5 when available is stored and shown.

---

## 4. Legacy report path

- **Still available:** Yes. When USE_PHASE5_REPORT is not set and use_phase5_report is not True on the spec, the legacy path runs (structural pipeline if USE_STRUCTURAL_PIPELINE, else intelligence_writer from evidence).
- **Control:** Environment variable or Streamlit secret `USE_PHASE5_REPORT=true`; or per-spec `use_phase5_report: true` in report_options. Generator UI displays which path is active.

---

## 5–7. Example live customer report, signal map, evidence appendix

- **Example report:** When Phase 5 is enabled, a full run produces an HTML report that includes Executive Summary, Signal Map (distribution by section), development sections with evidence, and Appendix A — Evidence Signals. See **Live Results/** in the repo for sample outputs (e.g. HTC Global Market Intelligence_*.html). The same structure is generated in-app and stored in run metadata (html_content).

---

## 8. Validation note for all checks (§19)

See **VALIDATION_CHECKLIST_S19.md** in this package. All checks A–N are satisfied as of the implementation date.

---

## 9. Temporary fallbacks

- **CONFIGURATOR_TO_CLASSIFIER** in `intelligence_report.py`: Used when signals do not have a classifier_category (e.g. from candidate_articles.category). Plan §9 states per-candidate classifier_category (Phase 2e / development behaviour) is the target. This mapping is documented as temporary; final replacement is to wire classifier_category from classification/doctrine output or run Phase 2e-equivalent in live and persist classifier_category on candidate_articles.
- **Run-scoped “master” signals:** Plan §6.1 describes a persistent master classified signal dataset. Current implementation uses run-scoped candidate_articles as the source for each run (`get_master_signals_for_run(run_id)`). A future global master table would require schema and pipeline changes.

---

*Package generated: 2026-02-08*
