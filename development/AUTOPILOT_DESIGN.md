# Autopilot Feature - Design Document

## 1. Executive Summary

### 1.1 Purpose
This document describes the design for an **Autopilot** feature that enables automated, scheduled report generation. Users can create schedules that automatically generate reports with all choices pre-selected, producing HTML files without manual intervention.

### 1.2 Key Objectives
- Enable users to schedule automatic report generation
- Execute reports with all categories/regions selected by default
- Store generated HTML files for later retrieval
- Provide schedule management interface
- Maintain compatibility with existing frequency enforcement
- Support multiple scheduling patterns (daily, weekly, monthly, custom)

### 1.3 Scope
- **In Scope:**
  - Schedule creation and management UI
  - Automated report generation execution
  - HTML file storage and retrieval
  - Schedule status tracking
  - Error handling and logging
  
- **Out of Scope (Future):**
  - Email delivery of reports
  - Custom notification channels
  - Advanced scheduling (timezone-aware, complex cron expressions)
  - Schedule templates

## 2. System Architecture

### 2.1 Current Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Configurator   │     │      Admin      │     │    Generator    │
│      App        │────▶│      App        │────▶│      App        │
│  (Port 8501)    │     │   (Port 8502)   │     │   (Port 8503)   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                       │                       │
         └───────────────────────┴───────────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │   Supabase Database     │
                    │   (PostgreSQL)          │
                    └─────────────────────────┘
```

### 2.2 Proposed Architecture with Autopilot

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Configurator   │     │      Admin      │     │    Generator    │
│      App        │     │      App        │     │      App        │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                          │
                                                          │ (Schedule Management UI)
                                                          ▼
                    ┌─────────────────────────────────────────────┐
                    │         Supabase Database                    │
                    │  ┌──────────────────────────────────────┐   │
                    │  │  autopilot_schedules (NEW TABLE)    │   │
                    │  │  newsletter_runs (EXISTING)          │   │
                    │  │  newsletter_specifications (EXISTING)│   │
                    │  └──────────────────────────────────────┘   │
                    └─────────────────────────────────────────────┘
                                                          │
                                                          │ (Poll/Trigger)
                                                          ▼
                    ┌─────────────────────────────────────────────┐
                    │      Autopilot Worker                        │
                    │  (Separate Process/Service)                  │
                    │  - Polls schedules                           │
                    │  - Executes report generation                │
                    │  - Updates schedule status                   │
                    └─────────────────────────────────────────────┘
                                                          │
                                                          ▼
                    ┌─────────────────────────────────────────────┐
                    │      execute_generator()                    │
                    │  (Existing Core Function)                   │
                    └─────────────────────────────────────────────┘
```

### 2.3 Deployment Constraint

**Critical Constraint:** The platform is deployed on **Streamlit Cloud**, which is serverless and does NOT support:
- Long-running background processes
- Persistent worker processes
- Cron jobs within the app

**Solution Options:**
1. **External Worker Service** (Recommended)
   - Separate service/container that runs independently
   - Can be deployed on: Railway, Render, Heroku, AWS Lambda, Google Cloud Functions
   - Polls database for schedules and executes them

2. **Supabase Edge Functions** (Alternative)
   - Serverless functions triggered by database events or cron
   - More integrated with existing infrastructure
   - Requires Supabase Pro plan for cron triggers

3. **Cloud Scheduler + Webhook** (Alternative)
   - AWS EventBridge, Google Cloud Scheduler, or similar
   - Triggers HTTP endpoint that executes generation
   - Requires API endpoint (separate service)

## 3. Data Model

### 3.1 New Table: `autopilot_schedules`

```sql
CREATE TABLE autopilot_schedules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Foreign Keys
    specification_id UUID NOT NULL REFERENCES newsletter_specifications(id) ON DELETE CASCADE,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    created_by VARCHAR(255) NOT NULL, -- User email who created the schedule
    
    -- Schedule Configuration
    schedule_name VARCHAR(255) NOT NULL, -- User-friendly name
    schedule_type VARCHAR(50) NOT NULL CHECK (schedule_type IN ('daily', 'weekly', 'monthly', 'custom')),
    
    -- Timing Configuration (JSONB for flexibility)
    schedule_config JSONB NOT NULL, -- See structure below
    
    -- Report Generation Options
    categories_override JSONB, -- NULL = use all from spec, otherwise array of category IDs
    regions_override JSONB,    -- NULL = use all from spec, otherwise array of region names
    cadence_override VARCHAR(20), -- NULL = use spec frequency, otherwise override
    
    -- Status & Control
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    status VARCHAR(50) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'paused', 'cancelled', 'error')),
    
    -- Execution Tracking
    last_run_at TIMESTAMPTZ,
    last_run_status VARCHAR(50), -- 'success', 'failed', NULL
    last_run_error TEXT,
    next_run_at TIMESTAMPTZ NOT NULL, -- Calculated based on schedule_type and schedule_config
    run_count INTEGER NOT NULL DEFAULT 0,
    success_count INTEGER NOT NULL DEFAULT 0,
    failure_count INTEGER NOT NULL DEFAULT 0,
    
    -- Metadata
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_autopilot_schedules_spec ON autopilot_schedules(specification_id);
CREATE INDEX idx_autopilot_schedules_workspace ON autopilot_schedules(workspace_id);
CREATE INDEX idx_autopilot_schedules_enabled ON autopilot_schedules(enabled, next_run_at);
CREATE INDEX idx_autopilot_schedules_next_run ON autopilot_schedules(next_run_at) WHERE enabled = TRUE;
```

