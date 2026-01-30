"""
Webhook integration for Make.com (formerly Integromat).
Handles asynchronous HTTP POST requests with retry logic and error handling.
"""

import os
import time
import logging
import threading
from typing import Dict, Optional
from datetime import datetime

# Try to import requests, fallback gracefully if not available
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("Warning: requests library not installed. Webhook functionality will be disabled.")

# Configure logging
logger = logging.getLogger(__name__)


def get_webhook_config() -> Dict[str, Optional[str]]:
    """
    Get webhook configuration from environment variables or Streamlit secrets.
    
    Returns:
        Dictionary with webhook_url, webhook_secret, and source_app
    """
    webhook_url = None
    webhook_secret = None
    source_app = None
    
    # Try Streamlit secrets first (for Streamlit Cloud), then environment variables
    try:
        import streamlit as st
        webhook_url = st.secrets.get("ORDER_WEBHOOK_URL") or os.getenv("ORDER_WEBHOOK_URL")
        webhook_secret = st.secrets.get("WEBHOOK_SECRET") or os.getenv("WEBHOOK_SECRET")
        source_app = st.secrets.get("SOURCE_APP") or os.getenv("SOURCE_APP", "pu_observatory")
    except (AttributeError, FileNotFoundError, RuntimeError):
        # Not running in Streamlit or secrets not available, use environment variables
        webhook_url = os.getenv("ORDER_WEBHOOK_URL")
        webhook_secret = os.getenv("WEBHOOK_SECRET")
        source_app = os.getenv("SOURCE_APP", "pu_observatory")
    
    return {
        "webhook_url": webhook_url,
        "webhook_secret": webhook_secret,
        "source_app": source_app
    }


def send_order_webhook_async(payload: Dict) -> None:
    """
    Send webhook asynchronously in a background thread.
    Fail-open: errors are logged but don't raise exceptions.
    
    Args:
        payload: Webhook payload dictionary
    """
    if not REQUESTS_AVAILABLE:
        logger.warning("Webhook disabled: requests library not installed")
        return
    
    # Start background thread
    thread = threading.Thread(
        target=_send_webhook_sync,
        args=(payload,),
        daemon=True  # Daemon thread won't prevent app shutdown
    )
    thread.start()
    logger.info(f"Webhook thread started for request_id: {payload.get('request_id')}")


def _send_webhook_sync(payload: Dict) -> None:
    """
    Synchronous webhook sender (called from background thread).
    Implements retry logic with exponential backoff.
    
    Args:
        payload: Webhook payload dictionary
    """
    config = get_webhook_config()
    webhook_url = config["webhook_url"]
    webhook_secret = config["webhook_secret"]
    request_id = payload.get("request_id", "unknown")
    
    # Check if webhook is configured
    if not webhook_url:
        logger.debug("Webhook not configured (ORDER_WEBHOOK_URL not set), skipping")
        return
    
    # Prepare headers
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "PU-Observatory-Webhook/1.0"
    }
    
    # Add authentication header if secret is configured
    if webhook_secret:
        headers["X-Webhook-Secret"] = webhook_secret
    
    # Retry configuration
    max_attempts = 3
    timeout = 5  # seconds
    base_delay = 1  # seconds (exponential backoff base)
    
    last_error = None
    
    for attempt in range(1, max_attempts + 1):
        try:
            logger.info(f"Webhook attempt {attempt}/{max_attempts} for request_id: {request_id}")
            
            # Send HTTP POST request
            response = requests.post(
                webhook_url,
                json=payload,
                headers=headers,
                timeout=timeout
            )
            
            # Check response status
            if response.status_code >= 200 and response.status_code < 300:
                logger.info(
                    f"Webhook success for request_id: {request_id} "
                    f"(attempt {attempt}/{max_attempts}, status: {response.status_code})"
                )
                return  # Success, exit retry loop
            
            else:
                # Non-2xx response
                error_msg = (
                    f"Webhook failed for request_id: {request_id} "
                    f"(attempt {attempt}/{max_attempts}, status: {response.status_code})"
                )
                logger.warning(error_msg)
                last_error = f"HTTP {response.status_code}"
                
                # Don't retry on 4xx client errors (except 429 rate limit)
                if 400 <= response.status_code < 500 and response.status_code != 429:
                    logger.error(f"Client error {response.status_code}, not retrying")
                    return
        
        except requests.exceptions.Timeout:
            error_msg = (
                f"Webhook timeout for request_id: {request_id} "
                f"(attempt {attempt}/{max_attempts}, timeout: {timeout}s)"
            )
            logger.warning(error_msg)
            last_error = "Timeout"
        
        except requests.exceptions.ConnectionError as e:
            error_msg = (
                f"Webhook connection error for request_id: {request_id} "
                f"(attempt {attempt}/{max_attempts}): {str(e)}"
            )
            logger.warning(error_msg)
            last_error = f"Connection error: {str(e)}"
        
        except Exception as e:
            error_msg = (
                f"Webhook error for request_id: {request_id} "
                f"(attempt {attempt}/{max_attempts}): {str(e)}"
            )
            logger.error(error_msg, exc_info=True)
            last_error = str(e)
        
        # Calculate delay before next attempt (exponential backoff)
        if attempt < max_attempts:
            delay = base_delay * (2 ** (attempt - 1))  # 1s, 2s, 4s...
            logger.info(f"Retrying webhook in {delay}s...")
            time.sleep(delay)
    
    # All attempts failed
    logger.error(
        f"Webhook failed after {max_attempts} attempts for request_id: {request_id}. "
        f"Last error: {last_error}"
    )


def build_order_webhook_payload(
    request_id: str,
    submitted_at: str,
    contact_email: str,
    company_name: str,
    newsletter_name: str,
    frequency: str,
    price_data: Dict,
    source_app: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None
) -> Dict:
    """
    Build webhook payload for order submission event.
    Payload is compatible with Make.com Order Intent Webhook Flow and Dashboard HTC Global deal creation.
    
    Args:
        request_id: Unique request ID (UUID)
        submitted_at: ISO timestamp of submission
        contact_email: Contact email address
        company_name: Company name
        newsletter_name: Product/newsletter name
        frequency: Cadence (daily/weekly/monthly)
        price_data: Pricing information from calculate_price()
        source_app: Source application identifier (default: "pu_observatory")
        first_name: Contact first name (optional, for Make.com flow)
        last_name: Contact last name (optional, for Make.com flow)
    
    Returns:
        Webhook payload dictionary
    """
    config = get_webhook_config()
    app_identifier = source_app or config["source_app"]
    
    payload = {
        "event_type": "order_submitted",
        "source_app": app_identifier,
        "request_id": request_id,
        "submitted_at": submitted_at,
        "status": "pending_review",
        "contact_email": contact_email,
        "company_name": company_name,
        "newsletter_name": newsletter_name,
        "product_name": newsletter_name,
        "pricing": {
            "amount": price_data.get("total_price", 0),
            "currency": price_data.get("currency", "USD"),
            "cadence": frequency,
            "price_per_user_monthly": price_data.get("price_per_user_monthly", 0),
            "price_per_user_yearly": price_data.get("price_per_user_yearly", 0),
            "breakdown": price_data.get("breakdown", {})
        }
    }
    if first_name is not None:
        payload["first_name"] = first_name
    if last_name is not None:
        payload["last_name"] = last_name
    
    return payload

