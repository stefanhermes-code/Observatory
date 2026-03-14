"""
CHARLIEC – Scope Filter Input Diagnostic

Produces a diagnostic for the exact signals that ENTER the customer scope filter.
Uses the same dataset as the pipeline: table candidate_articles, filtered by run_id.
Filtering fields used by the scope filter: region, category, value_chain_link.
Does NOT run the scope filter.

Output: Live Results/Scope Filter Input Check.txt with:
  - Total signals entering scope filter
  - CATEGORY DISTRIBUTION
  - REGION DISTRIBUTION
  - VALUE_CHAIN_LINK DISTRIBUTION

Usage:
  python development/scope_filter_input_check.py <run_id>

run_id can be the full UUID (e.g. 292fb71c-1645-48a7-b92b-81c51c985c5f) or a short
prefix (e.g. 292fb71c). If short, the script resolves it to the full UUID via
newsletter_runs so the candidate_articles query succeeds.
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


def _is_full_uuid(s: str) -> bool:
    s = (s or "").strip()
    return len(s) == 36 and s.count("-") == 4


def _resolve_run_id(run_id: str) -> str:
    """If run_id looks like a short prefix (e.g. 292fb71c), resolve to full UUID from newsletter_runs."""
    run_id = (run_id or "").strip()
    if _is_full_uuid(run_id):
        return run_id
    try:
        from core.admin_db import get_recent_runs
        runs, _ = get_recent_runs(limit=200)
        prefix = run_id.lower()
        matches = [r for r in runs if r.get("id") and str(r["id"]).lower().startswith(prefix)]
        if len(matches) == 1:
            return matches[0]["id"]
        if len(matches) > 1:
            return matches[0]["id"]  # most recent
    except Exception:
        pass
    return run_id


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python development/scope_filter_input_check.py <run_id>")
        sys.exit(1)
    run_id_arg = sys.argv[1].strip()
    if not run_id_arg:
        print("Provide a non-empty run_id.")
        sys.exit(1)

    run_id = _resolve_run_id(run_id_arg)
    if run_id_arg != run_id:
        print(f"Resolved run_id prefix '{run_id_arg}' to full UUID: {run_id}")

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
    ]
    if run_id_arg != run_id:
        lines.append(f"(resolved from: {run_id_arg})")
    lines.extend([
        "",
        f"Total signals entering scope filter: {total}",
        "",
        "1. CATEGORY DISTRIBUTION",
        "category | count",
        "-" * 40,
    ])
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
