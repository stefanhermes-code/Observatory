"""
Utility script to upload company list to OpenAI Assistant's vector store.
Run this script whenever the company list is updated.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.company_list_manager import upload_company_list_to_assistant
import os
from dotenv import load_dotenv

load_dotenv()


def main():
    """Upload company list to OpenAI Assistant."""
    # Fix Windows console encoding
    import sys
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    
    print("=" * 60)
    print("Uploading company list to OpenAI Assistant...")
    print("=" * 60)
    print("")
    
    assistant_id = os.getenv("OPENAI_ASSISTANT_ID")
    if not assistant_id:
        print("[ERROR] OPENAI_ASSISTANT_ID not set in .env file")
        return
    
    vector_store_id = os.getenv("OPENAI_VECTOR_STORE_ID")
    if vector_store_id:
        print(f"[INFO] Using vector store from .env: {vector_store_id}")
    else:
        print("[INFO] No OPENAI_VECTOR_STORE_ID in .env - will create or find existing one")
    print("")
    
    company_list_path = Path(__file__).parent / "company_list.json"
    
    if not company_list_path.exists():
        print(f"[ERROR] Company list file not found: {company_list_path}")
        print("")
        print("Please run convert_company_list.bat first to create the JSON file.")
        return
    
    try:
        result = upload_company_list_to_assistant(
            assistant_id=assistant_id,
            company_list_path=str(company_list_path)
        )
        
        print("")
        print("[SUCCESS] Company list uploaded to Assistant.")
        print("")
        print(f"File ID: {result['file_id']}")
        print(f"Vector Store ID: {result['vector_store_id']}")
        print("")
        
        # Check if vector store ID is already in .env
        if not vector_store_id:
            print("IMPORTANT: Add this to your .env file:")
            print(f"OPENAI_VECTOR_STORE_ID={result['vector_store_id']}")
            print("")
        
        print("The Assistant will now use this company list when generating reports.")
        print("You can update the company list by:")
        print("  1. Editing development/company_list.json")
        print("  2. Running this script again to upload the updated list")
        
    except Exception as e:
        print(f"[ERROR] Error uploading company list: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

