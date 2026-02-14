"""
Token usage tracking and cost calculation for OpenAI API usage.
Supports both Assistant API and Response API metadata shapes.
"""

from typing import List, Dict, Optional, Tuple
from datetime import datetime
from core.admin_db import get_supabase_client


# OpenAI pricing per 1M tokens (Assistant and Response API; check OpenAI pricing page for current rates)
PRICING_PER_1M_TOKENS = {
    "gpt-4o": {
        "input": 2.50,
        "output": 10.00
    },
    "gpt-4o-mini": {
        "input": 0.15,
        "output": 0.60
    },
    "gpt-4-turbo": {
        "input": 10.00,
        "output": 30.00
    },
    "gpt-4": {
        "input": 30.00,
        "output": 60.00
    },
    "gpt-3.5-turbo": {
        "input": 0.50,
        "output": 1.50
    }
}

DEFAULT_PRICING = PRICING_PER_1M_TOKENS["gpt-4o"]


def _normalize_model_for_pricing(model: str) -> str:
    """Map API model id to a pricing key (e.g. gpt-4o-2024-11-20 -> gpt-4o)."""
    if not model or model == "unknown":
        return "gpt-4o"
    m = (model or "").strip().lower()
    for key in PRICING_PER_1M_TOKENS:
        if m == key or m.startswith(key + "-") or m.startswith(key + ":"):
            return key
    return "gpt-4o"


def _extract_token_usage_from_metadata(metadata: Dict) -> Tuple[int, Optional[int], Optional[int], str, Optional[float]]:
    """
    Extract token usage from run metadata. Supports:
    - Assistant API: metadata.tokens_used, metadata.model
    - Response API (flat): metadata.input_tokens, metadata.output_tokens; or metadata.total_tokens
    - Response API (nested): metadata.usage.input_tokens, metadata.usage.output_tokens
    - Optional: metadata.estimated_cost or metadata.cost (use when present for display)
    Returns: (total_tokens, input_tokens or None, output_tokens or None, model, stored_cost or None)
    """
    if not metadata or not isinstance(metadata, dict):
        return (0, None, None, "unknown", None)
    # Stored cost from generator (Response/Assistant may write this)
    stored_cost = metadata.get("estimated_cost")
    if stored_cost is None:
        stored_cost = metadata.get("cost")
    if stored_cost is not None and not isinstance(stored_cost, (int, float)):
        stored_cost = None
    model = (metadata.get("model") or "unknown").strip() or "unknown"
    # Nested usage (Response API)
    usage = metadata.get("usage")
    if isinstance(usage, dict):
        inp = usage.get("input_tokens")
        out = usage.get("output_tokens")
        total = usage.get("total_tokens")
        if inp is not None or out is not None:
            inp = int(inp) if inp is not None else 0
            out = int(out) if out is not None else 0
            total = total if total is not None else (inp + out)
            return (int(total), inp, out, model, stored_cost)
        if total is not None:
            return (int(total), None, None, model, stored_cost)
    # Flat: input_tokens / output_tokens (Response API flat)
    inp = metadata.get("input_tokens")
    out = metadata.get("output_tokens")
    if inp is not None or out is not None:
        inp = int(inp) if inp is not None else 0
        out = int(out) if out is not None else 0
        total = metadata.get("total_tokens")
        total = int(total) if total is not None else (inp + out)
        return (total, inp, out, model, stored_cost)
    # Legacy: tokens_used (Assistant API)
    tokens_used = metadata.get("tokens_used")
    if tokens_used is not None:
        return (int(tokens_used), None, None, model, stored_cost)
    return (0, None, None, "unknown", None)


