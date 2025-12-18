"""
Validation functions for the Configurator app.
"""

import re
from typing import List, Tuple


def validate_email(email: str) -> Tuple[bool, str]:
    """Validate email format."""
    if not email or not email.strip():
        return False, "Email is required"
    
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email.strip()):
        return False, "Please enter a valid email address"
    
    return True, ""


def validate_categories(categories: List[str]) -> Tuple[bool, str]:
    """Validate that at least one category is selected."""
    if not categories or len(categories) == 0:
        return False, "Please select at least one category"
    
    return True, ""


def validate_regions(regions: List[str]) -> Tuple[bool, str]:
    """Validate that at least one region is selected."""
    if not regions or len(regions) == 0:
        return False, "Please select at least one region"
    
    return True, ""


def validate_frequency(frequency: str) -> Tuple[bool, str]:
    """Validate frequency selection."""
    valid_frequencies = ["daily", "weekly", "monthly"]
    if frequency not in valid_frequencies:
        return False, f"Frequency must be one of: {', '.join(valid_frequencies)}"
    
    return True, ""


def validate_newsletter_name(name: str) -> Tuple[bool, str]:
    """Validate newsletter name."""
    if not name or not name.strip():
        return False, "Newsletter name is required"
    
    name = name.strip()
    
    if len(name) < 3:
        return False, "Newsletter name must be at least 3 characters"
    
    if len(name) > 100:
        return False, "Newsletter name must be less than 100 characters"
    
    # Basic character validation (allow letters, numbers, spaces, hyphens, underscores)
    if not re.match(r'^[a-zA-Z0-9\s\-_]+$', name):
        return False, "Newsletter name can only contain letters, numbers, spaces, hyphens, and underscores"
    
    return True, ""


def validate_company_name(company_name: str) -> Tuple[bool, str]:
    """Validate company name."""
    if not company_name or not company_name.strip():
        return False, "Company name is required"
    
    if len(company_name.strip()) < 2:
        return False, "Company name must be at least 2 characters"
    
    return True, ""


def validate_specification(
    categories: List[str],
    regions: List[str],
    frequency: str,
    newsletter_name: str,
    company_name: str,
    contact_email: str
) -> Tuple[bool, List[str]]:
    """
    Validate entire specification.
    Returns (is_valid, list_of_errors)
    """
    errors = []
    
    # Validate each field
    cat_valid, cat_error = validate_categories(categories)
    if not cat_valid:
        errors.append(cat_error)
    
    reg_valid, reg_error = validate_regions(regions)
    if not reg_valid:
        errors.append(reg_error)
    
    freq_valid, freq_error = validate_frequency(frequency)
    if not freq_valid:
        errors.append(freq_error)
    
    name_valid, name_error = validate_newsletter_name(newsletter_name)
    if not name_valid:
        errors.append(name_error)
    
    company_valid, company_error = validate_company_name(company_name)
    if not company_valid:
        errors.append(company_error)
    
    email_valid, email_error = validate_email(contact_email)
    if not email_valid:
        errors.append(email_error)
    
    return len(errors) == 0, errors

