"""
Merge multiple company list text files into one, removing duplicates.
"""

import sys
from pathlib import Path
from typing import List, Dict, Set

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


def parse_company_from_text(text: str, filename: str) -> List[Dict]:
    """
    Parse companies from text content.
    Supports tab-separated, pipe-separated, and structured formats.
    Returns list of company dictionaries.
    """
    companies = []
    lines = text.strip().split('\n')
    
    current_company = None
    header_line = None
    
    for line_num, line in enumerate(lines, 1):
        line = line.strip()
        
        # Skip empty lines and comments
        if not line or line.startswith('#'):
            continue
        
        # Check if it's a header line (first line with column names)
        if line_num == 1 or (header_line is None and ('Company' in line or 'company' in line.lower())):
            header_line = line
            # Try to detect separator
            if '\t' in line:
                separator = '\t'
            elif '|' in line:
                separator = '|'
            else:
                separator = None
            continue
        
        # Check if it's tab-separated format (most common for company lists)
        if '\t' in line:
            parts = [p.strip() for p in line.split('\t')]
            if len(parts) >= 1 and parts[0]:
                company = {
                    "name": parts[0],
                    "aliases": [],
                    "value_chain_position": [],
                    "regions": [],
                    "status": "active",
                    "notes": "",
                    "source_file": filename
                }
                
                # Parse based on header if available
                if header_line and '\t' in header_line:
                    headers = [h.strip().lower() for h in header_line.split('\t')]
                    
                    # Map common header names
                    for i, header in enumerate(headers):
                        if i >= len(parts):
                            break
                        value = parts[i].strip()
                        if not value:
                            continue
                        
                        if 'company' in header or header == 'name':
                            company["name"] = value
                        elif 'alias' in header or 'also known' in header:
                            company["aliases"] = [a.strip() for a in value.split(',') if a.strip()]
                        elif 'position' in header or 'role' in header or 'value' in header or 'chain' in header:
                            # Split by semicolon or comma
                            positions = value.replace(';', ',').split(',')
                            company["value_chain_position"] = [p.strip() for p in positions if p.strip()]
                        elif 'region' in header or 'primary region' in header:
                            # Handle "Global (EMEA, Americas, APAC)" format
                            if '(' in value:
                                # Extract regions from parentheses
                                regions_part = value[value.find('(')+1:value.find(')')]
                                company["regions"] = [r.strip() for r in regions_part.split(',') if r.strip()]
                            else:
                                company["regions"] = [r.strip() for r in value.split(',') if r.strip()]
                        elif 'country' in header or 'hq' in header:
                            if not company.get("notes"):
                                company["notes"] = f"HQ: {value}"
                            else:
                                company["notes"] += f"; HQ: {value}"
                        elif 'status' in header:
                            company["status"] = value.lower()
                        else:
                            # Add to notes
                            if not company.get("notes"):
                                company["notes"] = f"{header.title()}: {value}"
                            else:
                                company["notes"] += f"; {header.title()}: {value}"
                
                # If no header parsing, use positional (assume: name, position, region)
                elif len(parts) >= 2:
                    if not company.get("value_chain_position"):
                        company["value_chain_position"] = [parts[1]] if parts[1] else []
                    if len(parts) >= 3 and not company.get("regions"):
                        company["regions"] = [parts[2]] if parts[2] else []
                
                companies.append(company)
            continue
        
        # Check if line contains pipe (CSV-like format)
        if '|' in line:
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 1 and parts[0]:
                company = {
                    "name": parts[0],
                    "aliases": [a.strip() for a in parts[1].split(',')] if len(parts) > 1 and parts[1] else [],
                    "value_chain_position": [p.strip() for p in parts[2].split(',')] if len(parts) > 2 and parts[2] else [],
                    "regions": [r.strip() for r in parts[3].split(',')] if len(parts) > 3 and parts[3] else [],
                    "status": parts[4].lower() if len(parts) > 4 and parts[4] else "active",
                    "notes": parts[5] if len(parts) > 5 else "",
                    "source_file": filename
                }
                companies.append(company)
            continue
        
        # Check if it's a separator (new company)
        if line.startswith('---') or line.startswith('==='):
            if current_company and current_company.get('name'):
                companies.append(current_company)
                current_company = None
            continue
        
        # Check for key-value pairs
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip().lower()
            value = value.strip()
            
            if not current_company:
                # Check if this looks like a company name line
                if 'name' in key or 'company' in key:
                    current_company = {
                        "name": value,
                        "aliases": [],
                        "value_chain_position": [],
                        "regions": [],
                        "status": "active",
                        "notes": "",
                        "source_file": filename
                    }
                else:
                    # Assume previous line was company name, this is first property
                    continue
            else:
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
                "notes": "",
                "source_file": filename
            }
    
    # Add last company if exists
    if current_company and current_company.get('name'):
        companies.append(current_company)
    
    return companies


