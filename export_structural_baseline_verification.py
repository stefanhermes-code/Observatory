"""
Phase 5A – Export verification CSV and summary counts from structural_baseline_events.
Output: verify_structural_baseline_events.csv and summary (count by year, region_macro, segment, signal_type)
        plus 5 sample rows per signal_type for spot check.
"""
import os
import sys
import csv
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

EXPORT_COLUMNS = [
    "event_date", "year", "company_name", "region_macro", "country", "segment",
    "signal_type", "numeric_value", "numeric_unit", "description",
]


def fetch_all():
    from core.generator_db import get_supabase_client
    supabase = get_supabase_client()
    result = supabase.table("structural_baseline_events").select("*").order("event_date").execute()
    return result.data or []


def run(out_dir: str):
    os.makedirs(out_dir, exist_ok=True)
    rows = fetch_all()
    csv_path = os.path.join(out_dir, "verify_structural_baseline_events.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=EXPORT_COLUMNS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in EXPORT_COLUMNS})
    print(f"Wrote {csv_path} ({len(rows)} rows)")

    by_year = defaultdict(int)
    by_region = defaultdict(int)
    by_segment = defaultdict(int)
    by_signal = defaultdict(int)
    by_signal_rows = defaultdict(list)
    for r in rows:
        by_year[r.get("year")] += 1
        by_region[r.get("region_macro") or ""] += 1
        by_segment[r.get("segment") or ""] += 1
        st = r.get("signal_type") or ""
        by_signal[st] += 1
        if len(by_signal_rows[st]) < 5:
            by_signal_rows[st].append(r)

    print("\n--- Summary counts ---")
    print("By year:", dict(sorted(by_year.items())))
    print("By region_macro:", dict(sorted(by_region.items())))
    print("By segment:", dict(sorted(by_segment.items())))
    print("By signal_type:", dict(sorted(by_signal.items())))
    print("\n--- 5 sample rows per signal_type ---")
    for st in sorted(by_signal_rows.keys()):
        print(f"\n[{st}]")
        for i, r in enumerate(by_signal_rows[st], 1):
            desc = (r.get("description") or "")[:60]
            if len(r.get("description") or "") > 60:
                desc += "..."
            print(f"  {i}. {r.get('event_date')} | {r.get('company_name')} | {r.get('region_macro')} | {r.get('segment')} | {desc}")
    return csv_path


def main():
    repo_root = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(repo_root, "phase5a_verification")
    run(out_dir)


if __name__ == "__main__":
    main()
