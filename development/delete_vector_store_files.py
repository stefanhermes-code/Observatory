"""
Delete files from OpenAI Vector Store.
Use this to clear the old company list before uploading a new one.
"""

import sys
from pathlib import Path
import os
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("[ERROR] OpenAI package not installed")


def get_openai_client():
    """Initialize and return OpenAI client."""
    if not OPENAI_AVAILABLE:
        return None
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    
    return OpenAI(api_key=api_key)


def list_vector_store_files(vector_store_id: str):
    """List all files in a vector store."""
    client = get_openai_client()
    if not client:
        raise Exception("OpenAI client not available. Check OPENAI_API_KEY.")
    
    files = client.beta.vector_stores.files.list(vector_store_id=vector_store_id)
    return files.data


def delete_vector_store_file(vector_store_id: str, file_id: str):
    """Delete a file from a vector store."""
    client = get_openai_client()
    if not client:
        raise Exception("OpenAI client not available. Check OPENAI_API_KEY.")
    
    result = client.beta.vector_stores.files.delete(
        vector_store_id=vector_store_id,
        file_id=file_id
    )
    return result


def main():
    """Delete files from vector store."""
    # Fix Windows console encoding
    import sys
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    
    print("=" * 60)
    print("Delete Files from Vector Store")
    print("=" * 60)
    print()
    
    vector_store_id = os.getenv("OPENAI_VECTOR_STORE_ID")
    if not vector_store_id:
        print("[ERROR] OPENAI_VECTOR_STORE_ID not set in .env file")
        print()
        input("Press Enter to exit...")
        return
    
    print(f"Vector Store ID: {vector_store_id}")
    print()
    
    try:
        # List all files
        print("Fetching files from vector store...")
        files = list_vector_store_files(vector_store_id)
        
        if not files:
            print("[INFO] No files found in vector store.")
            print()
            input("Press Enter to exit...")
            return
        
        print(f"Found {len(files)} file(s) in vector store:")
        print()
        for i, file in enumerate(files, 1):
            print(f"{i}. File ID: {file.id}")
            print(f"   Status: {getattr(file, 'status', 'unknown')}")
            print()
        
        # Ask for confirmation
        print("=" * 60)
        response = input("Delete ALL files from this vector store? (yes/no): ").strip().lower()
        
        if response != 'yes':
            print("Cancelled.")
            print()
            input("Press Enter to exit...")
            return
        
        # Delete all files
        print()
        print("Deleting files...")
        deleted_count = 0
        for file in files:
            try:
                delete_vector_store_file(vector_store_id, file.id)
                print(f"[OK] Deleted file: {file.id}")
                deleted_count += 1
            except Exception as e:
                print(f"[ERROR] Failed to delete {file.id}: {str(e)}")
        
        print()
        print(f"[SUCCESS] Deleted {deleted_count} out of {len(files)} file(s)")
        print()
        print("You can now upload your new company list using upload_company_list.bat")
        print()
        
    except Exception as e:
        print(f"[ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        print()
    
    input("Press Enter to exit...")


if __name__ == "__main__":
    main()

