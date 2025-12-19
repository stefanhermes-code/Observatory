"""
Check what files are in the OpenAI Vector Store.
This helps verify the company list is properly uploaded.
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


def get_file_info(client, file_id: str):
    """Get file information."""
    try:
        file_info = client.files.retrieve(file_id)
        return file_info
    except Exception as e:
        return None


def main():
    """Check vector store files."""
    # Fix Windows console encoding
    import sys
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    
    print("=" * 60)
    print("Check Vector Store Files")
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
        client = get_openai_client()
        if not client:
            print("[ERROR] Could not initialize OpenAI client")
            input("Press Enter to exit...")
            return
        
        # List all files
        print("Fetching files from vector store...")
        files = list_vector_store_files(vector_store_id)
        
        if not files:
            print("[WARNING] No files found in vector store!")
            print()
            print("This means the company list is not uploaded.")
            print("Run upload_company_list.bat to upload it.")
            print()
            input("Press Enter to exit...")
            return
        
        print(f"Found {len(files)} file(s) in vector store:")
        print()
        
        for i, file in enumerate(files, 1):
            print(f"{i}. File ID: {file.id}")
            print(f"   Status: {getattr(file, 'status', 'unknown')}")
            
            # Try to get file details
            file_info = get_file_info(client, file.id)
            if file_info:
                print(f"   Filename: {getattr(file_info, 'filename', 'unknown')}")
                print(f"   Purpose: {getattr(file_info, 'purpose', 'unknown')}")
                print(f"   Created: {getattr(file_info, 'created_at', 'unknown')}")
                print(f"   Size: {getattr(file_info, 'bytes', 0)} bytes")
            
            # Check file status in vector store
            file_status = getattr(file, 'status', 'unknown')
            if file_status == 'completed':
                print(f"   ✓ File is indexed and ready")
            elif file_status == 'in_progress':
                print(f"   ⏳ File is still being indexed (wait a few minutes)")
            elif file_status == 'failed':
                print(f"   ✗ File indexing failed - may need to re-upload")
            else:
                print(f"   Status: {file_status}")
            
            print()
        
        print("=" * 60)
        print("Summary:")
        print(f"- Total files: {len(files)}")
        print(f"- If you see 'tmpx...' filenames, these are temporary files")
        print(f"- The Assistant uses semantic search, so filename doesn't matter")
        print(f"- But having multiple files might confuse the Assistant")
        print()
        print("If you see multiple files or old files, consider:")
        print("  1. Run delete_vector_store_files.bat to clean up")
        print("  2. Run upload_company_list.bat to upload fresh")
        print()
        
    except Exception as e:
        print(f"[ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        print()
    
    input("Press Enter to exit...")


if __name__ == "__main__":
    main()

