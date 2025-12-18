"""
Test script to verify Supabase connection and database setup.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_supabase_connection():
    """Test Supabase connection and database access."""
    print("="*60)
    print("Testing Supabase Connection")
    print("="*60)
    print()
    
    # Check environment variables
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_ANON_KEY")
    
    print("1. Checking Environment Variables:")
    print(f"   SUPABASE_URL: {'[OK] Set' if supabase_url else '[FAIL] Missing'}")
    if supabase_url:
        print(f"      {supabase_url}")
    print(f"   SUPABASE_ANON_KEY: {'[OK] Set' if supabase_key else '[FAIL] Missing'}")
    if supabase_key:
        print(f"      (starts with: {supabase_key[:20]}...)")
    print()
    
    if not supabase_url or not supabase_key:
        print("[FAIL] Missing required environment variables!")
        print("   Please add SUPABASE_URL and SUPABASE_ANON_KEY to your .env file.")
        print()
        print("   Get these from:")
        print("   - Supabase Dashboard -> Project Settings -> API")
        print("   - Project URL -> SUPABASE_URL")
        print("   - anon public key -> SUPABASE_ANON_KEY")
        return False
    
    # Test Supabase import
    print("2. Testing Supabase Library:")
    try:
        from supabase import create_client, Client
        print("   [OK] supabase-py library available")
    except ImportError:
        print("   [FAIL] supabase-py not installed")
        print("   Install with: pip install supabase")
        return False
    print()
    
    # Test client initialization
    print("3. Testing Client Initialization:")
    try:
        supabase = create_client(supabase_url, supabase_key)
        print("   [OK] Supabase client initialized successfully")
    except Exception as e:
        print(f"   [FAIL] Error initializing client: {e}")
        return False
    print()
    
    # Test table access
    print("4. Testing Database Tables:")
    tables_to_test = [
        "specification_requests",
        "workspaces",
        "workspace_members",
        "newsletter_specifications",
        "newsletter_runs",
        "audit_log"
    ]
    
    all_tables_ok = True
    for table_name in tables_to_test:
        try:
            # Try to select (even if empty)
            result = supabase.table(table_name).select("*").limit(1).execute()
            print(f"   [OK] {table_name} - accessible")
        except Exception as e:
            error_msg = str(e)
            if "relation" in error_msg.lower() or "does not exist" in error_msg.lower():
                print(f"   [FAIL] {table_name} - table does not exist")
                print(f"          Run development/supabase_schema.sql to create tables")
            else:
                print(f"   [WARN] {table_name} - access issue: {error_msg[:60]}")
            all_tables_ok = False
    
    print()
    
    if not all_tables_ok:
        print("[WARN] Some tables are missing or inaccessible.")
        print("       Run the SQL script in development/supabase_schema.sql to create tables.")
        print()
    
    # Test basic CRUD operation
    print("5. Testing Basic Operations:")
    try:
        # Try to read from specification_requests
        result = supabase.table("specification_requests").select("id").limit(1).execute()
        print("   [OK] Read operation successful")
        
        # Note: We don't test write here to avoid creating test data
        print("   [OK] Connection verified")
    except Exception as e:
        print(f"   [FAIL] Error: {e}")
        return False
    print()
    
    print("="*60)
    if all_tables_ok:
        print("[OK] Supabase connection verified! Database is ready.")
    else:
        print("[WARN] Connection works, but some tables need to be created.")
        print("       See SUPABASE_SETUP.md for instructions.")
    print("="*60)
    
    return True

if __name__ == "__main__":
    test_supabase_connection()

