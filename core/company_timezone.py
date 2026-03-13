"""
Derive a best-effort IANA timezone name from company location.

Primary signals:
- country (preferred, either full name or ISO alpha-2)
- city (optional refinement for multi-timezone countries)

This is deterministic logic, not an LLM call at runtime.
Mappings can be extended as new customer locations are added.
"""

from __future__ import annotations

from typing import Optional


_COUNTRY_TZ_MAP = {
    # Europe
    "netherlands": "Europe/Amsterdam",
    "nl": "Europe/Amsterdam",
    "belgium": "Europe/Brussels",
    "be": "Europe/Brussels",
    "germany": "Europe/Berlin",
    "de": "Europe/Berlin",
    "france": "Europe/Paris",
    "fr": "Europe/Paris",
    "united kingdom": "Europe/London",
    "uk": "Europe/London",
    "gb": "Europe/London",
    "ireland": "Europe/Dublin",
    "ie": "Europe/Dublin",
    "spain": "Europe/Madrid",
    "es": "Europe/Madrid",
    "italy": "Europe/Rome",
    "it": "Europe/Rome",
    "switzerland": "Europe/Zurich",
    "ch": "Europe/Zurich",

    # Americas
    "united states": "America/New_York",
    "usa": "America/New_York",
    "us": "America/New_York",
    "canada": "America/Toronto",
    "ca": "America/Toronto",
    "mexico": "America/Mexico_City",
    "mx": "America/Mexico_City",

    # Asia-Pacific
    "thailand": "Asia/Bangkok",
    "th": "Asia/Bangkok",
    "china": "Asia/Shanghai",
    "cn": "Asia/Shanghai",
    "japan": "Asia/Tokyo",
    "jp": "Asia/Tokyo",
    "south korea": "Asia/Seoul",
    "kr": "Asia/Seoul",
    "singapore": "Asia/Singapore",
    "sg": "Asia/Singapore",
    "australia": "Australia/Sydney",
    "au": "Australia/Sydney",
}


def guess_timezone_from_country_city(country: str = "", city: str = "") -> Optional[str]:
    """
    Return an IANA timezone name from country/city, or None if unknown.

    - country: full name or ISO alpha-2 code (case-insensitive)
    - city: currently used only for future refinements when a country spans multiple timezones
    """
    if not country and not city:
        return None

    country_key = (country or "").strip().lower()
    if not country_key and city:
        country_key = city.strip().lower()

    if not country_key:
        return None

    tz = _COUNTRY_TZ_MAP.get(country_key)
    if tz:
        return tz

    # Future: refine by city for multi-timezone countries
    return None

