# Cursor Build Plan V2 (Evidence-first Observatory)

**Current phase:** Phase 5 (Portal UI updates). Phases 1–4 are done. Phase 4 (extraction + bounded writer) implemented: report is generated from `candidate_articles` only; no OpenAI Assistant for report writing.

## Guardrails
- Do not change business workflow: Configurator → Admin → Portal run generation + cadence
- Implement admin-only global Source Registry
- Metadata-only storage (no full article text)
- Evidence-first: report can only cite candidate_articles URLs

---

## Phase 1: DB + plumbing

### V2-DB-01 Add sources/candidate_articles/signals tables
Files:
- create: development/DATA_MODEL_V2.sql
- create: development/migrations/001_v2_sources_and_evidence.sql
Acceptance:
- migrations apply cleanly in Supabase
- tables visible in Admin export

### V2-DB-02 Update newsletter_runs to allow pre-created run record
Goal:
- create a run row early (status=running) so candidate_articles can reference run_id
Files:
- modify: core/generator_execution.py, core/generator_db.py
Acceptance:
- run_id exists before evidence ingestion begins

---

## Phase 2: Source Registry (Admin)

### V2-ADMIN-01 Add "Sources" section to Admin app
Files:
- modify: admin_app.py
- create/modify: core/admin_db.py with CRUD for sources
UI:
- list sources, create/edit/delete, enable/disable
- support rss/sitemap/html_list fields + selectors JSON
Acceptance:
- can add an RSS source and see it stored in DB

---

## Phase 3: Evidence Engine

### V2-EE-01 Implement URL canonicalizer + validator
Files:
- create: core/url_tools.py
- modify: core/content_pipeline.py (re-use validator)
Rules:
- accept 2xx and 3xx as valid
- mark 403 as restricted (do not drop)
Acceptance:
- validator returns status enum + http_status

### V2-EE-02 Implement connectors
Files:
- create: core/connectors/rss.py
- create: core/connectors/sitemap.py
- create: core/connectors/html_list.py
Each returns: list of {url,title,published_at,snippet,source_name}
Acceptance:
- one connector can ingest known RSS and produce candidates

### V2-EE-03 Implement query planner (code, no LLM)
Files:
- create: core/query_planner.py
Inputs:
- selected regions
- selected signal types
- company aliases (from existing company list logic)
Outputs:
- list of queries with query_id/query_text/intent
Acceptance:
- query plan stable for same spec options

### V2-EE-04 Implement SearchProvider interface + OpenAIWebSearchProvider
Files:
- create: core/search_providers/base.py
- create: core/search_providers/openai_web_search.py
Acceptance:
- executing search returns list of candidates (url/title/snippet/date if available)

### V2-EE-05 EvidenceEngine orchestrator
Files:
- create: core/evidence_engine.py
Flow:
- load enabled sources from DB
- ingest sources into candidate list
- execute query plan searches into candidate list
- insert into candidate_articles with validation + dedup
Acceptance:
- candidate_articles rows created for a run

---

## Phase 4: Intelligence extraction + report generation ✅

### V2-LLM-01 Implement structured extraction from candidate_articles ✅
Files:
- create: core/intelligence_extraction.py
Contract:
- input is candidate_articles rows
- output is list of normalized signals
- must reference candidate_article_id
Acceptance:
- signals + signal_occurrences persisted

### V2-LLM-02 Implement bounded report writer (Exec + BD) ✅
Files:
- create: core/intelligence_writer.py
- render: core/content_pipeline.py render_html_from_content accepts writer markdown (no change needed)
Acceptance:
- report includes only URLs from candidate_articles
- if evidence < N, writer outputs coverage note and stops

---

## Phase 5: Portal UI updates

### V2-PORTAL-01 Update generator_app.py into Portal behaviors
Add:
- evidence counts
- “what changed since last run”
- show sources ingested and queries used (transparency)
Acceptance:
- user can run and see evidence transparency section

---

## Phase 6: Cleanup

### V2-CLEAN-01 Reduce reliance on Dashboard instructions
Goal:
- store instruction_version in repo and attach to run metadata
Acceptance:
- runs show instruction_version and query_plan_version in metadata
