"""
V2: Single source of truth for run date range.
Uses application date (datetime.utcnow()) only — never the LLM's date.

Canonical input for date-window logic: report_period_days (int).
The only low-level function that turns "how many days" into (lookback_date, reference_date)
is get_lookback_from_days(report_period_days, reference_date). All runtime date filtering
must be driven by that; callers resolve report_period_days from spec (and optional builder
override) and pass it explicitly.
"""

from datetime import datetime, timedelta
from typing import Optional, Tuple


def get_lookback_days(cadence: str) -> int:
    """
    Return lookback days for a cadence. daily=2, weekly=7, monthly=30.
    Use only when resolving report_period_days for legacy specs that have no
    report_period_days set (migration fallback). Do not use for date-window
    filtering; use get_lookback_from_days(report_period_days, ref_date) instead.
    """
    c = (cadence or "monthly").strip().lower()
    if c == "daily":
        return 2
    if c == "weekly":
        return 7
    return 30  # monthly or unknown


def get_lookback_from_cadence(
    cadence: str,
    reference_date: Optional[datetime] = None,
) -> Tuple[datetime, datetime]:
    """
    DEPRECATED for live path. Return (lookback_date, reference_date) from cadence.
    Use only for migration/backward compatibility when report_period_days is not yet
    persisted. In live path callers must pass report_period_days and use
    get_lookback_from_days(report_period_days, reference_date) only.
    """
    ref = reference_date if reference_date is not None else datetime.utcnow()
    days = get_lookback_days(cadence)
    lookback = ref - timedelta(days=days)
    return lookback, ref


def get_lookback_from_days(
    report_period_days: int,
    reference_date: Optional[datetime] = None,
) -> Tuple[datetime, datetime]:
    """
    Sole canonical date-window function. Accepts only report_period_days (int).
    Returns (lookback_date, reference_date). reference_date defaults to
    datetime.utcnow(). All runtime date filtering must use this with
    report_period_days passed explicitly from the caller.
    """
    ref = reference_date if reference_date is not None else datetime.utcnow()
    days = max(1, min(365, int(report_period_days)))
    lookback = ref - timedelta(days=days)
    return lookback, ref


def parse_published_at(value) -> Optional[datetime]:
    """
    Parse published_at from candidate (string or date). Returns datetime or None.
    Used to filter candidates by date range; unparseable => None (item kept if we allow no-date).
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    s = (value if isinstance(value, str) else str(value)).strip()
    if not s:
        return None
    # ISO date or date part only
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        try:
            return datetime.strptime(s[:10], "%Y-%m-%d")
        except ValueError:
            pass
    # DD/MM/YYYY or MM/DD/YYYY
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s[:10], fmt)
        except (ValueError, IndexError):
            continue
    return None


def is_in_date_range(
    published_at_value,
    lookback_date: datetime,
    reference_date: datetime,
) -> bool:
    """
    True if published_at is within [lookback_date, reference_date] (inclusive).
    If published_at is None or unparseable, returns True (keep item; e.g. web search without date).
    """
    dt = parse_published_at(published_at_value)
    if dt is None:
        return True
    # Normalize to date for comparison
    d = dt.date() if hasattr(dt, "date") else dt
    lb = lookback_date.date() if hasattr(lookback_date, "date") else lookback_date
    rf = reference_date.date() if hasattr(reference_date, "date") else reference_date
    return lb <= d <= rf
