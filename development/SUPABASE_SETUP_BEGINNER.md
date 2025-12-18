# Supabase Setup Guide - Complete Beginner Edition

## What is Supabase?

Supabase is a backend-as-a-service platform that provides:
- **Database**: PostgreSQL database (like Excel but much more powerful)
- **Storage**: File storage (for storing newsletter HTML files)
- **Authentication**: User login system (we'll use this later)

Think of it as your app's "back office" - it stores all your data securely in the cloud.

---

## Step 1: Get Your Supabase Credentials

You need two pieces of information from your Supabase project to connect your app.

### Finding Your Credentials

1. **In your Supabase dashboard** (where you are now), look at the **left sidebar**
2. Click on **"Settings"** (the gear icon at the bottom)
3. In the Settings menu, click **"API"** (or look for "Project API keys")

You'll see two important values:

#### A. Project URL
- **What it looks like**: `https://xxxxxxxxxxxxx.supabase.co`
- **Where to find it**: Under "Project URL" section
- **Copy this entire URL** - this is your `SUPABASE_URL`

#### B. Anon/Public Key
- **What it looks like**: A long string starting with `eyJ...` (about 200+ characters)
- **Where to find it**: Under "Project API keys" → Look for the key labeled **"anon"** or **"public"**
- **Copy this entire key** - this is your `SUPABASE_ANON_KEY`

⚠️ **Important**: 
- Use the **"anon"** or **"public"** key (NOT the "service_role" key)
- The anon key is safe to use in your app
- Never share your service_role key publicly

---

## Step 2: Add Credentials to Your Project

1. **Open your project folder** in your code editor (where you have the `.env` file)

2. **Open the `.env` file** (it should already exist with OpenAI keys)

3. **Add these two lines** at the bottom (replace with YOUR actual values):

```env
# Supabase Configuration
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=your_anon_key_here
```

**Example** (don't use this, use YOUR values):
```env
SUPABASE_URL=https://abcdefghijklmnop.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFiY2RlZmdoaWprbG1ub3AiLCJyb2xlIjoiYW5vbiIsImlhdCI6MTYxNjIzOTAyMiwiZXhwIjoxOTMxODE1MDIyfQ.example_signature_here
```

4. **Save the file**

---

## Step 3: Create the Database Tables

Your app needs several "tables" (think of them as spreadsheets) to store data. We'll create them using SQL (Structured Query Language).

### What are Tables?

Think of tables like Excel spreadsheets:
- Each table has **columns** (like Excel columns: Name, Email, Date)
- Each row is a **record** (like one person's information)

### Creating Tables Step-by-Step

1. **In your Supabase dashboard**, look at the **left sidebar**
2. Click on **"SQL Editor"** (the icon that looks like `>_` or code brackets)
3. You'll see a blank editor area

4. **Open the file `development/supabase_schema.sql`** from your project folder
   - This file contains all the SQL commands needed to create your tables
   - Copy the **entire contents** of this file

5. **Paste the SQL into the Supabase SQL Editor**

6. **Click the "Run" button** (usually at the bottom right, or press Ctrl+Enter)
   - You might see a confirmation dialog - click "Run" or "Execute"

7. **Wait for success message**
   - You should see: "Success. No rows returned" or similar
   - This means all tables were created successfully!

### What Tables Were Created?

After running the SQL, you'll have these tables:

1. **specification_requests** - Stores newsletter requests from the Configurator app
2. **workspaces** - Stores company/workspace information
3. **workspace_members** - Links users to workspaces
4. **newsletter_specifications** - Stores active newsletter configurations
5. **newsletter_runs** - Stores generation history (when newsletters were created)
6. **audit_log** - Stores admin actions for security tracking

### Verify Tables Were Created

1. In Supabase dashboard, click **"Table Editor"** (grid icon in left sidebar)
2. You should see all 6 tables listed
3. Click on any table to see its structure (columns)

---

## Step 4: Test Your Connection

Now let's verify everything is working!

1. **Open your terminal/command prompt**
2. **Navigate to your project folder**:
   ```bash
   cd "C:\Users\Stefan Hermes\OneDrive - Foam Innovations & Solutions\Documenten\Bedrijven\HTC\PRODUCTS\12. Polyurethane Observatory"
   ```

3. **Run the test script**:
   ```bash
   python test_supabase_connection.py
   ```

4. **What you should see**:
   ```
   ============================================================
   Testing Supabase Connection
   ============================================================
   
   1. Checking Environment Variables:
      SUPABASE_URL: [OK] Set
      SUPABASE_ANON_KEY: [OK] Set
   
   2. Testing Supabase Library:
      [OK] supabase-py library available
   
   3. Testing Client Initialization:
      [OK] Supabase client initialized successfully
   
   4. Testing Database Tables:
      [OK] specification_requests - accessible
      [OK] workspaces - accessible
      [OK] workspace_members - accessible
      [OK] newsletter_specifications - accessible
      [OK] newsletter_runs - accessible
      [OK] audit_log - accessible
   
   5. Testing Basic Operations:
      [OK] Read operation successful
      [OK] Connection verified
   
   ============================================================
   [OK] Supabase connection verified! Database is ready.
   ============================================================
   ```

### If You See Errors

**Error: "Missing required environment variables"**
- Check that you added `SUPABASE_URL` and `SUPABASE_ANON_KEY` to `.env`
- Make sure there are no extra spaces or quotes
- Restart your terminal after editing `.env`

**Error: "table does not exist"**
- Go back to Step 3 and run the SQL script again
- Make sure you copied the ENTIRE contents of `supabase_schema.sql`

**Error: "supabase-py not installed"**
- Run: `pip install supabase`
- Then try the test again

---

## Step 5: Set Up Storage (For Newsletter Files)

Your app will generate HTML newsletter files. We need a place to store them.

1. **In Supabase dashboard**, click **"Storage"** (folder icon in left sidebar)

2. **Click "Create a new bucket"** or **"New bucket"**

3. **Bucket settings**:
   - **Name**: `newsletter-artifacts` (exactly this name)
   - **Public bucket**: Toggle this to **ON** (so users can download newsletters)
   - Click **"Create bucket"**

4. **That's it!** Your storage is ready.

---

## Step 6: Verify Everything Works

Let's test that your apps can now use Supabase:

### Test Configurator App

1. **Run the Configurator**:
   ```bash
   streamlit run configurator_app.py
   ```

2. **Fill out the form** and submit a test newsletter request

3. **Check Supabase**:
   - Go to Supabase → Table Editor → `specification_requests`
   - You should see your test submission!

### Test Admin App

1. **Run the Admin app**:
   ```bash
   streamlit run admin_app.py
   ```

2. **Login** with an owner email (check your `.env` for `OWNER_EMAILS`)

3. **You should see** the test request from Configurator

### Test Generator App

1. **Run the Generator app**:
   ```bash
   streamlit run generator_app.py
   ```

2. **Login** with a workspace member email

3. **You should see** available newsletter specifications

---

## Troubleshooting Common Issues

### Issue: "Connection refused" or "Network error"
- **Check**: Is your Supabase project paused? (Free tier projects pause after inactivity)
- **Solution**: Go to Supabase dashboard → Settings → General → Resume project

### Issue: "Permission denied" or "RLS policy" errors
- **Check**: Row Level Security (RLS) might be blocking access
- **Solution**: For now, we'll use the anon key which should work. If you see RLS errors, we may need to adjust policies (advanced topic)

### Issue: Tables exist but apps show "simulated" messages
- **Check**: Is `.env` file in the correct location? (same folder as `app.py` files)
- **Check**: Did you restart your terminal after editing `.env`?
- **Check**: Are environment variable names exactly `SUPABASE_URL` and `SUPABASE_ANON_KEY`?

### Issue: Can't find SQL Editor
- **Look for**: Code icon `>_` or `</>` in the left sidebar
- **Alternative**: Click "Database" → "SQL Editor"

---

## What's Next?

Once Supabase is set up:

1. ✅ **Database**: Ready to store all your data
2. ✅ **Storage**: Ready to store newsletter HTML files
3. ⏳ **Authentication**: Can be integrated later (currently using simple email-based auth)

## Understanding Your Setup

### How It Works

```
Your Streamlit Apps → .env file (credentials) → Supabase Database
                                      ↓
                              Stores all data:
                              - Newsletter requests
                              - Workspaces
                              - Generation history
                              - Admin logs
```

### Current Status

- ✅ **OpenAI**: Connected and working
- ✅ **Supabase**: Database ready (after you complete setup)
- ⏳ **GitHub**: Not needed for database setup (we can set up later)

---

## Quick Reference

### Where to Find Things in Supabase

- **Credentials**: Settings (gear) → API
- **Create Tables**: SQL Editor → Paste SQL → Run
- **View Data**: Table Editor → Click table name
- **Storage**: Storage → Create bucket
- **Test Connection**: Run `python test_supabase_connection.py`

### Important Files

- `.env` - Contains your credentials (keep this secret!)
- `supabase_schema.sql` - SQL to create tables
- `test_supabase_connection.py` - Test script

---

## Need Help?

If you get stuck:

1. **Check the error message** - it usually tells you what's wrong
2. **Verify credentials** - Make sure they're correct in `.env`
3. **Check Supabase dashboard** - Are tables created? Is project active?
4. **Run test script** - `python test_supabase_connection.py` will diagnose issues

---

## Summary Checklist

- [ ] Got `SUPABASE_URL` from Settings → API
- [ ] Got `SUPABASE_ANON_KEY` from Settings → API (anon/public key)
- [ ] Added both to `.env` file
- [ ] Opened SQL Editor in Supabase
- [ ] Copied entire `supabase_schema.sql` file
- [ ] Pasted and ran SQL in Supabase
- [ ] Verified tables exist (Table Editor)
- [ ] Created storage bucket `newsletter-artifacts`
- [ ] Ran `python test_supabase_connection.py` - all tests pass
- [ ] Tested Configurator app - can submit requests
- [ ] Tested Admin app - can see requests
- [ ] Tested Generator app - can see specifications

Once all checkboxes are done, your Supabase setup is complete! 🎉

