# Admin: metrics and run history

## 1. Where measurements and timing are shown

- **Generator (Portal)** is customer-facing. It shows **no** timing, phase breakdown, or internal metrics. Customers see only high-level progress (e.g. “Found N items”, “Extracting and building report…”) and the final report.
- **Admin** is where all measurements and timing are shown:
  - **Dashboard**: run counts (Total Runs 30d, Runs 7d, Runs 24h, Success Rate, Avg Runs/Day).
  - **Generation History**: for each run, **Timing (s)** from `metadata.evidence_summary.timing_seconds` (ingestion, web search, validate/dedupe, persist, total), plus model, tokens, etc.

So: no internal metrics in the Generator; all timing and run metrics are in the Admin app.

---

## 2. Run history: how it works (facts from the code)

- **Same credentials**: Admin, Generator, and Configurator all use the same Supabase client pattern: `st.secrets.get("SUPABASE_URL")` and `st.secrets.get("SUPABASE_ANON_KEY")` (or env). There is no code path that uses different secrets for different apps.
- **Writer**: Generator writes to `newsletter_runs` via `core/generator_db.py` (`create_newsletter_run`, `update_run_status`).
- **Reader**: Admin reads run history via `core/admin_db.py` → `get_recent_runs()` → `SELECT` from `newsletter_runs` (with optional join to `newsletter_specifications` for the name).

If run history is empty in Admin, the cause is not “different secrets.” Check in Supabase: (1) Does the `newsletter_runs` table contain rows after a Generator run? (2) If RLS is enabled on `newsletter_runs`, does the anon role have a policy that allows `SELECT`?
