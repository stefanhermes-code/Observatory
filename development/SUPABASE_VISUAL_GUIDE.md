# Supabase Setup - Visual Step-by-Step Guide

Based on what you're seeing in your Supabase dashboard right now.

---

## What You're Looking At

You're on the **Home** page of your Supabase project. You can see:
- Left sidebar with icons
- Top navigation bar
- Main content area showing "Welcome to your new project"

---

## Step 1: Get Your Credentials

### Where to Click:

1. **Look at the LEFT SIDEBAR** (dark gray area on the left)
2. **Scroll down** to the bottom
3. **Click the GEAR ICON** ⚙️ - This is **"Settings"** or **"Project Settings"**

### What You'll See:

A new page with tabs/sections. Look for:
- **API** tab or section
- Click on **"API"**

### On the API Page:

You'll see two important sections:

#### Section 1: Project URL
- **Label**: "Project URL" or "API URL"
- **Value**: Something like `https://abcdefghijklmnop.supabase.co`
- **Action**: Click the copy icon (📋) or select and copy this entire URL
- **This is**: Your `SUPABASE_URL`

#### Section 2: Project API Keys
- You'll see a table or list with different keys
- Look for the row labeled **"anon"** or **"public"**
- **Value**: A very long string starting with `eyJhbGciOiJIUzI1NiIs...`
- **Action**: Click the copy icon (📋) or select and copy this entire key
- **This is**: Your `SUPABASE_ANON_KEY`

⚠️ **Don't use**: The "service_role" key (that's secret and dangerous)

---

## Step 2: Add to Your .env File

1. **Go back to your code editor** (where your project files are)
2. **Open the `.env` file** (same folder as your Python files)
3. **Add these lines** at the bottom:

```env
# Supabase Configuration
SUPABASE_URL=paste_your_url_here
SUPABASE_ANON_KEY=paste_your_key_here
```

**Replace** `paste_your_url_here` and `paste_your_key_here` with the values you just copied.

**Example** (don't copy this, use YOUR values):
```env
SUPABASE_URL=https://abcdefghijklmnop.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFiY2RlZmdoaWprbG1ub3AiLCJyb2xlIjoiYW5vbiIsImlhdCI6MTYxNjIzOTAyMiwiZXhwIjoxOTMxODE1MDIyfQ.example
```

4. **Save the file** (Ctrl+S)

---

## Step 3: Create Database Tables

### Where to Click:

1. **Back in Supabase dashboard**
2. **Look at LEFT SIDEBAR** again
3. **Find the icon that looks like code**: `>_` or `</>` 
   - This is **"SQL Editor"**
   - It's usually near the top, after "Table Editor"
4. **Click "SQL Editor"**

### What You'll See:

- A blank editor area (like a code editor)
- A "Run" button somewhere (usually bottom right)
- Maybe some example SQL on the left

### What to Do:

1. **Open your project folder** in your code editor
2. **Find the file**: `development/supabase_schema.sql`
3. **Open it** - you'll see lots of SQL code
4. **Select ALL** the text (Ctrl+A)
5. **Copy it** (Ctrl+C)
6. **Go back to Supabase SQL Editor**
7. **Click in the editor** (to make sure it's active)
8. **Paste** (Ctrl+V) - all the SQL should appear
9. **Click "Run"** button (or press Ctrl+Enter)
10. **Wait** - you should see a success message like "Success. No rows returned"

✅ **Success!** Your tables are now created!

### Verify Tables Were Created:

1. **Click "Table Editor"** in the left sidebar (grid icon)
2. You should now see **6 tables** listed:
   - specification_requests
   - workspaces
   - workspace_members
   - newsletter_specifications
   - newsletter_runs
   - audit_log

---

## Step 4: Create Storage Bucket

### Where to Click:

1. **Look at LEFT SIDEBAR**
2. **Find the FOLDER icon** 📁 - This is **"Storage"**
3. **Click "Storage"**

### What You'll See:

- A page about storage buckets
- A button like **"New bucket"** or **"Create bucket"** or **"Create a new bucket"**

### What to Do:

1. **Click "New bucket"** or **"Create bucket"**
2. **A form will appear** with fields:
   - **Name**: Type exactly: `newsletter-artifacts`
   - **Public bucket**: Toggle this to **ON** (slide it to the right)
   - **File size limit**: Leave default
   - **Allowed MIME types**: Leave default
3. **Click "Create bucket"** or **"Save"**

✅ **Done!** Storage is ready.

---

## Step 5: Test Your Setup

### Open Terminal/Command Prompt:

1. **Open PowerShell** or **Command Prompt**
2. **Navigate to your project folder**:

```powershell
cd "C:\Users\Stefan Hermes\OneDrive - Foam Innovations & Solutions\Documenten\Bedrijven\HTC\PRODUCTS\12. Polyurethane Observatory"
```

3. **Run the test**:

```powershell
python test_supabase_connection.py
```

### What You Should See:

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

### If You See Errors:

**"[FAIL] Missing required environment variables"**
- Go back to Step 2
- Make sure you saved the `.env` file
- Make sure there are no extra spaces
- Restart your terminal

**"[FAIL] table does not exist"**
- Go back to Step 3
- Make sure you copied ALL the SQL
- Try running the SQL again

---

## You're Done! 🎉

Your Supabase is now fully set up and connected to your PU Observatory platform!

### What Happens Now:

- ✅ Your apps will use the real Supabase database
- ✅ Data will be stored permanently
- ✅ You can view data in Supabase Table Editor
- ✅ Newsletter files will be stored in Storage

### Next Steps:

1. **Test Configurator**: `streamlit run configurator_app.py`
   - Submit a test request
   - Check Supabase → Table Editor → `specification_requests` to see it!

2. **Test Admin**: `streamlit run admin_app.py`
   - Login and approve requests

3. **Test Generator**: `streamlit run generator_app.py`
   - Generate newsletters!

---

## Quick Reference: Where Things Are

| What You Need | Where to Find It |
|--------------|------------------|
| **Credentials** | Settings (gear) → API |
| **Create Tables** | SQL Editor (`>_` icon) |
| **View Data** | Table Editor (grid icon) |
| **Storage** | Storage (folder icon) |
| **Test Connection** | Run `python test_supabase_connection.py` |

---

## About GitHub

You mentioned connecting GitHub but not creating the repo yet. That's fine! 

**GitHub is NOT needed for Supabase setup.** You can:
- Set up Supabase first (what we just did)
- Create GitHub repo later (optional, for version control)
- They work independently

The Supabase database works whether you have GitHub or not.

---

**Need more help?** Check [SUPABASE_SETUP_BEGINNER.md](SUPABASE_SETUP_BEGINNER.md) for detailed explanations of everything.

