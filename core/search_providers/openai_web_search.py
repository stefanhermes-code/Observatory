"""
OpenAI web search provider for V2 Evidence Engine.
Uses OpenAI Responses API / web search tool to run queries and return candidates.
Injects app date and recency into the prompt so the model uses correct "today" (not its own wrong date).
"""

from typing import Any, List, Dict, Optional
from datetime import datetime
import os

try:
    from openai import OpenAI
    _HAS_OPENAI = True
except ImportError:
    _HAS_OPENAI = False

from core.search_providers.base import SearchProvider


def _get_client():
    try:
        import streamlit as st
        api_key = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
    except Exception:
        api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or not _HAS_OPENAI:
        return None
    return OpenAI(api_key=api_key)


def _run_web_search(
    query: str,
    max_results: int = 10,
    reference_date: Optional[datetime] = None,
    lookback_days: Optional[int] = None,
) -> tuple:
    """
    Use OpenAI with web search to get results.
    Returns (list of {url, title, snippet, published_at?, source_name}, usage_dict or None).
    usage_dict: input_tokens, output_tokens, total_tokens, model for Admin cost tracking.
    """
    client = _get_client()
    if not client:
        return [], None
    ref = reference_date or datetime.utcnow()
    today_str = ref.strftime("%Y-%m-%d")
    recency = (
        f" Prefer articles from the past {lookback_days} days (since {lookback_days} days before {today_str})."
        if lookback_days is not None and lookback_days > 0
        else ""
    )
    user_content = (
        f"Today's date is {today_str}. Search the web for: {query}.{recency} "
        "Return a list of relevant article URLs with title and short snippet. Only return factual search results."
    )
    try:
        response = client.responses.create(
            model="gpt-4o",
            input=[{"role": "user", "content": user_content}],
            tools=[{"type": "web_search"}],
        )
        out: List[Dict[str, Any]] = []

        # Parse response for URL citations first (modern Responses + web_search shape).
        # We look for message/output_text blocks and use their annotations (type=url_citation)
        # as the primary source of URLs and titles. Snippet comes from the output_text text.
        primary_snippet_text: Optional[str] = None

        for item in getattr(response, "output", []) or []:
            if getattr(item, "type", None) != "message" or not getattr(item, "content", None):
                continue
            for block in getattr(item, "content", []) or []:
                if getattr(block, "type", None) != "output_text":
                    continue
                text = getattr(block, "text", "") or ""
                if text and primary_snippet_text is None:
                    primary_snippet_text = text

                # Newer API: citations live in annotations as url_citation objects
                annotations = getattr(block, "annotations", None) or getattr(block, "_annotations", None)
                if annotations is None and isinstance(block, dict):
                    annotations = block.get("annotations") or block.get("_annotations")
                annotations = annotations or []

                for ann in annotations:
                    ann_type = getattr(ann, "type", None) or (ann.get("type") if isinstance(ann, dict) else None)
                    if ann_type != "url_citation":
                        continue

                    # url_citation may be nested or flat; handle both.
                    uc = getattr(ann, "url_citation", None) or (ann.get("url_citation") if isinstance(ann, dict) else None) or ann
                    url = (
                        getattr(uc, "url", None)
                        or (uc.get("url") if isinstance(uc, dict) else None)
                    )
                    title = (
                        getattr(uc, "title", None)
                        or (uc.get("title") if isinstance(uc, dict) else None)
                    )
                    if not url:
                        continue
                    if url in [x.get("url") for x in out]:
                        continue
                    out.append(
                        {
                            "url": url,
                            "title": title,
                            "snippet": (text[:300] if text else None),
                            "published_at": None,
                            "source_name": "web_search",
                        }
                    )
                    if len(out) >= max_results:
                        return _out_with_usage(out[:max_results], response)

        # Fallback: try to parse plain URLs from the output_text text if no annotations.
        if not out:
            import re

            for item in getattr(response, "output", []) or []:
                if getattr(item, "type", None) != "message" or not getattr(item, "content", None):
                    continue
                for block in getattr(item, "content", []) or []:
                    if getattr(block, "type", None) != "output_text":
                        continue
                    text = getattr(block, "text", "") or ""
                    if text and primary_snippet_text is None:
                        primary_snippet_text = text
                    for m in re.finditer(r"https?://[^\s\)\]\"]+", text or ""):
                        url = m.group(0).rstrip(".,;")
                        if url in [x.get("url") for x in out]:
                            continue
                        out.append(
                            {
                                "url": url,
                                "title": None,
                                "snippet": (text[:300] if text else None),
                                "published_at": None,
                                "source_name": "web_search",
                            }
                        )
                        if len(out) >= max_results:
                            return _out_with_usage(out[:max_results], response)

        return _out_with_usage(out[:max_results], response)
    except Exception:
        return [], None


def _out_with_usage(out: List[Dict[str, Any]], response: Any) -> tuple:
    """Build (results, usage_dict) from Responses API response."""
    usage_dict = None
    u = getattr(response, "usage", None)
    if u is not None:
        inp = getattr(u, "input_tokens", None) or getattr(u, "prompt_tokens", 0)
        out_tok = getattr(u, "output_tokens", None) or getattr(u, "completion_tokens", 0)
        total = getattr(u, "total_tokens", None)
        if total is None and (inp is not None or out_tok is not None):
            total = (inp or 0) + (out_tok or 0)
        usage_dict = {
            "input_tokens": inp or 0,
            "output_tokens": out_tok or 0,
            "total_tokens": total or 0,
            "model": getattr(response, "model", None) or "gpt-4o",
        }
    return (out, usage_dict)


class OpenAIWebSearchProvider(SearchProvider):
    """Search provider using OpenAI web search tool. Injects app date and recency into prompt."""

    def search(
        self,
        query: str,
        max_results: int = 10,
        *,
        reference_date: Optional[datetime] = None,
        lookback_days: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        return _run_web_search(
            query,
            max_results=max_results,
            reference_date=reference_date,
            lookback_days=lookback_days,
        )
