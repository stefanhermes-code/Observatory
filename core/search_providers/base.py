"""
Search provider interface for V2 Evidence Engine.
Implementations return list of candidates: url, title, snippet, published_at (optional), source_name.
Callers should pass reference_date and lookback_days so the provider can request recent results
(app date, not model date).
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class SearchProvider(ABC):
    """Abstract search provider. Execute search returns list of candidate items."""

    @abstractmethod
    def search(
        self,
        query: str,
        max_results: int = 10,
        *,
        reference_date: Optional[Any] = None,
        lookback_days: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Execute a single search query.
        reference_date: app "today" (datetime); provider should inject into prompt so model uses correct date.
        lookback_days: prefer results from the last N days (cadence-based).
        Returns list of dicts: url, title, snippet, published_at (optional), source_name.
        """
        pass
