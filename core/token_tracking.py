"""
Token usage tracking and cost calculation for OpenAI API usage.
"""

from typing import List, Dict, Optional
from datetime import datetime
from core.admin_db import get_supabase_client


# OpenAI Assistant API Pricing (as of 2024)
# Note: These are approximate - check OpenAI pricing page for current rates
PRICING_PER_1M_TOKENS = {
    "gpt-4o": {
        "input": 2.50,   # $2.50 per 1M input tokens
        "output": 10.00  # $10.00 per 1M output tokens
    },
    "gpt-4-turbo": {
        "input": 10.00,  # $10.00 per 1M input tokens
        "output": 30.00  # $30.00 per 1M output tokens
    },
    "gpt-4": {
        "input": 30.00,  # $30.00 per 1M input tokens
        "output": 60.00  # $60.00 per 1M output tokens
    },
    "gpt-3.5-turbo": {
        "input": 0.50,   # $0.50 per 1M input tokens
        "output": 1.50   # $1.50 per 1M output tokens
    }
}

# Default pricing if model not found (use gpt-4o as default)
DEFAULT_PRICING = PRICING_PER_1M_TOKENS["gpt-4o"]


def get_token_usage_by_workspace(workspace_id: Optional[str] = None, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> Dict:
    """
    Get token usage aggregated by workspace (company).
    
    Args:
        workspace_id: Optional workspace ID to filter by. If None, returns all workspaces.
        start_date: Optional start date to filter runs
        end_date: Optional end date to filter runs
    
    Returns:
        Dictionary with workspace_id as key and token stats as value
    """
    supabase = get_supabase_client()
    
    # Build query
    query = supabase.table("newsletter_runs").select("workspace_id, metadata, created_at")
    
    if workspace_id:
        query = query.eq("workspace_id", workspace_id)
    
    if start_date:
        query = query.gte("created_at", start_date.isoformat())
    
    if end_date:
        query = query.lte("created_at", end_date.isoformat())
    
    # Only get successful runs (they have token data)
    query = query.eq("status", "success")
    
    result = query.execute()
    runs = result.data if result.data else []
    
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
            except:
                metadata = {}
        
        tokens_used = metadata.get("tokens_used", 0)
        model = metadata.get("model", "unknown")
        
        if ws_id not in workspace_stats:
            workspace_stats[ws_id] = {
                "total_tokens": 0,
                "run_count": 0,
                "models": {},
                "estimated_cost": 0.0
            }
        
        workspace_stats[ws_id]["total_tokens"] += tokens_used
        workspace_stats[ws_id]["run_count"] += 1
        
        # Track model usage
        if model not in workspace_stats[ws_id]["models"]:
            workspace_stats[ws_id]["models"][model] = {"tokens": 0, "runs": 0}
        workspace_stats[ws_id]["models"][model]["tokens"] += tokens_used
        workspace_stats[ws_id]["models"][model]["runs"] += 1
        
        # Calculate estimated cost (using total tokens, assuming 80% input, 20% output)
        pricing = PRICING_PER_1M_TOKENS.get(model, DEFAULT_PRICING)
        input_tokens = int(tokens_used * 0.8)
        output_tokens = int(tokens_used * 0.2)
        cost = (input_tokens / 1_000_000 * pricing["input"]) + (output_tokens / 1_000_000 * pricing["output"])
        workspace_stats[ws_id]["estimated_cost"] += cost
    
    return workspace_stats


def get_token_usage_summary(start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> Dict:
    """
    Get overall token usage summary across all workspaces.
    
    Returns:
        Dictionary with total tokens, total runs, total cost, etc.
    """
    workspace_stats = get_token_usage_by_workspace(start_date=start_date, end_date=end_date)
    
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

