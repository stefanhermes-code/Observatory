# Autopilot Feature - Implementation Plan

## 1. Overview

This document provides a detailed implementation plan for the Autopilot feature, including tool selection, cost analysis, step-by-step implementation guide, and deployment considerations.

## 2. Scheduling Tool Comparison & Cost Analysis

### 2.1 Tool Options

#### Option 1: APScheduler (Advanced Python Scheduler)
**Type:** Python library (in-process scheduler)

**Pros:**
- ✅ Free and open-source (MIT License)
- ✅ Lightweight (~50KB, minimal dependencies)
- ✅ Simple integration (single Python package)
- ✅ Supports multiple trigger types (cron, interval, date)
- ✅ Persistent job storage (can use database backend)
- ✅ Well-documented and actively maintained
- ✅ No external dependencies (Redis, message broker, etc.)

**Cons:**
- ❌ Runs in-process (requires persistent process)
- ❌ Not suitable for Streamlit Cloud (serverless)
- ❌ Single-process limitation (scaling requires external coordination)
- ❌ No built-in distributed execution

**Cost:** **$0** (Free, open-source)

**Dependencies:**
```python
APScheduler==3.10.4  # ~50KB, no sub-dependencies
```

**Best For:** Separate worker service/container

---

#### Option 2: Celery
**Type:** Distributed task queue

**Pros:**
- ✅ Free and open-source (BSD License)
- ✅ Highly scalable (distributed workers)
- ✅ Robust error handling and retries
- ✅ Multiple broker options (Redis, RabbitMQ, SQS)
- ✅ Built-in monitoring (Flower)
- ✅ Production-ready for large-scale systems

**Cons:**
- ❌ Complex setup (requires message broker)
- ❌ Additional infrastructure (Redis/RabbitMQ)
- ❌ Overkill for simple scheduling needs
- ❌ Steeper learning curve
- ❌ Higher resource requirements

**Cost:** 
- **Software:** $0 (Free, open-source)
- **Infrastructure:** 
  - Redis: $0-15/month (free tier available on Railway/Render)
  - RabbitMQ: $0-20/month (free tier available)
  - **Total:** $0-35/month

**Dependencies:**
```python
celery==5.3.4
redis==5.0.1  # or rabbitmq, etc.
```

**Best For:** Large-scale deployments with high volume

---

#### Option 3: Huey
**Type:** Lightweight task queue

**Pros:**
- ✅ Free and open-source (MIT License)
- ✅ Simpler than Celery
- ✅ Multiple storage backends (Redis, SQLite, in-memory)
- ✅ Built-in task scheduling
- ✅ Minimal dependencies

**Cons:**
- ❌ Still requires Redis for production (or SQLite for small scale)
- ❌ Less mature than Celery
- ❌ Smaller community

**Cost:**
- **Software:** $0 (Free, open-source)
- **Infrastructure:** Redis $0-15/month (if using Redis backend)

**Dependencies:**
```python
huey==2.5.0
redis==5.0.1  # Optional, can use SQLite
```

**Best For:** Medium-scale deployments wanting simplicity

---

#### Option 4: Rocketry
**Type:** Modern Python scheduling framework

**Pros:**
- ✅ Free and open-source (MIT License)
- ✅ Modern API with dependency injection
- ✅ Built-in task scheduling
- ✅ Can use database for persistence
- ✅ Clean, intuitive syntax

**Cons:**
- ❌ Newer project (less battle-tested)
- ❌ Smaller community
- ❌ Still requires persistent process

**Cost:** **$0** (Free, open-source)

**Dependencies:**
```python
rocketry==2.10.0
```

**Best For:** Modern Python projects wanting clean API

---

#### Option 5: Cloud-Native Solutions

##### 5a. Supabase Edge Functions + pg_cron
**Type:** Serverless functions with database cron

**Pros:**
- ✅ Integrated with existing Supabase infrastructure
- ✅ No separate worker service needed
- ✅ Serverless (no process management)
- ✅ Automatic scaling

**Cons:**
- ❌ Requires Supabase Pro plan ($25/month) for pg_cron
- ❌ Less flexible than dedicated scheduler
- ❌ Function execution limits (timeouts)

**Cost:** 
- **Supabase Pro:** $25/month (required for pg_cron)
- **Edge Functions:** Included in Pro plan
- **Total:** $25/month

**Dependencies:**
- Supabase Pro plan
- Edge Functions runtime

---

##### 5b. AWS EventBridge + Lambda
**Type:** Cloud-native event-driven scheduling

**Pros:**
- ✅ Fully managed (no infrastructure)
- ✅ Highly reliable
- ✅ Automatic scaling
- ✅ Pay-per-use pricing

