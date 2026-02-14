"""
Company List Manager for PU Observatory.
Loads and manages the company list (JSON). Used by evidence engine for company-news queries
and by admin/development tools. No upload to Assistant or vector store.
"""

import json
from typing import Optional, Dict, List
from pathlib import Path


def load_company_list(file_path: Optional[str] = None) -> Dict:
    """
    Load company list from JSON file.
    
    Args:
        file_path: Path to company list JSON file. Defaults to development/company_list.json
    
    Returns:
        Dictionary containing company list data
    """
    if file_path is None:
        file_path = Path(__file__).parent.parent / "development" / "company_list.json"
    else:
        file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"Company list file not found: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def format_company_list_for_display(company_data: Dict) -> str:
    """
    Format company list data into readable text (for viewing or export).
    
    Args:
        company_data: Company list dictionary
    
    Returns:
        Formatted text string
    """
    lines = [
        "# PU Industry Company List",
        "",
        f"Last Updated: {company_data.get('last_updated', 'Unknown')}",
        "",
        "## Companies to Track:",
        ""
    ]
    
    for company in company_data.get("companies", []):
        if company.get("status") != "active":
            continue  # Skip inactive companies
        
        lines.append(f"### {company['name']}")
        
        if company.get("aliases"):
            aliases = ", ".join(company["aliases"])
            lines.append(f"**Also known as:** {aliases}")
        
        if company.get("value_chain_position"):
            positions = ", ".join(company["value_chain_position"])
            lines.append(f"**Value Chain Position:** {positions}")
        
        if company.get("regions"):
            regions = ", ".join(company["regions"])
            lines.append(f"**Regions:** {regions}")
        
        if company.get("notes"):
            lines.append(f"**Notes:** {company['notes']}")
        
        lines.append("")
    
    lines.extend([
        "## Company Categories:",
        ""
    ])
    
    categories = company_data.get("categories", {})
    for category, companies in categories.items():
        lines.append(f"**{category}:** {', '.join(companies)}")
        lines.append("")
    
    return "\n".join(lines)


def update_company_list_file(
    company_list_path: Optional[str] = None,
    companies: Optional[List[Dict]] = None
) -> None:
    """
    Update the company list JSON file.
    
    Args:
        company_list_path: Path to company list JSON file
        companies: List of company dictionaries to update
    """
    if company_list_path is None:
        company_list_path = Path(__file__).parent.parent / "development" / "company_list.json"
    else:
        company_list_path = Path(company_list_path)
    
    if companies is None:
        raise ValueError("Companies list is required")
    
    from datetime import datetime
    
    # Load existing data or create new
    if company_list_path.exists():
        with open(company_list_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    else:
        data = {
            "version": "1.0",
            "last_updated": datetime.utcnow().strftime("%Y-%m-%d"),
            "companies": [],
            "categories": {}
        }
    
    # Update companies
    data["companies"] = companies
    data["last_updated"] = datetime.utcnow().strftime("%Y-%m-%d")
    
    # Rebuild categories
    categories = {}
    for company in companies:
        if company.get("status") != "active":
            continue
        for position in company.get("value_chain_position", []):
            if position not in categories:
                categories[position] = []
            if company["name"] not in categories[position]:
                categories[position].append(company["name"])
    
    data["categories"] = categories
    
    # Save updated file
    with open(company_list_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

