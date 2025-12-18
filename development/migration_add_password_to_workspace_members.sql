-- Migration: Add password field to workspace_members table
-- Run this in Supabase SQL Editor
-- 
-- This migration adds password authentication support for workspace members.
-- Passwords are stored as bcrypt hashes (60 characters) but we use VARCHAR(255) for flexibility.
-- The column is nullable to allow existing members without passwords (they will need to set one).

ALTER TABLE workspace_members 
ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255);

COMMENT ON COLUMN workspace_members.password_hash IS 'Bcrypt hashed password for workspace member authentication. Nullable to support existing members who need to set passwords.';

-- Optional: Add index for faster password lookups (if needed)
-- CREATE INDEX IF NOT EXISTS idx_workspace_members_password ON workspace_members(user_email) WHERE password_hash IS NOT NULL;

