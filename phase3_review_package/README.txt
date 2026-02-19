Phase 3 review package – extraction, clustering, classification integrity.

Test namespace: Use a single test run only (no production). This codebase uses tables
candidate_articles, extracted_signals, signal_clusters scoped by run_id (no *_v2_test tables).

Workflow to produce the full evidence set:

1. Seed test run and 20 candidates
   From repo root:
     python phase3_review_package/01_seed_script.py
   Capture the printed run_id. Optionally set WORKSPACE_ID, SPEC_ID (or PHASE3_*) for your test spec.

2. Run extraction + clustering + classification and write run trace
     python phase3_review_package/run_phase3_trace.py <run_id> --out-dir phase3_review_package
   This populates 06_run_trace.txt.

3. Export all CSVs and JSONL
     python phase3_review_package/export_phase3_data.py <run_id> --out-dir phase3_review_package
   Overwrites: 01_candidate_articles.csv, 02_extracted_signals.csv, 02_extracted_signals_raw.jsonl,
   02_pivot_summary.txt, 03_signal_clusters.csv, 03_cluster_members.csv, 04_phase3_classification_snapshot.csv.

4. Deliver the folder phase3_review_package/ as-is (including 05_prompts_and_code/ with migrations and exact prompts/code).

STOP RULE: Do not proceed to Phase 4 (baseline memory) or Phase 5 (synthesis) until Phase 3 passes review.
