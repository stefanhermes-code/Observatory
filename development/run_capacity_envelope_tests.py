"""
CHARLIEC – Generator Capacity Envelope Test – orchestrator.
Runs the 8-run matrix locally with 720s timeout per run. No code/config changes during sequence.
Produces Live Results/Generator Capacity Envelope.txt.
Requires env: SPEC_ID, WORKSPACE_ID (use an active spec with included_sections and min strength as per plan).
"""
import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime, timezone

REPO_ROOT = Path(__file__).resolve().parent.parent
TIMEOUT_PER_RUN = 720  # seconds
SINGLE_RUN_SCRIPT = REPO_ROOT / "development" / "run_single_capacity_run.py"
OUTPUT_FILE = REPO_ROOT / "Live Results" / "Generator Capacity Envelope.txt"


def _git_info():
    try:
        r = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=5,
        )
        commit = (r.stdout or "").strip() if r.returncode == 0 else "unknown"
    except Exception:
        commit = "unknown"
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=5,
        )
        branch = (r.stdout or "").strip() if r.returncode == 0 else "unknown"
    except Exception:
        branch = "unknown"
    return commit, branch


def _run_one(run_number: int, spec_id: str, workspace_id: str) -> dict:
    env = os.environ.copy()
    env["RUN_NUMBER"] = str(run_number)
    env["SPEC_ID"] = spec_id
    env["WORKSPACE_ID"] = workspace_id
    try:
        proc = subprocess.run(
            [sys.executable, str(SINGLE_RUN_SCRIPT)],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_PER_RUN,
        )
        out = (proc.stdout or "").strip()
        if not out and proc.stderr:
            return {
                "run_number": run_number,
                "status": "timeout_suspected" if proc.returncode == -9 or "TimeoutExpired" in str(proc.stderr) else "failure",
                "error_message": proc.stderr[:500],
                "elapsed_seconds": TIMEOUT_PER_RUN,
            }
        try:
            return json.loads(out.split("\n")[-1])
        except json.JSONDecodeError:
            return {"run_number": run_number, "status": "failure", "error_message": out[:500]}
    except subprocess.TimeoutExpired:
        return {
            "run_number": run_number,
            "status": "timeout_suspected",
            "elapsed_seconds": TIMEOUT_PER_RUN,
            "error_message": "Run exceeded 720s and was stopped.",
            "start_timestamp": None,
            "end_timestamp": datetime.now(timezone.utc).isoformat(),
            "html_generated": "no",
            "audit_generated": "no",
            "developments_visible": 0,
        }
    except Exception as e:
        return {"run_number": run_number, "status": "failure", "error_message": str(e)[:500]}


def _classify(results: list) -> dict:
    """SAFE / UNSTABLE / UNSAFE and failure mode summary."""
    safe = []
    unstable = []
    unsafe = []
    for r in results:
        s = r.get("status") or "failure"
        if s == "success" and r.get("html_generated") == "yes" and r.get("audit_generated") == "yes":
            safe.append(r["run_number"])
        elif s in ("timeout_suspected", "failure"):
            unsafe.append(r["run_number"])
        else:
            unstable.append(r["run_number"])
    return {"SAFE": safe, "UNSTABLE": unstable, "UNSAFE": unsafe}


