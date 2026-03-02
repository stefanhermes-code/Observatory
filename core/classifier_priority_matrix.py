from __future__ import annotations

from dataclasses import dataclass
from typing import List, Pattern
import re

from core.structural_categories import StructuralCategory


@dataclass(frozen=True)
class ClassificationRule:
    """
    Deterministic rule definition.

    - pattern: compiled regex matched against combined text fields (e.g. title, snippet, metadata).
    - category: structural category assigned when the rule matches.
    - description: short human-readable explanation used in logs and diagnostics.
    """

    pattern: Pattern[str]
    category: StructuralCategory
    description: str


def _rule(pattern: str, category: StructuralCategory, description: str) -> ClassificationRule:
    return ClassificationRule(re.compile(pattern, flags=re.IGNORECASE), category, description)


# Ordered list: first matching rule determines the primary category.
PRIORITY_RULES: List[ClassificationRule] = [
    # Capacity Expansion
    _rule(r"\b(capacity (expansion|increase|ramp[- ]up)|new plant|debottlenecking)\b", StructuralCategory.CAPACITY_EXPANSION, "Capacity expansion / new plant"),
    # Capacity Reduction or Shutdown
    _rule(r"\b(plant (closure|shutdown)|capacity (reduction|cut)|idling of capacity)\b", StructuralCategory.CAPACITY_REDUCTION_OR_SHUTDOWN, "Shutdown or capacity reduction"),
    # Mergers and Acquisitions
    _rule(r"\b(acquisition|acquires|merger|merges with|takeover)\b", StructuralCategory.MERGERS_AND_ACQUISITIONS, "Mergers and acquisitions"),
    # Investments
    _rule(r"\b(capex|capital expenditure|invest(s|ment) in|investment plan)\b", StructuralCategory.INVESTMENTS, "Investments / capex"),
    # Joint Ventures and Strategic Partnerships
    _rule(r"\b(joint venture|JV|strategic partnership|collaboration agreement)\b", StructuralCategory.JOINT_VENTURES_AND_STRATEGIC_PARTNERSHIPS, "Joint ventures and partnerships"),
    # Regulation and Policy
    _rule(r"\b(regulation|policy|legislation|ban on|REACH|compliance requirement)\b", StructuralCategory.REGULATION_AND_POLICY, "Regulation and policy"),
    # Sustainability and Circularity
    _rule(r"\b(recycling|circular( economy)?|bio[- ]based|low carbon|decarbonization|net zero)\b", StructuralCategory.SUSTAINABILITY_AND_CIRCULARITY, "Sustainability and circularity"),
    # Technology and Innovation
    _rule(r"\b(new technology|innovation|R&D|patent|novel (process|material))\b", StructuralCategory.TECHNOLOGY_AND_INNOVATION, "Technology and innovation"),
    # Market and Pricing
    _rule(r"\b(price (increase|hike|decrease|drop)|market (outlook|forecast)|demand (rise|fall))\b", StructuralCategory.MARKET_AND_PRICING, "Market and pricing"),
    # Corporate Strategy and Restructuring
    _rule(r"\b(restructuring|spin[- ]off|divest(s|iture)|strategic review)\b", StructuralCategory.CORPORATE_STRATEGY_AND_RESTRUCTURING, "Corporate strategy and restructuring"),
    # Downstream Application Shifts
    _rule(r"\b(applications? in|end[- ]use|downstream (shift|trend))\b", StructuralCategory.DOWNSTREAM_APPLICATION_SHIFTS, "Downstream application shifts"),
]


def classifier_priority_matrix() -> List[ClassificationRule]:
    """
    Return the ordered list of classification rules.

    This must not be modified at runtime; callers should treat the result as read-only.
    """
    return list(PRIORITY_RULES)

