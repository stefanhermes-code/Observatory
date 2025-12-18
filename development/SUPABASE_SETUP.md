# Supabase Setup Guide

> **👋 New to Supabase?** Check out **[SUPABASE_SETUP_BEGINNER.md](SUPABASE_SETUP_BEGINNER.md)** for a complete step-by-step guide with detailed explanations!

## Overview

The PU Observatory platform uses Supabase for:
- **Database**: PostgreSQL for all data storage
- **Storage**: HTML artifacts (newsletter files)
- **Authentication**: User authentication (to be integrated)

## Required Credentials

You need two values from your Supabase project:

1. **Project URL**: Found in Project Settings → API → Project URL
   - Format: `https://xxxxx.supabase.co`

2. **Anon/Public Key**: Found in Project Settings → API → Project API keys → `anon` `public`
   - This is the public key safe to use in client-side code

## Environment Variables

Add these to your `.env` file:

```env
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_ANON_KEY=your_anon_key_here
```

## Database Schema

The platform requires the following tables. Run the SQL script in `development/supabase_schema.sql` to create them.

### Core Tables

1. **specification_requests** - Configurator submissions (pending approval)
2. **workspaces** - Workspace/company entities
3. **workspace_members** - User-workspace relationships
4. **specifications** - Active newsletter specifications
5. **newsletter_runs** - Generation history and artifacts
6. **audit_logs** - Admin action audit trail

### Optional Tables

- **categories** - Custom category definitions (defaults to taxonomy.py)
- **regions** - Custom region definitions (defaults to taxonomy.py)

## Quick Setup Steps

1. **Create Supabase Project**
   - Go to https://supabase.com
   - Create a new project
   - Wait for database to initialize

2. **Get Credentials**
   - Go to Project Settings → API
   - Copy Project URL → `SUPABASE_URL`
   - Copy `anon` `public` key → `SUPABASE_ANON_KEY`

3. **Create Database Schema**
   - Go to SQL Editor in Supabase dashboard
   - Run the SQL from `development/supabase_schema.sql`

4. **Set Up Storage Bucket** (for HTML artifacts)
   - Go to Storage → Create bucket
   - Name: `newsletter-artifacts`
   - Make it public (or set up RLS policies)

5. **Update .env File**
   - Add `SUPABASE_URL` and `SUPABASE_ANON_KEY`

6. **Test Connection**
   - Run: `python test_supabase_connection.py`

## Current Status

- ✅ Code is ready for Supabase integration
- ✅ Simulation fallback works for development
- ⏳ Database schema needs to be created
- ⏳ Storage bucket needs to be configured
- ⏳ Authentication integration pending

## Testing

Once configured, test the connection:

```bash
python test_supabase_connection.py
```

This will verify:
- ✅ Connection to Supabase
- ✅ Table access permissions
- ✅ Basic CRUD operations

## Row Level Security (RLS)

For production, you'll need to set up RLS policies:

- **specification_requests**: Public read/write for submissions
- **workspaces**: Owner-only access
- **workspace_members**: Users can read their own memberships
- **specifications**: Workspace members can read their workspace specs
- **newsletter_runs**: Workspace members can read their workspace runs
- **audit_logs**: Owner-only access

See `supabase_rls_policies.sql` for example policies.

## Storage Setup

1. Create bucket: `newsletter-artifacts`
2. Set public access (or configure RLS)
3. Update code to use Supabase Storage API for artifact uploads

## Next Steps After Setup

1. Test database operations in each app
2. Configure RLS policies for security
3. Set up Supabase Auth (replace current session-based auth)
4. Test end-to-end workflow:
   - Configurator → Admin → Generator