def _write_output(results: list, commit: str, branch: str, final: bool) -> None:
    """Write / update the Generator Capacity Envelope report.

    When final=False, this is a progress snapshot for completed runs so far.
    When final=True, it includes full classification and production rules.
    """
    lines = [
        "CHARLIEC – Generator Capacity Envelope",
        "======================================",
        "",
        "Precondition: Spec used (SPEC_ID) must have included_sections = [Market Developments, Technology and Innovation, Capacity and Investment Activity, Corporate Developments, Sustainability and Circular Economy, Strategic Implications], minimum_signal_strength_in_report = None. Phase-5 is hardwired.",
        "",
        "Repository: stefanhermes-code/Observatory",
        f"Branch: {branch}",
        f"Commit: {commit}",
        "Local = Streamlit Cloud: confirmed (same repo/branch/commit, no code changes during test)",
        "",
        "Test matrix (8 runs)",
        "-------------------",
    ]
    for r in results:
        lines.append(
            f"RUN {r['run_number']}: report_period_days={r.get('report_period_days')} "
            f"categories={r.get('categories_count')} regions={r.get('regions_count')} "
            f"value_chain_links={r.get('value_chain_links_count')}"
        )

    lines.extend(
        [
            "",
            f"Progress: {len(results)}/8 runs completed.",
            "" if not final else "Per-run results",
        ]
    )
    if final:
        lines.append("----------------")

    # Per-run results for completed runs
    for r in results:
        lines.append(
            f"Run {r['run_number']}: run_id={r.get('run_id')} status={r.get('status')} "
            f"start={r.get('start_timestamp')} end={r.get('end_timestamp')} "
            f"elapsed_sec={r.get('elapsed_seconds')} HTML={r.get('html_generated')} "
            f"audit={r.get('audit_generated')} developments_visible={r.get('developments_visible')}"
        )
        if r.get("audit_generated") == "yes":
            lines.append(
                f"  audit: signals_after_query_plan={r.get('signals_after_query_plan')} "
                f"stage_2={r.get('stage_2_after_date_filter')} "
                f"signals_after_preinsert={r.get('signals_after_preinsert_validation')} "
                f"stage_3={r.get('stage_3_after_customer_scope_filter')} "
                f"stage_4={r.get('stage_4_after_section_mapping')} "
                f"stage_5={r.get('stage_5_clusters_formed')} "
                f"stage_6={r.get('stage_6_developments_extracted')} "
                f"stage_8={r.get('stage_8_developments_written_to_report')}"
            )
        if r.get("status") != "success":
            lines.append(
                f"  last_completed_stage={r.get('last_completed_stage')} "
                f"failure_mode={r.get('failure_mode')} error={r.get('error_message')}"
            )

    if final:
        classification = _classify(results)
        lines.extend(
            [
                "",
                "Failure mode classification",
                "-----------------------------",
                *[f"  {k}: {v}" for k, v in classification.items()],
                "",
                "SAFE / UNSTABLE / UNSAFE",
                "-------------------------",
                f"SAFE (complete with HTML + audit): runs {classification['SAFE']}",
                f"UNSTABLE: runs {classification['UNSTABLE']}",
                f"UNSAFE (fail or timeout): runs {classification['UNSAFE']}",
                "",
                "Practical production rules",
                "---------------------------",
                "Inferred from results:",
            ]
        )
        safe_runs = [
            r for r in results if r.get("run_number") in classification["SAFE"]
        ]
        if safe_runs:
            small = [
                r
                for r in safe_runs
                if r.get("categories_count", 0) <= 2
                and r.get("regions_count", 0) <= 2
            ]
            medium = [
                r
                for r in safe_runs
                if 2 < (r.get("categories_count") or 0) <= 5
            ]
            large = [
                r
                for r in safe_runs
                if (r.get("categories_count") or 0) > 5
            ]
            max_lookback_small = max(
                [r["report_period_days"] for r in small], default=0
            )
            max_lookback_medium = max(
                [r["report_period_days"] for r in medium], default=0
            )
            lines.append(
                f"  maximum reliable lookback small runs: {max_lookback_small} days"
            )
            lines.append(
                f"  maximum reliable lookback medium runs: {max_lookback_medium} days"
            )
            lines.append(
                "  60-day large runs safe: "
                f"{any(r.get('report_period_days') == 60 and (r.get('categories_count') or 0) > 5 for r in safe_runs)}"
            )
        lines.append(
            f"  120-day runs: {'unsafe' if 8 in classification['UNSAFE'] else 'see UNSTABLE/SAFE'}"
        )
        lines.append(
            "  synchronous execution: run within 720s per run; see UNSAFE for limits."
        )

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text("\n".join(lines), encoding="utf-8")


def main():
    spec_id = os.environ.get("SPEC_ID", "").strip()
    workspace_id = os.environ.get("WORKSPACE_ID", "").strip()
    if not spec_id or not workspace_id:
        print("Set SPEC_ID and WORKSPACE_ID (active spec and its workspace). Then run again.")
        sys.exit(1)

    commit, branch = _git_info()
    results = []

    # Create initial progress file (0/8) so user sees something immediately.
    _write_output(results, commit, branch, final=False)

    for run_num in range(1, 9):
        print(f"Run {run_num}/8 ...")
        r = _run_one(run_num, spec_id, workspace_id)
        r["end_timestamp"] = datetime.now(timezone.utc).isoformat()
        if r.get("elapsed_seconds") is None and r.get("start_timestamp"):
            # single run script may have set start only
            pass
        results.append(r)
        # Update progress file after each run
        _write_output(results, commit, branch, final=False)

    # Final write with classification and production rules
    _write_output(results, commit, branch, final=True)
    print(f"Written: {OUTPUT_FILE}")
    sys.exit(0)


if __name__ == "__main__":
    main()
