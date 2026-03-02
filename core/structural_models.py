from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, List, Literal, Optional

from core.structural_categories import StructuralCategory


SourceType = Literal["lane_a", "lane_b", "lane_c"]
ClassificationSource = Literal["rule", "llm"]


@dataclass
class EvidenceItem:
    """
    Unified evidence representation for all intake lanes.
    """

    id: str
    source_type: SourceType
    title: str
    url: str
    snippet: Optional[str]
    published_at: Optional[datetime]
    ingested_at: datetime
    region_tags: List[str]
    raw_metadata: Dict[str, object]

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass
class ClassificationResult:
    """
    Structural classification result for a single evidence item.
    """

    evidence_id: str
    primary_category: StructuralCategory
    secondary_categories: List[StructuralCategory]
    classification_source: ClassificationSource

    def to_dict(self) -> Dict[str, object]:
        data = asdict(self)
        data["primary_category"] = self.primary_category.value
        data["secondary_categories"] = [c.value for c in self.secondary_categories]
        return data


@dataclass
class StructuralSignal:
    """
    Aggregated structural signal built from one or more evidence items.
    """

    id: str
    title: str
    structural_interpretation: str
    primary_category: StructuralCategory
    regions: List[str]
    companies: List[str]
    confidence_level: float
    evidence_ids: List[str]
    evidence_count: int

    def to_dict(self) -> Dict[str, object]:
        data = asdict(self)
        data["primary_category"] = self.primary_category.value
        return data