def normalize_company_name(name: str) -> str:
    """
    Normalize company name for duplicate detection.
    Removes common suffixes like 'plc', 'inc', 'ltd', 'ag', 'se', 'corp', etc.
    """
    name = name.lower().strip()
    
    # Remove common legal suffixes
    suffixes = [
        ' plc', 'plc', ' inc', 'inc', ' inc.', 'inc.',
        ' ltd', 'ltd', ' ltd.', 'ltd.', ' limited', 'limited',
        ' ag', 'ag', ' se', 'se', ' corp', 'corp', ' corp.', 'corp.',
        ' corporation', 'corporation', ' company', 'company', ' co.', 'co.',
        ' group', 'group', ' holdings', 'holdings', ' holding', 'holding',
        ' international', 'international', ' intl', 'intl'
    ]
    
    for suffix in suffixes:
        if name.endswith(suffix):
            name = name[:-len(suffix)].strip()
            break
    
    return name


def merge_companies(company_lists: List[List[Dict]]) -> List[Dict]:
    """
    Merge multiple company lists, removing duplicates.
    Duplicates are identified by normalized company name (case-insensitive, without legal suffixes).
    When duplicates are found, merge their properties (aliases, positions, regions).
    """
    merged = {}
    seen_names: Set[str] = set()
    name_to_key: Dict[str, str] = {}  # Map normalized name to actual key
    
    for company_list in company_lists:
        for company in company_list:
            name = company.get('name', '').strip()
            if not name:
                continue
            
            name_lower = name.lower()
            normalized = normalize_company_name(name)
            
            # Check if we've seen this normalized name before
            if normalized in seen_names:
                # Found duplicate - merge with existing
                existing_key = name_to_key[normalized]
                existing = merged[existing_key]
                
                # Use the longer/more complete name
                if len(name) > len(existing['name']):
                    existing['name'] = name
                
                # Merge aliases
                existing_aliases = set(a.lower() for a in existing.get('aliases', []))
                new_aliases = set(a.lower() for a in company.get('aliases', []))
                # Add the other name as alias if different
                if name_lower != existing['name'].lower():
                    existing_aliases.add(name_lower)
                existing['aliases'] = list(existing_aliases | new_aliases)
                
                # Merge positions
                existing_positions = set(p.lower() for p in existing.get('value_chain_position', []))
                new_positions = set(p.lower() for p in company.get('value_chain_position', []))
                existing['value_chain_position'] = list(existing_positions | new_positions)
                
                # Merge regions
                existing_regions = set(r.lower() for r in existing.get('regions', []))
                new_regions = set(r.lower() for r in company.get('regions', []))
                existing['regions'] = list(existing_regions | new_regions)
                
                # Keep notes from both (if different)
                if company.get('notes') and company.get('notes') != existing.get('notes'):
                    if existing.get('notes'):
                        existing['notes'] = f"{existing['notes']}; {company['notes']}"
                    else:
                        existing['notes'] = company['notes']
                
                # Keep status (prefer active)
                if company.get('status') == 'active':
                    existing['status'] = 'active'
                
                # Track source files
                if 'source_files' not in existing:
                    existing['source_files'] = [existing.get('source_file', '')]
                if company.get('source_file') not in existing['source_files']:
                    existing['source_files'].append(company.get('source_file', ''))
            else:
                # New company
                seen_names.add(normalized)
                name_to_key[normalized] = name_lower
                merged[name_lower] = company.copy()
                merged[name_lower]['source_files'] = [company.get('source_file', '')]
                merged[name_lower] = company.copy()
                merged[name_lower]['source_files'] = [company.get('source_file', '')]
    
    # Convert back to list and sort by name
    result = list(merged.values())
    result.sort(key=lambda x: x.get('name', '').lower())
    
    return result


