from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List


class StructuralCategory(str, Enum):
    CAPACITY_EXPANSION = "capacity_expansion"
    CAPACITY_REDUCTION_OR_SHUTDOWN = "capacity_reduction_or_shutdown"
    MERGERS_AND_ACQUISITIONS = "mergers_and_acquisitions"
    INVESTMENTS = "investments"
    JOINT_VENTURES_AND_STRATEGIC_PARTNERSHIPS = "joint_ventures_and_strategic_partnerships"
    REGULATION_AND_POLICY = "regulation_and_policy"
    SUSTAINABILITY_AND_CIRCULARITY = "sustainability_and_circularity"
    TECHNOLOGY_AND_INNOVATION = "technology_and_innovation"
    MARKET_AND_PRICING = "market_and_pricing"
    CORPORATE_STRATEGY_AND_RESTRUCTURING = "corporate_strategy_and_restructuring"
    DOWNSTREAM_APPLICATION_SHIFTS = "downstream_application_shifts"


DISPLAY_ORDER: List[StructuralCategory] = [
    StructuralCategory.CAPACITY_EXPANSION,
    StructuralCategory.CAPACITY_REDUCTION_OR_SHUTDOWN,
    StructuralCategory.MERGERS_AND_ACQUISITIONS,
    StructuralCategory.INVESTMENTS,
    StructuralCategory.JOINT_VENTURES_AND_STRATEGIC_PARTNERSHIPS,
    StructuralCategory.REGULATION_AND_POLICY,
    StructuralCategory.SUSTAINABILITY_AND_CIRCULARITY,
    StructuralCategory.TECHNOLOGY_AND_INNOVATION,
    StructuralCategory.MARKET_AND_PRICING,
    StructuralCategory.CORPORATE_STRATEGY_AND_RESTRUCTURING,
    StructuralCategory.DOWNSTREAM_APPLICATION_SHIFTS,
]


def all_structural_categories() -> List[StructuralCategory]:
    """Return all 11 structural categories in display order."""
    return list(DISPLAY_ORDER)


def category_from_string(value: str) -> StructuralCategory:
    """Parse category from a stable string representation."""
    try:
        return StructuralCategory(value)
    except ValueError as exc:
        raise ValueError(f"Unknown structural category: {value}") from exc


def category_to_string(category: StructuralCategory) -> str:
    """Serialize category to a stable string representation."""
    return category.value


@dataclass(frozen=True)
class CategoryDisplayInfo:
    key: StructuralCategory
    label: str


DISPLAY_INFO: List[CategoryDisplayInfo] = [
    CategoryDisplayInfo(StructuralCategory.CAPACITY_EXPANSION, "Capacity Expansion"),
    CategoryDisplayInfo(StructuralCategory.CAPACITY_REDUCTION_OR_SHUTDOWN, "Capacity Reduction or Shutdown"),
    CategoryDisplayInfo(StructuralCategory.MERGERS_AND_ACQUISITIONS, "Mergers and Acquisitions"),
    CategoryDisplayInfo(StructuralCategory.INVESTMENTS, "Investments"),
    CategoryDisplayInfo(
        StructuralCategory.JOINT_VENTURES_AND_STRATEGIC_PARTNERSHIPS,
        "Joint Ventures and Strategic Partnerships",
    ),
    CategoryDisplayInfo(StructuralCategory.REGULATION_AND_POLICY, "Regulation and Policy"),
    CategoryDisplayInfo(StructuralCategory.SUSTAINABILITY_AND_CIRCULARITY, "Sustainability and Circularity"),
    CategoryDisplayInfo(StructuralCategory.TECHNOLOGY_AND_INNOVATION, "Technology and Innovation"),
    CategoryDisplayInfo(StructuralCategory.MARKET_AND_PRICING, "Market and Pricing"),
    CategoryDisplayInfo(
        StructuralCategory.CORPORATE_STRATEGY_AND_RESTRUCTURING,
        "Corporate Strategy and Restructuring",
    ),
    CategoryDisplayInfo(
        StructuralCategory.DOWNSTREAM_APPLICATION_SHIFTS,
        "Downstream Application Shifts",
    ),
]


def display_label(category: StructuralCategory) -> str:
    """Return human-readable label for a category."""
    for info in DISPLAY_INFO:
        if info.key is category:
            return info.label
    return category.value

