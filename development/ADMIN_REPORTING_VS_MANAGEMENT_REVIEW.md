# Admin app: Reporting vs management review

Review of all Admin pages to identify where **reporting** (analytics, summaries, exports) is mixed with **management** (CRUD, configuration, viewing actual content). Suggested changes move reporting into the **Reporting** page and keep management pages focused on configuration and content.

---

## 1. Pages that mix management and reporting

### 🔗 Sources
| What’s there | Type | Suggestion |
|-------------|------|------------|
| Source Registry: import JSON, add/edit/test/toggle/delete sources | **Management** | Keep on Sources page. |
| **Historical productivity** – table “Total candidate articles per source (all time)” from `get_source_productivity()` | **Reporting** | **Move to Reporting.** Add report type **“Source Productivity”** (or “Historical Source Productivity”): same dataframe (Source, Items (all time)) + CSV export. Remove the “Historical productivity” block from the Sources page. |

---

### 📊 Dashboard
| What’s there | Type | Suggestion |
|-------------|------|------------|
| Flags & Alerts, Overall Performance (runs 30d/7d/24h, success rate, avg runs/day), Request Status Metrics, Core Metrics, Recent Activity (audit log) | **Reporting** | Dashboard is effectively a **report** (metrics + recent activity). **Option A:** Leave as-is: single “at a glance” landing page. **Option B:** Add a report type **“Dashboard Summary”** under Reporting that shows the same metrics + export, and keep the Dashboard page as a short summary with links to Reporting for details. No strong recommendation; both are valid. |

---

### 📚 Generation History
| What’s there | Type | Suggestion |
|-------------|------|------------|
| List of runs, per-run expand with status, download HTML, timing, model, tokens | **Management + content** | Keep: this is the place to **view and download** runs. |
| “Total Runs: N”, CSV export “Export Generation History” | **Reporting** | Already duplicated in **Reporting > Generation History**. No change needed: page = operational view + download; report = same data in Reporting. |

---

### 📰 Intelligence Specifications
| What’s there | Type | Suggestion |
|-------------|------|------------|
| List specs, filter by status/company, edit spec, activate/pause, override frequency | **Management** | Keep on Specifications page. |
| Per-spec: “Categories: N”, “Regions: …”, **“Last Run: …”** | **Reporting (inline)** | Inline info for each spec; “Last Run” is the only clear reporting element. **Optional:** Add report type **“Specification Summary”** in Reporting (e.g. spec name, status, frequency, last run, company) with CSV export. Then Specifications page stays management-only; last-run analytics live in Reporting. |

---

### 🏢 Companies
| What’s there | Type | Suggestion |
|-------------|------|------------|
| Create company, list companies, edit company, view specs, address/VAT | **Management** | Keep. “Specifications: N” per company is contextual, not a standalone report. No change. |

---

### 🏭 Industry list
| What’s there | Type | Suggestion |
|-------------|------|------------|
| “In database: N companies”, sync from file, add/edit/delete tracked companies | **Management + one metric** | The count is a single contextual metric. **Optional:** If you later add more analytics (e.g. by region, by value chain), add report **“Tracked companies summary”** under Reporting. Not needed for current scope. |

---

### 💰 Invoicing
| What’s there | Type | Suggestion |
|-------------|------|------------|
| Filter by status, list requests, pricing per request, generate invoice, download, send email | **Management** | Keep. Revenue/billing analytics are already under **Reporting > Revenue Analytics**. No change. |

---

### 📋 Audit Log
| What’s there | Type | Suggestion |
|-------------|------|------------|
| List of audit entries (action, user, timestamp, reason), CSV export | **Reporting-style** | Functionally a read-only report with export. **Optional:** Add report type **“Audit Log”** under Reporting (same list + CSV) so all “reports” live in one place; keep the Audit Log page as a dedicated compliance view, or link “Also available under Reporting”. |

---

## 2. Pages that are management-only (no change)

- **📥 Process Requests** – Approve/reject/assign. No reporting.
- **👤 Users** – Workspace members, add/remove/roles. No reporting.
- **🔐 Administrators** – Admin users, add/remove/password. No reporting.

---

## 3. Suggested changes (priority)

| Priority | Change |
|----------|--------|
| **1. Do** (done) | **Sources:** Move “Historical productivity” to Reporting. Add report type **“Source Productivity”** (candidate_articles count per source, table + CSV). Remove the Historical productivity block from the Sources page. |
| **2. Consider** | **Reporting:** Add **“Specification Summary”** (specs with status, frequency, last run, company) + CSV, if you want spec analytics in one place. |
| **3. Consider** | **Reporting:** Add **“Audit Log”** report type (same content + export as Audit Log page) for consistency. |
| **4. Optional** | **Dashboard:** Either leave as landing report or add “Dashboard Summary” report type and keep Dashboard as a short overview. |
| **5. Optional** | **Industry list:** Only if you add more analytics later; then add “Tracked companies summary” report. |

---

## 4. Reporting page – current and proposed report types

**Current:** Platform Overview, Company Activity, Generation Performance, Generation Time, Generation History, Source Usage Analytics, Token Usage & Costs, Revenue Analytics.

**Proposed additions:**
- **Source Productivity** (from Sources page) – candidate_articles count per source, all time. **Implemented.**

---

## 5. Summary

- **Done:** Historical productivity on **Sources** → report **“Source Productivity”** on **Reporting**; remove it from Sources.
- **Not doing:** Specification Summary, Audit Log report, Dashboard Summary, Tracked companies summary (per product owner).
