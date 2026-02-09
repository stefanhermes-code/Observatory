"""
OpenAI web search provider for V2 Evidence Engine.
Uses OpenAI Responses API / web search tool to run queries and return candidates.
Injects app date and recency into the prompt so the model uses correct "today" (not its own wrong date).
"""

from typing import List, Dict, Any, Optional
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
) -> List[Dict[str, Any]]:
    """
    Use OpenAI with web search to get results. Returns list of {url, title, snippet, published_at?, source_name}.
    Injects today's date and recency so the model does not use its own (possibly wrong) date.
    """
    client = _get_client()
    if not client:
        return []
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
        # Parse response for citations / search results (structure may vary)
        for item in getattr(response, "output", []) or []:
            if getattr(item, "type", None) == "message" and getattr(item, "content", None):
                for block in item.content:
                    if getattr(block, "type", None) == "output_text":
                        text = getattr(block, "text", "") or ""
                        # Try to extract URLs from citations if present
                        if hasattr(block, "citations"):
                            for c in getattr(block, "citations", []) or []:
                                url = getattr(c, "url", None) or (c.get("url") if isinstance(c, dict) else None)
                                title = getattr(c, "title", None) or (c.get("title") if isinstance(c, dict) else None)
                                if url:
                                    out.append({
                                        "url": url,
                                        "title": title,
                                        "snippet": (text[:300] if text else None),
                                        "published_at": None,
                                        "source_name": "web_search",
                                    })
                                    if len(out) >= max_results:
                                        return out
        # If no citations, try to parse URLs from output text
        for item in getattr(response, "output", []) or []:
            if getattr(item, "type", None) == "message" and getattr(item, "content", None):
                for block in item.content:
                    if getattr(block, "type", None) == "output_text":
                        text = getattr(block, "text", "") or ""
                        import re
                        for m in re.finditer(r"https?://[^\s\)\]\"]+", text):
                            url = m.group(0).rstrip(".,;")
                            if len(out) < max_results and url not in [x.get("url") for x in out]:
                                out.append({
                                    "url": url,
                                    "title": None,
                                    "snippet": text[:300] if text else None,
                                    "published_at": None,
                                    "source_name": "web_search",
                                })
        return out[:max_results]
    except Exception:
        return []


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
