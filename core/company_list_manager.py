"""
Company List Manager for PU Observatory.
Loads and manages the company list (JSON). Used by evidence engine for company-news queries
and by admin/development tools. No upload to Assistant or vector store.
"""

import json
from typing import Optional, Dict, List
from pathlib import Path

from core.taxonomy import VALUE_CHAIN_LINKS


VALUE_CHAIN_LABELS = {item["id"]: item["name"] for item in VALUE_CHAIN_LINKS}


def _rebuild_categories(companies: List[Dict]) -> Dict[str, List[str]]:
    """Rebuild the category map from active company records."""
    categories: Dict[str, List[str]] = {}
    for company in companies or []:
        if company.get("status") != "active":
            continue
        name = (company.get("name") or "").strip()
        if not name:
            continue
        for position in company.get("value_chain_position", []) or []:
            label = (position or "").strip()
            if not label:
                continue
            if label not in categories:
                categories[label] = []
            if name not in categories[label]:
                categories[label].append(name)
    return categories


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
        data = json.load(f)

    if isinstance(data, dict):
        companies = data.get("companies") if isinstance(data.get("companies"), list) else []
        data["categories"] = _rebuild_categories(companies)
    return data


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
            positions = ", ".join(VALUE_CHAIN_LABELS.get(pos, pos) for pos in company["value_chain_position"])
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
        lines.append(f"**{VALUE_CHAIN_LABELS.get(category, category)}:** {', '.join(companies)}")
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
    data["categories"] = _rebuild_categories(companies)
    
    # Save updated file
    with open(company_list_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

