"""
Helpers for handling paid market-report style listings in evidence.

Detects obvious paid listing URLs/snippets and extracts coarse facts such as
market size, CAGR, base year, regions, segments, and key players.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional
from urllib.parse import urlparse

# Minimal allowlist of common market report and paid listing domains.
PAID_LISTING_DOMAINS = frozenset(
    {
        "grandviewresearch.com",
        "marketsandmarkets.com",
        "mordorintelligence.com",
        "fortunebusinessinsights.com",
        "prnewswire.com",
        "globenewswire.com",
        "marketwatch.com",
        "marketresearchfuture.com",
        "technavio.com",
    }
)

# Phrases that strongly suggest a paid market listing / report.
PAID_LISTING_PHRASES: List[str] = [
    "buy now",
    "request sample",
    "request a sample",
    "download sample",
    "get sample",
    "market report",
    "industry report",
    "full report",
    "purchase report",
    "license type",
    "single user license",
    "corporate license",
    "pricing details",
    "inquire before buying",
    "speak to analyst",
]


def _normalize_domain(url: str) -> Optional[str]:
    try:
        netloc = urlparse(url or "").netloc.lower()
        if not netloc:
            return None
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return netloc
    except Exception:
        return None


def is_paid_listing(url: str, title: str, snippet: str, enriched_text: str) -> bool:
    """
    Return True when the result looks like a paid market listing.

    - URL domain is in PAID_LISTING_DOMAINS, OR
    - Any PAID_LISTING_PHRASES appear in the combined text.
    """
    domain = _normalize_domain(url)
    if domain and any(domain == d or domain.endswith("." + d) for d in PAID_LISTING_DOMAINS):
        return True

    blob = " ".join(
        part for part in [title or "", snippet or "", enriched_text or ""] if part
    ).lower()
    return any(phrase in blob for phrase in PAID_LISTING_PHRASES)


def extract_paid_listing_facts(text: str) -> Dict[str, Optional[object]]:
    """
    Extract coarse market facts from a paid listing body.

    Returns dict with keys:
      - market_size: str or None
      - cagr: str or None
      - base_year: str or None
      - regions: List[str]
      - segments: List[str]
      - key_players: List[str]
    """
    if not text:
        return {
            "market_size": None,
            "cagr": None,
            "base_year": None,
            "regions": [],
            "segments": [],
            "key_players": [],
        }

    lowered = text.lower()

    # Market size, e.g. "USD 10.5 billion", "$10 billion", "US$ 3.2 billion"
    market_size_match = re.search(
        r"\b(?:usd|us\$|\$)\s*([\d,\.]+)\s*(billion|million|trillion)?\b", text, re.IGNORECASE
    )
    market_size = market_size_match.group(0) if market_size_match else None

    # CAGR, e.g. "CAGR of 7.5%" or "compound annual growth rate of 4.2%"
    cagr_match = re.search(
        r"(?:cagr|compound annual growth rate)[^0-9%]{0,40}([\d,\.]+)\s*%", text, re.IGNORECASE
    )
    cagr = f"{cagr_match.group(1)}%" if cagr_match else None

    # Base year, e.g. "base year 2024" or "in 2024 (base year)"
    base_year_match = re.search(
        r"(?:base year[^0-9]{0,10}|in\s+)(20[0-4][0-9])", text, re.IGNORECASE
    )
    base_year = base_year_match.group(1) if base_year_match else None

    # Regions: simple presence check for common region names.
    known_regions = [
        "north america",
        "europe",
        "asia pacific",
        "asia-pacific",
        "middle east",
        "latin america",
        "south america",
        "africa",
        "mea",
        "apac",
    ]
    regions: List[str] = []
    for r in known_regions:
        if r in lowered:
            regions.append(r)
    regions = sorted(set(regions))

    # Segments: very coarse extraction from "by type", "by application", etc.
    segments: List[str] = []
    segment_patterns = [
        r"by type[^:\n]*:\s*(.+?)(?:\.\s|\n)",
        r"by application[^:\n]*:\s*(.+?)(?:\.\s|\n)",
        r"by end[- ]use[^:\n]*:\s*(.+?)(?:\.\s|\n)",
    ]
    for pat in segment_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if not m:
            continue
        raw = m.group(1)
        for part in re.split(r",|;| and ", raw):
            cleaned = part.strip(" .;:")
            if cleaned:
                segments.append(cleaned)
    segments = sorted(set(segments))

    # Key players, e.g. "Key players include A, B, C and D."
    key_players: List[str] = []
    kp_match = re.search(
        r"key players? (?:include|are)\s+(.+?)(?:\.\s|\n|$)", text, re.IGNORECASE
    )
    if kp_match:
        raw = kp_match.group(1)
        parts = re.split(r",| and ", raw)
        for part in parts:
            cleaned = part.strip(" .;:")
            if cleaned:
                key_players.append(cleaned)

    return {
        "market_size": market_size,
        "cagr": cagr,
        "base_year": base_year,
        "regions": regions,
        "segments": segments,
        "key_players": key_players,
    }