**Cons:**
- ❌ AWS account required
- ❌ More complex setup
- ❌ Vendor lock-in
- ❌ Requires API endpoint

**Cost:**
- **EventBridge:** $1.00 per million events (first 14 days free)
- **Lambda:** $0.20 per 1M requests + compute time
- **Estimated:** $5-20/month for moderate usage

**Dependencies:**
- AWS account
- Lambda function
- API Gateway (if needed)

---

##### 5c. Google Cloud Scheduler + Cloud Functions
**Type:** Cloud-native scheduling

**Pros:**
- ✅ Fully managed
- ✅ Simple HTTP triggers
- ✅ Reliable

**Cons:**
- ❌ Google Cloud account required
- ❌ Vendor lock-in
- ❌ Requires API endpoint

**Cost:**
- **Cloud Scheduler:** $0.10 per job per month
- **Cloud Functions:** Pay-per-use
- **Estimated:** $5-15/month

---

### 2.2 Cost Comparison Summary

| Solution | Software Cost | Infrastructure Cost | Total Monthly Cost | Complexity |
|----------|--------------|---------------------|-------------------|------------|
| **APScheduler** | $0 | $0-10* | **$0-10** | Low |
| **Celery** | $0 | $0-35 | **$0-35** | High |
| **Huey** | $0 | $0-15 | **$0-15** | Medium |
| **Rocketry** | $0 | $0-10* | **$0-10** | Low |
| **Supabase Edge Functions** | $0 | $25 | **$25** | Medium |
| **AWS EventBridge** | $0 | $5-20 | **$5-20** | Medium |
| **Google Cloud Scheduler** | $0 | $5-15 | **$5-15** | Medium |

*Infrastructure cost for hosting worker service (Railway free tier, Render free tier, or small VPS)

### 2.3 Recommendation

**Recommended: APScheduler + Separate Worker Service**

**Rationale:**
1. **Zero software cost** - Free and open-source
2. **Low infrastructure cost** - Can use free tiers (Railway, Render)
3. **Simple integration** - Minimal code changes
4. **Sufficient for needs** - Handles scheduling requirements
5. **No vendor lock-in** - Can migrate to other solutions later
6. **Fits architecture** - Works with separate worker service pattern

**Infrastructure Options (Free Tiers Available):**
- **Railway:** Free tier: $5 credit/month (sufficient for worker)
- **Render:** Free tier: 750 hours/month (sufficient for worker)
- **Heroku:** Free tier discontinued, but Eco dyno: $5/month
- **DigitalOcean App Platform:** $5/month minimum
- **Small VPS:** $3-5/month (Hetzner, Vultr, etc.)

**Total Estimated Cost: $0-5/month** (using free tiers)

---

## 3. Implementation Steps

### Phase 1: Database Schema (Day 1)

#### Step 1.1: Create Migration Script
**File:** `development/migration_autopilot_schedules.sql`

```sql
-- Create autopilot_schedules table
CREATE TABLE autopilot_schedules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    specification_id UUID NOT NULL REFERENCES newsletter_specifications(id) ON DELETE CASCADE,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    created_by VARCHAR(255) NOT NULL,
    schedule_name VARCHAR(255) NOT NULL,
    schedule_type VARCHAR(50) NOT NULL CHECK (schedule_type IN ('daily', 'weekly', 'monthly', 'custom')),
    schedule_config JSONB NOT NULL,
    categories_override JSONB,
    regions_override JSONB,
    cadence_override VARCHAR(20),
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    status VARCHAR(50) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'paused', 'cancelled', 'error')),
    last_run_at TIMESTAMPTZ,
    last_run_status VARCHAR(50),
    last_run_error TEXT,
    next_run_at TIMESTAMPTZ NOT NULL,
    run_count INTEGER NOT NULL DEFAULT 0,
    success_count INTEGER NOT NULL DEFAULT 0,
    failure_count INTEGER NOT NULL DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes
CREATE INDEX idx_autopilot_schedules_spec ON autopilot_schedules(specification_id);
CREATE INDEX idx_autopilot_schedules_workspace ON autopilot_schedules(workspace_id);
CREATE INDEX idx_autopilot_schedules_enabled ON autopilot_schedules(enabled, next_run_at);
CREATE INDEX idx_autopilot_schedules_next_run ON autopilot_schedules(next_run_at) WHERE enabled = TRUE;

-- Add autopilot_schedule_id to newsletter_runs
ALTER TABLE newsletter_runs 
ADD COLUMN autopilot_schedule_id UUID REFERENCES autopilot_schedules(id) ON DELETE SET NULL;

-- Create trigger for updated_at
CREATE TRIGGER update_autopilot_schedules_updated_at 
BEFORE UPDATE ON autopilot_schedules
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

#### Step 1.2: Run Migration
- Execute SQL in Supabase SQL Editor
- Verify table creation
- Test indexes

**Estimated Time:** 30 minutes

---

### Phase 2: Core Database Module (Day 1-2)

#### Step 2.1: Create `core/autopilot_db.py`

**Functions to implement:**
1. `create_autopilot_schedule()` - Create schedule with validation
2. `get_autopilot_schedules()` - List schedules (with filters)
3. `get_due_schedules()` - Get schedules ready to execute
4. `update_schedule_after_run()` - Update after execution
5. `calculate_next_run()` - Calculate next execution time
6. `enable_schedule()` / `disable_schedule()` - Toggle
7. `delete_schedule()` - Soft or hard delete
8. `get_schedule_detail()` - Get single schedule

**Key Implementation Details:**
- Use existing `get_supabase_client()` pattern
- Handle timezone calculations (start with UTC)
- Validate schedule_config JSON structure
- Calculate next_run_at on creation/update

**Estimated Time:** 4-6 hours

---

### Phase 3: Worker Service (Day 2-3)

#### Step 3.1: Create `autopilot_worker.py`

**Structure:**
```python
#!/usr/bin/env python3
"""
Autopilot Worker Service
Polls database for due schedules and executes report generation.
"""

