# Lookback and audit verification (CharlieC checklist)

## 1. Source of the 2-day lookback

- **Diagnostic log:** Every run now writes an `audit_log` row with `action_type = 'run_lookback_debug'` immediately after the run is created. It includes:
  - `run_id`, `user_email`, `spec_id`, `workspace_id`
  - `lookback_override_param` (value passed to `execute_generator`)
  - `spec_report_period_days`, `spec_frequency`
  - `effective_report_period_days` (value actually used for evidence and report)

- **Query in Supabase:**
  ```sql
  SELECT run_id, details->>'user_email' AS user_email,
         details->>'lookback_override_param' AS lookback_override_param,
         details->>'spec_report_period_days' AS spec_report_period_days,
         details->>'spec_frequency' AS spec_frequency,
         details->>'effective_report_period_days' AS effective_report_period_days,
         created_at
  FROM audit_log
  WHERE action_type = 'run_lookback_debug'
  ORDER BY created_at DESC
  LIMIT 20;
  ```

- **Priority:** `lookback_override` → `spec["report_period_days"]` → `get_lookback_days(frequency)`.

## 2. Builder override in Generator UI

- The Generator UI (builder only) **only** sends one of: **1, 7, 30, 60, 90, 120, 150, 180** days. A 2-day value **cannot** come from this UI; it would come from a dev script or direct API call.
- The UI default is **7 days** (`index=1`). The selectbox key is `builder_lookback`; Streamlit keeps the last selection for the session.

## 3. Phase-5 report period

- The controller now passes `report_period_days=run_specification.get("report_period_days")` into `generate_report_from_signals(...)`, so the HTML header window label matches the runtime window.

## 4. Customer scope filter – candidate breakdown

- **Script:** `python development/candidate_scope_breakdown.py <run_id>`
- Prints region, category, and value_chain_link distributions for that run’s `candidate_articles`. If Supabase is not configured, it prints the equivalent SQL for you to run in the Supabase SQL editor.

## 5. Audit instrumentation for customer scope

- `filter_candidates_by_spec_with_stats` is used in the controller; its return value `customer_filter_drop_counts` is passed into `build_run_audit`.
- **Derived safeguard:** `build_run_audit` now always sets:
  - `drop_customer_scope_total = candidates_after_date_filter_count - candidates_after_customer_filter_count`
  - and exposes it in `drop_reason_counts["drop_customer_scope_total"]`, and uses it as fallback for `failed_customer_filter` when the detailed stats are zero.
