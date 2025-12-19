"""
Clean up old files from vector store and re-upload company list.
This ensures a clean upload with proper indexing.
"""

import sys
from pathlib import Path
import os
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.company_list_manager import upload_company_list_to_assistant
from development.delete_vector_store_files import list_vector_store_files, delete_vector_store_file, get_openai_client
load_dotenv()


def main():
    """Clean up and re-upload company list."""
    # Fix Windows console encoding
    import sys
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    
    print("=" * 60)
    print("Cleanup and Re-upload Company List")
    print("=" * 60)
    print()
    
    vector_store_id = os.getenv("OPENAI_VECTOR_STORE_ID")
    if not vector_store_id:
        print("[ERROR] OPENAI_VECTOR_STORE_ID not set in .env file")
        print()
        input("Press Enter to exit...")
        return
    
    assistant_id = os.getenv("OPENAI_ASSISTANT_ID")
    if not assistant_id:
        print("[ERROR] OPENAI_ASSISTANT_ID not set in .env file")
        print()
        input("Press Enter to exit...")
        return
    
    print(f"Vector Store ID: {vector_store_id}")
    print(f"Assistant ID: {assistant_id}")
    print()
    
    try:
        # Step 1: List and delete old files
        print("Step 1: Checking existing files...")
        files = list_vector_store_files(vector_store_id)
        
        if files:
            print(f"Found {len(files)} file(s) in vector store:")
            for i, file in enumerate(files, 1):
                print(f"  {i}. File ID: {file.id} (Status: {getattr(file, 'status', 'unknown')})")
            print()
            
            print("Deleting old files...")
            deleted_count = 0
            for file in files:
                try:
                    delete_vector_store_file(vector_store_id, file.id)
                    print(f"  [OK] Deleted: {file.id}")
                    deleted_count += 1
                except Exception as e:
                    print(f"  [ERROR] Failed to delete {file.id}: {str(e)}")
            
            print(f"\n[SUCCESS] Deleted {deleted_count} file(s)")
            print()
        else:
            print("[INFO] No existing files found in vector store")
            print()
        
        # Step 2: Upload new company list
        print("Step 2: Uploading company list...")
        print()
        
        company_list_path = Path(__file__).parent / "company_list.json"
        
        if not company_list_path.exists():
            print(f"[ERROR] Company list file not found: {company_list_path}")
            print()
            print("Please run convert_company_list.bat first to create the JSON file.")
            input("Press Enter to exit...")
            return
        
        result = upload_company_list_to_assistant(
            assistant_id=assistant_id,
            company_list_path=str(company_list_path)
        )
        
        print()
        print("[SUCCESS] Company list uploaded successfully!")
        print()
        print(f"File ID: {result['file_id']}")
        print(f"Vector Store ID: {result['vector_store_id']}")
        print()
        print("The Assistant will now use this company list when generating reports.")
        print("Note: It may take a few minutes for the file to be fully indexed.")
        print()
        
    except Exception as e:
        print(f"[ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        print()
    
    input("Press Enter to exit...")


if __name__ == "__main__":
    main()

