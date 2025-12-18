# Generator Execution Pattern

This document describes the canonical execution pattern implemented in the Generator app.

## Core Principle

**The Generator is the orchestrator. The OpenAI Assistant is an execution engine.**

- The Assistant does not remember users, preferences, or prior runs
- All intelligence boundaries are enforced by the Generator through explicit inputs
- The Assistant receives only the run package - no other context

## 7-Step Canonical Execution Flow

### Step 1: Retrieve Active Specification
- Generator retrieves the active Generator Specification from storage
- Specification includes: selected deliverables, regions, supply-chain links, cadence type, activation status
- **If specification is not active, execution stops**

### Step 2: Enforce Cadence Rules
- Before any execution, determine the cadence period (daily/weekly/monthly)
- Check for existing successful run within the same period
- **If successful run exists, block execution and return clear status message**
- Only successful runs consume a cadence slot

### Step 3: Assemble Run Package
The Generator builds a complete run package consisting of:
- **System instruction**: "Polyurethane Observatory Intelligence Analyst" (from OpenAI Instructions)
- **User-specific Generator Specification**: Complete spec with deliverables, regions, cadence
- **Cadence context**: daily/weekly/monthly
- **Optional historical reference**: Previous run IDs or timestamps (for context, not memory)

This package represents the **full and only context** provided to the Assistant.

### Step 4: Execute Assistant
- Generator submits run package to OpenAI
- **Rules:**
  - Assistant must not infer or assume any context beyond the package
  - Assistant must not expand scope
  - Assistant must not store state

### Step 5: Validate Output
Generator validates the returned output:
- Structural correctness
- Alignment with selected deliverables
- Absence of out-of-scope content
- **If validation fails, run is marked as failed and does NOT consume cadence quota**

### Step 6: Persist Results
For successful runs:
- Store generated artifact (HTML or structured output)
- Store run metadata (timestamp, cadence period key, status)
- Link run to specification and workspace
- **Artifacts are immutable once stored**

### Step 7: Return Result to User
Generator presents output to authenticated user:
- Preview
- Download
- History access

## Statelessness Guarantee

- Each execution is independent
- The Assistant does not remember previous runs
- Continuity is managed by the Generator and storage layer
- This guarantees reproducibility, auditability, and scope discipline

## Implementation Files

- `core/generator_execution.py` - Main execution orchestrator (7-step flow)
- `core/openai_assistant.py` - OpenAI integration (run package assembly, execution, validation)
- `core/content_pipeline.py` - HTML rendering from Assistant output
- `apps/generator/app.py` - UI that calls the execution pattern

## Environment Variables

```env
OPENAI_API_KEY=your_openai_api_key
OPENAI_ASSISTANT_ID=asst_...  # Required for Assistants API
```

**Note:** The implementation uses OpenAI Assistants API, which requires both an API key and an Assistant ID. The Assistant's system instructions are configured in the OpenAI platform.

## Why This Pattern Is Mandatory

This execution pattern ensures:
- ✅ Strict enforcement of paid scope
- ✅ Clean separation between product logic and AI execution
- ✅ Zero cross-user leakage risk
- ✅ Predictable cost and performance
- ✅ Future extensibility (multi-industry, additional deliverables)

Any deviation from this pattern risks breaking pricing, governance, and credibility.

## Implementation Guardrails

- ✅ Never embed user-specific logic inside the Assistant
- ✅ Never allow the Assistant to decide scope
- ✅ Always pass the full specification on each run
- ✅ Treat the Assistant as replaceable infrastructure, not a system of record

This execution pattern is authoritative and should be followed exactly.

