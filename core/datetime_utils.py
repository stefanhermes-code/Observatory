"""
Shared timestamp display for Admin, Generator, and Configurator apps.

- **Format**: DD-MM-YYYY / hh:mm
- **Timezone resolution order**:
  1. If the `LOCAL_TIMEZONE` environment variable is set to an IANA name
     (e.g. `Europe/Amsterdam`, `Asia/Bangkok`), use that.
  2. Otherwise, fall back to the **system local timezone** (Windows clock
     when run locally; server local time in production).
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo


def _get_preferred_tz() -> timezone | None:
    """Return a preferred timezone from env, or None if not configured/invalid."""
    tz_name = os.getenv("LOCAL_TIMEZONE", "").strip()
    if not tz_name:
        return None
    try:
        return ZoneInfo(tz_name)
    except Exception:
        return None


def format_ts_local(ts: str) -> str:
    """
    Format an ISO timestamp string (UTC) as DD-MM-YYYY / hh:mm.

    - Tries `LOCAL_TIMEZONE` first (if set), then system-local timezone.
    - Returns a readable string; falls back gracefully if parsing fails.
    """
    if not ts or not isinstance(ts, str):
        return "Unknown time"
    ts = ts.strip()
    if not ts:
        return "Unknown time"

    preferred_tz = _get_preferred_tz()

    def _to_local(dt: datetime) -> datetime:
        if dt.tzinfo is None:
            dt_with_tz = dt.replace(tzinfo=timezone.utc)
        else:
            dt_with_tz = dt
        if preferred_tz is not None:
            return dt_with_tz.astimezone(preferred_tz)
        return dt_with_tz.astimezone()

    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        local = _to_local(dt)
        return local.strftime("%d-%m-%Y / %H:%M")
    except Exception:
        try:
            dt = datetime.fromisoformat(ts)
            local = _to_local(dt)
            return local.strftime("%d-%m-%Y / %H:%M")
        except Exception:
            return ts[:19] if len(ts) >= 19 else ts
    