-- Migration 019: RLS policies for newsletter_specifications (and specification_requests) so Admin/Generator can insert and update.
-- Error seen without this: "new row violates row-level security policy for table newsletter_specifications" (code 42501).
-- Apply in Supabase SQL Editor (Dashboard → SQL Editor → New query). Idempotent.
--
-- Your app uses the Supabase anon key; RLS was blocking INSERT. These policies allow the anon role to
-- perform the operations the Observatory Admin and Generator apps need. Auth is handled at the app layer (Streamlit).

-- 1) newsletter_specifications: allow anon to SELECT, INSERT, UPDATE, DELETE
--    Required for: Admin "Assign & Activate" (insert), Generator/Admin listing and edits (select/update).
DROP POLICY IF EXISTS "Allow anon all newsletter_specifications" ON newsletter_specifications;
CREATE POLICY "Allow anon all newsletter_specifications"
  ON newsletter_specifications
  FOR ALL
  TO anon
  USING (true)
  WITH CHECK (true);

-- 2) specification_requests: allow anon to SELECT and UPDATE (Admin reads requests and sets status to paid_activated)
DROP POLICY IF EXISTS "Allow anon all specification_requests" ON specification_requests;
CREATE POLICY "Allow anon all specification_requests"
  ON specification_requests
  FOR ALL
  TO anon
  USING (true)
  WITH CHECK (true);
