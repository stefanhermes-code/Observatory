-- Migration: Add report_options column for live alignment plan (§13, §14)
-- Stores report_title, included_sections, signal_map_enabled, evidence_appendix_enabled,
-- minimum_signal_strength_in_report, company_signal_tracking_enabled.
-- Run this in your Supabase SQL editor if the column does not exist.

-- specification_requests: so Configurator-submitted report options are stored
ALTER TABLE specification_requests
ADD COLUMN IF NOT EXISTS report_options JSONB DEFAULT NULL;

-- newsletter_specifications: so Admin can persist report options when assigning/editing
ALTER TABLE newsletter_specifications
ADD COLUMN IF NOT EXISTS report_options JSONB DEFAULT NULL;

COMMENT ON COLUMN specification_requests.report_options IS 'Report layer options: report_title, included_sections, signal_map_enabled, evidence_appendix_enabled, minimum_signal_strength_in_report, company_signal_tracking_enabled';
COMMENT ON COLUMN newsletter_specifications.report_options IS 'Report layer options; flattened into spec by get_specification_detail for generator';
