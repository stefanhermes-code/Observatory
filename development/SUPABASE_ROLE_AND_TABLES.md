# Supabase role and when tables get populated

Supabase is the **single backend** for all three apps: **Configurator**, **Admin**, and **Generator (Portal)**. Auth, workspaces, specifications, runs, evidence, and audit all live there. Tables stay empty until you perform the actions that write to them.

---

## Role of Supabase

- **Configurator**: reads/writes `specification_requests` (customer requests); no direct workspace/spec creation (Admin approves and creates those).
- **Admin**: creates and manages `workspaces`, `newsletter_specifications`, `sources`, `tracked_companies`, `audit_log`; approves requests and assigns workspaces.
- **Generator (Portal)**: reads `workspace_members`, `newsletter_specifications`; creates `newsletter_runs` and (via evidence pipeline) `candidate_articles`, `signals`, `signal_occurrences`.

Same database, same project — different apps use different tables depending on the workflow step.

---

## Tables and when they get data

| Table | Populated by | When it gets data |
|-------|--------------|--------------------|
| **workspaces** | Admin | When Admin creates a company/workspace. |
| **workspace_members** | Admin | When Admin adds users to a workspace. |
| **specification_requests** | Configurator | When a customer submits a request in the Configurator. |
| **newsletter_specifications** | Admin | When Admin approves a request and creates (or updates) a spec. |
| **newsletter_runs** | Generator | Every time a user runs “Generate Report” in the Portal. |
| **sources** | Admin | When Admin adds or imports sources in the Sources (Source Registry) page. |
| **tracked_companies** | Admin | When Admin uses “Sync from file” (company_list.json) or adds/edits companies in Industry list. |
| **candidate_articles** | Generator | During each report run: evidence engine ingests sources + search and inserts rows per run. |
| **signals** | Generator | During each report run: extraction step creates one signal per candidate (normalized). |
| **signal_occurrences** | Generator | During each report run: links each signal to a run and candidate_article_id. |
| **audit_log** | Admin (and some Generator actions) | When Admin (or app) logs actions (e.g. source edit, company add, seed). |
| **run_feedback** | (Future) | Defined in migration 001; **no app code uses it yet**. Reserved for optional user feedback on runs (e.g. usefulness, accuracy, timeliness). |

---

## Why some tables are still empty

- **sources** — Empty until you add or import sources in Admin → Sources.
- **tracked_companies** — Empty until you run “Sync from file” (or add companies) in Admin → Industry list. Evidence engine can fall back to `company_list.json` if the table is empty.
- **candidate_articles** — Empty until at least one report has been generated (evidence engine runs and inserts per run).
- **signals** / **signal_occurrences** — Empty until at least one report has been generated (extraction runs after evidence and inserts these).
- **audit_log** — Fills as Admin (and logged actions) are used; empty if you haven’t done any logged actions yet.
- **run_feedback** — Reserved for future “rate this report” style features; **no code reads or writes it yet**. All other tables are used by the app.

So: **empty = normal** until you’ve used the corresponding part of the workflow (Admin setup vs. generating reports).

---

## Minimal path to “everything used”

1. **Admin**: Create workspace(s) and users → **workspaces**, **workspace_members** get rows.
2. **Admin**: Create/approve at least one newsletter specification → **newsletter_specifications** gets rows.
3. **Admin**: Add at least one source (e.g. RSS) in Sources → **sources** gets rows.
4. **Admin**: “Sync from file” or add companies in Industry list → **tracked_companies** gets rows.
5. **Portal**: Run “Generate Report” for a spec → **newsletter_runs**, **candidate_articles**, **signals**, **signal_occurrences** get rows.

If you skip step 3 or 4, the evidence engine can still run (e.g. using only search, or company_list.json), but **candidate_articles** (and thus **signals** / **signal_occurrences**) will only fill when a run actually finds and stores candidates.
