"""
CHARLIEC – RUN 9 CAPACITY TEST (Ultra-relaxed + fixed classification)

Local only runner. Requires env:
  - SPEC_ID
  - WORKSPACE_ID

Writes:
  - Live Results/Generator Capacity Run 9.txt
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime, timezone

REPO_ROOT = Path(__file__).resolve().parent.parent
SINGLE_RUN_SCRIPT = REPO_ROOT / "development" / "run_single_capacity_run.py"
OUTPUT_FILE = REPO_ROOT / "Live Results" / "Generator Capacity Run 9.txt"

TIMEOUT_SEC = 3600


def _classify_runtime(elapsed_seconds) -> str:
    if elapsed_seconds is None:
        return "TIMEOUT_SUSPECTED"
    if elapsed_seconds <= 720:
        return "SAFE"
    if elapsed_seconds <= 1800:
        return "SLOW_BUT_COMPLETE"
    if elapsed_seconds <= 3600:
        return "VERY_SLOW_BUT_COMPLETE"
    return "TIMEOUT_SUSPECTED"


def _git_info():
    try:
        r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True, timeout=5)
        commit = (r.stdout or "").strip() if r.returncode == 0 else "unknown"
    except Exception:
        commit = "unknown"
    try:
        r = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True, timeout=5)
        branch = (r.stdout or "").strip() if r.returncode == 0 else "unknown"
    except Exception:
        branch = "unknown"
    return commit, branch


def main():
    spec_id = os.environ.get("SPEC_ID", "").strip()
    workspace_id = os.environ.get("WORKSPACE_ID", "").strip()
    if not spec_id or not workspace_id:
        print("Set SPEC_ID and WORKSPACE_ID, then run again.", file=sys.stderr)
        sys.exit(1)

    env = os.environ.copy()
    env["RUN_NUMBER"] = "9"
    env["SPEC_ID"] = spec_id
    env["WORKSPACE_ID"] = workspace_id

    start_wall = datetime.now(timezone.utc).isoformat()
    start_ts = datetime.now(timezone.utc)

    try:
        proc = subprocess.run(
            [sys.executable, str(SINGLE_RUN_SCRIPT)],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SEC,
        )

        out = (proc.stdout or "").strip()
        if not out:
            r = {
                "run_number": 9,
                "status": "timeout_suspected" if proc.stderr and "timeout" in proc.stderr.lower() else "failure",
                "run_id": None,
                "start_timestamp": start_wall,
                "end_timestamp": datetime.now(timezone.utc).isoformat(),
                "elapsed_seconds": TIMEOUT_SEC,
                "html_generated": "no",
                "audit_generated": "no",
                "developments_visible": 0,
                "error_message": (proc.stderr or "")[:500],
            }
        else:
            try:
                r = json.loads(out.split("\n")[-1])
            except json.JSONDecodeError:
                r = {
                    "run_number": 9,
                    "status": "failure",
                    "run_id": None,
                    "start_timestamp": start_wall,
                    "end_timestamp": datetime.now(timezone.utc).isoformat(),
                    "elapsed_seconds": None,
                    "html_generated": "no",
                    "audit_generated": "no",
                    "developments_visible": 0,
                    "error_message": out[:500],
                }

    except subprocess.TimeoutExpired:
        r = {
            "run_number": 9,
            "status": "timeout_suspected",
            "run_id": None,
            "start_timestamp": start_wall,
            "end_timestamp": datetime.now(timezone.utc).isoformat(),
            "elapsed_seconds": TIMEOUT_SEC,
            "html_generated": "no",
            "audit_generated": "no",
            "developments_visible": 0,
            "error_message": f"Run exceeded {TIMEOUT_SEC} seconds and was stopped.",
        }

    elapsed = r.get("elapsed_seconds")
    runtime_status = _classify_runtime(elapsed)
    completed_within_1800 = "yes" if (elapsed is not None and elapsed <= 1800 and runtime_status != "TIMEOUT_SUSPECTED") else "no"
    completed_within_3600 = "yes" if (elapsed is not None and elapsed <= 3600) else "no"
    production_safe = "yes" if runtime_status == "SAFE" else "no"

    commit, branch = _git_info()

    category_distribution = r.get("category_distribution") or {}
    section_distribution = r.get("section_distribution") or {}

    # Format distributions
    def _fmt_dist(d: dict) -> str:
        if not d:
            return "(none)"
        total = sum(int(v) for v in d.values())
        parts = []
        for k, v in sorted(d.items(), key=lambda x: int(x[1]), reverse=True):
            share = (int(v) / total) if total else 0
            parts.append(f"  - {k}: {v} ({share:.1%})")
        return "\n".join(parts)

    lines = [
        "CHARLIEC – RUN 9 CAPACITY TEST",
        "===============================",
        "",
        "run number = 9",
        f"run_id = {r.get('run_id') or ''}",
        f"start timestamp = {r.get('start_timestamp') or ''}",
        f"end timestamp = {r.get('end_timestamp') or ''}",
        f"elapsed seconds = {r.get('elapsed_seconds')}",
        f"status = {runtime_status}",
        "",
        f"production_safe = {production_safe}",
        f"completed_within_1800 = {completed_within_1800}",
        f"completed_within_3600 = {completed_within_3600}",
        "",
        f"HTML generated = {r.get('html_generated', 'no')}",
        f"audit generated = {r.get('audit_generated', 'no')}",
        f"developments visible in report = {r.get('developments_visible', 0)}",
        "",
        f"Git commit = {commit}",
        f"branch = {branch}",
        "",
        "Audit (pipeline counters):",
        f"  signals_after_query_plan = {r.get('signals_after_query_plan')}",
        f"  stage_2_after_date_filter = {r.get('stage_2_after_date_filter')}",
        f"  signals_after_preinsert_validation = {r.get('signals_after_preinsert_validation')}",
        f"  stage_3_after_customer_scope_filter = {r.get('stage_3_after_customer_scope_filter')}",
        f"  stage_4_after_section_mapping = {r.get('stage_4_after_section_mapping')}",
        f"  stage_5_clusters_formed = {r.get('stage_5_clusters_formed')}",
        f"  stage_6_developments_extracted = {r.get('stage_6_developments_extracted')}",
        f"  stage_8_developments_written_to_report = {r.get('stage_8_developments_written_to_report')}",
        "",
        "Audit (validation & distributions):",
        f"  validation_pass_rate = {r.get('validation_pass_rate')}",
        f"  mapped signals count = {r.get('mapped_signals_count')}",
        "",
        "Category distribution (Run 9 allowed categories):",
        _fmt_dist(category_distribution),
        "",
        "Section distribution (Run 9 flexible mapping):",
        _fmt_dist(section_distribution),
        "",
    ]

    if r.get("status") not in ("success",):
        lines.extend(
            [
                "Failure / timeout details:",
                f"  last visible trace marker = {r.get('last_completed_stage') or (r.get('error_message') or '')[:60] or 'n/a'}",
                f"  probable failure mode = {r.get('failure_mode') or (r.get('error_message') or 'n/a')}",
            ]
        )

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text("\n".join(lines), encoding="utf-8")
    print(f"Written: {OUTPUT_FILE}")
    sys.exit(0 if runtime_status != "TIMEOUT_SUSPECTED" else 1)


if __name__ == "__main__":
    main()

