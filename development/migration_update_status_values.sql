-- Migration: Update status values for specification_requests
-- Date: 2025-12-16
-- Description: Adds additional status values needed for the workflow: approved_pending_invoice, invoiced, paid_activated

ALTER TABLE specification_requests 
DROP CONSTRAINT IF EXISTS specification_requests_status_check;

ALTER TABLE specification_requests 
ADD CONSTRAINT specification_requests_status_check 
CHECK (status IN (
    'pending_review', 
    'approved', 
    'approved_pending_invoice',
    'invoiced',
    'paid_activated',
    'rejected', 
    'on_hold'
));

