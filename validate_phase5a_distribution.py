"""
Phase 5A expansion – validate distribution against strict numeric targets.
Loads seed CSV (same validation/dedupe as ingest), prints counts, percentages, and range checks.
"""
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ingest_curated_seed import load_and_dedupe_csv

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(REPO_ROOT, "curated_structural_seed_2020_2024.csv")


def run():
    rows, errors = load_and_dedupe_csv(CSV_PATH)
    if errors:
        for e in errors:
            print(e)
        print(f"Validation errors: {len(errors)}. Fix CSV first.")
        sys.exit(1)
    n = len(rows)
    print(f"Total rows (after dedupe): {n}")
    if n < 40 or n > 45:
        print(f"  FAIL: total must be 40-45 (current {n})")
    else:
        print(f"  OK: total within 40-45")

    by_year = defaultdict(int)
    by_region = defaultdict(int)
    by_segment = defaultdict(int)
    by_signal = defaultdict(int)
    by_segment_rows = defaultdict(list)
    for r in rows:
        by_year[r.get("year")] += 1
        by_region[r.get("region_macro") or ""] += 1
        by_segment[r.get("segment") or ""] += 1
        by_signal[r.get("signal_type") or ""] += 1
        seg = r.get("segment") or ""
        if len(by_segment_rows[seg]) < 5:
            by_segment_rows[seg].append(r)

    print("\n--- Distribution by year ---")
    for y in sorted(by_year.keys()):
        print(f"  {y}: {by_year[y]}")
    print("\n--- Distribution by region_macro ---")
    for r in sorted(by_region.keys()):
        print(f"  {r}: {by_region[r]}")
    print("\n--- Distribution by segment ---")
    for s in sorted(by_segment.keys()):
        pct = (by_segment[s] / n * 100) if n else 0
        print(f"  {s}: {by_segment[s]} ({pct:.1f}%)")
    print("\n--- Distribution by signal_type ---")
    for t in sorted(by_signal.keys()):
        pct = (by_signal[t] / n * 100) if n else 0
        print(f"  {t}: {by_signal[t]} ({pct:.1f}%)")

    raw_pct = (by_segment.get("raw_materials", 0) / n * 100) if n else 0
    foam_total = by_segment.get("flexible_foam", 0) + by_segment.get("rigid_foam", 0)
    foam_pct = (foam_total / n * 100) if n else 0
    tpu_pct = (by_segment.get("tpu", 0) / n * 100) if n else 0
    case_pct = (by_segment.get("case", 0) / n * 100) if n else 0
    cap_pct = (by_signal.get("capacity", 0) / n * 100) if n else 0

    print("\n--- Value chain targets (mandatory ranges) ---")
    print(f"  raw_materials: {raw_pct:.1f}% (target 50-60%, hard bounds 45-65%)")
    print(f"  flexible_foam + rigid_foam: {foam_pct:.1f}% (target 20-25%)")
    print(f"  tpu: {tpu_pct:.1f}% (target 10-15%, min 3 events) -> {by_segment.get('tpu', 0)} events")
    print(f"  case: {case_pct:.1f}% (target 5-10%)")
    print("\n--- Signal type targets ---")
    print(f"  capacity: {cap_pct:.1f}% (target 50-60%, hard bounds 45-65%)")
    print(f"  mna: {(by_signal.get('mna',0)/n*100):.1f}% (target 15-20%)")
    print(f"  regulation: {(by_signal.get('regulation',0)/n*100):.1f}% (target 10-15%)")
    print(f"  technology: {(by_signal.get('technology',0)/n*100):.1f}% (target 10-15%)")

    fails = []
    if raw_pct < 45 or raw_pct > 65:
        fails.append("raw_materials outside 45-65%")
    if cap_pct < 45 or cap_pct > 65:
        fails.append("capacity outside 45-65%")
    if by_segment.get("tpu", 0) < 3:
        fails.append("TPU events < 3")
    if foam_total < 3:
        fails.append("foam events (flexible+rigid) < 3")
    if by_signal.get("technology", 0) < 2:
        fails.append("technology events < 2")
    if fails:
        print("\n  FAILS:", "; ".join(fails))
    else:
        print("\n  All mandatory range checks passed.")

    print("\n--- 5 sample rows per segment (for review) ---")
    for seg in sorted(by_segment_rows.keys()):
        print(f"\n[{seg}]")
        for i, r in enumerate(by_segment_rows[seg], 1):
            desc = (r.get("description") or "")[:55]
            if len(r.get("description") or "") > 55:
                desc += "..."
            print(f"  {i}. {r.get('event_date')} | {r.get('company_name')} | {r.get('region_macro')} | {r.get('signal_type')} | {desc}")


if __name__ == "__main__":
    run()
