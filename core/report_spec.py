"""
PU Observatory – Customer report specification and customer profile.

Used by: Configurator (customer choices), Admin (approve + create profile after payment),
and the generator (harvest + report driven by spec).

- regions, categories, value_chain_links: drive the query plan (what to harvest).
- included_sections, report_title, etc.: drive report content and layout.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

# Query-plan keys (customer chooses in Configurator; used by build_query_plan)
REGIONS_OPTIONS = ["Europe", "Asia", "Americas", "North America", "China", "Middle East", "India"]
CATEGORIES_OPTIONS = list(
    {
        "company_news", "regional_monitoring", "industry_context", "value_chain",
        "value_chain_link", "competitive", "sustainability", "capacity",
        "m_and_a", "early_warning", "executive_briefings",
    }
)
VALUE_CHAIN_OPTIONS = ["raw_materials", "system_houses", "foam_converters", "end_use"]

# Report content options (single source of truth for Configurator/Admin/generator)
REPORT_SECTIONS_OPTIONS = [
    "Market Developments",
    "Technology and Innovation",
    "Capacity and Investment Activity",
    "Corporate Developments",
    "Sustainability and Circular Economy",
    "Strategic Implications",
]
SIGNAL_STRENGTH_OPTIONS = [None, "Weak", "Moderate", "Strong"]  # None = include all

# Default report specification (content-driven; evidence appendix and signal map on)
# When running for a customer, load from customer profile so regions/categories/value_chain_links drive the harvest.
DEFAULT_REPORT_SPEC: Dict[str, Any] = {
    # Canonical numeric window for reporting period (days). Labels derive from this.
    "report_period_days": 30,
    # Deprecated text label kept only for legacy compatibility; not used in logic.
    "report_period": "90-day window",
    "report_title": "Polyurethane Industry Intelligence Briefing",
    "included_sections": [
        "Market Developments",
        "Technology and Innovation",
        "Capacity and Investment Activity",
        "Corporate Developments",
        "Sustainability and Circular Economy",
        "Strategic Implications",
    ],
    "signal_map_enabled": True,
    "evidence_appendix_enabled": True,
    "minimum_signal_strength_in_report": None,  # None = include all; or "Weak" | "Moderate" | "Strong"
    "company_signal_tracking_enabled": False,  # Phase 6: when True, trigger company tracking layer later
    # Customer choices (Configurator → drive query plan when running generator)
    "regions": ["Europe", "Asia", "Americas"],
    "categories": ["industry_context", "sustainability", "capacity", "m_and_a", "value_chain"],
    "value_chain_links": ["raw_materials", "system_houses", "end_use"],
    "company_aliases": [],  # optional company names for company_news
}


def get_report_spec(config_path: None | Path = None) -> Dict[str, Any]:
    """
    Return report specification. If config_path points to a JSON file and it exists,
    merge it over DEFAULT_REPORT_SPEC. Otherwise try config/report_config.json relative
    to this file's parent (project root), then return defaults.
    """
    spec = dict(DEFAULT_REPORT_SPEC)
    if config_path is None:
        config_path = Path(__file__).resolve().parent.parent / "config" / "report_config.json"
    if config_path and Path(config_path).exists():
        try:
            data = json.loads(Path(config_path).read_text(encoding="utf-8"))
            if isinstance(data, dict):
                spec.update(data)
        except Exception:
            pass
    return spec


def get_customer_spec(profile_path: None | Path = None) -> Dict[str, Any]:
    """
    Return the spec to use for a customer run (harvest + report).
    If profile_path is given and the file exists, the profile must contain either:
      - a "spec" object (used as-is, with defaults for missing keys), or
      - top-level keys same as report spec (regions, categories, value_chain_links, etc.).
    Profile may also contain: customer_id, status (e.g. "approved"), created_at.
    Admin creates the profile once payment is made; generator uses this for the run.
    """
    spec = dict(DEFAULT_REPORT_SPEC)
    if not profile_path or not Path(profile_path).exists():
        return spec
    try:
        data = json.loads(Path(profile_path).read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return spec
        if "spec" in data:
            spec.update(data["spec"])
        else:
            for key in list(DEFAULT_REPORT_SPEC.keys()) + ["regions", "categories", "value_chain_links", "company_aliases"]:
                if key in data:
                    spec[key] = data[key]
    except Exception:
        pass
    return spec


def customer_profile_from_configurator_choices(
    regions: List[str],
    categories: List[str],
    value_chain_links: List[str],
    company_aliases: None | List[str] = None,
    report_title: str = "Polyurethane Industry Intelligence Briefing",
) -> Dict[str, Any]:
    """Build a customer profile dict from Configurator choices (for Admin to save after approval/payment)."""
    return {
        "status": "draft",  # Admin sets to "approved" after payment
        "spec": {
            "regions": list(regions or []),
            "categories": list(categories or []),
            "value_chain_links": list(value_chain_links or []),
            "company_aliases": list(company_aliases or []),
            "report_title": report_title,
            "report_period_days": DEFAULT_REPORT_SPEC["report_period_days"],
            "report_period": DEFAULT_REPORT_SPEC["report_period"],
            "included_sections": DEFAULT_REPORT_SPEC["included_sections"],
            "signal_map_enabled": DEFAULT_REPORT_SPEC["signal_map_enabled"],
            "evidence_appendix_enabled": DEFAULT_REPORT_SPEC["evidence_appendix_enabled"],
            "minimum_signal_strength_in_report": DEFAULT_REPORT_SPEC["minimum_signal_strength_in_report"],
            "company_signal_tracking_enabled": DEFAULT_REPORT_SPEC["company_signal_tracking_enabled"],
        },
    }
