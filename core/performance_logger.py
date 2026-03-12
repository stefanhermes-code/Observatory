"""
Phase 8 – Performance metadata logger (minimal intrusion).
Captures runtime, token usage, failure modes per run; persists to run_performance, run_stage_performance, llm_call_performance.
Use monotonic timers for durations, UTC for timestamps.
"""

from __future__ import annotations

import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from core.performance_constants import estimate_cost_usd

# Module-level context for current run (set by start_run, cleared by end_run)
_run_id: Optional[str] = None
_run_started_at: Optional[datetime] = None
_run_started_monotonic: Optional[float] = None
_stage_starts: Dict[str, float] = {}  # stage_name -> monotonic
_stage_started_at: Dict[str, datetime] = {}  # stage_name -> UTC
_warnings_count: int = 0
_errors_count: int = 0
_first_error_stage: Optional[str] = None
_first_error_summary: Optional[str] = None
_llm_costs: list[float] = []  # for run total
_llm_cost_unknown: bool = False


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _get_env() -> str:
    if os.environ.get("STREAMLIT_SERVER_RUNNING") or os.environ.get("STREAMLIT_SERVER_ENVIRONMENT"):
        return "streamlit_cloud"
    if os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS"):
        return "other"
    return "local"


def _get_git_sha() -> Optional[str]:
    v = os.environ.get("SOURCE_VERSION") or os.environ.get("GIT_COMMIT") or os.environ.get("HEROKU_SLUG_COMMIT")
    if v:
        return v[:40] if len(v) > 40 else v
    try:
        import subprocess
        r = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        )
        if r.returncode == 0 and r.stdout:
            return r.stdout.strip()[:40]
    except Exception:
        pass
    return None


def _parse_usage(usage: Any) -> tuple[int, int, int]:
    """
    Robust parser: input_tokens/output_tokens/total_tokens and legacy prompt_tokens/completion_tokens.
    Do not allow 0/0 when usage exists. Returns (prompt_tokens, completion_tokens, total_tokens).
    """
    if usage is None:
        return 0, 0, 0
    # Object with attributes (OpenAI response.usage)
    inp = getattr(usage, "input_tokens", None) or getattr(usage, "prompt_tokens", None)
    out = getattr(usage, "output_tokens", None) or getattr(usage, "completion_tokens", None)
    tot = getattr(usage, "total_tokens", None)
    if inp is not None or out is not None or tot is not None:
        inp = int(inp) if inp is not None else 0
        out = int(out) if out is not None else 0
        tot = int(tot) if tot is not None else (inp + out)
        return inp, out, tot
    # Dict
    if isinstance(usage, dict):
        inp = usage.get("input_tokens") or usage.get("prompt_tokens")
        out = usage.get("output_tokens") or usage.get("completion_tokens")
        tot = usage.get("total_tokens")
        inp = int(inp) if inp is not None else 0
        out = int(out) if out is not None else 0
        tot = int(tot) if tot is not None else (inp + out)
        return inp, out, tot
    return 0, 0, 0


def start_run(run_id: str) -> None:
    """Begin performance tracking for this run. Inserts run_performance row."""
    global _run_id, _run_started_at, _run_started_monotonic, _stage_starts, _stage_started_at
    global _warnings_count, _errors_count, _first_error_stage, _first_error_summary, _llm_costs, _llm_cost_unknown
    _run_id = run_id
    _run_started_at = _utc_now()
    _run_started_monotonic = time.monotonic()
    _stage_starts = {}
    _stage_started_at = {}
    _warnings_count = 0
    _errors_count = 0
    _first_error_stage = None
    _first_error_summary = None
    _llm_costs = []
    _llm_cost_unknown = False
    try:
        from core.generator_db import get_supabase_client
        supabase = get_supabase_client()
        supabase.table("run_performance").upsert({
            "run_id": run_id,
            "run_started_at": _run_started_at.isoformat(),
            "run_status": "running",
            "environment": _get_env(),
            "git_commit_sha": _get_git_sha(),
        }, on_conflict="run_id").execute()
    except Exception:
        pass


def end_run(
    run_status: str,
    *,
    candidate_articles_count: Optional[int] = None,
    extracted_signals_count: Optional[int] = None,
    clusters_count_total: Optional[int] = None,
    clusters_count_structural: Optional[int] = None,
    doctrine_overrides_count: Optional[int] = None,
    baseline_rows_updated_count: Optional[int] = None,
    momentum_rows_updated_count: Optional[int] = None,
    synthesis_reports_generated_count: Optional[int] = None,
    critique_items_generated_count: Optional[int] = None,
    regeneration_count: Optional[int] = None,
) -> None:
    """Finalize run_performance row."""
    global _run_id, _run_started_at, _run_started_monotonic, _llm_costs, _llm_cost_unknown
    if not _run_id:
        return
    finished = _utc_now()
    cost_total = None
    if _llm_costs:
        cost_total = round(sum(_llm_costs), 6)
    try:
        from core.generator_db import get_supabase_client
        supabase = get_supabase_client()
        row = {
            "run_id": _run_id,
            "run_started_at": _run_started_at.isoformat() if _run_started_at else None,
            "run_finished_at": finished.isoformat(),
            "run_status": run_status,
            "warnings_count": _warnings_count,
            "errors_count": _errors_count,
            "first_error_stage": _first_error_stage,
            "first_error_summary": _first_error_summary,
            "cost_usd_estimated_total_run": cost_total,
            "cost_unknown_flag": _llm_cost_unknown,
            "updated_at": finished.isoformat(),
        }
        if candidate_articles_count is not None:
            row["candidate_articles_count"] = candidate_articles_count
        if extracted_signals_count is not None:
            row["extracted_signals_count"] = extracted_signals_count
        if clusters_count_total is not None:
            row["clusters_count_total"] = clusters_count_total
        if clusters_count_structural is not None:
            row["clusters_count_structural"] = clusters_count_structural
        if doctrine_overrides_count is not None:
            row["doctrine_overrides_count"] = doctrine_overrides_count
        if baseline_rows_updated_count is not None:
            row["baseline_rows_updated_count"] = baseline_rows_updated_count
        if momentum_rows_updated_count is not None:
            row["momentum_rows_updated_count"] = momentum_rows_updated_count
        if synthesis_reports_generated_count is not None:
            row["synthesis_reports_generated_count"] = synthesis_reports_generated_count
        if critique_items_generated_count is not None:
            row["critique_items_generated_count"] = critique_items_generated_count
        if regeneration_count is not None:
            row["regeneration_count"] = regeneration_count
        supabase.table("run_performance").upsert(row, on_conflict="run_id").execute()
    except Exception as e:
        import sys
        print(f"[performance_logger] end_run upsert failed: {e}", file=sys.stderr)
    _run_id = None
    _run_started_at = None
    _run_started_monotonic = None
    _llm_costs = []
    _llm_cost_unknown = False