def get_token_usage_by_workspace(workspace_id: Optional[str] = None, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None, limit: int = 10000) -> Dict:
    """
    Get token usage aggregated by workspace (company).
    
    Args:
        workspace_id: Optional workspace ID to filter by. If None, returns all workspaces.
        start_date: Optional start date to filter runs
        end_date: Optional end date to filter runs
        limit: Maximum number of runs to process (default 10000 to prevent timeout)
    
    Returns:
        Dictionary with workspace_id as key and token stats as value
    """
    supabase = get_supabase_client()
    
    try:
        # Build query with limit to prevent timeout
        query = supabase.table("newsletter_runs").select("workspace_id, metadata, created_at")
        
        if workspace_id:
            query = query.eq("workspace_id", workspace_id)
        
        if start_date:
            query = query.gte("created_at", start_date.isoformat())
        
        if end_date:
            query = query.lte("created_at", end_date.isoformat())
        
        # Only get successful runs (they have token data)
        query = query.eq("status", "success")
        
        # Order by created_at desc and limit to prevent timeout
        query = query.order("created_at", desc=True).limit(limit)
        
        result = query.execute()
        runs = result.data if result.data else []
    except Exception as e:
        # If query fails (e.g., timeout), return empty dict
        print(f"Warning: Could not fetch token usage data: {e}")
        return {}
    
    # Aggregate by workspace
    workspace_stats = {}
    
    for run in runs:
        ws_id = run.get("workspace_id")
        if not ws_id:
            continue

        metadata = run.get("metadata", {})
        if isinstance(metadata, str):
            import json
            try:
                metadata = json.loads(metadata)
            except Exception:
                metadata = {}

        total_tokens, input_tokens, output_tokens, model, stored_cost = _extract_token_usage_from_metadata(metadata)
        if total_tokens <= 0:
            continue

        model_key = _normalize_model_for_pricing(model)
        if ws_id not in workspace_stats:
            workspace_stats[ws_id] = {
                "total_tokens": 0,
                "run_count": 0,
                "models": {},
                "estimated_cost": 0.0
            }

        workspace_stats[ws_id]["total_tokens"] += total_tokens
        workspace_stats[ws_id]["run_count"] += 1

        if model not in workspace_stats[ws_id]["models"]:
            workspace_stats[ws_id]["models"][model] = {"tokens": 0, "runs": 0}
        workspace_stats[ws_id]["models"][model]["tokens"] += total_tokens
        workspace_stats[ws_id]["models"][model]["runs"] += 1

        # Cost: use stored cost from metadata if present, else compute from actual or estimated split
        if stored_cost is not None and stored_cost >= 0:
            workspace_stats[ws_id]["estimated_cost"] += float(stored_cost)
        else:
            pricing = PRICING_PER_1M_TOKENS.get(model_key, DEFAULT_PRICING)
            if input_tokens is not None and output_tokens is not None:
                cost = (input_tokens / 1_000_000 * pricing["input"]) + (output_tokens / 1_000_000 * pricing["output"])
            else:
                inp_est = int(total_tokens * 0.8)
                out_est = int(total_tokens * 0.2)
                cost = (inp_est / 1_000_000 * pricing["input"]) + (out_est / 1_000_000 * pricing["output"])
            workspace_stats[ws_id]["estimated_cost"] += cost

    return workspace_stats


def get_token_usage_summary(start_date: Optional[datetime] = None, end_date: Optional[datetime] = None, limit: int = 10000) -> Dict:
    """
    Get overall token usage summary across all workspaces.
    
    Args:
        start_date: Optional start date to filter runs
        end_date: Optional end date to filter runs
        limit: Maximum number of runs to process (default 10000 to prevent timeout)
    
    Returns:
        Dictionary with total tokens, total runs, total cost, etc.
    """
    try:
        workspace_stats = get_token_usage_by_workspace(start_date=start_date, end_date=end_date, limit=limit)
    except Exception as e:
        # Return empty summary if query fails
        return {
            "total_tokens": 0,
            "total_runs": 0,
            "total_cost": 0.0,
            "workspace_count": 0,
            "model_breakdown": {},
            "workspace_details": {},
            "error": str(e),
            "limit_reached": True
        }
    
    total_tokens = sum(ws["total_tokens"] for ws in workspace_stats.values())
    total_runs = sum(ws["run_count"] for ws in workspace_stats.values())
    total_cost = sum(ws["estimated_cost"] for ws in workspace_stats.values())
    
    # Aggregate by model
    model_stats = {}
    for ws_stats in workspace_stats.values():
        for model, stats in ws_stats["models"].items():
            if model not in model_stats:
                model_stats[model] = {"tokens": 0, "runs": 0}
            model_stats[model]["tokens"] += stats["tokens"]
            model_stats[model]["runs"] += stats["runs"]
    
    return {
        "total_tokens": total_tokens,
        "total_runs": total_runs,
        "total_cost": total_cost,
        "workspace_count": len(workspace_stats),
        "model_breakdown": model_stats,
        "workspace_details": workspace_stats
    }


def format_token_cost(tokens: int, model: str = "gpt-4o") -> Dict:
    """
    Calculate and format cost for a given number of tokens.
    
    Returns:
        Dictionary with input_cost, output_cost, total_cost, breakdown
    """
    pricing = PRICING_PER_1M_TOKENS.get(model, DEFAULT_PRICING)
    
    # Estimate: 80% input, 20% output (typical for generation tasks)
    input_tokens = int(tokens * 0.8)
    output_tokens = int(tokens * 0.2)
    
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    total_cost = input_cost + output_cost
    
    return {
        "tokens": tokens,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "input_cost": input_cost,
        "output_cost": output_cost,
        "total_cost": total_cost,
        "model": model,
        "pricing_per_1M_input": pricing["input"],
        "pricing_per_1M_output": pricing["output"]
    }

