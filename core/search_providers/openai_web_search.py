"""
OpenAI web search provider for V2 Evidence Engine.
Uses OpenAI Responses API / web search tool to run queries and return candidates.
Falls back to no-op (empty list) if not configured or tool not available.
"""

from typing import List, Dict, Any
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


def _run_web_search(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Use OpenAI with web search to get results. Returns list of {url, title, snippet, published_at?, source_name}.
    If Responses API with web_search is not available, returns [].
    """
    client = _get_client()
    if not client:
        return []
    try:
        # Use Responses API with web_search tool (model that supports it)
        response = client.responses.create(
            model="gpt-4o",
            input=[{"role": "user", "content": f"Search the web for: {query}. Return a list of relevant article URLs with title and short snippet. Only return factual search results."}],
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
    """Search provider using OpenAI web search tool."""

    def search(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        return _run_web_search(query, max_results=max_results)