def format_merged_companies(companies: List[Dict]) -> str:
    """
    Format merged companies back to structured text format.
    """
    lines = []
    
    for company in companies:
        lines.append(company['name'])
        
        if company.get('aliases'):
            lines.append(f"Aliases: {', '.join(company['aliases'])}")
        
        if company.get('value_chain_position'):
            lines.append(f"Position: {', '.join(company['value_chain_position'])}")
        
        if company.get('regions'):
            lines.append(f"Regions: {', '.join(company['regions'])}")
        
        if company.get('notes'):
            lines.append(f"Notes: {company['notes']}")
        
        if company.get('status') and company.get('status') != 'active':
            lines.append(f"Status: {company['status']}")
        
        lines.append("---")
        lines.append("")
    
    return "\n".join(lines)


def main():
    """Main function."""
    print("=" * 60)
    print("Merge Company List Files")
    print("=" * 60)
    print()
    
    dev_dir = Path(__file__).parent
    
    # Find all .txt files in development directory
    txt_files = list(dev_dir.glob("*.txt"))
    
    # Filter to only company list files (exclude instructions, docs, merged output, test files, etc.)
    exclude_keywords = ['instruction', 'readme', 'setup', 'guide', 'document', 'openai', 'migration', 'schema', 'merged', 'test']
    company_files = [
        f for f in txt_files 
        if ('company' in f.name.lower() or 'companies' in f.name.lower())
        and not any(keyword in f.name.lower() for keyword in exclude_keywords)
        and f.name.lower() not in ['merged_companies.txt', 'test_companies.txt']
    ]
    
    # Sort to ensure consistent order (Companies 1.txt, Companies 2.txt)
    company_files.sort(key=lambda x: x.name.lower())
    
    if len(company_files) < 2:
        print(f"[ERROR] Need at least 2 company list files (.txt) in development directory")
        print()
        print("Found files:")
        for f in txt_files:
            print(f"  - {f.name}")
        print()
        input("Press Enter to exit...")
        return
    
    print(f"Found {len(company_files)} company list file(s):")
    for f in company_files:
        print(f"  - {f.name}")
    print()
    
    # Read and parse all files
    all_companies = []
    for file_path in company_files:
        print(f"Reading {file_path.name}...")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            companies = parse_company_from_text(content, file_path.name)
            print(f"  Found {len(companies)} companies")
            all_companies.append(companies)
        except Exception as e:
            print(f"  [ERROR] Failed to read {file_path.name}: {str(e)}")
    
    if not all_companies:
        print("[ERROR] No companies found in any file")
        print()
        input("Press Enter to exit...")
        return
    
    print()
    print("Merging companies and removing duplicates...")
    
    # Merge companies
    merged = merge_companies(all_companies)
    
    total_before = sum(len(cl) for cl in all_companies)
    total_after = len(merged)
    duplicates = total_before - total_after
    
    print(f"  Before: {total_before} companies")
    print(f"  After: {total_after} companies")
    print(f"  Duplicates removed: {duplicates}")
    print()
    
    # Format and save
    output_file = dev_dir / "merged_companies.txt"
    formatted_text = format_merged_companies(merged)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(formatted_text)
    
    print(f"[SUCCESS] Merged company list saved to: {output_file.name}")
    print()
    print("Next steps:")
    print("  1. Review merged_companies.txt")
    print("  2. Run convert_company_list.bat to convert to JSON")
    print("  3. Run upload_company_list.bat to upload to Assistant")
    print()
    
    # Keep window open (only if running interactively)
    try:
        input("Press Enter to exit...")
    except (EOFError, KeyboardInterrupt):
        # Running from batch file or non-interactive, let batch handle pause
        pass


if __name__ == "__main__":
    main()

