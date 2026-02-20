"""
Phase 5A – Ingest curated structural seed (2020–2024) into structural_baseline_events.
Validates required fields, normalizes region_macro and segment, derives year from event_date,
rejects rows outside 2020–2024, deduplicates (company_name, event_date ±7d, signal_type, country/region, numeric_value).
Requires: SUPABASE_URL, SUPABASE_ANON_KEY in .env (or Streamlit secrets if run from app context).
"""
import os
import sys
import csv
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# Allowed values (DB CHECK constraints)
REGION_MACRO = {"EMEA", "APAC", "Americas"}
SEGMENT = {"raw_materials", "flexible_foam", "rigid_foam", "tpu", "case"}
SIGNAL_TYPE = {"capacity", "mna", "regulation", "technology", "investment", "demand"}
NUMERIC_UNIT = {"TPA", "percent", "USD", "EUR"}
DIRECTION = {"increase", "decrease", "neutral"}

DATE_MIN = date(2020, 1, 1)
DATE_MAX = date(2024, 12, 31)


def _norm_region_macro(v: str) -> Optional[str]:
    v = (v or "").strip().upper()
    if v in ("EMEA", "APAC", "AMERICAS"):
        return "Americas" if v == "AMERICAS" else v
    return None


def _norm_segment(v: str) -> Optional[str]:
    v = (v or "").strip().lower().replace("-", "_")
    if v in SEGMENT:
        return v
    if v == "raw materials":
        return "raw_materials"
    if v == "flexible foam":
        return "flexible_foam"
    if v == "rigid foam":
        return "rigid_foam"
    return None


def _parse_date(s: str) -> Optional[date]:
    if not (s and s.strip()):
        return None
    s = s.strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _parse_numeric(s: str) -> Optional[float]:
    if s is None or (isinstance(s, str) and not s.strip()):
        return None
    try:
        return float(str(s).replace(",", "").strip())
    except ValueError:
        return None


def _dedupe_key(row: Dict[str, Any]) -> tuple:
    """Key for deduplication: company_name, event_date (normalized to week), signal_type, country or region_macro, numeric_value."""
    ed = row.get("event_date")
    if isinstance(ed, date):
        week_start = ed - timedelta(days=ed.weekday())
    else:
        week_start = None
    return (
        (row.get("company_name") or "").strip(),
        week_start,
        (row.get("signal_type") or "").strip(),
        (row.get("country") or row.get("region_macro") or "").strip(),
        row.get("numeric_value"),
    )


def validate_and_normalize_row(raw: Dict[str, str], index: int) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Returns (normalized_row, error_message). If error, normalized_row is None."""
    # Required
    event_date_s = raw.get("event_date", "").strip()
    event_date = _parse_date(event_date_s)
    if not event_date:
        return None, f"Row {index}: missing or invalid event_date"
    if event_date < DATE_MIN or event_date > DATE_MAX:
        return None, f"Row {index}: event_date {event_date} outside 2020-2024"
    year = event_date.year

    company_name = (raw.get("company_name") or "").strip()
    if not company_name:
        return None, f"Row {index}: missing company_name"

    region_macro = _norm_region_macro(raw.get("region_macro", ""))
    if not region_macro:
        return None, f"Row {index}: invalid or missing region_macro (must be EMEA | APAC | Americas)"

    segment = _norm_segment(raw.get("segment", ""))
    if not segment:
        return None, f"Row {index}: invalid or missing segment"

    signal_type = (raw.get("signal_type") or "").strip().lower()
    if signal_type not in SIGNAL_TYPE:
        return None, f"Row {index}: invalid signal_type (must be one of {SIGNAL_TYPE})"

    description = (raw.get("description") or "").strip()
    if not description:
        return None, f"Row {index}: missing description"

    source_name = (raw.get("source_name") or "").strip()
    if not source_name:
        return None, f"Row {index}: missing source_name"

    # Optional
    country = (raw.get("country") or "").strip() or None
    numeric_value = _parse_numeric(raw.get("numeric_value", ""))
    numeric_unit = (raw.get("numeric_unit") or "").strip() or None
    if numeric_unit and numeric_unit not in NUMERIC_UNIT:
        numeric_unit = None
    direction = (raw.get("direction") or "").strip().lower() or None
    if direction and direction not in DIRECTION:
        direction = None
    source_url = (raw.get("source_url") or "").strip() or None
    notes = (raw.get("notes") or "").strip() or None

    return {
        "event_date": event_date.isoformat(),
        "year": year,
        "company_name": company_name,
        "region_macro": region_macro,
        "country": country,
        "segment": segment,
        "signal_type": signal_type,
        "numeric_value": numeric_value,
        "numeric_unit": numeric_unit,
        "direction": direction,
        "description": description,
        "source_name": source_name,
        "source_url": source_url,
        "notes": notes,
        "final_classification": "structural",
        "materiality_flag": True,
    }, None


def load_and_dedupe_csv(path: str) -> tuple[List[Dict[str, Any]], List[str]]:
    """Load CSV, validate/normalize each row, dedupe (keep first). Returns (rows, errors)."""
    rows: List[Dict[str, Any]] = []
    errors: List[str] = []
    seen_keys = set()

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, raw in enumerate(reader, start=2):  # 1-based + header
            norm, err = validate_and_normalize_row(raw, i)
            if err:
                errors.append(err)
                continue
            key = _dedupe_key(norm)
            if key in seen_keys:
                continue  # skip duplicate
            seen_keys.add(key)
            rows.append(norm)
    return rows, errors


def ingest(rows: List[Dict[str, Any]]) -> int:
    """Insert rows into structural_baseline_events. Returns count inserted."""
    from core.generator_db import get_supabase_client
    supabase = get_supabase_client()
    # Insert in batches to avoid payload limits
    batch_size = 20
    total = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        supabase.table("structural_baseline_events").insert(batch).execute()
        total += len(batch)
    return total


def main():
    dry_run = "--dry-run" in sys.argv
    repo_root = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(repo_root, "curated_structural_seed_2020_2024.csv")
    if not os.path.isfile(csv_path):
        print(f"CSV not found: {csv_path}")
        sys.exit(1)
    rows, errors = load_and_dedupe_csv(csv_path)
    if errors:
        for e in errors:
            print(e)
        print(f"Total validation errors: {len(errors)}. Fix CSV and re-run.")
        sys.exit(1)
    if not rows:
        print("No rows to ingest after validation and deduplication.")
        sys.exit(0)
    if dry_run:
        print(f"Dry-run: would ingest {len(rows)} rows. Run without --dry-run to insert.")
        sys.exit(0)
    n = ingest(rows)
    print(f"Ingested {n} rows into structural_baseline_events.")


if __name__ == "__main__":
    main()
