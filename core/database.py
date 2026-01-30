"""
Database models and Supabase connection for the PU Observatory platform.
"""

import os
from datetime import datetime
from typing import Optional
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Supabase will be imported when available
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    print("Warning: supabase-py not installed. Database operations will be simulated.")


def get_supabase_client() -> object:
    """Initialize and return Supabase client. Raises exception if not configured."""
    if not SUPABASE_AVAILABLE:
        raise Exception("supabase-py library is not installed. Install with: pip install supabase")
    
    # Try Streamlit secrets first (for Streamlit Cloud), then environment variables (for local .env)
    try:
        import streamlit as st
        supabase_url = st.secrets.get("SUPABASE_URL") or os.getenv("SUPABASE_URL")
        supabase_key = st.secrets.get("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_ANON_KEY")
    except (AttributeError, FileNotFoundError, RuntimeError):
        # Not running in Streamlit or secrets not available, use environment variables
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_ANON_KEY")
    
    if not supabase_url or not supabase_key:
        raise Exception("Supabase is not configured. Set SUPABASE_URL and SUPABASE_ANON_KEY in Streamlit Cloud secrets or .env file.")
    
    try:
        client = create_client(supabase_url, supabase_key)
        # Test connection by trying to access a table
        client.table("specification_requests").select("id").limit(1).execute()
        return client
    except Exception as e:
        raise Exception(f"Failed to connect to Supabase: {str(e)}. Check your credentials and database connection.")


def create_specification_request(
    newsletter_name: str,
    industry_code: str,
    categories: list,
    regions: list,
    frequency: str,
    company_name: str,
    contact_email: str,
    first_name: str = "",
    last_name: str = "",
    street: str = "",
    house_number: str = "",
    city: str = "",
    zip_code: str = "",
    country: str = "",
    vat_number: str = ""
) -> dict:
    """
    Create a new specification request in the database.
    
    Returns the created specification record.
    """
    supabase = get_supabase_client()
    
    specification = {
        "newsletter_name": newsletter_name,
        "industry_code": industry_code,
        "categories": categories,  # List of category IDs
        "regions": regions,  # List of region names
        "frequency": frequency,
        "company_name": company_name,
        "contact_email": contact_email,
        "first_name": first_name,
        "last_name": last_name,
        "street": street,
        "house_number": house_number,
        "city": city,
        "zip_code": zip_code,
        "country": country,
        "vat_number": vat_number,
        "submission_timestamp": datetime.utcnow().isoformat(),
        "status": "pending_review"
    }
    
    supabase = get_supabase_client()
    
    result = supabase.table("specification_requests").insert(specification).execute()
    if not result.data or len(result.data) == 0:
        raise Exception("Failed to save specification request: database returned no data")
    
    created_request = result.data[0]
    
    # Fire webhook asynchronously (fail-open: errors don't break order creation)
    try:
        from core.webhook import send_order_webhook_async, build_order_webhook_payload
        from core.pricing import calculate_price
        
        # Calculate pricing for webhook payload
        try:
            price_data = calculate_price(
                categories=categories,
                regions=regions,
                frequency=frequency,
                num_users=1  # Default to 1 user for webhook
            )
        except Exception as price_error:
            # If pricing calculation fails, use defaults
            logger = __import__('logging').getLogger(__name__)
            logger.warning(f"Pricing calculation failed for webhook: {price_error}")
            price_data = {
                "total_price": 0,
                "currency": "USD",
                "price_per_user_monthly": 0,
                "price_per_user_yearly": 0,
                "breakdown": {}
            }
        
        # Build webhook payload (product_name and first_name/last_name for Make.com / Dashboard deal flow)
        webhook_payload = build_order_webhook_payload(
            request_id=created_request.get("id"),
            submitted_at=created_request.get("submission_timestamp") or "",
            contact_email=contact_email,
            company_name=company_name,
            newsletter_name=newsletter_name,
            frequency=frequency,
            price_data=price_data,
            first_name=first_name or "",
            last_name=last_name or ""
        )
        
        # Send webhook asynchronously (non-blocking)
        send_order_webhook_async(webhook_payload)
        
    except Exception as webhook_error:
        # Fail-open: log error but don't break order creation
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Webhook error (order creation succeeded): {webhook_error}", exc_info=True)
    
    return created_request


def update_specification_request(
    request_id: str,
    newsletter_name: str,
    industry_code: str,
    categories: list,
    regions: list,
    frequency: str,
    company_name: str,
    contact_email: str,
    first_name: str = "",
    last_name: str = "",
    street: str = "",
    house_number: str = "",
    city: str = "",
    zip_code: str = "",
    country: str = "",
    vat_number: str = ""
) -> dict:
    """
    Update an existing specification request in the database.
    
    Returns the updated specification record.
    """
    supabase = get_supabase_client()
    
    specification = {
        "newsletter_name": newsletter_name,
        "industry_code": industry_code,
        "categories": categories,  # List of category IDs
        "regions": regions,  # List of region names
        "frequency": frequency,
        "company_name": company_name,
        "contact_email": contact_email,
        "first_name": first_name,
        "last_name": last_name,
        "street": street,
        "house_number": house_number,
        "city": city,
        "zip_code": zip_code,
        "country": country,
        "vat_number": vat_number,
        "updated_at": datetime.utcnow().isoformat()
    }
    
    result = supabase.table("specification_requests")\
        .update(specification)\
        .eq("id", request_id)\
        .execute()
    
    if not result.data or len(result.data) == 0:
        raise Exception(f"Failed to update specification request {request_id}: database returned no data")
    
    return result.data[0]


def get_taxonomy_data():
    """Retrieve taxonomy data (categories and regions) from database or return defaults."""
    try:
        supabase = get_supabase_client()
        categories_result = supabase.table("categories").select("*").execute()
        regions_result = supabase.table("regions").select("*").execute()
        
        if categories_result.data and regions_result.data:
            return {
                "categories": categories_result.data,
                "regions": [r["name"] for r in regions_result.data]
            }
    except:
        pass
    
    # Return defaults from taxonomy.py if database tables don't exist
    from core.taxonomy import PU_CATEGORIES, REGIONS
    return {
        "categories": PU_CATEGORIES,
        "regions": REGIONS
    }