import time
import logging
from datetime import datetime
from core.autopilot_db import get_due_schedules, update_schedule_after_run
from core.generator_execution import execute_generator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def process_due_schedules():
    """Poll and process due schedules."""
    due_schedules = get_due_schedules()
    
    if not due_schedules:
        logger.info("No due schedules found")
        return
    
    logger.info(f"Found {len(due_schedules)} due schedule(s)")
    
    for schedule in due_schedules:
        try:
            logger.info(f"Processing schedule {schedule['id']} for spec {schedule['specification_id']}")
            
            # Execute generation
            success, error_message, result_data, artifact_path = execute_generator(
                spec_id=schedule['specification_id'],
                workspace_id=schedule['workspace_id'],
                user_email=schedule['created_by'],
                categories_override=schedule.get('categories_override'),
                regions_override=schedule.get('regions_override'),
                cadence_override=schedule.get('cadence_override')
            )
            
            # Update schedule
            update_schedule_after_run(
                schedule_id=schedule['id'],
                success=success,
                error_message=error_message,
                run_id=result_data.get('run_id') if result_data else None
            )
            
            if success:
                logger.info(f"Successfully executed schedule {schedule['id']}")
            else:
                logger.error(f"Failed to execute schedule {schedule['id']}: {error_message}")
                
        except Exception as e:
            logger.exception(f"Exception processing schedule {schedule['id']}: {e}")
            update_schedule_after_run(
                schedule_id=schedule['id'],
                success=False,
                error_message=str(e)
            )

def main():
    """Main worker loop."""
    poll_interval = int(os.getenv('AUTOPILOT_POLL_INTERVAL', '300'))  # 5 minutes default
    
    logger.info(f"Starting Autopilot Worker (poll interval: {poll_interval}s)")
    
    while True:
        try:
            process_due_schedules()
        except Exception as e:
            logger.exception(f"Error in main loop: {e}")
        
        time.sleep(poll_interval)

if __name__ == '__main__':
    main()
