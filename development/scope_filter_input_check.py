"""
CHARLIEC – Scope Filter Input Diagnostic

Produces a diagnostic for the exact signals that ENTER the customer scope filter
(i.e. candidates in DB for this run_id = signals_after_preinsert_validation).
Does NOT run the scope filter.

Output: Live Results/Scope Filter Input Check.txt with:
  - Total signals entering scope filter
  - CATEGORY DISTRIBUTION
  - REGION DISTRIBUTION
  - VALUE_CHAIN_LINK DISTRIBUTION

Usage:
  python development/scope_filter_input_check.py <run_id>
"""

import sys
from pathlib import Path
from collections import Counter

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

LIVE_RESULTS_DIR = REPO_ROOT / "Live Results"
OUTPUT_FILENAME = "Scope Filter Input Check.txt"


def _norm(v) -> str:
    if v is None or (isinstance(v, str) and not v.strip()):
        return "unknown"
    return (v if isinstance(v, str) else str(v)).strip()


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python development/scope_filter_input_check.py <run_id>")
        sys.exit(1)
    run_id = sys.argv[1].strip()
    if not run_id:
        print("Provide a non-empty run_id.")
        sys.exit(1)

    try:
        from core.generator_db import get_candidate_articles_for_run
    except Exception as e:
        print(f"Cannot import generator_db: {e}")
        sys.exit(1)

    candidates = get_candidate_articles_for_run(run_id)
    total = len(candidates)

    category_dist = Counter(_norm(c.get("category")) for c in candidates)
    region_dist = Counter(_norm(c.get("region")) for c in candidates)
    value_chain_dist = Counter(_norm(c.get("value_chain_link")) for c in candidates)

    LIVE_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = LIVE_RESULTS_DIR / OUTPUT_FILENAME

    lines = [
        f"Run ID: {run_id}",
        "",
        f"Total signals entering scope filter: {total}",
        "",
        "1. CATEGORY DISTRIBUTION",
        "category | count",
        "-" * 40,
    ]
    for key in sorted(category_dist.keys(), key=lambda k: (-category_dist[k], k)):
        lines.append(f"{key} | {category_dist[key]}")
    lines.extend([
        "",
        "2. REGION DISTRIBUTION",
        "region | count",
        "-" * 40,
    ])
    for key in sorted(region_dist.keys(), key=lambda k: (-region_dist[k], k)):
        lines.append(f"{key} | {region_dist[key]}")
    lines.extend([
        "",
        "3. VALUE_CHAIN_LINK DISTRIBUTION",
        "value_chain_link | count",
        "-" * 40,
    ])
    for key in sorted(value_chain_dist.keys(), key=lambda k: (-value_chain_dist[k], k)):
        lines.append(f"{key} | {value_chain_dist[key]}")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {total} signals (scope filter input) to: {out_path}")


if __name__ == "__main__":
    main()
