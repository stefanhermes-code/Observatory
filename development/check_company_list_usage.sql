-- SQL Query to Check Company List Usage
-- Run this in Supabase SQL Editor to see which runs retrieved the company list

-- Check recent runs and their company list retrieval status
SELECT 
    nr.id AS run_id,
    ns.newsletter_name,
    nr.created_at,
    nr.status,
    nr.user_email,
    -- Extract company list retrieval status from metadata
    COALESCE(
        (nr.metadata->'tool_usage'->>'file_search_called')::boolean,
        false
    ) AS company_list_retrieved,
    COALESCE(
        (nr.metadata->'tool_usage'->>'file_search_count')::integer,
        0
    ) AS file_search_count,
    -- Show warning if not retrieved
    CASE 
        WHEN COALESCE((nr.metadata->'tool_usage'->>'file_search_called')::boolean, false) = true 
        THEN '✅ Retrieved'
        ELSE '⚠️ NOT Retrieved'
    END AS status_display
FROM newsletter_runs nr
LEFT JOIN newsletter_specifications ns ON nr.specification_id = ns.id
WHERE nr.status = 'success'  -- Only check successful runs
ORDER BY nr.created_at DESC
LIMIT 20;

-- Summary query - count how many runs retrieved vs didn't retrieve
SELECT 
    CASE 
        WHEN COALESCE((metadata->'tool_usage'->>'file_search_called')::boolean, false) = true 
        THEN '✅ Retrieved'
        ELSE '⚠️ NOT Retrieved'
    END AS retrieval_status,
    COUNT(*) AS run_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS percentage
FROM newsletter_runs
WHERE status = 'success'
GROUP BY 
    CASE 
        WHEN COALESCE((metadata->'tool_usage'->>'file_search_called')::boolean, false) = true 
        THEN '✅ Retrieved'
        ELSE '⚠️ NOT Retrieved'
    END
ORDER BY run_count DESC;