```

#### Step 3.2: Add Requirements
**Update `requirements.txt`:**
```txt
APScheduler==3.10.4  # For future use if needed, or remove if using simple polling
```

**Note:** For MVP, simple polling is sufficient. APScheduler can be added later if needed.

#### Step 3.3: Create Worker Startup Script
**File:** `run_autopilot_worker.bat` (Windows) and `run_autopilot_worker.sh` (Linux)

**Estimated Time:** 4-6 hours

---

### Phase 4: UI Integration (Day 3-4)

#### Step 4.1: Add Autopilot Page to Generator App

**File:** `generator_app.py`

**New Page:** "🤖 Autopilot"

**Sections:**
1. **Schedule List View**
   - Table showing: Name, Specification, Type, Status, Next Run, Last Run, Actions
   - Filter by workspace/specification
   - Enable/disable toggle

2. **Create Schedule Form**
   - Select specification
   - Schedule name
   - Schedule type (daily/weekly/monthly/custom)
   - Time configuration
   - Category/region selection (default: all)
   - Save button

3. **Schedule Detail/Edit View**
   - View schedule details
   - Edit schedule
   - View execution history
   - Test run button

4. **Execution History**
   - Filtered view of autopilot-generated runs
   - Link to existing History page with filter

#### Step 4.2: Create Helper Functions
**File:** `core/autopilot_ui.py` (optional, or integrate into generator_app.py)

**Functions:**
- Format schedule display
- Validate schedule config
- Calculate next run preview

**Estimated Time:** 6-8 hours

---

### Phase 5: Testing (Day 4-5)

#### Step 5.1: Unit Tests
- Test `calculate_next_run()` with various schedules
- Test database operations
- Test error handling

#### Step 5.2: Integration Tests
- Test worker polling
- Test schedule execution
- Test UI workflows

#### Step 5.3: End-to-End Tests
- Create schedule via UI
- Verify worker executes
- Verify HTML file generated
- Verify schedule updates

**Estimated Time:** 4-6 hours

---

### Phase 6: Deployment (Day 5)

#### Step 6.1: Deploy Database Migration
- Run migration in production Supabase
- Verify table creation

#### Step 6.2: Deploy Code Changes
- Push code to GitHub
- Streamlit Cloud auto-deploys Generator app

#### Step 6.3: Deploy Worker Service

**Option A: Railway (Recommended for Free Tier)**
1. Create Railway account
2. Create new service from GitHub repo
3. Set root directory (if needed)
4. Set start command: `python autopilot_worker.py`
5. Add environment variables:
   - `SUPABASE_URL`
   - `SUPABASE_ANON_KEY`
   - `OPENAI_API_KEY`
   - `OPENAI_ASSISTANT_ID`
   - `AUTOPILOT_POLL_INTERVAL=300`
6. Deploy

**Option B: Render**
1. Create Render account
2. Create new Web Service
3. Connect GitHub repo
4. Set build command: `pip install -r requirements.txt`
5. Set start command: `python autopilot_worker.py`
6. Add environment variables (same as Railway)
7. Deploy

**Option C: Small VPS**
1. Provision VPS (Hetzner, Vultr, etc.)
2. Install Python 3.8+
3. Clone repository
4. Install dependencies
5. Set up systemd service or screen/tmux
6. Configure environment variables
7. Start worker

#### Step 6.4: Monitor Worker
- Check logs for successful polling
- Verify schedules execute
- Monitor error rates

**Estimated Time:** 2-4 hours

---

## 4. Implementation Timeline

| Phase | Tasks | Estimated Time | Dependencies |
|-------|-------|---------------|--------------|
| **Phase 1** | Database schema migration | 0.5 hours | None |
| **Phase 2** | Core database module | 4-6 hours | Phase 1 |
| **Phase 3** | Worker service | 4-6 hours | Phase 2 |
| **Phase 4** | UI integration | 6-8 hours | Phase 2 |
| **Phase 5** | Testing | 4-6 hours | Phases 2-4 |
| **Phase 6** | Deployment | 2-4 hours | All phases |
| **Total** | | **21-35 hours** | |

**Estimated Duration:** 3-5 days (assuming 6-8 hours/day)

---

## 5. Risk Mitigation

### 5.1 Technical Risks

**Risk:** Worker service goes down
- **Mitigation:** Use managed platform (Railway/Render) with auto-restart
- **Monitoring:** Set up alerts for worker downtime

**Risk:** Database connection issues
- **Mitigation:** Add retry logic in worker
- **Monitoring:** Log connection errors

**Risk:** Schedule execution failures
- **Mitigation:** Error handling in worker, continue with next schedule
- **Monitoring:** Track failure_count in schedules table

### 5.2 Operational Risks

**Risk:** Worker costs exceed budget
- **Mitigation:** Use free tiers, monitor usage
- **Fallback:** Migrate to cheaper VPS if needed

**Risk:** High database load from polling
- **Mitigation:** Optimize queries, use indexes, adjust poll interval
- **Monitoring:** Monitor query performance

---

## 6. Success Metrics

### 6.1 Functional Metrics
- ✅ Schedules created successfully
- ✅ Reports generate at scheduled times
- ✅ HTML files stored correctly
- ✅ Schedule management works

### 6.2 Performance Metrics
- Worker poll time < 30 seconds
- Schedule execution within 5 minutes of scheduled time
- 99%+ worker uptime
- <1% execution failure rate

### 6.3 Cost Metrics
- Worker infrastructure cost < $10/month
- No unexpected cost spikes

---

## 7. Post-Implementation

### 7.1 Documentation
- Update README with autopilot instructions
- Create user guide for schedule management
- Document worker deployment process

### 7.2 Monitoring
- Set up alerts for worker downtime
- Monitor schedule execution rates
- Track error rates

### 7.3 Future Enhancements
- Email delivery (Phase 2)
- Timezone support (Phase 2)
- Advanced scheduling options (Phase 3)

---

**Document Version:** 1.0  
**Last Updated:** 2025-01-XX  
**Author:** Development Team

