"""
Phase 8 – Versioned pricing map for cost estimation.
Keyed by model_name; if model not in map, store cost as NULL and set cost_unknown_flag.
Do not hardcode one model; use the model_name field as the key.
"""

from typing import Optional, Tuple

# Version for auditing
PRICING_VERSION = "1.0"

# USD per 1M tokens (input, output). Keep in sync with OpenAI pricing page.
# Keys are base model names; API may return e.g. gpt-4o-2024-11-20 -> match gpt-4o.
PRICING_PER_1M_TOKENS = {
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-4": {"input": 30.00, "output": 60.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
}


def normalize_model_for_pricing(model: str) -> str:
    """Map API model id to a pricing key (e.g. gpt-4o-2024-11-20 -> gpt-4o)."""
    if not model or not isinstance(model, str):
        return ""
    m = model.strip().lower()
    for key in PRICING_PER_1M_TOKENS:
        if m == key or m.startswith(key + "-") or m.startswith(key + ":"):
            return key
    return ""


def estimate_cost_usd(
    prompt_tokens: int, completion_tokens: int, model_name: str
) -> Tuple[Optional[float], bool]:
    """Returns (cost_usd_estimated or None, cost_unknown_flag). If model not in map: (None, True)."""
    key = normalize_model_for_pricing(model_name)
    if not key:
        return None, True
    pricing = PRICING_PER_1M_TOKENS.get(key)
    if not pricing:
        return None, True
    try:
        p = int(prompt_tokens) if prompt_tokens is not None else 0
        c = int(completion_tokens) if completion_tokens is not None else 0
    except (TypeError, ValueError):
        return None, True
    cost = (p / 1_000_000 * pricing["input"]) + (c / 1_000_000 * pricing["output"])
    return round(cost, 6), False
