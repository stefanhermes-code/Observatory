# Quick Start: Supabase Setup (5 Minutes)

## Step 1: Get Your Credentials (2 minutes)

1. In Supabase dashboard → Click **Settings** (gear icon at bottom of left sidebar)
2. Click **API** in the settings menu
3. Copy these two values:

   **A. Project URL**
   - Look for "Project URL" section
   - Copy the entire URL (looks like `https://xxxxx.supabase.co`)
   - This is your `SUPABASE_URL`

   **B. Anon Key**
   - Look for "Project API keys" section
   - Find the key labeled **"anon"** or **"public"**
   - Copy the entire key (long string starting with `eyJ...`)
   - This is your `SUPABASE_ANON_KEY`

## Step 2: Add to .env File (1 minute)

Open your `.env` file and add:

```env
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=your_anon_key_here
```

Replace with YOUR actual values from Step 1.

## Step 3: Create Database Tables (1 minute)

1. In Supabase dashboard → Click **SQL Editor** (code icon `>_` in left sidebar)
2. Open `development/supabase_schema.sql` file from your project
3. Copy **ALL** the contents
4. Paste into Supabase SQL Editor
5. Click **Run** button (or press Ctrl+Enter)
6. Wait for "Success" message

## Step 4: Create Storage Bucket (30 seconds)

1. In Supabase dashboard → Click **Storage** (folder icon)
2. Click **"New bucket"** or **"Create bucket"**
3. Name: `newsletter-artifacts`
4. Toggle **"Public bucket"** to ON
5. Click **Create**

## Step 5: Test It! (30 seconds)

Run in terminal:
```bash
python test_supabase_connection.py
```

You should see all `[OK]` messages!

---

## That's It! 🎉

Your Supabase is now set up. Your apps will automatically use the real database instead of simulation mode.

---

**Need more help?** See [SUPABASE_SETUP_BEGINNER.md](SUPABASE_SETUP_BEGINNER.md) for detailed explanations.