### 3.2 `schedule_config` JSONB Structure

**For `schedule_type = 'daily'`:**
```json
{
  "time": "09:00",  // HH:MM format in UTC
  "timezone": "UTC"  // Future: support timezones
}
```

**For `schedule_type = 'weekly'`:**
```json
{
  "day_of_week": 1,  // 0=Monday, 6=Sunday
  "time": "09:00",
  "timezone": "UTC"
}
```

**For `schedule_type = 'monthly'`:**
```json
{
  "day_of_month": 1,  // 1-28 (to avoid month-end issues)
  "time": "09:00",
  "timezone": "UTC"
}
```

**For `schedule_type = 'custom'`:**
```json
{
  "cron_expression": "0 9 * * 1",  // Cron format: "minute hour day month weekday"
  "timezone": "UTC"
}
```

### 3.3 Modified Table: `newsletter_runs`

Add optional field to track autopilot execution:
```sql
ALTER TABLE newsletter_runs 
ADD COLUMN autopilot_schedule_id UUID REFERENCES autopilot_schedules(id) ON DELETE SET NULL;
```

This allows tracking which runs were generated by autopilot vs manual generation.

## 4. User Flows

### 4.1 Create Schedule Flow

```
User → Generator App → "Autopilot" Page
  ↓
Select Specification
  ↓
Configure Schedule:
  - Schedule Name
  - Schedule Type (daily/weekly/monthly/custom)
  - Time Settings
  - Category Selection (default: all)
  - Region Selection (default: all)
  ↓
Save Schedule
  ↓
Schedule stored in database
Next run time calculated
  ↓
Confirmation shown to user
```

### 4.2 Schedule Execution Flow (Background)

```
Autopilot Worker (runs every 5 minutes)
  ↓
Query: SELECT * FROM autopilot_schedules 
       WHERE enabled = TRUE 
       AND next_run_at <= NOW()
  ↓
For each due schedule:
  ↓
  Validate specification is still active
  ↓
  Check frequency enforcement (if not overridden)
  ↓
  Execute: execute_generator(
    spec_id=schedule.specification_id,
    workspace_id=schedule.workspace_id,
    user_email=schedule.created_by,
    categories_override=schedule.categories_override,
    regions_override=schedule.regions_override,
    cadence_override=schedule.cadence_override
  )
  ↓
  Update schedule:
    - last_run_at = NOW()
    - last_run_status = success/failed
    - last_run_error = error message (if failed)
    - run_count += 1
    - success_count += 1 (if success) OR failure_count += 1 (if failed)
    - next_run_at = calculate_next_run(schedule)
  ↓
  Log execution in audit_log
```

### 4.3 Schedule Management Flow

```
User → Generator App → "Autopilot" Page
  ↓
View List of Schedules
  ↓
Actions Available:
  - View Schedule Details
  - Edit Schedule
  - Enable/Disable Schedule
  - Delete Schedule
  - View Execution History
  - Test Run (execute immediately)
```

## 5. Core Components

### 5.1 Database Module: `core/autopilot_db.py`

**Functions:**
- `create_autopilot_schedule()` - Create new schedule
- `get_autopilot_schedules()` - List schedules for workspace/spec
- `get_due_schedules()` - Get schedules ready to execute
- `update_schedule_after_run()` - Update schedule after execution
- `calculate_next_run()` - Calculate next execution time
- `enable_schedule()` / `disable_schedule()` - Toggle schedule
- `delete_schedule()` - Remove schedule

### 5.2 Worker Script: `autopilot_worker.py`

**Responsibilities:**
- Poll database for due schedules (every 5 minutes)
- Execute report generation for each due schedule
- Update schedule status and next run time
- Handle errors gracefully
- Log all activities

