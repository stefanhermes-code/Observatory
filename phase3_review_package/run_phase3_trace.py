# Run extraction, clustering, classification for run_id and write 06_run_trace.txt
# Usage: python run_phase3_trace.py <run_id> [--out-dir .]
import os
import sys
from datetime import datetime, timezone
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

def run(run_id, out_dir):
    from core.generator_db import get_candidate_articles_for_run, get_signal_clusters_for_run
    from core.signal_extraction_v2 import run_signal_extraction_v2
    from core.signal_clustering_v2 import run_signal_clustering_v2
    from core.signal_classification_v2 import run_signal_classification_v2
    from collections import Counter
    os.makedirs(out_dir, exist_ok=True)
    lines = []
    ts = datetime.now(timezone.utc).isoformat()
    lines.append("timestamp_of_run=" + ts)
    candidates = get_candidate_articles_for_run(run_id)
    n_candidates = len(candidates)
    lines.append("number_of_candidate_articles_processed=" + str(n_candidates))
    errors = []
    try:
        ext = run_signal_extraction_v2(run_id=run_id, candidates=candidates)
        lines.append("extraction_result=" + str(ext))
        lines.append("number_of_extracted_signals_inserted=" + str(ext.get("signals_inserted", 0)))
    except Exception as e:
        errors.append("extraction: " + str(e))
        lines.append("extraction_error=" + str(e))
    try:
        clust = run_signal_clustering_v2(run_id=run_id)
        lines.append("clustering_result=" + str(clust))
        lines.append("number_of_clusters_produced=" + str(clust.get("clusters_created", 0)))
    except Exception as e:
        errors.append("clustering: " + str(e))
        lines.append("clustering_error=" + str(e))
    try:
        class_result = run_signal_classification_v2(run_id=run_id)
        lines.append("classification_result=" + str(class_result))
        clusters = get_signal_clusters_for_run(run_id)
        dist = Counter(c.get("classification") for c in clusters if c.get("classification"))
        lines.append("classification_distribution=" + str(dict(dist)))
    except Exception as e:
        errors.append("classification: " + str(e))
        lines.append("classification_error=" + str(e))
    lines.append("errors_or_warnings_logged=" + ("; ".join(errors) if errors else "none"))
    path = os.path.join(out_dir, "06_run_trace.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("Wrote " + path)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_phase3_trace.py <run_id> [--out-dir .]")
        sys.exit(1)
    run_id = sys.argv[1]
    out_dir = "."
    if "--out-dir" in sys.argv:
        i = sys.argv.index("--out-dir")
        if i + 1 < len(sys.argv):
            out_dir = sys.argv[i + 1]
    run(run_id, out_dir)
