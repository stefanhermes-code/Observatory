"""
Shared timestamp display: use system local timezone (e.g. Windows date/time when run locally).
Format: DD-MM-YYYY / hh-mm. Used by Admin, Generator, and Configurator apps.
"""

from __future__ import annotations

from datetime import datetime, timezone


def format_ts_local(ts: str) -> str:
    """
    Format an ISO timestamp string (UTC) as DD-MM-YYYY / hh-mm in the **system local** timezone.
    When the app runs on your PC, this follows Windows date/time. On a server, it uses the server's TZ.
    Returns a readable string; falls back gracefully if parsing fails.
    """
    if not ts or not isinstance(ts, str):
        return "Unknown time"
    ts = ts.strip()
    if not ts:
        return "Unknown time"
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        # .astimezone() with no argument uses system local timezone (Windows clock when run locally)
        local = dt.astimezone()
        return local.strftime("%d-%m-%Y / %H-%M")
    except Exception:
        try:
            dt = datetime.fromisoformat(ts)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            local = dt.astimezone()
            return local.strftime("%d-%m-%Y / %H-%M")
        except Exception:
            return ts[:19] if len(ts) >= 19 else ts
