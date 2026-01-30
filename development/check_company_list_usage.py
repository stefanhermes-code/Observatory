"""
Quick script to check if company list is being retrieved from knowledge base.
Run this to verify recent runs and their file_search usage.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.generator_db import get_specification_history
from datetime import datetime

def check_company_list_usage(spec_id: str = None, limit: int = 10):
    """
    Check recent runs to see if company list was retrieved.
    
    Args:
        spec_id: Optional specification ID to check. If None, checks all specs.
        limit: Number of recent runs to check
    """
    print("=" * 70)
    print("COMPANY LIST USAGE VERIFICATION")
    print("=" * 70)
    print()
    
    # Get recent runs
    if spec_id:
        runs = get_specification_history(spec_id)
    else:
        # Get runs from all specs (you may need to modify this based on your DB structure)
        print("⚠️  Please provide a spec_id to check specific runs")
        print("   Or modify this script to query all runs from database")
        return
    
    if not runs:
        print("❌ No runs found for this specification")
        return
    
    runs_to_check = runs[:limit]
    
    print(f"Checking {len(runs_to_check)} most recent runs...")
    print()
    
    retrieved_count = 0
    not_retrieved_count = 0
    
    for i, run in enumerate(runs_to_check, 1):
        run_id = run.get("id", "Unknown")
        created_at = run.get("created_at", "Unknown")
        status = run.get("status", "unknown")
        
        # Parse created_at if it's a string
        if isinstance(created_at, str):
            try:
                dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                created_str = dt.strftime("%Y-%m-%d %H:%M")
            except:
                created_str = created_at[:19] if len(created_at) > 19 else created_at
        else:
            created_str = str(created_at)
        
        # Check metadata
        metadata = run.get("metadata", {})
        tool_usage = metadata.get("tool_usage", {})
        file_search_called = tool_usage.get("file_search_called", False)
        file_search_count = tool_usage.get("file_search_count", 0)
        
        status_icon = "✅" if status == "success" else "❌" if status == "failed" else "⏳"
        list_icon = "✅" if file_search_called else "⚠️"
        
        print(f"{i}. {status_icon} {created_str} - {status.upper()}")
        print(f"   Run ID: {run_id}")
        print(f"   Company List Retrieved: {list_icon} {'YES' if file_search_called else 'NO'}")
        if file_search_called:
            print(f"   File Search Calls: {file_search_count}")
            retrieved_count += 1
        else:
            print(f"   ⚠️  Company list was NOT retrieved from knowledge base")
            not_retrieved_count += 1
        print()
    
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total runs checked: {len(runs_to_check)}")
    print(f"✅ Company list retrieved: {retrieved_count}")
    print(f"⚠️  Company list NOT retrieved: {not_retrieved_count}")
    
    if not_retrieved_count > 0:
        print()
        print("⚠️  WARNING: Some runs did not retrieve the company list!")
        print("   Check OpenAI Assistant configuration:")
        print("   1. Vector store is attached to Assistant")
        print("   2. File Search tool is enabled")
        print("   3. Company list file is in the vector store")
    else:
        print()
        print("✅ All checked runs successfully retrieved the company list!")

if __name__ == "__main__":
    # You can modify this to check a specific spec_id
    # Get spec_id from command line or modify here
    if len(sys.argv) > 1:
        spec_id = sys.argv[1]
    else:
        print("Usage: python check_company_list_usage.py <spec_id>")
        print("Or modify the script to use a default spec_id")
        print()
        print("To find a spec_id, check the Generator app or database")
        sys.exit(1)
    
    check_company_list_usage(spec_id)