**Execution Pattern:**
```python
while True:
    due_schedules = get_due_schedules()
    for schedule in due_schedules:
        try:
            execute_generator(...)
            update_schedule_after_run(schedule_id, success=True)
        except Exception as e:
            update_schedule_after_run(schedule_id, success=False, error=str(e))
            log_error(schedule_id, e)
    sleep(300)  # 5 minutes
```

### 5.3 UI Module: Generator App Enhancement

**New Page: "🤖 Autopilot"**

**Sections:**
1. **Schedule List** - Table of all schedules with status
2. **Create Schedule** - Form to create new schedule
3. **Schedule Details** - View/edit existing schedule
4. **Execution History** - Filtered view of autopilot-generated runs

### 5.4 Integration with Existing Code

**Minimal Changes Required:**
- `execute_generator()` already supports all needed parameters
- No changes to core generation logic
- Only add autopilot_schedule_id to run record

## 6. Error Handling & Monitoring

### 6.1 Error Scenarios

1. **Specification No Longer Active**
   - Mark schedule as `status = 'error'`
   - Set `last_run_error = 'Specification is not active'`
   - Do not update `next_run_at` (requires manual intervention)

2. **Frequency Limit Reached**
   - Skip this execution
   - Update `next_run_at` to next eligible time
   - Log warning (not error)

3. **Generation Failure**
   - Mark `last_run_status = 'failed'`
   - Store error message
   - Increment `failure_count`
   - Continue with next scheduled run

4. **Worker Process Down**
   - Schedules will accumulate
   - When worker restarts, it will catch up
   - Consider alerting if schedules are overdue by >24 hours

### 6.2 Logging

- All autopilot executions logged to `audit_log` table
- Include: schedule_id, execution time, status, error (if any)
- Worker logs to stdout/stderr (for cloud logging services)

### 6.3 Monitoring

**Admin Dashboard Enhancement:**
- Show autopilot statistics:
  - Total active schedules
  - Schedules with errors
  - Success rate
  - Next scheduled runs

## 7. Security Considerations

### 7.1 Access Control
- Only workspace members can create schedules for their workspace
- Only schedule creator or workspace owner can modify/delete schedules
- Admin can view all schedules across workspaces

### 7.2 Rate Limiting
- Respect existing frequency enforcement
- Autopilot cannot bypass frequency limits (unless cadence_override is set)
- Consider additional rate limiting for autopilot (prevent abuse)

### 7.3 Data Privacy
- Generated reports stored same way as manual reports
- No additional data exposure
- Schedule configurations visible only to authorized users

## 8. Performance Considerations

### 8.1 Database Queries
- Index on `(enabled, next_run_at)` for efficient polling
- Index on `specification_id` for schedule lookups
- Consider partitioning if schedule count grows very large (>10,000)

### 8.2 Worker Polling Frequency
- Default: Every 5 minutes
- Configurable via environment variable
- Balance between responsiveness and database load

### 8.3 Concurrent Execution
- Worker processes schedules sequentially
- For high volume, consider:
  - Multiple worker instances (with locking)
  - Queue-based system (Celery, RQ)

## 9. Future Enhancements

### 9.1 Phase 2 Features
- Email delivery of generated reports
- Custom notification channels (Slack, Teams, etc.)
- Timezone support for schedules
- Schedule templates
- Retry logic for failed runs
- Schedule analytics dashboard

### 9.2 Phase 3 Features
- Conditional scheduling (only if new content available)
- Multi-specification batch runs
- Schedule dependencies
- Advanced cron expressions with UI builder

## 10. Success Criteria

### 10.1 Functional Requirements
- ✅ Users can create schedules via UI
- ✅ Reports generate automatically at scheduled times
- ✅ All categories/regions selected by default
- ✅ HTML files stored and retrievable
- ✅ Schedule management (enable/disable/edit/delete)
- ✅ Execution history visible

### 10.2 Non-Functional Requirements
- ✅ Worker reliability: 99%+ uptime
- ✅ Execution accuracy: Runs within 5 minutes of scheduled time
- ✅ Error recovery: Failed runs don't block future runs
- ✅ Performance: Worker poll completes in <30 seconds
- ✅ Scalability: Supports 100+ concurrent schedules

## 11. Dependencies

### 11.1 New Python Packages
- Scheduling library (see Implementation Plan for options)
- No other new dependencies required

### 11.2 Infrastructure
- Separate worker service/container (see Implementation Plan)
- Database migration (new table)

### 11.3 External Services
- None (uses existing Supabase and OpenAI)

---

**Document Version:** 1.0  
**Last Updated:** 2025-01-XX  
**Author:** Development Team

