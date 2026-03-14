"""
CHARLIEC – Customer Scope Filter Diagnostic

Produces a diagnostic dataset for the candidates that passed the date filter
(BEFORE the customer scope filter is applied). Does NOT run the scope filter.

Output: Live Results/Customer Scope Check.txt with:
  - Total candidate count
  - CATEGORY DISTRIBUTION (category | count)
  - REGION DISTRIBUTION (region | count)
  - VALUE_CHAIN_LINK DISTRIBUTION (value_chain_link | count)

This allows identifying why the scope filter rejects all signals (e.g. missing
or mismatched category/region/value_chain_link vs spec vocabulary).

Usage:
  python development/customer_scope_check.py <run_id>
  python development/customer_scope_check.py c7aaa579-68d1-4391-8061-b3992e42e545
"""

import sys
from pathlib import Path
from collections import Counter

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

OUTPUT_FILENAME = "Customer Scope Check.txt"


def _norm(v) -> str:
    """Normalize null/empty to a single label for counting."""
    if v is None or (isinstance(v, str) and not v.strip()):
        return "unknown"
    return (v if isinstance(v, str) else str(v)).strip()


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python development/customer_scope_check.py <run_id>")
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

    # Load candidates for this run. These are the rows that passed the date filter;
    # we do NOT apply the customer scope filter here.
    candidates = get_candidate_articles_for_run(run_id)
    total = len(candidates)

    category_dist = Counter(_norm(c.get("category")) for c in candidates)
    region_dist = Counter(_norm(c.get("region")) for c in candidates)
    value_chain_dist = Counter(_norm(c.get("value_chain_link")) for c in candidates)

    # Write to Customer Scope Check.txt (repo root or current dir)
    out_path = REPO_ROOT / OUTPUT_FILENAME
    lines = [
        f"Run ID: {run_id}",
        "",
        f"Total candidate count: {total}",
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
    print(f"Wrote {total} candidates (before scope filter) to: {out_path}")
    print("(Compare category/region/value_chain_link to the spec to find mismatches.)")


if __name__ == "__main__":
    main()
