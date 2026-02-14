"""
View the company list in formatted form (as loaded from JSON).
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.company_list_manager import load_company_list, format_company_list_for_display
from dotenv import load_dotenv

load_dotenv()


def main():
    """Show the company list (formatted)."""
    # Fix Windows console encoding
    import sys
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    
    print("=" * 60)
    print("Company List (formatted)")
    print("=" * 60)
    print()
    
    # Try to load the company list - check multiple possible locations
    dev_dir = Path(__file__).parent
    json_file = None
    
    # Check for company_list.json first
    if (dev_dir / "company_list.json").exists():
        json_file = dev_dir / "company_list.json"
        print(f"[INFO] Using: company_list.json")
    # Check for test_company_list.json as fallback
    elif (dev_dir / "test_company_list.json").exists():
        json_file = dev_dir / "test_company_list.json"
        print(f"[INFO] Using: test_company_list.json (test file)")
    else:
        print(f"[ERROR] Company list file not found!")
        print()
        print("Looked for:")
        print(f"  - {dev_dir / 'company_list.json'}")
        print(f"  - {dev_dir / 'test_company_list.json'}")
        print()
        print("Please run convert_company_list.bat first to create the JSON file.")
        input("\nPress Enter to exit...")
        return
    
    print(f"[INFO] File: {json_file}")
    print()
    
    try:
        # Load and format
        company_data = load_company_list(str(json_file))
        formatted_text = format_company_list_for_display(company_data)
        
        print("-" * 60)
        print(formatted_text)
        print("-" * 60)
        print()
        print(f"Total companies: {len(company_data.get('companies', []))}")
        print(f"Active companies: {sum(1 for c in company_data.get('companies', []) if c.get('status') == 'active')}")
        print()
        
    except Exception as e:
        print(f"[ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        print()
    
    # Keep window open
    input("Press Enter to exit...")


if __name__ == "__main__":
    main()

