# How to Verify Company List is Being Used

## Overview
The Observatory uses a comprehensive list of 152+ PU industry companies stored in the OpenAI Assistant's knowledge base (vector store). This guide explains how to verify that the company list is actually being retrieved and used.

## Automatic Verification

### 1. Generator App - After Report Generation
After generating a report, the Generator app will display:
- ✅ **Success**: "Report generated successfully! ✅ Company list from knowledge base was retrieved."
- ⚠️ **Warning**: "Report generated, but company list from knowledge base was NOT retrieved. Results may be incomplete."

### 2. History Page - For Past Runs
When viewing report history, runs that didn't retrieve the company list will show:
- ⚠️ "Company list was NOT retrieved for this run - results may be incomplete"

### 3. Report Content Warning
If the company list wasn't retrieved, a warning will appear at the top of the generated report:
- "⚠️ [SYSTEM WARNING: Company list from knowledge base was not retrieved. Results may be incomplete.]"

## Manual Verification

### Check OpenAI Assistant Configuration

1. **Open OpenAI Dashboard**: https://platform.openai.com/assistants
2. **Select Your Assistant** (the one with ID matching `OPENAI_ASSISTANT_ID`)
3. **Check Vector Store Attachment**:
   - Go to "Knowledge" or "Files" section
   - Verify that a vector store is attached
   - Verify that the company list file is in the vector store
   - File should contain 152+ companies with names, aliases, value chain positions, regions

4. **Check Tools Enabled**:
   - Go to "Tools" section
   - Verify that **"File Search"** tool is enabled
   - This is required for the assistant to retrieve files from the knowledge base

### Check Run Steps in OpenAI Dashboard

1. **View Run Details**: In OpenAI dashboard, go to "Runs" or "Threads"
2. **Check Tool Calls**: Look for `file_search` tool calls in the run steps
3. **Verify File Retrieval**: Check if the company list file was retrieved

### Check Metadata in Database

The `newsletter_runs` table stores metadata including:
- `tool_usage.file_search_called`: Boolean indicating if file_search was called
- `tool_usage.file_search_count`: Number of times file_search was called
- `company_list_retrieved`: Boolean flag (true if file_search was called)

Query example:
```sql
SELECT 
    id,
    created_at,
    metadata->'tool_usage'->>'file_search_called' as company_list_retrieved,
    metadata->'tool_usage'->>'file_search_count' as file_search_count
FROM newsletter_runs
ORDER BY created_at DESC
LIMIT 10;
```

## Troubleshooting

### If Company List is NOT Being Retrieved:

1. **Check Vector Store Attachment**:
   - Ensure vector store is attached to the Assistant
   - Ensure company list file is uploaded to the vector store
   - File name should contain "company" or "companies"

2. **Check File Search Tool**:
   - Ensure File Search tool is enabled in Assistant configuration
   - This is different from Code Interpreter or Function Calling

3. **Check Instructions**:
   - Verify that the system instructions mention the company list
   - Instructions should explicitly require using file_search tool

4. **Check Assistant ID**:
   - Verify `OPENAI_ASSISTANT_ID` environment variable matches your Assistant
   - The Assistant must have the vector store attached

### Expected Behavior

When working correctly:
- Assistant should call `file_search` tool early in the run
- Should retrieve the company list file from vector store
- Should filter companies by value chain positions and regions
- Should search for news about companies from the filtered list
- Metadata will show `file_search_called: true`

## File Search Tool Requirements

The OpenAI Assistant API requires:
- **File Search tool enabled** in Assistant configuration
- **Vector store attached** to the Assistant (not just files)
- **Company list file uploaded** to the vector store
- **Proper file naming** (should contain "company" or "companies" for easy discovery)

## Monitoring

The system now tracks:
- Whether file_search was called (`file_search_called`)
- How many times it was called (`file_search_count`)
- Which files were retrieved (`files_retrieved`)

This information is stored in the `metadata.tool_usage` field of each run and displayed in the Generator app.
