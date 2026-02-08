"""
One-off script to fill tracked_companies from development/company_list.json.
Run after applying migration 002_tracked_companies.sql.

Usage (from repo root, with .env or Streamlit secrets set):
  python development/seed_tracked_companies.py
"""

import sys
from pathlib import Path

# Add repo root so core is importable
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

def main():
    try:
        from core.company_list_manager import load_company_list
        from core.admin_db import seed_tracked_companies_from_list
    except ImportError as e:
        print("Error: missing dependencies or wrong path.", e)
        return 1

    try:
        data = load_company_list()
    except FileNotFoundError as e:
        print("Error: company_list.json not found.", e)
        return 1

    companies = data.get("companies") or []
    if not companies:
        print("No companies in company_list.json.")
        return 0

    n = seed_tracked_companies_from_list(companies)
    print(f"Upserted {n} tracked companies into the database.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
