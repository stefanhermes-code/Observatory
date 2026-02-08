"""
Search provider interface for V2 Evidence Engine.
Implementations return list of candidates: url, title, snippet, published_at (optional), source_name.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any


class SearchProvider(ABC):
    """Abstract search provider. Execute search returns list of candidate items."""

    @abstractmethod
    def search(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Execute a single search query.
        Returns list of dicts: url, title, snippet, published_at (optional), source_name.
        """
        pass
