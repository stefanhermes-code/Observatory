"""
Customer-scope filter diagnostic: region/category/value_chain_link distribution for a run's candidates.

Run from repo root with a run_id to see which dimension is eliminating candidates at stage 3.
If Supabase is configured (Streamlit secrets or .env), queries the DB and prints distributions.
Otherwise prints SQL for you to run in Supabase.

Usage:
  python development/candidate_scope_breakdown.py <run_id>
  python development/candidate_scope_breakdown.py c7aaa579-68d1-4391-8061-b3992e42e545
"""

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

def main():
    if len(sys.argv) < 2:
        print("Usage: python development/candidate_scope_breakdown.py <run_id>")
        sys.exit(1)
    run_id = sys.argv[1].strip()
    if not run_id:
        print("Provide a non-empty run_id.")
        sys.exit(1)

    sql_region = f"""
-- Region distribution for run {run_id}
SELECT COALESCE(region, '(null)') AS region, COUNT(*) AS count
FROM candidate_articles
WHERE run_id = '{run_id}'
GROUP BY region
ORDER BY count DESC;
"""
    sql_category = f"""
-- Category distribution for run {run_id}
SELECT COALESCE(category, '(null)') AS category, COUNT(*) AS count
FROM candidate_articles
WHERE run_id = '{run_id}'
GROUP BY category
ORDER BY count DESC;
"""
    sql_vcl = f"""
-- Value chain link distribution for run {run_id}
SELECT COALESCE(value_chain_link, '(null)') AS value_chain_link, COUNT(*) AS count
FROM candidate_articles
WHERE run_id = '{run_id}'
GROUP BY value_chain_link
ORDER BY count DESC;
"""

    try:
        from core.admin_db import get_supabase_client
        supabase = get_supabase_client()
        from collections import Counter
        r = supabase.table("candidate_articles").select("region, category, value_chain_link").eq("run_id", run_id).execute()
        rows = r.data or []
        total = len(rows)
        print(f"Run ID: {run_id}")
        print(f"Total candidates: {total}")
        if total == 0:
            print("No rows. Run the SQL below in Supabase to double-check.")
            print(sql_region)
            print(sql_category)
            print(sql_vcl)
            return

        reg = Counter((x.get("region") or "(null)" for x in rows))
        print("\n--- Region distribution ---")
        for k, v in reg.most_common():
            print(f"  {k}: {v}")

        cat = Counter((x.get("category") or "(null)" for x in rows))
        print("\n--- Category distribution ---")
        for k, v in cat.most_common():
            print(f"  {k}: {v}")

        vcl = Counter((x.get("value_chain_link") or "(null)" for x in rows))
        print("\n--- Value chain link distribution ---")
        for k, v in vcl.most_common():
            print(f"  {k}: {v}")

        print("\n(Compare these to the spec's regions, categories, value_chain_links to see which dimension fails the customer scope filter.)")
    except Exception as e:
        print("Could not query Supabase:", e)
        print("\nRun the following SQL in Supabase (replace run_id if needed):\n")
        print(sql_region)
        print(sql_category)
        print(sql_vcl)


if __name__ == "__main__":
    main()
