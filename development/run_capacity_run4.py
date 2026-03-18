"""
CHARLIEC – RUN 4 CAPACITY TEST.
Runs matrix run 4 locally with 1800s max; produces Live Results/Generator Capacity Run 4.txt.
Requires env: SPEC_ID, WORKSPACE_ID.
No code or configuration changes during the run.

Runtime rule (Runs 4–8):
- Allow up to 1800 seconds wall-clock.
- Still record whether the run crossed 720 seconds.

Classification:
- SAFE: elapsed_sec <= 720
- SLOW_BUT_COMPLETE: 720 < elapsed_sec <= 1800
- TIMEOUT_SUSPECTED: did not complete within 1800 seconds
"""
import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime, timezone

REPO_ROOT = Path(__file__).resolve().parent.parent
TIMEOUT_SEC = 1800  # hard cap for Runs 4–8
PRODUCTION_LIMIT_SEC = 720  # production-safe threshold
SINGLE_RUN_SCRIPT = REPO_ROOT / "development" / "run_single_capacity_run.py"
OUTPUT_FILE = REPO_ROOT / "Live Results" / "Generator Capacity Run 4.txt"


def _classify(elapsed: float | None, completed: bool) -> tuple[str, str, str]:
    """Return (status, production_safe, completed_within_1800)."""
    if not completed or elapsed is None:
        return "TIMEOUT_SUSPECTED", "no", "no"
    if elapsed <= PRODUCTION_LIMIT_SEC:
        return "SAFE", "yes", "yes"
    if elapsed <= TIMEOUT_SEC:
        return "SLOW_BUT_COMPLETE", "no", "yes"
    # Should not happen if TIMEOUT_SEC is enforced, but keep for safety.
    return "TIMEOUT_SUSPECTED", "no", "no"


def main():
    spec_id = os.environ.get("SPEC_ID", "").strip()
    workspace_id = os.environ.get("WORKSPACE_ID", "").strip()
    if not spec_id or not workspace_id:
        print("Set SPEC_ID and WORKSPACE_ID, then run again.", file=sys.stderr)
        sys.exit(1)

    env = os.environ.copy()
    env["RUN_NUMBER"] = "4"
    env["SPEC_ID"] = spec_id
    env["WORKSPACE_ID"] = workspace_id

    start_wall = datetime.now(timezone.utc).isoformat()
    start_ts = datetime.now(timezone.utc).timestamp()
    completed = False

    try:
        proc = subprocess.run(
            [sys.executable, str(SINGLE_RUN_SCRIPT)],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SEC,
        )
        completed = True
        end_ts = datetime.now(timezone.utc).timestamp()
        elapsed = round(end_ts - start_ts, 1)
        out = (proc.stdout or "").strip()
        if out:
            try:
                r = json.loads(out.split("\n")[-1])
            except json.JSONDecodeError:
                r = {
                    "run_number": 4,
                    "run_id": None,
                    "start_timestamp": start_wall,
                    "end_timestamp": datetime.now(timezone.utc).isoformat(),
                    "elapsed_seconds": elapsed,
                    "html_generated": "no",
                    "audit_generated": "no",
                    "developments_visible": 0,
                    "error_message": out[:500],
                }
        else:
            r = {
                "run_number": 4,
                "run_id": None,
                "start_timestamp": start_wall,
                "end_timestamp": datetime.now(timezone.utc).isoformat(),
                "elapsed_seconds": elapsed,
                "html_generated": "no",
                "audit_generated": "no",
                "developments_visible": 0,
                "error_message": (proc.stderr or "")[:500],
            }
    except subprocess.TimeoutExpired:
        elapsed = TIMEOUT_SEC
        r = {
            "run_number": 4,
            "run_id": None,
            "start_timestamp": start_wall,
            "end_timestamp": datetime.now(timezone.utc).isoformat(),
            "elapsed_seconds": elapsed,
            "html_generated": "no",
            "audit_generated": "no",
            "developments_visible": 0,
            "error_message": f"Run exceeded {TIMEOUT_SEC} seconds and was stopped.",
        }
    except Exception as e:
        elapsed = None
        r = {
            "run_number": 4,
            "run_id": None,
            "start_timestamp": start_wall,
            "end_timestamp": datetime.now(timezone.utc).isoformat(),
            "elapsed_seconds": None,
            "html_generated": "no",
            "audit_generated": "no",
            "developments_visible": 0,
            "error_message": str(e)[:500],
        }

    status, production_safe, completed_within_1800 = _classify(elapsed, completed)

    # Build deliverable per CHARLIEC RUN 4 spec
    lines = [
        "CHARLIEC – RUN 4 CAPACITY TEST",
        "===============================",
        "",
        "run number = 4",
        f"run_id = {r.get('run_id') or ''}",
        f"start timestamp = {r.get('start_timestamp') or ''}",
        f"end timestamp = {r.get('end_timestamp') or ''}",
        f"elapsed seconds = {r.get('elapsed_seconds')}",
        f"status = {status}",
        f"HTML generated = {r.get('html_generated', 'no')}",
        f"audit generated = {r.get('audit_generated', 'no')}",
        f"developments visible in report = {r.get('developments_visible', 0)}",
        f"production_safe = {production_safe}",
        f"completed_within_1800 = {completed_within_1800}",
        "",
    ]
    if r.get("audit_generated") == "yes":
        lines.extend(
            [
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
            ]
        )
    if status != "SAFE":
        lines.extend(
            [
                "Failure / timeout details:",
                f"  last completed stage = {r.get('last_completed_stage') or 'n/a'}",
                f"  last visible trace marker = {r.get('last_completed_stage') or r.get('error_message') or 'n/a'}",
                f"  probable failure mode = {r.get('failure_mode') or (r.get('error_message') or 'n/a')}",
                "",
            ]
        )
    lines.append("GitHub requirement: No code changes were made during this run.")
    if os.environ.get("CHARLIEC_CODE_CHANGES_MADE") == "1":
        lines[
            -1
        ] = "GitHub requirement: Code changes were required; confirm all changes were committed and pushed to GitHub."

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text("\n".join(lines), encoding="utf-8")
    print(f"Written: {OUTPUT_FILE}")
    sys.exit(0 if status in ("SAFE", "SLOW_BUT_COMPLETE") else 1)


if __name__ == "__main__":
    main()

