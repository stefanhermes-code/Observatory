"""
Phase 3 review – export all CSVs and JSONL for a given run_id (test run only).
Usage: python export_phase3_data.py <run_id> [--out-dir .]
Writes: 01_candidate_articles.csv, 02_extracted_signals.csv, 02_extracted_signals_raw.jsonl,
        03_signal_clusters.csv, 03_cluster_members.csv, 04_phase3_classification_snapshot.csv,
        and 02_pivot_summary.txt
"""
import csv
import hashlib
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))


def _cluster_key(company_name: str, signal_type: str, region: str, segment: str) -> str:
    c = (company_name or "").strip()
    t = (signal_type or "other").strip()
    r = (region or "").strip()
    s = (segment or "unknown").strip()
    raw = f"{c}|{t}|{r}|{s}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def run(run_id: str, out_dir: str):
    from core.generator_db import (
        get_candidate_articles_for_run,
        get_extracted_signals_for_run,
        get_signal_clusters_for_run,
    )

    os.makedirs(out_dir, exist_ok=True)

    # 01 – candidate_articles
    candidates = get_candidate_articles_for_run(run_id)
    cols01 = ["id", "title", "snippet", "source_name", "published_at", "category", "region", "value_chain_link", "url", "canonical_url", "query_id"]
    path01 = os.path.join(out_dir, "01_candidate_articles.csv")
    with open(path01, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols01, extrasaction="ignore")
        w.writeheader()
        for c in candidates:
            row = {k: c.get(k) for k in cols01}
            row["id"] = c.get("id")
            w.writerow(row)
    print(f"Wrote {path01} ({len(candidates)} rows)")

    # 02 – extracted_signals
    signals = get_extracted_signals_for_run(run_id)
    cols02 = ["article_id", "company_name", "segment", "region", "signal_type", "numeric_value", "numeric_unit", "currency", "time_horizon", "confidence_score"]
    path02_csv = os.path.join(out_dir, "02_extracted_signals.csv")
    path02_jsonl = os.path.join(out_dir, "02_extracted_signals_raw.jsonl")
    path02_pivot = os.path.join(out_dir, "02_pivot_summary.txt")

    with open(path02_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols02 + ["raw_json"], extrasaction="ignore")
        w.writeheader()
        for s in signals:
            row = {k: s.get(k) for k in cols02}
            row["raw_json"] = json.dumps(s.get("raw_json")) if s.get("raw_json") is not None else ""
            w.writerow(row)

    with open(path02_jsonl, "w", encoding="utf-8") as f:
        for s in signals:
            f.write(json.dumps(s.get("raw_json")) + "\n")

    # Pivot: count by signal_type, segment, region
    by_type = defaultdict(int)
    by_segment = defaultdict(int)
    by_region = defaultdict(int)
    for s in signals:
        by_type[s.get("signal_type") or "other"] += 1
        by_segment[s.get("segment") or "unknown"] += 1
        by_region[s.get("region") or ""] += 1
    with open(path02_pivot, "w", encoding="utf-8") as f:
        f.write("count by signal_type:\n")
        for k, v in sorted(by_type.items(), key=lambda x: -x[1]):
            f.write(f"  {k}: {v}\n")
        f.write("count by segment:\n")
        for k, v in sorted(by_segment.items(), key=lambda x: -x[1]):
            f.write(f"  {k}: {v}\n")
        f.write("count by region:\n")
        for k, v in sorted(by_region.items(), key=lambda x: -x[1]):
            f.write(f"  {k or '(empty)'}: {v}\n")
    print(f"Wrote {path02_csv} ({len(signals)} rows), {path02_jsonl}, {path02_pivot}")

    # 03 – signal_clusters
    clusters = get_signal_clusters_for_run(run_id)
    cols03 = ["cluster_key", "signal_type", "region", "segment", "aggregated_numeric_value", "aggregated_numeric_unit", "cluster_size", "structural_weight"]
    path03 = os.path.join(out_dir, "03_signal_clusters.csv")
    with open(path03, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols03, extrasaction="ignore")
        w.writeheader()
        for c in clusters:
            w.writerow({k: c.get(k) for k in cols03})
    print(f"Wrote {path03} ({len(clusters)} rows)")

    # 03 – cluster_members: cluster_key -> signal id list (we do not store members in DB; derive from signals)
    key_to_ids: dict = defaultdict(list)
    for s in signals:
        key = _cluster_key(s.get("company_name"), s.get("signal_type"), s.get("region"), s.get("segment"))
        sid = s.get("id")
        if sid:
            key_to_ids[key].append(str(sid))
    path03_members = os.path.join(out_dir, "03_cluster_members.csv")
    with open(path03_members, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["cluster_key", "signal_id"])
        for key, ids in sorted(key_to_ids.items()):
            for sid in ids:
                w.writerow([key, sid])
    print(f"Wrote {path03_members}")

    # 04 – phase3_classification_snapshot (Phase 4: final_classification, override_source, materiality_flag)
    cols04 = ["cluster_key", "cluster_size", "signal_type", "segment", "region", "llm_classification",
              "doctrine_classification", "final_classification", "override_source", "override_reason", "materiality_flag", "repeat_flag"]
    path04 = os.path.join(out_dir, "04_phase3_classification_snapshot.csv")
    with open(path04, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols04, extrasaction="ignore")
        w.writeheader()
        for c in clusters:
            final = c.get("final_classification") or c.get("classification")
            row = {
                "cluster_key": c.get("cluster_key"),
                "cluster_size": c.get("cluster_size"),
                "signal_type": c.get("signal_type"),
                "segment": c.get("segment"),
                "region": c.get("region"),
                "llm_classification": c.get("classification"),
                "doctrine_classification": c.get("final_classification") if c.get("override_source") == "doctrine" else None,
                "final_classification": final,
                "override_source": c.get("override_source"),
                "override_reason": c.get("override_reason"),
                "materiality_flag": c.get("materiality_flag"),
                "repeat_flag": None,
            }
            w.writerow(row)
    print(f"Wrote {path04} ({len(clusters)} rows)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python export_phase3_data.py <run_id> [--out-dir .]")
        sys.exit(1)
    run_id = sys.argv[1]
    out_dir = "."
    if "--out-dir" in sys.argv:
        i = sys.argv.index("--out-dir")
        if i + 1 < len(sys.argv):
            out_dir = sys.argv[i + 1]
    run(run_id, out_dir)
