# V2 Setup Status & Generator Test

## Where we are (new setup)

### Done

| Area | Status | Notes |
|------|--------|--------|
| **DB & migrations** | Done | `001` (sources, candidate_articles, signals, run_feedback), `002` (tracked_companies), `003` (categories on tracked_companies). Run record created **before** evidence ingestion (V2-DB-02). |
| **Admin – Source Registry** | Done | List, add/edit/delete, enable/disable, import from JSON, **Test** (RSS/sitemap/html_list) with clickable links. |
| **Admin – Industry list** | Done | Sync from file, add/edit/delete; **Regions**, **Value chain link**, **Categories** are taxonomy dropdowns (multiselect). |
| **Evidence engine** | Done | Connectors (RSS, sitemap, html_list), query planner (code, no LLM), OpenAI web search provider, URL canonicalize/validate, dedupe. `run_evidence_engine()` runs **after** run creation, inserts into `candidate_articles`, returns `evidence_summary` stored in run metadata. |
| **Generator execution** | Done | 7-step flow: spec → cadence check → build_run_package → **create run** → **run_evidence_engine** → execute_assistant → validate → render HTML → update run. Evidence summary is in run metadata. |

### Not done (build plan)

| Item | Plan | Notes |
|------|------|--------|
| **Phase 4 – Intelligence extraction** | V2-LLM-01 | `intelligence_extraction.py`: candidate_articles → normalized signals + signal_occurrences. Not implemented. |
| **Phase 4 – Bounded report writer** | V2-LLM-02 | `intelligence_writer.py`: report that **only** cites URLs from candidate_articles; “Coverage low” if evidence &lt; N. Not implemented. |
| **Phase 5 – Portal UI** | V2-PORTAL-01 | Evidence counts, “what changed”, show sources/queries. Not implemented. |
| **Phase 6 – Cleanup** | V2-CLEAN-01 | instruction_version in repo and run metadata. Not implemented. |

So: **evidence is collected and stored**, but the **report is still produced by the existing OpenAI Assistant**. The Assistant does **not** receive the list of `candidate_articles`; it uses file_search (company list) and its own tools (e.g. web search) to generate the newsletter.

---

## Do you need to change the OpenAI Assistant before testing the Generator?

**No.** You can test the Generator as-is:

1. **No Assistant config change required**  
   The app already uses `OPENAI_ASSISTANT_ID` and `OPENAI_VECTOR_STORE_ID`. The Assistant is expected to have:
   - **file_search** enabled (company list in vector store).
   - **web_search** (or equivalent) if you want it to fetch news; otherwise it may still produce a report from its own knowledge.

2. **What happens when you run the Generator**
   - Run record is created (status `running`).
   - **Evidence engine runs**: ingests Admin sources + runs query plan (OpenAI web search), writes to `candidate_articles` for this run, returns `evidence_summary`.
   - **Assistant runs** with the same run package as before (spec, cadence, lookback, instructions). It does **not** get the `candidate_articles` list.
   - Output is validated and turned into HTML; run is updated to `success` and `evidence_summary` is stored in run metadata.

So you can **test end-to-end** (run creation, evidence ingestion, Assistant run, HTML, history) without touching the Assistant.

---

## Optional next step: make the report evidence-based

If you want the report to **only cite URLs from candidate_articles** (per V2 design):

- **Option A – Keep Assistant, add evidence to run package**  
  - After `run_evidence_engine()`, load `candidate_articles` for this run from the DB.  
  - Extend `build_run_package()` (or add a post-step) to include a “Mandatory evidence list” in the user message: title, url, snippet, source per candidate.  
  - Update system/user instructions to: “Only cite URLs from this list; do not add URLs from your own search.”  
  - No new OpenAI Assistant in the dashboard is required; only code and prompt changes.

- **Option B – Replace Assistant with extraction + writer (Phase 4)**  
  - Implement `intelligence_extraction.py` and `intelligence_writer.py`.  
  - Generator calls extraction → writer instead of `execute_assistant()`.  
  - Report is fully driven by candidate_articles; no Assistant for report writing.

**Summary:** You do **not** need to change the OpenAI Assistant before testing. For strict evidence-only reporting, we’d either pass candidate_articles into the current Assistant (Option A) or implement the bounded writer (Option B).
