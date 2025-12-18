"""
Convert a text file of companies into the JSON format for the company list.
Supports multiple input formats.
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime


def parse_simple_list(txt_content: str) -> List[Dict]:
    """
    Parse a simple text file with one company per line.
    Format: Company Name
    """
    companies = []
    lines = txt_content.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        
        # Simple format: just company name
        companies.append({
            "name": line,
            "aliases": [],
            "value_chain_position": [],  # Will need to be filled manually
            "regions": [],  # Will need to be filled manually
            "status": "active",
            "notes": ""
        })
    
    return companies


def parse_structured_list(txt_content: str) -> List[Dict]:
    """
    Parse a structured text file with company information.
    Supports formats like:
    
    Company Name
    Aliases: Alias1, Alias2
    Position: MDI Producer, Polyols Producer
    Regions: EMEA, North America
    Notes: Some notes here
    ---
    
    Or:
    Company Name | Aliases | Position | Regions | Notes
    """
    companies = []
    lines = txt_content.strip().split('\n')
    
    current_company = None
    
    for line in lines:
        line = line.strip()
        
        # Skip empty lines and comments
        if not line or line.startswith('#'):
            continue
        
        # Check if it's a separator (new company)
        if line.startswith('---') or line.startswith('==='):
            if current_company:
                companies.append(current_company)
                current_company = None
            continue
        
        # Check if it's a header row (CSV-like format)
        if '|' in line and 'Company' in line.lower():
            continue  # Skip header row
        
        # Check if line contains pipe (CSV-like format)
        if '|' in line:
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 1:
                company = {
                    "name": parts[0],
                    "aliases": parts[1].split(',') if len(parts) > 1 and parts[1] else [],
                    "value_chain_position": [p.strip() for p in parts[2].split(',')] if len(parts) > 2 and parts[2] else [],
                    "regions": [p.strip() for p in parts[3].split(',')] if len(parts) > 3 and parts[3] else [],
                    "status": "active",
                    "notes": parts[4] if len(parts) > 4 else ""
                }
                companies.append(company)
            continue
        
        # Check for key-value pairs
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip().lower()
            value = value.strip()
            
            if not current_company:
                # Assume this is a new company name
                current_company = {
                    "name": value if 'name' in key or 'company' in key else line.split(':')[0].strip(),
                    "aliases": [],
                    "value_chain_position": [],
                    "regions": [],
                    "status": "active",
                    "notes": ""
                }
                if 'name' not in key and 'company' not in key:
                    current_company["name"] = line.split(':')[0].strip()
                    # Process the key-value
                    key, value = line.split(':', 1)
                    key = key.strip().lower()
                    value = value.strip()
            
            if 'alias' in key:
                current_company["aliases"] = [a.strip() for a in value.split(',')]
            elif 'position' in key or 'value chain' in key:
                current_company["value_chain_position"] = [p.strip() for p in value.split(',')]
            elif 'region' in key:
                current_company["regions"] = [r.strip() for r in value.split(',')]
            elif 'note' in key or 'comment' in key:
                current_company["notes"] = value
            elif 'status' in key:
                current_company["status"] = value.lower()
            continue
        
        # If no special format detected, treat as company name
        if not current_company:
            current_company = {
                "name": line,
                "aliases": [],
                "value_chain_position": [],
                "regions": [],
                "status": "active",
                "notes": ""
            }
    
    # Add last company if exists
    if current_company:
        companies.append(current_company)
    
    return companies


def convert_txt_to_json(txt_file_path: str, output_json_path: Optional[str] = None) -> str:
    """
    Convert a text file to JSON company list format.
    
    Args:
        txt_file_path: Path to input text file
        output_json_path: Path to output JSON file (defaults to company_list.json in same directory)
    
    Returns:
        Path to created JSON file
    """
    txt_path = Path(txt_file_path)
    if not txt_path.exists():
        raise FileNotFoundError(f"Text file not found: {txt_file_path}")
    
    # Read text file
    with open(txt_path, 'r', encoding='utf-8') as f:
        txt_content = f.read()
    
    # Try to detect format and parse
    # Check if it looks structured (has colons, pipes, or separators)
    has_structure = ':' in txt_content or '|' in txt_content or '---' in txt_content
    
    if has_structure:
        companies = parse_structured_list(txt_content)
    else:
        companies = parse_simple_list(txt_content)
    
    if not companies:
        raise ValueError("No companies found in text file. Check the format.")
    
    # Build categories from companies
    categories = {}
    for company in companies:
        if company.get("status") != "active":
            continue
        for position in company.get("value_chain_position", []):
            if position not in categories:
                categories[position] = []
            if company["name"] not in categories[position]:
                categories[position].append(company["name"])
    
    # Create JSON structure
    from datetime import timezone
    json_data = {
        "version": "1.0",
        "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "companies": companies,
        "categories": categories
    }
    
    # Determine output path
    if output_json_path is None:
        output_json_path = txt_path.parent / "company_list.json"
    else:
        output_json_path = Path(output_json_path)
    
    # Write JSON file
    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)
    
    print(f"[OK] Converted {len(companies)} companies to JSON")
    print(f"[INFO] Output file: {output_json_path}")
    print("")
    print("[NOTE] You may need to manually add:")
    print("   - Value chain positions for companies that don't have them")
    print("   - Regions for companies that don't have them")
    print("   - Aliases/alternative names")
    print("")
    print("Then run: upload_company_list.bat")
    
    return str(output_json_path)


def main():
    """Main function for command-line usage."""
    # Fix Windows console encoding
    import sys
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    
    if len(sys.argv) < 2:
        print("Usage: python convert_company_list_txt.py <input_txt_file> [output_json_file]")
        print("")
        print("Example:")
        print("  python convert_company_list_txt.py companies.txt")
        print("  python convert_company_list_txt.py companies.txt company_list.json")
        print("")
        print("Supported formats:")
        print("  1. Simple list (one company per line)")
        print("  2. Structured format with key-value pairs")
        print("  3. Pipe-separated format (CSV-like)")
        return
    
    input_file = sys.argv[1]
    # If no output file specified, create it in the same directory as input with .json extension
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    else:
        input_path = Path(input_file)
        output_file = str(input_path.parent / "company_list.json")
    
    try:
        output_path = convert_txt_to_json(input_file, output_file)
        print(f"\n[SUCCESS] JSON file created: {output_path}")
    except Exception as e:
        print(f"[ERROR] {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

