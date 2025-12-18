"""
Pricing calculation for PU Observatory specifications.
Based on: Polyurethane Industry Observatory – Pricing document

Pricing Principles:
- Pricing is per user, per month
- Cadence reflects depth and urgency, not raw cost
- Scope (companies / regions / value-chain links) determines the package tier
"""

from typing import Dict, List


def calculate_price(
    categories: List[str],
    regions: List[str],
    frequency: str,
    num_users: int = 1
) -> Dict[str, any]:
    """
    Calculate the annual price for a newsletter specification.
    
    Based on official pricing:
    - Monthly: $19 per user per month = $228 per user per year
    - Weekly: $39 per user per month = $468 per user per year
    - Daily: $119 per user per month = $1,428 per user per year
    
    Args:
        categories: List of category IDs (affects scope tier)
        regions: List of region names (affects scope tier)
        frequency: 'daily', 'weekly', or 'monthly'
        num_users: Number of users (default: 1)
    
    Returns:
        Dictionary with:
        - price_per_user_monthly: Price per user per month
        - price_per_user_yearly: Price per user per year
        - total_monthly: Total monthly price for all users
        - total_price: Total annual price for all users
        - currency: Currency code (USD)
        - breakdown: Detailed breakdown
    """
    # Cadence pricing (per user per month) - from official pricing document
    CADENCE_PRICING = {
        "monthly": 19,   # USD per user per month
        "weekly": 39,    # USD per user per month
        "daily": 119     # USD per user per month
    }
    
    # Get base price per user per month based on cadence
    price_per_user_monthly = CADENCE_PRICING.get(frequency, 19)
    price_per_user_yearly = price_per_user_monthly * 12
    
    # Calculate totals
    total_monthly = price_per_user_monthly * num_users
    total_yearly = price_per_user_yearly * num_users
    
    # Determine scope tier based on selection
    num_categories = len(categories)
    num_regions = len(regions)
    
    # Scope packages (for reference, doesn't affect price directly per pricing doc)
    if num_categories <= 3 and num_regions <= 1:
        scope_tier = "Starter"
    elif num_categories <= 6 and num_regions <= 2:
        scope_tier = "Medium"
    elif num_categories <= 9 and num_regions <= 4:
        scope_tier = "Pro"
    else:
        scope_tier = "Enterprise"
    
    # Create breakdown
    breakdown = {
        "cadence": {
            "type": frequency,
            "price_per_user_monthly": price_per_user_monthly,
            "price_per_user_yearly": price_per_user_yearly,
            "label": frequency.title()
        },
        "users": {
            "count": num_users,
            "note": "Pricing is per user"
        },
        "scope": {
            "categories_count": num_categories,
            "regions_count": num_regions,
            "tier": scope_tier,
            "note": "Scope determines package tier (all plans include full Observatory access)"
        },
        "total_monthly": total_monthly,
        "total_yearly": total_yearly
    }
    
    return {
        "price_per_user_monthly": price_per_user_monthly,
        "price_per_user_yearly": price_per_user_yearly,
        "total_monthly": total_monthly,
        "total_price": total_yearly,
        "currency": "USD",
        "breakdown": breakdown
    }


def format_price(price_data: Dict, show_per_user: bool = False) -> str:
    """
    Format price data for display.
    
    Args:
        price_data: Price calculation result
        show_per_user: If True, show per-user pricing
    
    Returns formatted price string like "$1,428/year" or "$1,428 per user per year"
    """
    if show_per_user:
        total = price_data["price_per_user_yearly"]
        suffix = " per user/year"
    else:
        total = price_data["total_price"]
        suffix = "/year"
    
    currency_symbol = "$" if price_data["currency"] == "USD" else price_data["currency"]
    
    # Format with thousand separators
    formatted_total = f"{total:,.0f}"
    
    return f"{currency_symbol}{formatted_total}{suffix}"