def start_stage(stage_name: str) -> None:
    """Record stage start (monotonic timer and UTC)."""
    global _stage_starts, _stage_started_at
    _stage_starts[stage_name] = time.monotonic()
    _stage_started_at[stage_name] = _utc_now()


def end_stage(
    stage_name: str,
    status: str,
    error_type: Optional[str] = None,
    error_message: Optional[str] = None,
) -> None:
    """Record stage end and persist run_stage_performance row."""
    global _run_id, _stage_starts, _first_error_stage, _first_error_summary, _errors_count
    if not _run_id:
        return
    started_mono = _stage_starts.pop(stage_name, None)
    started_at = _stage_started_at.pop(stage_name, None)
    duration_ms = None
    if started_mono is not None:
        duration_ms = int((time.monotonic() - started_mono) * 1000)
    if status == "fail" and error_message:
        _errors_count += 1
        if _first_error_stage is None:
            _first_error_stage = stage_name
            _first_error_summary = (error_message or "")[:500]
    try:
        from core.generator_db import get_supabase_client
        supabase = get_supabase_client()
        row = {
            "run_id": _run_id,
            "stage_name": stage_name,
            "stage_started_at": started_at.isoformat() if started_at else (_run_started_at.isoformat() if _run_started_at else None),
            "stage_finished_at": _utc_now().isoformat(),
            "stage_duration_ms": duration_ms,
            "stage_status": status,
            "error_type": error_type,
            "error_message": error_message,
        }
        supabase.table("run_stage_performance").upsert(row, on_conflict="run_id,stage_name").execute()
    except Exception as e:
        import sys
        print(f"[performance_logger] end_stage upsert failed: {e}", file=sys.stderr)


def log_llm_call(
    stage_name: str,
    call_type: str,
    model_name: str,
    temperature: Optional[float],
    usage: Any,
    response_time_ms: int,
    call_status: str,
    *,
    request_id: Optional[str] = None,
    error_type: Optional[str] = None,
    error_message: Optional[str] = None,
) -> Optional[str]:
    """
    Log one LLM call to llm_call_performance. usage can be response.usage (object) or dict.
    Returns call_id (UUID string) for reference.
    """
    global _run_id, _llm_costs, _llm_cost_unknown
    if not _run_id:
        return None
    prompt_tokens, completion_tokens, total_tokens = _parse_usage(usage)
    cost_usd, cost_unknown = estimate_cost_usd(prompt_tokens, completion_tokens, model_name)
    if cost_usd is not None:
        _llm_costs.append(cost_usd)
    else:
        _llm_cost_unknown = cost_unknown
    call_id = str(uuid.uuid4())
    try:
        from core.generator_db import get_supabase_client
        supabase = get_supabase_client()
        row = {
            "call_id": call_id,
            "run_id": _run_id,
            "stage_name": stage_name,
            "call_type": call_type,
            "model_name": model_name,
            "temperature": temperature,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "request_id": request_id,
            "response_time_ms": response_time_ms,
            "call_status": call_status,
            "error_type": error_type,
            "error_message": error_message,
            "cost_usd_estimated_per_call": cost_usd,
            "cost_unknown_flag": cost_unknown,
        }
        supabase.table("llm_call_performance").insert(row).execute()
    except Exception as e:
        import sys
        print(f"[performance_logger] log_llm_call insert failed: {e}", file=sys.stderr)
    return call_id


def log_warning() -> None:
    global _warnings_count
    _warnings_count += 1


def log_error(stage_name: str, summary: str) -> None:
    global _errors_count, _first_error_stage, _first_error_summary
    _errors_count += 1
    if _first_error_stage is None:
        _first_error_stage = stage_name
        _first_error_summary = (summary or "")[:500]


def get_current_run_id() -> Optional[str]:
    return _run_id


def set_regression_result(run_id: str, regression_pass: bool, regression_fail_reason: Optional[str] = None) -> None:
    """Update run_performance with regression outcome (call from regression harness)."""
    try:
        from core.generator_db import get_supabase_client
        supabase = get_supabase_client()
        supabase.table("run_performance").update({
            "regression_pass": regression_pass,
            "regression_fail_reason": regression_fail_reason,
            "updated_at": _utc_now().isoformat(),
        }).eq("run_id", run_id).execute()
    except Exception:
        pass
